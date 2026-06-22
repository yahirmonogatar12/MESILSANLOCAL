"""Gestion de roles ACOTADA por departamento (Administracion de autoridad).

Permite a un responsable de area (ej. Supervisor QA, departamento Calidad)
crear/editar roles de SU departamento y asignarles permisos, pero SOLO
permisos de su propia area (permisos_botones.departamento = su depto, o NULL
= comunes). El superadmin no tiene restriccion.

Gate: permiso de boton "Administración de autoridad" (mismo <li> del sidebar).
La regla de alcance se valida SIEMPRE en servidor.

Doble candado:
  - El rol creado/editado queda marcado roles.departamento = depto del admin.
  - Solo se pueden tocar roles de ese depto.
  - Solo se pueden asignar permisos del depto (+ comunes NULL).

Sigue WF_002/WF_003.
"""

import logging

from flask import Blueprint, jsonify, render_template, request, session

from app.api.shared import auth_system, requiere_permiso_dropdown
from app.api.shared.alcance_departamento import alcance_actual
from app.db_mysql import get_db_connection
from app.api.admin.usuarios import get_dict_cursor

logger = logging.getLogger(__name__)

bp = Blueprint("gestion_roles_depto", __name__)

_PERM_PAGINA = "LISTA_INFORMACIONBASICA"
_PERM_SECCION = "Administración de usuario"
_PERM_BOTON = "Administración de autoridad"

# Roles que un delegado nunca puede crear/editar ni clonar.
_ROLES_RESERVADOS = ("superadmin", "admin")


def _rol_en_alcance(cursor, rol_id, es_super, depto):
    """True si el admin actual puede tocar ese rol."""
    cursor.execute("SELECT nombre, departamento FROM roles WHERE id = %s", (rol_id,))
    rol = cursor.fetchone()
    if not rol:
        return False, None
    if rol["nombre"] in _ROLES_RESERVADOS:
        return False, rol
    if es_super:
        return True, rol
    return (rol.get("departamento") or "") == depto, rol


@bp.route("/gestion-roles-depto")
@requiere_permiso_dropdown(_PERM_PAGINA, _PERM_SECCION, _PERM_BOTON)
def gestion_roles_depto_template():
    try:
        return render_template("INFORMACION BASICA/gestion_roles_depto.html")
    except Exception as e:
        logger.error("Error al cargar gestion_roles_depto: %s", e)
        return f"Error al cargar el contenido: {str(e)}", 500


@bp.route("/api/gestion-roles-depto/contexto")
@requiere_permiso_dropdown(_PERM_PAGINA, _PERM_SECCION, _PERM_BOTON)
def contexto():
    es_super, depto = alcance_actual()
    return jsonify({"es_superadmin": es_super, "departamento": depto})


