"""Endpoints HTTP para gestion de roles y permisos de dropdowns.

Forma parte del Panel de Administracion (accesible desde el boton
'Panel de Administracion' del navbar, ruta `/admin/panel`).

Rutas (con url_prefix `/admin`):
  GET  /admin/permisos-dropdowns                      -> render HTML
  GET  /admin/api/roles                               -> lista de roles activos
  GET  /admin/api/dropdowns                           -> lista de dropdowns con permisos
  GET  /admin/api/role-permissions/<role_name>        -> permisos de un rol
  POST /admin/api/toggle-permission                   -> add/remove permiso de rol
  POST /admin/api/enable-all-permissions              -> habilitar todos los permisos a un rol
  POST /admin/api/disable-all-permissions             -> deshabilitar todos los permisos de un rol

Migrado desde `app/admin_api.py` (2026-05-22). Mismo blueprint name
('admin') y mismas rutas; el frontend no requiere cambios.

NOTA WF_003: este modulo conserva `get_db_connection()` directo porque
todas las operaciones de escritura combinan SELECT + INSERT/DELETE con
commit final. Migrar a `execute_query()` requeriria reestructurar la
logica de transacciones.
"""

from functools import wraps

from flask import Blueprint, jsonify, redirect, render_template, request, session

from app.api.shared import auth_system
from app.db import get_db_connection


bp = Blueprint("admin", __name__, url_prefix="/admin")


