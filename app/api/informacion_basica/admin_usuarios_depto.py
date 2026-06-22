"""Administracion de usuarios ACOTADA por departamento (Informacion Basica).

A diferencia del Panel de Administracion del superadmin (`/admin/panel`,
`app/api/admin/usuarios.py`), este modulo permite delegar la creacion/edicion
de usuarios a responsables de area: un usuario con el permiso de boton
"Administracion de usuario" solo puede gestionar usuarios de SU PROPIO
departamento (`session['departamento']`) y solo asignarles roles de ese
departamento (`roles.departamento`) o roles transversales (`departamento NULL`).

El superadmin no tiene restriccion (bypass del decorador + alcance == todos).

Gate: `requiere_permiso_dropdown(LISTA_INFORMACIONBASICA, "Administracion de
usuario", "Administracion de usuario")` -> mismo permiso que muestra el boton
en el sidebar. La regla de alcance por departamento se valida SIEMPRE en
servidor (el frontend solo oculta).

Sigue WF_002/WF_003: blueprint en app/api/<seccion>/, helpers desde
app.api.shared, registrado en _MODULOS_REGISTRADOS.
"""

import logging

from flask import Blueprint, jsonify, render_template, request, session

from app.api.shared import auth_system, requiere_permiso_dropdown
from app.api.shared.alcance_departamento import alcance_actual
from app.db_mysql import get_db_connection
from app.api.admin.usuarios import (
    get_dict_cursor,
    _merge_catalog_values,
    DEFAULT_USER_CARGOS,
)
from app.api.pda.shipping import AVAILABLE_CARGOS

logger = logging.getLogger(__name__)

bp = Blueprint("admin_usuarios_depto", __name__)

# Coordenadas del permiso de boton (mismas que el <li> del sidebar).
_PERM_PAGINA = "LISTA_INFORMACIONBASICA"
_PERM_SECCION = "Administración de usuario"
_PERM_BOTON = "Administración de usuario"


def _todos_los_departamentos():
    from app.api.admin.departamentos import obtener_departamentos_activos
    return obtener_departamentos_activos()


# Roles que SOLO el superadmin real puede asignar, nunca un delegado de
# departamento (aunque sean transversales / departamento NULL).
_ROLES_RESERVADOS = ("superadmin", "admin")


def _roles_asignables(cursor, es_super, depto):
    """Lista de nombres de rol que el usuario actual puede asignar."""
    if es_super:
        cursor.execute(
            "SELECT nombre FROM roles WHERE activo = 1 ORDER BY nivel DESC, nombre"
        )
        return [r["nombre"] for r in cursor.fetchall()]

    # Delegado: roles de su departamento + transversales (NULL),
    # EXCLUYENDO siempre los roles reservados (admin/superadmin).
    placeholders = ", ".join(["%s"] * len(_ROLES_RESERVADOS))
    cursor.execute(
        f"""
        SELECT nombre FROM roles
        WHERE activo = 1
          AND (departamento = %s OR departamento IS NULL)
          AND nombre NOT IN ({placeholders})
        ORDER BY nivel DESC, nombre
        """,
        (depto, *_ROLES_RESERVADOS),
    )
    return [r["nombre"] for r in cursor.fetchall()]


@bp.route("/admin-usuarios-depto")
@requiere_permiso_dropdown(_PERM_PAGINA, _PERM_SECCION, _PERM_BOTON)
def admin_usuarios_depto_template():
    """Servir el fragmento AJAX del modulo."""
    try:
        return render_template("INFORMACION BASICA/admin_usuarios_depto.html")
    except Exception as e:
        logger.error("Error al cargar admin_usuarios_depto: %s", e)
        return f"Error al cargar el contenido: {str(e)}", 500


