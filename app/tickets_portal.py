import os
import secrets
import threading
from datetime import date, datetime

from flask import Blueprint, current_app, jsonify, redirect, render_template, request, session, url_for
from werkzeug.utils import secure_filename

from .db import get_db_connection

TICKET_ALLOWED_TYPES = {"normal", "superticket"}
TICKET_ALLOWED_PRIORITIES = {"baja", "media", "alta", "critica"}
TICKET_ALLOWED_STATUSES = {"abierto", "en_proceso", "resuelto", "cerrado"}
TICKET_ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
TICKET_MAX_ATTACHMENTS = 5

_ticket_schema_lock = threading.Lock()
_ticket_schema_ready = False
_auth_system = None


def create_tickets_blueprint(auth_system):
    global _auth_system
    _auth_system = auth_system

    tickets_bp = Blueprint("tickets_portal", __name__)

    @tickets_bp.route("/portal-tickets")
    def portal_tickets():
        auth_response, user_context = _require_ticket_login()
        if auth_response is not None:
            return auth_response

        _ensure_ticket_tables()

        return render_template(
            "portal_tickets.html",
            ticket_bootstrap={
                "current_user": {
                    "username": user_context["username"],
                    "display_name": user_context["display_name"],
                    "roles": user_context["roles"],
                    "primary_role": user_context["primary_role"],
                    "is_superadmin": user_context["is_superadmin"],
                },
                "allowed_statuses": list(TICKET_ALLOWED_STATUSES),
                "allowed_priorities": list(TICKET_ALLOWED_PRIORITIES),
                "allowed_types": list(TICKET_ALLOWED_TYPES),
            },
        )

    @tickets_bp.route("/api/tickets", methods=["GET", "POST"])
    def api_tickets():
        auth_response, user_context = _require_ticket_login(api=True)
        if auth_response is not None:
            return auth_response

        _ensure_ticket_tables()

        if request.method == "GET":
            return _handle_list_tickets(user_context)

        return _handle_create_ticket(user_context)

    @tickets_bp.route("/api/tickets/<int:ticket_id>")
    def api_ticket_detail(ticket_id):
        auth_response, user_context = _require_ticket_login(api=True)
        if auth_response is not None:
            return auth_response

        _ensure_ticket_tables()

        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            ticket_row = _load_ticket_row(cursor, ticket_id)
            if not ticket_row:
                return jsonify({"success": False, "message": "Ticket no encontrado"}), 404

            ticket_payload = _ticket_payload(ticket_row, user_context)
            if not ticket_payload["permissions"]["can_view"]:
                return jsonify({"success": False, "message": "No tienes acceso a este ticket"}), 403

            messages = _load_ticket_messages(cursor, ticket_id, user_context)
            return jsonify({"success": True, "ticket": ticket_payload, "messages": messages})
        except Exception as exc:
            print(f"Error cargando detalle de ticket {ticket_id}: {exc}")
            return jsonify({"success": False, "message": "No fue posible cargar el ticket"}), 500
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    @tickets_bp.route("/api/tickets/<int:ticket_id>/reply", methods=["POST"])
    def api_ticket_reply(ticket_id):
        auth_response, user_context = _require_ticket_login(api=True)
        if auth_response is not None:
            return auth_response

        _ensure_ticket_tables()

        payload = _ticket_request_payload()
        message_body = _normalize_ticket_text(payload.get("message"), max_length=4000)
        if not message_body:
            return jsonify({"success": False, "message": "El mensaje es obligatorio"}), 400

        conn = None
        cursor = None
        saved_attachments = []
        try:
            attachments = _ticket_uploaded_images()
            conn = get_db_connection()
            cursor = conn.cursor()
            ticket_row = _load_ticket_row(cursor, ticket_id)
            if not ticket_row:
                return jsonify({"success": False, "message": "Ticket no encontrado"}), 404

            ticket_payload = _ticket_payload(ticket_row, user_context)
            permissions = ticket_payload["permissions"]

            if not permissions["can_view"]:
                return jsonify({"success": False, "message": "No tienes acceso a este ticket"}), 403

            if not permissions["can_reply"]:
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": "Solo superadmin puede contestar un superticket",
                        }
                    ),
                    403,
                )

            now_text = _ticket_now_text()
            cursor.execute(
                """
                INSERT INTO support_ticket_messages (
                    ticket_id,
                    author_username,
                    author_name,
                    author_role,
                    message_body,
                    created_at
                ) VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    ticket_id,
                    user_context["username"],
                    user_context["display_name"],
                    user_context["primary_role"],
                    message_body,
                    now_text,
                ),
            )
            message_id = cursor.lastrowid

            next_status = ticket_payload["status"]
            assigned_to_username = ticket_payload.get("assigned_to_username")
            assigned_to_name = ticket_payload.get("assigned_to_name")
            if user_context["is_superadmin"]:
                assigned_to_username = user_context["username"]
                assigned_to_name = user_context["display_name"]
                if next_status == "abierto":
                    next_status = "en_proceso"
            elif ticket_payload["ticket_type"] == "normal" and next_status in {"resuelto", "cerrado"}:
                next_status = "abierto"

            cursor.execute(
                """
                UPDATE support_tickets
                SET updated_at = %s,
                    last_message_at = %s,
                    last_message_preview = %s,
                    status = %s,
                    assigned_to_username = %s,
                    assigned_to_name = %s
                WHERE id = %s
                """,
                (
                    now_text,
                    now_text,
                    _ticket_preview(message_body),
                    next_status,
                    assigned_to_username,
                    assigned_to_name,
                    ticket_id,
                ),
            )

            saved_attachments = _ticket_save_attachments(
                cursor, ticket_id, ticket_payload["ticket_no"], message_id, attachments
            )
            conn.commit()

            _auth_system.registrar_auditoria(
                usuario=user_context["username"],
                modulo="tickets",
                accion="responder_ticket",
                descripcion=f"Respuesta registrada en ticket {ticket_payload['ticket_no']}",
                resultado="EXITOSO",
            )

            ticket_row = _load_ticket_row(cursor, ticket_id)
            return jsonify(
                {
                    "success": True,
                    "message": "Respuesta registrada",
                    "ticket": _ticket_payload(ticket_row, user_context),
                    "messages": _load_ticket_messages(cursor, ticket_id, user_context),
                }
            )
        except ValueError as exc:
            if conn:
                conn.rollback()
            for attachment in saved_attachments:
                try:
                    os.remove(attachment["path"])
                except OSError:
                    pass
            return jsonify({"success": False, "message": str(exc)}), 400
        except Exception as exc:
            if conn:
                conn.rollback()
            for attachment in saved_attachments:
                try:
                    os.remove(attachment["path"])
                except OSError:
                    pass
            print(f"Error respondiendo ticket {ticket_id}: {exc}")
            return jsonify({"success": False, "message": "No fue posible guardar la respuesta"}), 500
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    @tickets_bp.route("/api/tickets/<int:ticket_id>/status", methods=["POST"])
    def api_ticket_status(ticket_id):
        auth_response, user_context = _require_ticket_login(api=True)
        if auth_response is not None:
            return auth_response

        if not user_context["is_superadmin"]:
            return jsonify({"success": False, "message": "Solo superadmin puede cambiar estados"}), 403

        _ensure_ticket_tables()

        payload = request.get_json(silent=True) or request.form
        status_value = _normalize_ticket_text(payload.get("status"), max_length=32)
        comment = _normalize_ticket_text(payload.get("comment"), max_length=1000)

        if status_value not in TICKET_ALLOWED_STATUSES:
            return jsonify({"success": False, "message": "Estado de ticket no valido"}), 400

        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            ticket_row = _load_ticket_row(cursor, ticket_id)
            if not ticket_row:
                return jsonify({"success": False, "message": "Ticket no encontrado"}), 404

            now_text = _ticket_now_text()
            status_message = comment or f"Estado actualizado a {status_value}"
            resolved_at = now_text if status_value in {"resuelto", "cerrado"} else None
            closed_at = now_text if status_value == "cerrado" else None

            cursor.execute(
                """
                UPDATE support_tickets
                SET status = %s,
                    updated_at = %s,
                    last_message_at = %s,
                    last_message_preview = %s,
                    assigned_to_username = %s,
                    assigned_to_name = %s,
                    resolved_at = %s,
                    closed_at = %s
                WHERE id = %s
                """,
                (
                    status_value,
                    now_text,
                    now_text,
                    _ticket_preview(status_message),
                    user_context["username"],
                    user_context["display_name"],
                    resolved_at,
                    closed_at,
                    ticket_id,
                ),
            )

            cursor.execute(
                """
                INSERT INTO support_ticket_messages (
                    ticket_id,
                    author_username,
                    author_name,
                    author_role,
                    message_body,
                    created_at
                ) VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    ticket_id,
                    user_context["username"],
                    user_context["display_name"],
                    user_context["primary_role"],
                    status_message,
                    now_text,
                ),
            )

            conn.commit()

            ticket_row = _load_ticket_row(cursor, ticket_id)
            return jsonify(
                {
                    "success": True,
                    "message": "Estado actualizado",
                    "ticket": _ticket_payload(ticket_row, user_context),
                    "messages": _load_ticket_messages(cursor, ticket_id, user_context),
                }
            )
        except Exception as exc:
            if conn:
                conn.rollback()
            print(f"Error actualizando estado de ticket {ticket_id}: {exc}")
            return jsonify({"success": False, "message": "No fue posible actualizar el ticket"}), 500
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    return tickets_bp