def requiere_superadmin_panel(f):
    """Permitir gestion de roles/permisos solo al superadmin central."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        usuario = session.get("usuario")
        if not usuario:
            if request.is_json:
                return jsonify({"error": "No autenticado", "codigo": 401}), 401
            return redirect("/login")

        roles = auth_system.obtener_roles_usuario(usuario)
        if "superadmin" not in roles:
            return jsonify({
                "error": "Solo superadmin puede administrar roles y permisos",
                "codigo": 403,
            }), 403

        return f(*args, **kwargs)

    return decorated_function


@bp.route("/permisos-dropdowns")
@auth_system.login_requerido_avanzado
@auth_system.requiere_permiso("sistema", "usuarios")
@requiere_superadmin_panel
def gestionar_permisos_dropdowns():
    """Pagina principal de gestion de permisos"""
    return render_template("admin/gestionar_permisos_dropdowns.html")


@bp.route("/api/roles")
@auth_system.login_requerido_avanzado
@auth_system.requiere_permiso("sistema", "usuarios")
@requiere_superadmin_panel
def get_roles():
    """Obtener todos los roles disponibles"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT nombre, descripcion
            FROM roles
            WHERE activo = 1
            ORDER BY nombre
        """)

        roles_raw = cursor.fetchall()

        roles = []
        for role_row in roles_raw:
            roles.append({
                "nombre": role_row[0],
                "descripcion": role_row[1] or f"Rol {role_row[0]}"
            })

        conn.close()
        return jsonify(roles)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/dropdowns")
@auth_system.login_requerido_avanzado
@auth_system.requiere_permiso("sistema", "usuarios")
@requiere_superadmin_panel
def get_dropdowns():
    """Obtener todos los dropdowns disponibles con estructura jerarquica"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT DISTINCT pagina, seccion, boton, descripcion
            FROM permisos_botones
            WHERE pagina IS NOT NULL AND seccion IS NOT NULL AND boton IS NOT NULL
            ORDER BY pagina, seccion, boton
        """)

        dropdowns_raw = cursor.fetchall()

        dropdowns = []
        for dropdown_row in dropdowns_raw:
            pagina = dropdown_row[0]
            seccion = dropdown_row[1]
            boton = dropdown_row[2]
            descripcion = dropdown_row[3] if dropdown_row[3] else f"{pagina} > {seccion} > {boton}"

            dropdowns.append({
                "pagina": pagina,
                "seccion": seccion,
                "boton": boton,
                "descripcion": descripcion,
                "key": f"{pagina}|{seccion}|{boton}",
                "display_name": f"{pagina} > {seccion} > {boton}"
            })

        conn.close()
        return jsonify(dropdowns)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/role-permissions/<role_name>")
@auth_system.login_requerido_avanzado
@auth_system.requiere_permiso("sistema", "usuarios")
@requiere_superadmin_panel
def get_role_permissions(role_name):
    """Obtener permisos de un rol especifico con estructura jerarquica"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT pb.pagina, pb.seccion, pb.boton
            FROM rol_permisos_botones rpb
            JOIN permisos_botones pb ON rpb.permiso_boton_id = pb.id
            JOIN roles r ON rpb.rol_id = r.id
            WHERE r.nombre = %s
            ORDER BY pb.pagina, pb.seccion, pb.boton
        """, (role_name,))

        permisos = cursor.fetchall()

        permissions = []
        for permiso in permisos:
            pagina = permiso[0]
            seccion = permiso[1]
            boton = permiso[2]

            permissions.append({
                "pagina": pagina,
                "seccion": seccion,
                "boton": boton,
                "key": f"{pagina}|{seccion}|{boton}",
                "display_name": f"{pagina} > {seccion} > {boton}",
                "rol": role_name
            })

        conn.close()
        return jsonify(permissions)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/toggle-permission", methods=["POST"])
@auth_system.login_requerido_avanzado
@auth_system.requiere_permiso("sistema", "usuarios")
@requiere_superadmin_panel
def toggle_permission():
    """Alternar permiso para un rol usando estructura jerarquica"""
    try:
        data = request.get_json()
        role = data.get("role")
        permission_key = data.get("permission_key")  # formato: "pagina|seccion|boton"
        action = data.get("action")  # 'add' o 'remove'

        if not all([role, permission_key, action]):
            return jsonify({"error": "Faltan parametros requeridos"}), 400

        try:
            pagina, seccion, boton = permission_key.split("|")
        except ValueError:
            return jsonify({"error": "Formato de permiso invalido"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM roles WHERE nombre = %s", (role,))
        rol_result = cursor.fetchone()
        if not rol_result:
            return jsonify({"error": f"Rol {role} no encontrado"}), 404
        rol_id = rol_result[0]

        cursor.execute("""
            SELECT id FROM permisos_botones
            WHERE pagina = %s AND seccion = %s AND boton = %s
        """, (pagina, seccion, boton))
        permiso_result = cursor.fetchone()
        if not permiso_result:
            return jsonify({"error": f"Permiso {pagina}>{seccion}>{boton} no encontrado"}), 404
        permiso_id = permiso_result[0]

        message = ""

        if action == "add":
            cursor.execute("""
                SELECT COUNT(*) FROM rol_permisos_botones
                WHERE rol_id = %s AND permiso_boton_id = %s
            """, (rol_id, permiso_id))

            if cursor.fetchone()[0] == 0:
                cursor.execute("""
                    INSERT INTO rol_permisos_botones (rol_id, permiso_boton_id, fecha_asignacion)
                    VALUES (%s, %s, NOW())
                """, (rol_id, permiso_id))
                message = f"Permiso {pagina}>{seccion}>{boton} asignado a {role}"
            else:
                message = f"El permiso ya existia para {role}"

        elif action == "remove":
            cursor.execute("""
                DELETE FROM rol_permisos_botones
                WHERE rol_id = %s AND permiso_boton_id = %s
            """, (rol_id, permiso_id))
            message = f"Permiso {pagina}>{seccion}>{boton} removido de {role}"
        else:
            conn.close()
            return jsonify({
                "success": False,
                "error": f"Accion {action} no valida"
            }), 400

        conn.commit()
        conn.close()
        auth_system.invalidar_cache_permisos_botones()

        return jsonify({"success": True, "message": message})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/enable-all-permissions", methods=["POST"])
@auth_system.login_requerido_avanzado
@auth_system.requiere_permiso("sistema", "usuarios")
@requiere_superadmin_panel
def enable_all_permissions():
    """Habilitar todos los permisos de dropdown para un rol"""
    try:
        data = request.get_json()
        role = data.get("role")

        if not role:
            return jsonify({"error": "Falta el parametro rol"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM roles WHERE nombre = %s", (role,))
        rol_result = cursor.fetchone()
        if not rol_result:
            return jsonify({"error": f"Rol {role} no encontrado"}), 404
        rol_id = rol_result[0]

        cursor.execute("SELECT id FROM permisos_botones")
        all_permisos = cursor.fetchall()

        added_count = 0
        for permiso_row in all_permisos:
            permiso_id = permiso_row[0]

            cursor.execute("""
                INSERT IGNORE INTO rol_permisos_botones (rol_id, permiso_boton_id, fecha_asignacion)
                VALUES (%s, %s, NOW())
            """, (rol_id, permiso_id))

            if cursor.rowcount > 0:
                added_count += 1

        conn.commit()
        conn.close()
        auth_system.invalidar_cache_permisos_botones()

        return jsonify({
            "success": True,
            "message": f"{added_count} permisos habilitados para {role}"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/disable-all-permissions", methods=["POST"])
@auth_system.login_requerido_avanzado
@auth_system.requiere_permiso("sistema", "usuarios")
@requiere_superadmin_panel
def disable_all_permissions():
    """Deshabilitar todos los permisos de dropdown para un rol"""
    try:
        data = request.get_json()
        role = data.get("role")

        if not role:
            return jsonify({"error": "Falta el parametro rol"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM roles WHERE nombre = %s", (role,))
        rol_result = cursor.fetchone()
        if not rol_result:
            return jsonify({"error": f"Rol {role} no encontrado"}), 404
        rol_id = rol_result[0]

        cursor.execute("""
            DELETE FROM rol_permisos_botones
            WHERE rol_id = %s
        """, (rol_id,))

        affected = cursor.rowcount
        conn.commit()
        conn.close()
        auth_system.invalidar_cache_permisos_botones()

        return jsonify({
            "success": True,
            "message": f"{affected} permisos deshabilitados para {role}"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