@bp.route("/api/admin-usuarios-depto/contexto")
@requiere_permiso_dropdown(_PERM_PAGINA, _PERM_SECCION, _PERM_BOTON)
def contexto():
    """Datos para poblar el formulario: departamentos y roles asignables."""
    conn = None
    try:
        es_super, depto = alcance_actual()
        conn = get_db_connection()
        cursor = get_dict_cursor(conn)

        departamentos = _todos_los_departamentos() if es_super else ([depto] if depto else [])
        roles = _roles_asignables(cursor, es_super, depto)
        cargos = _merge_catalog_values(DEFAULT_USER_CARGOS, AVAILABLE_CARGOS)

        return jsonify({
            "es_superadmin": es_super,
            "departamento_propio": depto,
            "departamentos": departamentos,
            "roles": roles,
            "cargos": cargos,
        })
    except Exception as e:
        logger.error("Error en contexto: %s", e)
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@bp.route("/api/admin-usuarios-depto/usuarios")
@requiere_permiso_dropdown(_PERM_PAGINA, _PERM_SECCION, _PERM_BOTON)
def listar_usuarios():
    """Usuarios del departamento del alcance (todos si superadmin)."""
    conn = None
    try:
        es_super, depto = alcance_actual()
        conn = get_db_connection()
        cursor = get_dict_cursor(conn)

        sql = """
            SELECT u.id, u.username, u.email, u.nombre_completo,
                   u.departamento, u.cargo, u.activo, u.ultimo_acceso,
                   GROUP_CONCAT(r.nombre) AS roles
            FROM usuarios_sistema u
            LEFT JOIN usuario_roles ur ON u.id = ur.usuario_id
            LEFT JOIN roles r ON ur.rol_id = r.id AND r.activo = 1
        """
        params = []
        if not es_super:
            sql += " WHERE u.departamento = %s"
            params.append(depto)
        sql += " GROUP BY u.id ORDER BY u.fecha_creacion DESC"

        cursor.execute(sql, tuple(params))
        usuarios = []
        for row in cursor.fetchall():
            roles_str = row.get("roles") or ""
            row["roles"] = roles_str.split(",") if roles_str else []
            ua = row.get("ultimo_acceso")
            row["ultimo_acceso"] = ua.strftime("%Y-%m-%d %H:%M:%S") if hasattr(ua, "strftime") else (str(ua) if ua else "")
            usuarios.append(row)

        return jsonify(usuarios)
    except Exception as e:
        logger.error("Error listando usuarios: %s", e)
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@bp.route("/api/admin-usuarios-depto/guardar_usuario", methods=["POST"])
@requiere_permiso_dropdown(_PERM_PAGINA, _PERM_SECCION, _PERM_BOTON)
def guardar_usuario():
    """Crear o actualizar un usuario DENTRO del alcance del admin actual."""
    conn = None
    try:
        data = request.get_json() or {}
        usuario_actual = session.get("usuario")
        es_super, depto = alcance_actual()

        username = (data.get("username") or "").strip()
        if not username:
            return jsonify({"error": "Username es requerido"}), 400
        if not (data.get("nombre_completo") or "").strip():
            return jsonify({"error": "Nombre completo es requerido"}), 400

        # Proteccion del usuario admin (igual que el panel del superadmin).
        if username == "admin":
            return jsonify({"error": "El usuario administrador esta protegido."}), 403

        depto_destino = (data.get("departamento") or "").strip()
        roles_destino = [r for r in (data.get("roles") or []) if r]

        # --- VALIDACION DE ALCANCE (servidor, no confiar en el frontend) ---
        if not es_super:
            if not depto:
                return jsonify({"error": "Tu usuario no tiene departamento asignado."}), 403
            # El delegado solo puede crear/editar en su propio departamento.
            if depto_destino and depto_destino != depto:
                return jsonify({
                    "error": f"Solo puedes administrar usuarios del departamento {depto}.",
                }), 403
            depto_destino = depto  # forzar al propio departamento

        conn = get_db_connection()
        cursor = get_dict_cursor(conn)

        # Roles permitidos segun alcance.
        permitidos = set(_roles_asignables(cursor, es_super, depto))
        invalidos = [r for r in roles_destino if r not in permitidos]
        if invalidos:
            return jsonify({
                "error": "No puedes asignar estos roles: " + ", ".join(invalidos),
            }), 403

        # Si se edita un usuario existente, validar que este dentro del alcance.
        cursor.execute(
            "SELECT id, departamento FROM usuarios_sistema WHERE username = %s",
            (username,),
        )
        existe = cursor.fetchone()
        if existe and not es_super and (existe.get("departamento") or "") != depto:
            return jsonify({
                "error": "No puedes modificar usuarios de otro departamento.",
            }), 403

        if existe:
            params = [
                data.get("nombre_completo"),
                data.get("email", ""),
                depto_destino,
                data.get("cargo", ""),
                data.get("activo", 1),
                usuario_actual,
                auth_system.get_mexico_time_mysql(),
                username,
            ]
            if data.get("password") and data["password"].strip():
                cursor.execute(
                    """
                    UPDATE usuarios_sistema SET
                        password_hash = %s, nombre_completo = %s, email = %s,
                        departamento = %s, cargo = %s, activo = %s,
                        modificado_por = %s, fecha_modificacion = %s,
                        intentos_fallidos = 0, bloqueado_hasta = NULL
                    WHERE username = %s
                    """,
                    [auth_system.hash_password(data["password"])] + params,
                )
            else:
                cursor.execute(
                    """
                    UPDATE usuarios_sistema SET
                        nombre_completo = %s, email = %s, departamento = %s,
                        cargo = %s, activo = %s, modificado_por = %s,
                        fecha_modificacion = %s
                    WHERE username = %s
                    """,
                    params,
                )
            usuario_id = existe["id"]
            accion, mensaje = "actualizar_usuario", f"Usuario {username} actualizado"
        else:
            if not data.get("password"):
                return jsonify({"error": "Password es requerido para nuevos usuarios"}), 400
            cursor.execute(
                """
                INSERT INTO usuarios_sistema (
                    username, password_hash, nombre_completo, email,
                    departamento, cargo, activo, creado_por
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    username,
                    auth_system.hash_password(data["password"]),
                    data.get("nombre_completo"),
                    data.get("email", ""),
                    depto_destino,
                    data.get("cargo", ""),
                    data.get("activo", 1),
                    usuario_actual,
                ),
            )
            usuario_id = cursor.lastrowid
            accion, mensaje = "crear_usuario", f"Usuario {username} creado"

        # Reemplazar roles.
        cursor.execute("DELETE FROM usuario_roles WHERE usuario_id = %s", (usuario_id,))
        for rol_nombre in roles_destino:
            cursor.execute("SELECT id FROM roles WHERE nombre = %s", (rol_nombre,))
            rol = cursor.fetchone()
            if rol:
                cursor.execute(
                    "INSERT INTO usuario_roles (usuario_id, rol_id, asignado_por) VALUES (%s, %s, %s)",
                    (usuario_id, rol["id"], usuario_actual),
                )

        conn.commit()

        auth_system.registrar_auditoria(
            usuario=usuario_actual,
            modulo="sistema",
            accion=accion,
            descripcion=f"{mensaje} (admin depto: {depto or 'superadmin'})",
            datos_despues={"username": username, "departamento": depto_destino, "roles": roles_destino},
        )
        return jsonify({"success": True, "mensaje": mensaje})

    except Exception as e:
        logger.exception("Error guardando usuario (depto): %s", e)
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()