def _require_ticket_login(api=False):
    user_context = _ticket_user_context()
    if user_context:
        return None, user_context

    if api:
        return jsonify({"success": False, "message": "Sesion expirada"}), None

    return redirect(url_for("inicio")), None


def _ticket_user_context():
    username = session.get("usuario")
    if not username:
        return None

    roles = session.get("roles")
    if not isinstance(roles, list) or not roles:
        roles = _auth_system.obtener_roles_usuario(username) or []
        session["roles"] = roles
        session["rol_principal"] = roles[0] if roles else None
        session.modified = True

    primary_role = session.get("rol_principal") or (roles[0] if roles else "usuario")
    return {
        "username": username,
        "display_name": session.get("nombre_completo") or username,
        "email": session.get("email") or "",
        "roles": roles,
        "primary_role": primary_role,
        "is_superadmin": "superadmin" in roles,
    }


def _ticket_now_text():
    return _auth_system.get_mexico_time_mysql()


def _ticket_preview(text, limit=220):
    if not text:
        return ""
    compact = " ".join(str(text).split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."


def _normalize_ticket_text(value, max_length=None):
    text = " ".join(str(value or "").strip().split())
    if max_length:
        text = text[:max_length].strip()
    return text


def _ticket_message_text(value, max_length=None):
    text = str(value or "").strip()
    if max_length:
        text = text[:max_length].strip()
    return text


def _ticket_request_payload():
    if request.is_json:
        return request.get_json(silent=True) or {}
    return request.form or {}


def _ticket_uploaded_images():
    files = []
    for file_storage in request.files.getlist("attachments"):
        if not file_storage or not getattr(file_storage, "filename", ""):
            continue
        files.append(file_storage)

    if len(files) > TICKET_MAX_ATTACHMENTS:
        raise ValueError(f"Solo puedes adjuntar hasta {TICKET_MAX_ATTACHMENTS} imagenes por mensaje")

    for file_storage in files:
        extension = os.path.splitext(file_storage.filename or "")[1].lower()
        if extension not in TICKET_ALLOWED_IMAGE_EXTENSIONS:
            raise ValueError("Solo se permiten archivos de imagen")

    return files


def _ticket_upload_dir():
    upload_dir = os.path.join(current_app.root_path, "static", "uploads", "tickets")
    os.makedirs(upload_dir, exist_ok=True)
    return upload_dir


def _ticket_save_attachments(cursor, ticket_id, ticket_no, message_id, files):
    if not files:
        return []

    saved_attachments = []
    upload_dir = _ticket_upload_dir()
    now_text = _ticket_now_text()

    try:
        for index, file_storage in enumerate(files, start=1):
            original_name = secure_filename(file_storage.filename or "imagen")
            extension = os.path.splitext(original_name)[1].lower()
            stored_name = f"{ticket_no}-{message_id}-{index}-{secrets.token_hex(4)}{extension}"
            absolute_path = os.path.join(upload_dir, stored_name)
            relative_url = f"/static/uploads/tickets/{stored_name}"

            file_storage.save(absolute_path)
            cursor.execute(
                """
                INSERT INTO support_ticket_attachments (
                    ticket_id,
                    message_id,
                    original_name,
                    stored_name,
                    file_url,
                    mime_type,
                    created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    ticket_id,
                    message_id,
                    original_name,
                    stored_name,
                    relative_url,
                    getattr(file_storage, "mimetype", "image/*"),
                    now_text,
                ),
            )
            saved_attachments.append({"path": absolute_path, "url": relative_url})
    except Exception:
        for attachment in saved_attachments:
            try:
                os.remove(attachment["path"])
            except OSError:
                pass
        raise

    return saved_attachments


def _ticket_number(ticket_type):
    prefix = "STK" if ticket_type == "superticket" else "TKT"
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{prefix}-{stamp}-{secrets.token_hex(2).upper()}"


def _ticket_json_row(row):
    if row is None:
        return None

    row_dict = dict(row)
    payload = {}
    for key, value in row_dict.items():
        if isinstance(value, datetime):
            payload[key] = value.strftime("%Y-%m-%d %H:%M:%S")
        elif isinstance(value, date):
            payload[key] = value.strftime("%Y-%m-%d")
        else:
            payload[key] = value
    return payload


def _ticket_permissions(ticket_row, user_context):
    requester_username = ticket_row.get("requester_username")
    is_owner = requester_username == user_context["username"]
    is_superadmin = user_context["is_superadmin"]
    can_view = is_superadmin or is_owner
    can_reply = False

    if can_view:
        if ticket_row.get("ticket_type") == "superticket":
            can_reply = is_superadmin
        else:
            can_reply = is_superadmin or is_owner

    return {
        "can_view": can_view,
        "can_reply": can_reply,
        "can_change_status": is_superadmin,
    }


def _ticket_payload(ticket_row, user_context):
    payload = _ticket_json_row(ticket_row)
    payload["permissions"] = _ticket_permissions(payload, user_context)
    payload["is_superticket"] = payload.get("ticket_type") == "superticket"
    return payload


def _load_ticket_row(cursor, ticket_id):
    cursor.execute(
        """
        SELECT
            t.id,
            t.ticket_no,
            t.title,
            t.description,
            t.ticket_type,
            t.category,
            t.priority,
            t.status,
            t.requester_username,
            t.requester_name,
            t.requester_email,
            t.assigned_to_username,
            t.assigned_to_name,
            t.last_message_preview,
            t.created_at,
            t.updated_at,
            t.last_message_at,
            t.resolved_at,
            t.closed_at,
            (
                SELECT COUNT(*)
                FROM support_ticket_messages m
                WHERE m.ticket_id = t.id
            ) AS message_count
        FROM support_tickets t
        WHERE t.id = %s
        """,
        (ticket_id,),
    )
    return cursor.fetchone()


def _load_ticket_messages(cursor, ticket_id, user_context):
    cursor.execute(
        """
        SELECT
            id,
            message_id,
            original_name,
            stored_name,
            file_url,
            mime_type,
            created_at
        FROM support_ticket_attachments
        WHERE ticket_id = %s
        ORDER BY id ASC
        """,
        (ticket_id,),
    )
    attachments_by_message = {}
    for row in cursor.fetchall() or []:
        payload = _ticket_json_row(row)
        attachments_by_message.setdefault(payload.get("message_id"), []).append(payload)

    cursor.execute(
        """
        SELECT
            id,
            ticket_id,
            author_username,
            author_name,
            author_role,
            message_body,
            created_at
        FROM support_ticket_messages
        WHERE ticket_id = %s
        ORDER BY created_at ASC, id ASC
        """,
        (ticket_id,),
    )
    messages = []
    for row in cursor.fetchall() or []:
        payload = _ticket_json_row(row)
        payload["is_current_user"] = payload.get("author_username") == user_context["username"]
        payload["is_superadmin_reply"] = payload.get("author_role") == "superadmin"
        payload["attachments"] = attachments_by_message.get(payload.get("id"), [])
        messages.append(payload)
    return messages


def _handle_list_tickets(user_context):
    status_filter = _normalize_ticket_text(request.args.get("status"), max_length=32)
    type_filter = _normalize_ticket_text(request.args.get("type"), max_length=32)
    scope = _normalize_ticket_text(request.args.get("scope"), max_length=16) or "mine"

    if status_filter and status_filter not in TICKET_ALLOWED_STATUSES:
        return jsonify({"success": False, "message": "Filtro de estado no valido"}), 400

    if type_filter and type_filter not in TICKET_ALLOWED_TYPES:
        return jsonify({"success": False, "message": "Filtro de tipo no valido"}), 400

    if not user_context["is_superadmin"]:
        scope = "mine"
    elif scope not in {"mine", "all"}:
        scope = "all"

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        sql = [
            """
            SELECT
                t.id,
                t.ticket_no,
                t.title,
                t.description,
                t.ticket_type,
                t.category,
                t.priority,
                t.status,
                t.requester_username,
                t.requester_name,
                t.requester_email,
                t.assigned_to_username,
                t.assigned_to_name,
                t.last_message_preview,
                t.created_at,
                t.updated_at,
                t.last_message_at,
                t.resolved_at,
                t.closed_at,
                (
                    SELECT COUNT(*)
                    FROM support_ticket_messages m
                    WHERE m.ticket_id = t.id
                ) AS message_count
            FROM support_tickets t
            WHERE 1 = 1
            """
        ]
        params = []

        if scope != "all":
            sql.append(" AND t.requester_username = %s")
            params.append(user_context["username"])

        if status_filter:
            sql.append(" AND t.status = %s")
            params.append(status_filter)

        if type_filter:
            sql.append(" AND t.ticket_type = %s")
            params.append(type_filter)

        sql.append(
            """
            ORDER BY
                CASE
                    WHEN t.status = 'abierto' THEN 0
                    WHEN t.status = 'en_proceso' THEN 1
                    WHEN t.status = 'resuelto' THEN 2
                    ELSE 3
                END,
                t.updated_at DESC
            LIMIT 200
            """
        )

        cursor.execute("".join(sql), tuple(params))
        tickets = [_ticket_payload(row, user_context) for row in cursor.fetchall() or []]
        summary = {
            "total": len(tickets),
            "open": sum(1 for ticket in tickets if ticket.get("status") == "abierto"),
            "in_progress": sum(1 for ticket in tickets if ticket.get("status") == "en_proceso"),
            "supertickets": sum(1 for ticket in tickets if ticket.get("ticket_type") == "superticket"),
        }

        return jsonify(
            {
                "success": True,
                "tickets": tickets,
                "summary": summary,
                "scope": scope,
            }
        )
    except Exception as exc:
        print(f"Error listando tickets: {exc}")
        return jsonify({"success": False, "message": "No fue posible cargar tickets"}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def _handle_create_ticket(user_context):
    payload = _ticket_request_payload()
    title = _normalize_ticket_text(payload.get("title"), max_length=180)
    description = _ticket_message_text(payload.get("description"), max_length=6000)
    category = _normalize_ticket_text(payload.get("category"), max_length=60) or "general"
    priority = _normalize_ticket_text(payload.get("priority"), max_length=16) or "media"
    ticket_type = _normalize_ticket_text(payload.get("ticket_type"), max_length=20) or "normal"

    if not title:
        return jsonify({"success": False, "message": "El titulo es obligatorio"}), 400

    if len(description) < 10:
        return jsonify({"success": False, "message": "La descripcion debe tener al menos 10 caracteres"}), 400

    if ticket_type not in TICKET_ALLOWED_TYPES:
        return jsonify({"success": False, "message": "Tipo de ticket no valido"}), 400

    if priority not in TICKET_ALLOWED_PRIORITIES:
        return jsonify({"success": False, "message": "Prioridad no valida"}), 400

    conn = None
    cursor = None
    saved_attachments = []
    try:
        attachments = _ticket_uploaded_images()
        conn = get_db_connection()
        cursor = conn.cursor()
        ticket_no = _ticket_number(ticket_type)
        now_text = _ticket_now_text()

        cursor.execute(
            """
            INSERT INTO support_tickets (
                ticket_no,
                requester_username,
                requester_name,
                requester_email,
                title,
                description,
                ticket_type,
                category,
                priority,
                status,
                created_at,
                updated_at,
                last_message_at,
                last_message_preview
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                ticket_no,
                user_context["username"],
                user_context["display_name"],
                user_context["email"],
                title,
                description,
                ticket_type,
                category,
                priority,
                "abierto",
                now_text,
                now_text,
                now_text,
                _ticket_preview(description),
            ),
        )
        ticket_id = cursor.lastrowid

        cursor.execute(
            """
            INSERT INTO support_ticket_messages (
                ticket_id,
                author_username,
                author_name,
                author_role,
                message_body,
                created_at
            ) VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                ticket_id,
                user_context["username"],
                user_context["display_name"],
                user_context["primary_role"],
                description,
                now_text,
            ),
        )
        message_id = cursor.lastrowid

        saved_attachments = _ticket_save_attachments(
            cursor, ticket_id, ticket_no, message_id, attachments
        )
        conn.commit()

        _auth_system.registrar_auditoria(
            usuario=user_context["username"],
            modulo="tickets",
            accion="crear_ticket",
            descripcion=f"Creacion de ticket {ticket_no}",
            resultado="EXITOSO",
        )

        ticket_row = _load_ticket_row(cursor, ticket_id)
        return (
            jsonify(
                {
                    "success": True,
                    "message": "Ticket creado correctamente",
                    "ticket": _ticket_payload(ticket_row, user_context),
                    "messages": _load_ticket_messages(cursor, ticket_id, user_context),
                }
            ),
            201,
        )
    except ValueError as exc:
        if conn:
            conn.rollback()
        for attachment in saved_attachments:
            try:
                os.remove(attachment["path"])
            except OSError:
                pass
        return jsonify({"success": False, "message": str(exc)}), 400
    except Exception as exc:
        if conn:
            conn.rollback()
        for attachment in saved_attachments:
            try:
                os.remove(attachment["path"])
            except OSError:
                pass
        print(f"Error creando ticket: {exc}")
        return jsonify({"success": False, "message": "No fue posible crear el ticket"}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def _ensure_ticket_tables():
    global _ticket_schema_ready
    if _ticket_schema_ready:
        return

    with _ticket_schema_lock:
        if _ticket_schema_ready:
            return

        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            if conn is None:
                raise RuntimeError("No se pudo abrir la conexion para tickets")

            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS support_tickets (
                    id INTEGER PRIMARY KEY AUTO_INCREMENT,
                    ticket_no VARCHAR(32) NOT NULL UNIQUE,
                    requester_username VARCHAR(120) NOT NULL,
                    requester_name VARCHAR(180) NOT NULL,
                    requester_email VARCHAR(180) NULL,
                    title VARCHAR(180) NOT NULL,
                    description TEXT NOT NULL,
                    ticket_type VARCHAR(20) NOT NULL DEFAULT 'normal',
                    category VARCHAR(60) NOT NULL DEFAULT 'general',
                    priority VARCHAR(16) NOT NULL DEFAULT 'media',
                    status VARCHAR(20) NOT NULL DEFAULT 'abierto',
                    assigned_to_username VARCHAR(120) NULL,
                    assigned_to_name VARCHAR(180) NULL,
                    last_message_preview VARCHAR(255) NULL,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    last_message_at DATETIME NOT NULL,
                    resolved_at DATETIME NULL,
                    closed_at DATETIME NULL,
                    INDEX idx_support_tickets_requester (requester_username),
                    INDEX idx_support_tickets_status (status),
                    INDEX idx_support_tickets_type (ticket_type),
                    INDEX idx_support_tickets_updated_at (updated_at)
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS support_ticket_messages (
                    id INTEGER PRIMARY KEY AUTO_INCREMENT,
                    ticket_id INTEGER NOT NULL,
                    author_username VARCHAR(120) NOT NULL,
                    author_name VARCHAR(180) NOT NULL,
                    author_role VARCHAR(80) NOT NULL DEFAULT 'usuario',
                    message_body TEXT NOT NULL,
                    created_at DATETIME NOT NULL,
                    INDEX idx_support_ticket_messages_ticket_created (ticket_id, created_at)
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS support_ticket_attachments (
                    id INTEGER PRIMARY KEY AUTO_INCREMENT,
                    ticket_id INTEGER NOT NULL,
                    message_id INTEGER NOT NULL,
                    original_name VARCHAR(255) NOT NULL,
                    stored_name VARCHAR(255) NOT NULL,
                    file_url VARCHAR(255) NOT NULL,
                    mime_type VARCHAR(120) NULL,
                    created_at DATETIME NOT NULL,
                    INDEX idx_support_ticket_attachments_message (message_id),
                    INDEX idx_support_ticket_attachments_ticket (ticket_id)
                )
                """
            )
            conn.commit()
            _ticket_schema_ready = True
        except Exception as exc:
            if conn:
                conn.rollback()
            print(f"Error asegurando esquema de tickets: {exc}")
            raise
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
