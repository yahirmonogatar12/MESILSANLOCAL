"""Endpoints HTTP del modulo Control de metal mask.

Migrado desde `app/routes.py` (2026-05-26). Sin cambios funcionales.

Rutas:
  GET  /control-mask-metal-ajax  -> render HTML del modulo
  GET  /api/masks                -> listar masks (filtra por disuse)
  POST /api/masks                -> crear mask
  PUT  /api/masks/<int:mask_id>  -> actualizar mask

NO mover aqui `/api/masks/info` (routes.py:17174): es compartida con el
modulo "Control de operacion SMT" (`control-operacion-smt-ajax.js:1560`).

DDL `init_metal_mask_tables` migrado a este modulo el 2026-05-28; lo invoca
`app/startup_init.py` para garantizar la existencia de las tablas `masks`
y `storage_boxes` al arranque.
"""

import traceback
from functools import wraps

from flask import Blueprint, jsonify, render_template, request, session

# Importar directo desde modulos fuente (NO desde app.api.shared) para
# evitar import circular: shared -> routes -> metal_mask -> shared.
from app.db_mysql import execute_query, get_connection


# `login_requerido` y `requiere_permiso_dropdown` viven en `app.routes`.
# Se importan dentro de las funciones que los necesitan (tarde) para evitar
# que metal_mask arrastre app.routes al ser importado por shared.
def login_requerido(f):
    """Proxy del decorador real definido en `app.routes`."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from app import routes as _r
        return _r.login_requerido(f)(*args, **kwargs)

    return decorated_function


def requiere_permiso_dropdown(pagina, seccion, boton):
    """Proxy del decorador real definido en `app.routes`."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from app import routes as _r
            real_decorator = _r.requiere_permiso_dropdown(pagina, seccion, boton)
            return real_decorator(f)(*args, **kwargs)

        return decorated_function

    return decorator


bp = Blueprint("control_produccion_metal_mask", __name__)


# =============================
# CONTROL DE METAL MASK
# =============================

METAL_MASK_PERMISO_PAGINA = "LISTA_CONTROLDEPRODUCCION"
METAL_MASK_PERMISO_SECCION = "Control de SMT"
METAL_MASK_PERMISO_BOTON = "Control de mask de metal"