@bp.route("/api/gestion-roles-depto/roles")
@requiere_permiso_dropdown(_PERM_PAGINA, _PERM_SECCION, _PERM_BOTON)
def listar_roles():
    """Roles del departamento del admin (todos si superadmin)."""
    conn = None
    try:
        es_super, depto = alcance_actual()
        conn = get_db_connection()
        cursor = get_dict_cursor(conn)
        sql = """
            SELECT r.id, r.nombre, r.descripcion, r.nivel, r.departamento,
                   COUNT(ur.usuario_id) AS total_usuarios
            FROM roles r
            LEFT JOIN usuario_roles ur ON r.id = ur.rol_id
            WHERE r.activo = 1 AND r.nombre NOT IN (%s, %s)
        """
        params = [*_ROLES_RESERVADOS]
        if not es_super:
            sql += " AND r.departamento = %s"
            params.append(depto)
        sql += " GROUP BY r.id ORDER BY r.nivel DESC, r.nombre"
        cursor.execute(sql, tuple(params))
        return jsonify(cursor.fetchall())
    except Exception as e:
        logger.error("Error listando roles depto: %s", e)
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@bp.route("/api/gestion-roles-depto/permisos-disponibles")
@requiere_permiso_dropdown(_PERM_PAGINA, _PERM_SECCION, _PERM_BOTON)
def permisos_disponibles():
    """Permisos que el admin puede repartir: los de su depto + comunes (NULL).

    Agrupados por pagina > seccion. Superadmin ve todos."""
    conn = None
    try:
        es_super, depto = alcance_actual()
        conn = get_db_connection()
        cursor = get_dict_cursor(conn)
        if es_super:
            cursor.execute("""
                SELECT id, pagina, seccion, boton, descripcion, departamento
                FROM permisos_botones WHERE activo = 1
                ORDER BY pagina, seccion, boton
            """)
        else:
            # Solo permisos EXPLICITAMENTE asignados a su area (tabla puente
            # permiso_departamentos). Permisos sin clasificar no se delegan.
            cursor.execute("""
                SELECT pb.id, pb.pagina, pb.seccion, pb.boton, pb.descripcion
                FROM permisos_botones pb
                JOIN permiso_departamentos pd ON pd.permiso_boton_id = pb.id
                WHERE pb.activo = 1 AND pd.departamento = %s
                ORDER BY pb.pagina, pb.seccion, pb.boton
            """, (depto,))
        agrupado = {}
        for p in cursor.fetchall():
            agrupado.setdefault(p["pagina"], {}).setdefault(p["seccion"], []).append({
                "id": p["id"], "boton": p["boton"], "descripcion": p["descripcion"],
            })
        return jsonify(agrupado)
    except Exception as e:
        logger.error("Error listando permisos disponibles: %s", e)
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@bp.route("/api/gestion-roles-depto/permisos-rol/<int:rol_id>")
@requiere_permiso_dropdown(_PERM_PAGINA, _PERM_SECCION, _PERM_BOTON)
def permisos_rol(rol_id):
    """IDs de permisos actualmente asignados a un rol del alcance."""
    conn = None
    try:
        es_super, depto = alcance_actual()
        conn = get_db_connection()
        cursor = get_dict_cursor(conn)
        ok, _ = _rol_en_alcance(cursor, rol_id, es_super, depto)
        if not ok:
            return jsonify({"error": "Rol fuera de tu alcance"}), 403
        cursor.execute(
            "SELECT permiso_boton_id FROM rol_permisos_botones WHERE rol_id = %s",
            (rol_id,),
        )
        return jsonify([r["permiso_boton_id"] for r in cursor.fetchall()])
    except Exception as e:
        logger.error("Error obteniendo permisos del rol: %s", e)
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@bp.route("/api/gestion-roles-depto/guardar-rol", methods=["POST"])
@requiere_permiso_dropdown(_PERM_PAGINA, _PERM_SECCION, _PERM_BOTON)
def guardar_rol():
    """Crear o editar un rol del departamento del admin."""
    conn = None
    try:
        data = request.get_json() or {}
        usuario_actual = session.get("usuario")
        es_super, depto = alcance_actual()

        nombre = (data.get("nombre") or "").strip()
        descripcion = (data.get("descripcion") or "").strip()
        rol_id = data.get("rol_id")

        if not nombre:
            return jsonify({"error": "El nombre del rol es requerido"}), 400
        if nombre in _ROLES_RESERVADOS:
            return jsonify({"error": "Nombre de rol reservado"}), 403
        if not es_super and not depto:
            return jsonify({"error": "Tu usuario no tiene departamento asignado."}), 403

        # Departamento del rol: superadmin elige; delegado siempre su depto.
        depto_rol = (data.get("departamento") or "").strip() if es_super else depto
        depto_rol = depto_rol or None
        # Nivel acotado para delegados (no roles de sistema 8-10).
        nivel = data.get("nivel", 3)
        if not isinstance(nivel, int) or nivel < 1 or nivel > 7:
            nivel = 3

        conn = get_db_connection()
        cursor = get_dict_cursor(conn)

        if rol_id:
            ok, rol = _rol_en_alcance(cursor, rol_id, es_super, depto)
            if not ok:
                return jsonify({"error": "No puedes modificar este rol"}), 403
            # Evitar choque de nombre.
            cursor.execute(
                "SELECT id FROM roles WHERE nombre = %s AND id != %s", (nombre, rol_id)
            )
            if cursor.fetchone():
                return jsonify({"error": "Ya existe otro rol con ese nombre"}), 400
            cursor.execute(
                "UPDATE roles SET nombre = %s, descripcion = %s, departamento = %s WHERE id = %s",
                (nombre, descripcion, depto_rol, rol_id),
            )
            accion = "actualizar_rol_depto"
        else:
            cursor.execute("SELECT id FROM roles WHERE nombre = %s", (nombre,))
            if cursor.fetchone():
                return jsonify({"error": "Ya existe un rol con ese nombre"}), 400
            cursor.execute(
                """INSERT INTO roles (nombre, descripcion, nivel, departamento, activo)
                   VALUES (%s, %s, %s, %s, 1)""",
                (nombre, descripcion, nivel, depto_rol),
            )
            rol_id = cursor.lastrowid
            accion = "crear_rol_depto"

        conn.commit()
        auth_system.registrar_auditoria(
            usuario=usuario_actual, modulo="sistema", accion=accion,
            descripcion=f'Rol "{nombre}" (depto: {depto_rol})',
        )
        return jsonify({"success": True, "rol_id": rol_id, "mensaje": f'Rol "{nombre}" guardado'})
    except Exception as e:
        logger.exception("Error guardando rol depto: %s", e)
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@bp.route("/api/gestion-roles-depto/guardar-permisos", methods=["POST"])
@requiere_permiso_dropdown(_PERM_PAGINA, _PERM_SECCION, _PERM_BOTON)
def guardar_permisos():
    """Reemplazar los permisos de un rol, SOLO con permisos del alcance."""
    conn = None
    try:
        data = request.get_json() or {}
        usuario_actual = session.get("usuario")
        es_super, depto = alcance_actual()
        rol_id = data.get("rol_id")
        permisos_ids = [int(x) for x in (data.get("permisos_ids") or [])]

        if not rol_id:
            return jsonify({"error": "ID de rol requerido"}), 400

        conn = get_db_connection()
        cursor = get_dict_cursor(conn)

        ok, _ = _rol_en_alcance(cursor, rol_id, es_super, depto)
        if not ok:
            return jsonify({"error": "No puedes modificar este rol"}), 403

        # Conjunto de permisos que el admin PUEDE repartir.
        if es_super:
            cursor.execute("SELECT id FROM permisos_botones WHERE activo = 1")
            permitidos = {r["id"] for r in cursor.fetchall()}
        else:
            cursor.execute(
                """SELECT pb.id FROM permisos_botones pb
                   JOIN permiso_departamentos pd ON pd.permiso_boton_id = pb.id
                   WHERE pb.activo = 1 AND pd.departamento = %s""",
                (depto,),
            )
            permitidos = {r["id"] for r in cursor.fetchall()}

        invalidos = [pid for pid in permisos_ids if pid not in permitidos]
        if invalidos:
            return jsonify({
                "error": "Hay permisos fuera de tu área que no puedes asignar.",
            }), 403

        # IMPORTANTE: para no borrar permisos de OTRAS áreas que ya tenga el rol
        # (asignados por el superadmin), solo se reemplazan los del alcance.
        if es_super:
            cursor.execute("DELETE FROM rol_permisos_botones WHERE rol_id = %s", (rol_id,))
        else:
            cursor.execute(
                """DELETE rpb FROM rol_permisos_botones rpb
                   JOIN permiso_departamentos pd ON pd.permiso_boton_id = rpb.permiso_boton_id
                   WHERE rpb.rol_id = %s AND pd.departamento = %s""",
                (rol_id, depto),
            )
        for pid in permisos_ids:
            cursor.execute(
                "INSERT IGNORE INTO rol_permisos_botones (rol_id, permiso_boton_id) VALUES (%s, %s)",
                (rol_id, pid),
            )

        conn.commit()
        auth_system.invalidar_cache_permisos_botones()
        auth_system.registrar_auditoria(
            usuario=usuario_actual, modulo="sistema", accion="actualizar_permisos_rol_depto",
            descripcion=f"Permisos del rol {rol_id} actualizados (depto: {depto or 'superadmin'})",
        )
        return jsonify({"success": True, "mensaje": "Permisos actualizados"})
    except Exception as e:
        logger.exception("Error guardando permisos depto: %s", e)
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()