@bp.route("/control-mask-metal-ajax")
@login_requerido
@requiere_permiso_dropdown(
    METAL_MASK_PERMISO_PAGINA, METAL_MASK_PERMISO_SECCION, METAL_MASK_PERMISO_BOTON
)
def control_mask_metal_ajax():
    """Ruta AJAX para cargar dinamicamente el contenido de Control de mask de metal."""
    try:
        return render_template("Control de produccion/control_mask_metal_ajax.html")
    except Exception as e:
        print(f"Error al cargar template Control de mask de metal AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


# API: Masks
@bp.route("/api/masks", methods=["GET"])
@login_requerido
def api_list_masks():
    try:
        disuse = request.args.get("disuse", "ALL")
        sql = (
            "SELECT id, management_no, storage_box, pcb_code, side, "
            "COALESCE(DATE_FORMAT(production_date, '%Y-%m-%d'), '') AS production_date, "
            "used_count, max_count, allowance, model_name, tension_min, tension_max, thickness, "
            "supplier, registration_date, disuse FROM masks"
        )
        params = []
        if disuse and disuse != "ALL":
            sql += " WHERE disuse=%s"
            params.append(disuse)
        sql += " ORDER BY id DESC"
        rows = execute_query(sql, tuple(params) if params else None, fetch="all") or []

        # Normalizacion ligera de tipos para JSON
        out = []
        for r in rows:
            r = dict(r)
            for k in ("used_count", "max_count", "allowance"):
                try:
                    r[k] = int(r.get(k) or 0)
                except Exception:
                    pass
            for k in ("tension_min", "tension_max", "thickness"):
                v = r.get(k)
                try:
                    r[k] = float(v) if v is not None else None
                except Exception:
                    pass
            out.append(r)
        return jsonify(out)
    except Exception as e:
        print(f"Error en api_list_masks: {e}")
        return jsonify({"error": str(e)}), 500


@bp.route("/api/masks", methods=["POST"])
@login_requerido
def api_create_mask():
    try:
        data = request.get_json(force=True) or {}
        data.setdefault("used_count", 0)
        data.setdefault("max_count", 0)
        data.setdefault("allowance", 0)
        data.setdefault("disuse", "Uso")

        pd = data.get("production_date")
        if isinstance(pd, str) and len(pd) >= 10:
            data["production_date"] = pd[:10]
        else:
            data["production_date"] = None

        cols = (
            "management_no",
            "storage_box",
            "pcb_code",
            "side",
            "production_date",
            "used_count",
            "max_count",
            "allowance",
            "model_name",
            "tension_min",
            "tension_max",
            "thickness",
            "supplier",
            "registration_date",
            "disuse",
        )
        placeholders = ",".join(["%s"] * len(cols))
        values = [data.get(c) for c in cols]
        sql = f"INSERT INTO masks ({','.join(cols)}) VALUES ({placeholders})"
        execute_query(sql, tuple(values))
        return jsonify({"success": True, "message": "Registrado", "data": data}), 201
    except Exception as e:
        msg = str(e)
        if "Duplicate entry" in msg:
            return jsonify({"error": "El Nomero de Gestion ya existe"}), 400
        print(f"Error en api_create_mask: {e}")
        return jsonify({"error": msg}), 500


@bp.route("/api/masks/<int:mask_id>", methods=["PUT"])
@login_requerido
def api_update_mask(mask_id: int):
    try:
        p = request.get_json(force=True) or {}
        required = p.get("management_no", "").strip()
        if not required:
            return jsonify({"error": "Nomero de Gestion es requerido"}), 400

        sql = (
            "UPDATE masks SET management_no=%s, storage_box=%s, pcb_code=%s, side=%s, "
            "production_date=%s, used_count=%s, max_count=%s, allowance=%s, "
            "model_name=%s, tension_min=%s, tension_max=%s, thickness=%s, "
            "supplier=%s, registration_date=%s, disuse=%s WHERE id=%s"
        )
        params = (
            p.get("management_no", "").strip(),
            p.get("storage_box", "").strip(),
            p.get("pcb_code", "").strip(),
            p.get("side", "").strip(),
            (p.get("production_date") or None),
            p.get("used_count", 0),
            p.get("max_count", 0),
            p.get("allowance", 0),
            p.get("model_name", "").strip(),
            p.get("tension_min", 0),
            p.get("tension_max", 0),
            p.get("thickness", 0),
            p.get("supplier", "").strip(),
            p.get("registration_date", "").strip(),
            p.get("disuse", "Uso"),
            mask_id,
        )
        affected = execute_query(sql, params)
        if affected == 0:
            return jsonify({"error": "Moscara no encontrada"}), 404
        return jsonify({"success": True, "message": "Actualizado"})
    except Exception as e:
        msg = str(e)
        if "Duplicate entry" in msg:
            return jsonify({"error": "El Nomero de Gestion ya existe"}), 400
        print(f"Error en api_update_mask: {e}")
        return jsonify({"error": msg}), 500


# =============================
# GET /api/metal-mask/test  (health check)
# =============================
# Migracion 2026-05-27: ruta reintegrada en su blueprint (caller huerfano en
# control-operacion-smt-ajax.js:2581 - `testMetalMaskConnection`).
# Verifica conectividad a la tabla `masks` antes de cargar el historial.
# Respuesta: {success: bool, count?: int, error?: str}.

@bp.route("/api/metal-mask/test", methods=["GET"])
@login_requerido
def api_metal_mask_test():
    """Health check de conectividad a la tabla masks (consumido por Control de operacion SMT)."""
    try:
        row = execute_query("SELECT COUNT(*) AS c FROM masks", fetch="one")
        count = 0
        if row:
            count = row.get("c") if isinstance(row, dict) else row[0]
        return jsonify({"success": True, "count": int(count or 0)})
    except Exception as e:
        print(f"Error en api_metal_mask_test: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ---------------------------------------------------------------------------
# Fase 3.2 (2026-05-28): render template del modulo migrado desde routes.py.
# Vivia en routes.py como ruta independiente; pertenece naturalmente al
# modulo Metal Mask (consume el mismo template hermano).
# ---------------------------------------------------------------------------


@bp.route("/historial-tension-mask-metal-ajax")
@login_requerido
def historial_tension_mask_metal_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Historial de tension de mask de metal"""
    try:
        return render_template(
            "Control de produccion/historial_tension_mask_metal_ajax.html"
        )
    except Exception as e:
        print(
            f"Error al cargar template Historial de tension de mask de metal AJAX: {e}"
        )
        return f"Error al cargar el contenido: {str(e)}", 500


# ---------------------------------------------------------------------------
# Fase 3.3 (2026-05-28): render hermano "Historial de uso de mask de metal"
# (vive bajo el sidebar Control de calidad pero pertenece a este modulo).
# ---------------------------------------------------------------------------


@bp.route("/historial-uso-mask-metal-ajax")
@login_requerido
def historial_uso_mask_metal_ajax():
    """Template para Historial de uso de mask de metal"""
    return render_template("Control de calidad/historial_uso_mask_metal_ajax.html")


# ---------------------------------------------------------------------------
# Fase 4 (2026-05-28): 4 endpoints API gordos migrados desde routes.py.
#   /api/masks/info                  - lookup de mask por management_no
#   POST /api/metal-mask/history     - registrar uso en metal_mask_history
#   GET  /api/metal-mask/history     - listar historial con filtros
#   POST /api/metal-mask/update-used-count - actualizar used_count al fin de plan
# El comentario L11 ("NO mover aqui /api/masks/info") esta obsoleto: los
# blueprints Flask son namespaces de codigo, no aislan rutas — Control de
# operacion SMT sigue consumiendolas via su URL canonica sin cambios.
# ---------------------------------------------------------------------------


@bp.route("/api/masks/info", methods=["GET"])
@login_requerido
def api_masks_info():
    try:
        code = request.args.get("code", "").strip()
        if not code:
            return jsonify({"success": False, "error": "code requerido"}), 400

        conn = get_connection()
        cursor = conn.cursor()

        q = """
            SELECT management_no, storage_box, pcb_code, side, production_date,
                   used_count, max_count, allowance, model_name, tension_min,
                   tension_max, thickness, supplier, registration_date, disuse
            FROM masks
            WHERE management_no = %s
            LIMIT 1
        """
        cursor.execute(q, [code])
        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if not row:
            return jsonify(
                {"success": False, "found": False, "message": "No encontrado"}
            )

        fields = [
            "management_no",
            "storage_box",
            "pcb_code",
            "side",
            "production_date",
            "used_count",
            "max_count",
            "allowance",
            "model_name",
            "tension_min",
            "tension_max",
            "thickness",
            "supplier",
            "registration_date",
            "disuse",
        ]
        data = {
            fields[i]: (row[i] if i < len(row) else None) for i in range(len(fields))
        }

        def to_int(v):
            try:
                return int(v)
            except Exception:
                try:
                    return int(float(v))
                except Exception:
                    return 0

        data["used_count"] = to_int(data.get("used_count"))
        data["max_count"] = to_int(data.get("max_count"))
        data["allowance"] = to_int(data.get("allowance"))

        return jsonify({"success": True, "found": True, "data": data})
    except Exception as e:
        print("Error en api_masks_info:", e)
        print(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/api/metal-mask/history", methods=["POST"])
@login_requerido
def api_save_metal_mask_history():
    """Guardar historial de uso de Metal Mask"""
    try:
        data = request.get_json()

        # Validar datos requeridos
        required_fields = ["mask_code", "model_code", "linea", "quantity_used"]
        for field in required_fields:
            if not data.get(field):
                return jsonify(
                    {"success": False, "error": f"{field} es requerido"}
                ), 400

        conn = get_connection()
        cursor = conn.cursor()

        # Crear tabla si no existe
        create_table_query = """
            CREATE TABLE IF NOT EXISTS metal_mask_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                mask_code VARCHAR(50) NOT NULL,
                model_code VARCHAR(50) NOT NULL,
                linea VARCHAR(20) NOT NULL,
                quantity_used INT NOT NULL DEFAULT 0,
                scan_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                usuario VARCHAR(50),
                plan_id INT,
                run_id INT,
                available_uses INT DEFAULT 0,
                total_uses INT DEFAULT 0,
                status ENUM('OK', 'NG', 'WARNING') DEFAULT 'OK',
                notes TEXT,
                INDEX idx_mask_code (mask_code),
                INDEX idx_model_code (model_code),
                INDEX idx_linea (linea),
                INDEX idx_scan_date (scan_date)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        cursor.execute(create_table_query)
        conn.commit()

        # Insertar registro de historial
        insert_query = """
            INSERT INTO metal_mask_history
            (mask_code, model_code, linea, quantity_used, usuario, plan_id, run_id,
             available_uses, total_uses, status, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        usuario = session.get("usuario_logueado", "Sistema")
        plan_id = data.get("plan_id")
        run_id = data.get("run_id")
        available_uses = data.get("available_uses", 0)
        total_uses = data.get("total_uses", 0)
        status = data.get("status", "OK")
        notes = data.get("notes", "")

        cursor.execute(
            insert_query,
            [
                data["mask_code"],
                data["model_code"],
                data["linea"],
                data["quantity_used"],
                usuario,
                plan_id,
                run_id,
                available_uses,
                total_uses,
                status,
                notes,
            ],
        )

        history_id = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify(
            {
                "success": True,
                "history_id": history_id,
                "message": "Historial de Metal Mask guardado correctamente",
            }
        )

    except Exception as e:
        print("Error en api_save_metal_mask_history:", e)
        print(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/api/metal-mask/history", methods=["GET"])
@login_requerido
def api_get_metal_mask_history():
    """Obtener historial de uso de Metal Mask"""
    try:
        # Parametros de filtro
        mask_code = request.args.get("mask_code", "").strip()
        model_code = request.args.get("model_code", "").strip()
        linea = request.args.get("linea", "").strip()
        date_from = request.args.get("date_from", "").strip()
        date_to = request.args.get("date_to", "").strip()
        limit = int(request.args.get("limit", 100))

        conn = get_connection()
        cursor = conn.cursor()

        # Construir consulta con filtros
        where_conditions = []
        params = []

        if mask_code:
            where_conditions.append("mask_code = %s")
            params.append(mask_code)

        if model_code:
            where_conditions.append("model_code = %s")
            params.append(model_code)

        if linea:
            where_conditions.append("linea = %s")
            params.append(linea)

        if date_from:
            where_conditions.append("scan_date >= %s")
            params.append(date_from)

        if date_to:
            where_conditions.append("scan_date <= %s")
            params.append(date_to + " 23:59:59")

        where_clause = (
            "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        )

        query = f"""
            SELECT id, mask_code, model_code, linea, quantity_used,
                   DATE_FORMAT(scan_date, '%%Y-%%m-%%d %%H:%%i:%%s') as scan_date,
                   usuario, plan_id, run_id, available_uses, total_uses,
                   status, notes
            FROM metal_mask_history
            {where_clause}
            ORDER BY scan_date DESC
            LIMIT %s
        """

        params.append(limit)
        cursor.execute(query, params)
        rows = cursor.fetchall()

        columns = [
            "id",
            "mask_code",
            "model_code",
            "linea",
            "quantity_used",
            "scan_date",
            "usuario",
            "plan_id",
            "run_id",
            "available_uses",
            "total_uses",
            "status",
            "notes",
        ]

        data = [dict(zip(columns, row)) for row in rows]

        cursor.close()
        conn.close()

        return jsonify({"success": True, "data": data, "count": len(data)})

    except Exception as e:
        print(" Error en api_get_metal_mask_history:", e)
        print(" Traceback completo:")
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/api/metal-mask/update-used-count", methods=["POST"])
@login_requerido
def api_update_metal_mask_used_count():
    """Actualizar used_count de Metal Mask al finalizar plan"""
    try:
        data = request.get_json()
        plan_id = data.get("plan_id")
        cantidad_producida = int(data.get("cantidad_producida", 0))

        if not plan_id or cantidad_producida <= 0:
            return jsonify(
                {
                    "success": False,
                    "error": "plan_id y cantidad_producida son requeridos",
                }
            )

        conn = get_connection()
        cursor = conn.cursor()

        # 1. Obtener informacion del plan para saber el modelo y linea
        cursor.execute(
            """
            SELECT modelo, linea, nparte
            FROM plan_smd
            WHERE id = %s
        """,
            (plan_id,),
        )
        plan_info = cursor.fetchone()

        if not plan_info:
            return jsonify({"success": False, "error": "Plan no encontrado"})

        modelo, linea, nparte = plan_info

        # 2. Buscar Metal Masks que se usaron para este modelo/linea
        # Prioridad 1: Buscar por plan_id especifico
        cursor.execute(
            """
            SELECT DISTINCT mask_code, COUNT(*) as usage_count
            FROM metal_mask_history
            WHERE plan_id = %s
            GROUP BY mask_code
            ORDER BY usage_count DESC, scan_date DESC
        """,
            (plan_id,),
        )

        mask_codes = [row[0] for row in cursor.fetchall()]

        # Prioridad 2: Si no hay historial del plan, buscar por modelo/linea reciente
        if not mask_codes:
            cursor.execute(
                """
                SELECT DISTINCT mask_code, COUNT(*) as usage_count
                FROM metal_mask_history
                WHERE model_code = %s AND linea = %s
                AND scan_date >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                GROUP BY mask_code
                ORDER BY usage_count DESC, scan_date DESC
                LIMIT 3
            """,
                (modelo, linea),
            )
            mask_codes = [row[0] for row in cursor.fetchall()]

        # Prioridad 3: Buscar cualquier mask para el modelo (ultimo recurso)
        if not mask_codes:
            cursor.execute(
                """
                SELECT DISTINCT mask_code
                FROM metal_mask_history
                WHERE model_code = %s
                ORDER BY scan_date DESC
                LIMIT 1
            """,
                (modelo,),
            )
            mask_codes = [row[0] for row in cursor.fetchall()]

        updated_count = 0

        # 3. Actualizar used_count en la tabla masks para cada mask_code encontrada
        for mask_code in mask_codes:
            cursor.execute(
                """
                UPDATE masks
                SET used_count = used_count + %s
                WHERE management_no = %s
            """,
                (cantidad_producida, mask_code),
            )

            if cursor.rowcount > 0:
                updated_count += cursor.rowcount
                print(
                    f" Metal Mask {mask_code} - used_count incrementado en {cantidad_producida}"
                )

        # 4. Registrar el update en el historial para cada mask actualizada
        for mask_code in mask_codes:
            cursor.execute(
                """
                SELECT used_count, max_count, allowance
                FROM masks
                WHERE management_no = %s
            """,
                (mask_code,),
            )

            mask_info = cursor.fetchone()
            if mask_info:
                used_count, max_count, allowance = mask_info
                available_uses = max(0, (max_count + allowance) - used_count)

                cursor.execute(
                    """
                    INSERT INTO metal_mask_history
                    (mask_code, model_code, linea, quantity_used, plan_id,
                     available_uses, total_uses, status, notes, usuario, scan_date)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                """,
                    (
                        mask_code,
                        modelo,
                        linea,
                        cantidad_producida,
                        plan_id,
                        available_uses,
                        used_count,
                        "END_PLAN",
                        f"Finalizacion de plan {plan_id} - Producido: {cantidad_producida}",
                        session.get("usuario", "sistema"),
                    ),
                )

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify(
            {
                "success": True,
                "updated_masks": updated_count,
                "cantidad_producida": cantidad_producida,
                "plan_id": plan_id,
                "masks_actualizadas": mask_codes,
            }
        )

    except Exception as e:
        print(" Error actualizando used_count:", e)
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


# ---------------------------------------------------------------------------
# Bootstrap DDL (invocado desde app/startup_init.py al arranque)
# ---------------------------------------------------------------------------


def init_metal_mask_tables():
    """Crea/ajusta tablas `masks` y `storage_boxes` si no existen.

    Migrado desde `app/routes.py` el 2026-05-28. Sin cambios funcionales.
    """
    try:
        # Tabla principal de masks (nombres de columna en ingles, usados por el frontend).
        execute_query(
            """
            CREATE TABLE IF NOT EXISTS masks (
                id INT AUTO_INCREMENT PRIMARY KEY,
                management_no VARCHAR(64) UNIQUE,
                storage_box VARCHAR(64),
                pcb_code VARCHAR(64),
                side VARCHAR(16),
                production_date DATE,
                used_count INT DEFAULT 0,
                max_count INT DEFAULT 0,
                allowance INT DEFAULT 0,
                model_name VARCHAR(255),
                tension_min DECIMAL(6,2),
                tension_max DECIMAL(6,2),
                thickness DECIMAL(6,2),
                supplier VARCHAR(128),
                registration_date VARCHAR(64),
                disuse ENUM('Uso','Desuso','Scrap') DEFAULT 'Uso',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )

        # Asegurar valores del ENUM en caso de historiales previos (migracion suave).
        try:
            execute_query(
                "ALTER TABLE masks MODIFY COLUMN disuse ENUM('Use','Disuse','Uso','Desuso','Scrap') DEFAULT 'Uso'"
            )
            execute_query("UPDATE masks SET disuse='Uso' WHERE disuse='Use'")
            execute_query("UPDATE masks SET disuse='Desuso' WHERE disuse='Disuse'")
            execute_query(
                "ALTER TABLE masks MODIFY COLUMN disuse ENUM('Uso','Desuso','Scrap') DEFAULT 'Uso'"
            )
        except Exception:
            # Si falla (p.ej. por no existir la tabla/columna aun), continuar.
            pass

        # Tabla de cajas de almacenamiento.
        execute_query(
            """
            CREATE TABLE IF NOT EXISTS storage_boxes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                management_no VARCHAR(64) UNIQUE,
                code VARCHAR(64),
                name VARCHAR(64),
                location VARCHAR(64),
                storage_status ENUM('Disponible','Ocupado','Mantenimiento') DEFAULT 'Disponible',
                used_status ENUM('Usado','No Usado') DEFAULT 'Usado',
                note TEXT,
                registration_date VARCHAR(64),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )
        print(" Tablas Metal Mask creadas/verificadas")
    except Exception as e:
        print(f"Error creando/verificando tablas Metal Mask: {e}")
