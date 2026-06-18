"""Administracion de Usuarios para ILSAN MES.

Sistema completo de gestion de usuarios, roles, permisos y auditoria.
Forma parte del Panel de Administracion (boton del navbar, ruta `/admin/panel`).

Rutas principales (con url_prefix `/admin`, definido al registrar el blueprint):
  GET    /admin/panel                                  -> render panel
  GET    /admin/auditoria                              -> render auditoria
  GET    /admin/listar_usuarios                        -> JSON
  GET    /admin/obtener_usuario/<username>             -> JSON detalle
  POST   /admin/guardar_usuario                        -> crear/actualizar usuario
  POST   /admin/cambiar_estado_usuario                 -> activar/desactivar
  POST   /admin/desbloquear_usuario                    -> reset intentos fallidos
  DELETE /admin/borrar_usuario/<username>              -> eliminar permanentemente
  GET    /admin/listar_roles                           -> JSON roles + total_usuarios
  GET    /admin/obtener_permisos_rol/<rol_id>          -> permisos del rol
  GET    /admin/listar_permisos_dropdowns              -> permisos disponibles agrupados
  GET    /admin/obtener_permisos_dropdowns_rol/<rol_id>
  POST   /admin/actualizar_permisos_dropdowns_rol
  POST   /admin/sincronizar_permisos_dropdowns         -> scan LISTAS HTML
  GET    /admin/listar_permisos_botones
  GET    /admin/permisos_botones_rol/<rol_id>
  POST   /admin/actualizar_permisos_botones_rol
  GET    /admin/permisos_botones_usuario/<username>
  POST   /admin/verificar_permiso_dropdown
  GET    /admin/obtener_permisos_usuario_actual
  GET    /admin/buscar_auditoria
  GET    /admin/detalle_auditoria/<id>
  GET    /admin/estadisticas_auditoria
  GET    /admin/exportar_auditoria                     -> XLSX
  GET    /admin/actividad_reciente
  GET    /admin/verificar_permisos_usuario
  GET    /admin/test_permisos_debug                    -> sin auth, para debug
  POST   /admin/crear_rol
  DELETE /admin/eliminar_rol/<rol_id>
  PUT    /admin/actualizar_rol/<rol_id>

Migrado desde `app/user_admin.py` (2026-05-22). Cambios respecto al legacy:
  - `user_admin_bp` -> `bp` (encaja en el patron _MODULOS_REGISTRADOS)
  - `auth_system = AuthSystem()` (instancia local) -> import del singleton
    desde `app.api.shared`
  - Eliminada la funcion `init_admin_routes()` (codigo muerto)

Importa `AVAILABLE_CARGOS`, `AVAILABLE_DEPARTMENTS` y
`get_shipping_permission_dropdown_catalog` de `app.api.pda.shipping`.

NOTA WF_003: este modulo conserva `get_db_connection()` y `get_dict_cursor()`
directos porque tiene multiples transacciones complejas (crear_rol con
multiples INSERTs, sincronizar_permisos_dropdowns con N inserts/updates),
manejo de errores con rollback, y `cursor.lastrowid`. Migrar a
`execute_query()` requeriria reestructurar la logica de transacciones.
"""

import io
import json
import os
import tempfile
import time
import traceback
from datetime import datetime, timedelta
from functools import wraps

import mysql.connector
import pandas as pd
from flask import (
    Blueprint,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)

from app.api.shared import auth_system
from app.auth_system import ECO_CREATE_PERMISSION
from app.db_mysql import get_db_connection
from app.api.pda.shipping import (
    AVAILABLE_CARGOS,
    AVAILABLE_DEPARTMENTS,
    get_shipping_permission_dropdown_catalog,
)

import logging
logger = logging.getLogger(__name__)


# Importar MySQLdb para cursores de diccionario
try:
    import pymysql
    pymysql.install_as_MySQLdb()
    import MySQLdb
    MYSQLDB_AVAILABLE = True
    logger.info("MySQLdb disponible para user_admin")
except ImportError as e:
    MYSQLDB_AVAILABLE = False
    logger.warning(f"MySQLdb no disponible para user_admin: {e}")
    MySQLdb = None


bp = Blueprint("user_admin", __name__, url_prefix="/admin")

DEFAULT_USER_DEPARTMENTS = [
    'Almacén',
    'Producción',
    'Calidad',
    'Administración',
    'Sistemas',
    'Gerencia',
]
DEFAULT_USER_CARGOS = [
    'Almacenista',
    'Supervisor',
    'Operador',
    'Administrador',
]

EXTRA_DROPDOWN_PERMISSIONS = [
    ECO_CREATE_PERMISSION,
]


def _ensure_extra_dropdown_permissions(cursor):
    """Mantener permisos de accion que no salen de archivos LISTAS."""
    for permiso in EXTRA_DROPDOWN_PERMISSIONS:
        cursor.execute('''
            INSERT INTO permisos_botones (pagina, seccion, boton, descripcion, activo)
            VALUES (%s, %s, %s, %s, 1)
            ON DUPLICATE KEY UPDATE descripcion = VALUES(descripcion), activo = 1
        ''', (
            permiso['pagina'],
            permiso['seccion'],
            permiso['boton'],
            permiso['descripcion'],
        ))

        cursor.execute('''
            SELECT id FROM permisos_botones
            WHERE pagina = %s AND seccion = %s AND boton = %s
            LIMIT 1
        ''', (permiso['pagina'], permiso['seccion'], permiso['boton']))
        permiso_row = cursor.fetchone()
        permiso_id = permiso_row['id'] if isinstance(permiso_row, dict) else (permiso_row[0] if permiso_row else None)
        if not permiso_id:
            continue

        cursor.execute('SELECT id FROM roles WHERE nombre = %s AND activo = 1', ('superadmin',))
        superadmin_row = cursor.fetchone()
        superadmin_id = superadmin_row['id'] if isinstance(superadmin_row, dict) else (superadmin_row[0] if superadmin_row else None)
        if not superadmin_id:
            continue

        cursor.execute('''
            INSERT IGNORE INTO rol_permisos_botones (rol_id, permiso_boton_id)
            VALUES (%s, %s)
        ''', (superadmin_id, permiso_id))


def _merge_catalog_values(*groups):
    merged = []
    seen = set()

    for group in groups:
        for value in group:
            normalized = (value or '').strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            merged.append(normalized)

    return merged


def requiere_superadmin(f):
    """Restringir acciones criticas de roles/permisos al superadmin central."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        usuario = session.get('usuario')
        if not usuario:
            if request.is_json:
                return jsonify({'error': 'No autenticado', 'codigo': 401}), 401
            return redirect('/login')

        roles = auth_system.obtener_roles_usuario(usuario)
        if 'superadmin' not in roles:
            return jsonify({
                'error': 'Solo superadmin puede administrar roles y permisos',
                'codigo': 403,
            }), 403

        return f(*args, **kwargs)

    return decorated_function


def execute_with_retry(operation, max_retries=3, retry_delay=0.1):
    """Ejecuta una operacion de base de datos con reintentos automaticos"""
    for attempt in range(max_retries):
        try:
            return operation()
        except mysql.connector.Error as e:
            if "lock" in str(e).lower() and attempt < max_retries - 1:
                logger.info(f"Intento {attempt + 1}/{max_retries}: Base de datos ocupada, reintentando en {retry_delay}s...")
                time.sleep(retry_delay)
                retry_delay *= 2
                continue
            else:
                raise
        except Exception as e:
            raise


def get_dict_cursor(conn):
    """Obtener un cursor que devuelve diccionarios en lugar de tuplas."""
    if MYSQLDB_AVAILABLE and MySQLdb is not None:
        return conn.cursor(MySQLdb.cursors.DictCursor)
    else:
        return conn.cursor(dictionary=True)


@bp.route('/panel')
@auth_system.login_requerido_avanzado
@auth_system.requiere_permiso('sistema', 'usuarios')
def panel_administracion():
    """Panel principal de administracion de usuarios"""
    usuario = session.get('usuario')
    department_options = _merge_catalog_values(
        DEFAULT_USER_DEPARTMENTS,
        AVAILABLE_DEPARTMENTS,
    )
    cargo_options = _merge_catalog_values(
        DEFAULT_USER_CARGOS,
        AVAILABLE_CARGOS,
    )
    return render_template(
        'admin/panel_usuarios.html',
        usuario=usuario,
        department_options=department_options,
        cargo_options=cargo_options,
    )


@bp.route('/auditoria')
@auth_system.login_requerido_avanzado
@auth_system.requiere_permiso('sistema', 'auditoria')
def panel_auditoria():
    """Panel de auditoria y logs"""
    usuario = session.get('usuario')
    permisos = session.get('permisos', {})

    tiene_permisos_usuarios = False
    if isinstance(permisos, dict) and 'sistema' in permisos:
        tiene_permisos_usuarios = 'usuarios' in permisos['sistema']

    return render_template('admin/auditoria.html',
                         usuario=usuario,
                         tiene_permisos_usuarios=tiene_permisos_usuarios)


# === GESTIoN DE USUARIOS ===

@bp.route('/listar_usuarios')
@auth_system.login_requerido_avanzado
@auth_system.requiere_permiso('sistema', 'usuarios')
def listar_usuarios():
    """Obtener lista completa de usuarios con sus roles"""
    try:
        conn = get_db_connection()
        cursor = get_dict_cursor(conn)

        cursor.execute('''
            SELECT
                u.id, u.username, u.email, u.nombre_completo,
                u.departamento, u.cargo, u.activo, u.ultimo_acceso,
                u.fecha_creacion, u.intentos_fallidos, u.bloqueado_hasta,
                GROUP_CONCAT(r.nombre) as roles
            FROM usuarios_sistema u
            LEFT JOIN usuario_roles ur ON u.id = ur.usuario_id
            LEFT JOIN roles r ON ur.rol_id = r.id AND r.activo = 1
            GROUP BY u.id
            ORDER BY u.fecha_creacion DESC
        ''')

        usuarios = []
        for row in cursor.fetchall():
            usuario = row

            roles_str = usuario.get('roles', '') or ''
            usuario['roles'] = roles_str.split(',') if roles_str else []

            for campo in ['ultimo_acceso', 'fecha_creacion', 'bloqueado_hasta', 'fecha_modificacion']:
                if usuario.get(campo):
                    valor = usuario[campo]
                    if hasattr(valor, 'strftime'):
                        usuario[campo] = valor.strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        usuario[campo] = str(valor)

            bloqueado_hasta = usuario.get('bloqueado_hasta')
            if bloqueado_hasta:
                try:
                    if isinstance(bloqueado_hasta, str):
                        fecha_bloqueo = datetime.fromisoformat(bloqueado_hasta)
                    else:
                        fecha_bloqueo = bloqueado_hasta
                    usuario['bloqueado'] = fecha_bloqueo > auth_system.get_mexico_time().replace(tzinfo=None)
                except:
                    usuario['bloqueado'] = False
            else:
                usuario['bloqueado'] = False

            usuarios.append(usuario)

        conn.close()
        return jsonify(usuarios)

    except Exception as e:
        logger.error(f"Error listando usuarios: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/obtener_usuario/<username>')
@auth_system.login_requerido_avanzado
@auth_system.requiere_permiso('sistema', 'usuarios')
def obtener_usuario(username):
    """Obtener datos detallados de un usuario"""
    try:
        conn = get_db_connection()
        cursor = get_dict_cursor(conn)

        cursor.execute('SELECT * FROM usuarios_sistema WHERE username = %s', (username,))
        usuario = cursor.fetchone()
        if not usuario:
            return jsonify({'error': 'Usuario no encontrado'}), 404

        cursor.execute('''
            SELECT r.id, r.nombre, r.descripcion
            FROM roles r
            JOIN usuario_roles ur ON r.id = ur.rol_id
            WHERE ur.usuario_id = %s
        ''', (usuario['id'],))

        roles = cursor.fetchall()
        conn.close()

        usuario['roles'] = roles
        return jsonify(usuario)

    except Exception as e:
        logger.error(f"Error obteniendo usuario: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/guardar_usuario', methods=['POST'])
@auth_system.login_requerido_avanzado
@auth_system.requiere_permiso('sistema', 'usuarios')
def guardar_usuario():
    """Crear o actualizar un usuario"""
    try:
        data = request.get_json()
        usuario_actual = session.get('usuario')

        # PROTECCION: Bloquear modificacion del usuario admin
        if data.get('username') == 'admin':
            auth_system.registrar_auditoria(
                usuario=usuario_actual,
                modulo='sistema',
                accion='guardar_usuario_bloqueado',
                descripcion='Intento de modificar usuario admin bloqueado por seguridad',
                resultado='DENEGADO',
                datos_antes={'username': 'admin', 'accion': 'modificacion_bloqueada'}
            )
            return jsonify({
                'error': 'El usuario administrador esta protegido y no puede ser modificado por motivos de seguridad.',
                'success': False
            }), 403

        if not data.get('username'):
            return jsonify({'error': 'Username es requerido'}), 400

        if not data.get('nombre_completo'):
            return jsonify({'error': 'Nombre completo es requerido'}), 400

        conn = get_db_connection()
        cursor = get_dict_cursor(conn)

        cursor.execute('SELECT id FROM usuarios_sistema WHERE username = %s', (data['username'],))
        existe = cursor.fetchone()

        datos_antes = None
        if existe:
            cursor.execute('SELECT * FROM usuarios_sistema WHERE id = %s', (existe['id'],))
            datos_antes = cursor.fetchone()

        if existe:
            params = [
                data.get('nombre_completo'),
                data.get('email', ''),
                data.get('departamento', ''),
                data.get('cargo', ''),
                data.get('activo', 1),
                usuario_actual,
                auth_system.get_mexico_time_mysql(),
                data['username']
            ]

            if data.get('password') and data['password'].strip():
                cursor.execute('''
                    UPDATE usuarios_sistema SET
                        password_hash = %s,
                        nombre_completo = %s,
                        email = %s,
                        departamento = %s,
                        cargo = %s,
                        activo = %s,
                        modificado_por = %s,
                        fecha_modificacion = %s,
                        intentos_fallidos = 0,
                        bloqueado_hasta = NULL
                    WHERE username = %s
                ''', [auth_system.hash_password(data['password'])] + params)
            else:
                cursor.execute('''
                    UPDATE usuarios_sistema SET
                        nombre_completo = %s,
                        email = %s,
                        departamento = %s,
                        cargo = %s,
                        activo = %s,
                        modificado_por = %s,
                        fecha_modificacion = %s
                    WHERE username = %s
                ''', params)

            usuario_id = existe['id']
            accion = 'actualizar_usuario'
            mensaje = f'Usuario {data["username"]} actualizado'
        else:
            if not data.get('password'):
                return jsonify({'error': 'Password es requerido para nuevos usuarios'}), 400

            cursor.execute('''
                INSERT INTO usuarios_sistema (
                    username, password_hash, nombre_completo, email,
                    departamento, cargo, activo, creado_por
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                data['username'],
                auth_system.hash_password(data['password']),
                data.get('nombre_completo'),
                data.get('email', ''),
                data.get('departamento', ''),
                data.get('cargo', ''),
                data.get('activo', 1),
                usuario_actual
            ))

            usuario_id = cursor.lastrowid
            accion = 'crear_usuario'
            mensaje = f'Usuario {data["username"]} creado'

        # Actualizar roles
        cursor.execute('DELETE FROM usuario_roles WHERE usuario_id = %s', (usuario_id,))

        for rol_nombre in data.get('roles', []):
            cursor.execute('SELECT id FROM roles WHERE nombre = %s', (rol_nombre,))
            rol = cursor.fetchone()
            if rol:
                cursor.execute('''
                    INSERT INTO usuario_roles (usuario_id, rol_id, asignado_por)
                    VALUES (%s, %s, %s)
                ''', (usuario_id, rol['id'], usuario_actual))

        conn.commit()

        auth_system.registrar_auditoria(
            usuario=usuario_actual,
            modulo='sistema',
            accion=accion,
            descripcion=mensaje,
            datos_antes=datos_antes,
            datos_despues=data
        )

        conn.close()
        return jsonify({'success': True, 'mensaje': mensaje})

    except Exception as e:
        logger.error(f"Error guardando usuario: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@bp.route('/cambiar_estado_usuario', methods=['POST'])
@auth_system.login_requerido_avanzado
@auth_system.requiere_permiso('sistema', 'usuarios')
def cambiar_estado_usuario():
    """Activar/desactivar usuario"""
    try:
        data = request.get_json()
        username = data.get('username')
        activo = data.get('activo', True)
        usuario_actual = session.get('usuario')

        if username == 'admin':
            auth_system.registrar_auditoria(
                usuario=usuario_actual,
                modulo='sistema',
                accion='cambiar_estado_admin_bloqueado',
                descripcion='Intento de cambiar estado del usuario admin bloqueado por seguridad',
                resultado='DENEGADO',
                datos_antes={'username': 'admin', 'accion_intentada': 'cambiar_estado'}
            )
            return jsonify({
                'error': 'El usuario administrador esta protegido y no puede ser desactivado por motivos de seguridad.',
                'success': False
            }), 403

        if username == usuario_actual:
            return jsonify({'error': 'No puede desactivar su propio usuario'}), 400

        conn = get_db_connection()
        cursor = get_dict_cursor(conn)

        cursor.execute('SELECT * FROM usuarios_sistema WHERE username = %s', (username,))
        datos_antes = cursor.fetchone()

        cursor.execute('''
            UPDATE usuarios_sistema
            SET activo = %s, modificado_por = %s, fecha_modificacion = NOW()
            WHERE username = %s
        ''', (1 if activo else 0, usuario_actual, username))

        if cursor.rowcount > 0:
            if not activo:
                cursor.execute('''
                    UPDATE sesiones_activas
                    SET activa = 0
                    WHERE usuario_id = (SELECT id FROM usuarios_sistema WHERE username = %s)
                ''', (username,))

            conn.commit()

            accion = 'activar_usuario' if activo else 'desactivar_usuario'
            auth_system.registrar_auditoria(
                usuario=usuario_actual,
                modulo='sistema',
                accion=accion,
                descripcion=f'Usuario {username} {"activado" if activo else "desactivado"}',
                datos_antes={'activo': datos_antes['activo']},
                datos_despues={'activo': activo}
            )

            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Usuario no encontrado'}), 404

    except Exception as e:
        logger.error(f"Error cambiando estado: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()


@bp.route('/desbloquear_usuario', methods=['POST'])
@auth_system.login_requerido_avanzado
@auth_system.requiere_permiso('sistema', 'usuarios')
def desbloquear_usuario():
    """Desbloquear usuario manualmente"""
    try:
        data = request.get_json()
        username = data.get('username')
        usuario_actual = session.get('usuario')

        conn = get_db_connection()
        cursor = get_dict_cursor(conn)

        cursor.execute('''
            UPDATE usuarios_sistema
            SET intentos_fallidos = 0, bloqueado_hasta = NULL,
                modificado_por = %s, fecha_modificacion = NOW()
            WHERE username = %s
        ''', (usuario_actual, username))

        if cursor.rowcount > 0:
            conn.commit()

            auth_system.registrar_auditoria(
                usuario=usuario_actual,
                modulo='sistema',
                accion='desbloquear_usuario',
                descripcion=f'Usuario {username} desbloqueado manualmente'
            )

            return jsonify({'success': True, 'mensaje': f'Usuario {username} desbloqueado'})
        else:
            return jsonify({'error': 'Usuario no encontrado'}), 404

    except Exception as e:
        logger.error(f"Error desbloqueando usuario: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()


@bp.route('/borrar_usuario/<username>', methods=['DELETE'])
@auth_system.login_requerido_avanzado
@auth_system.requiere_permiso('sistema', 'usuarios')
def borrar_usuario(username):
    """Eliminar usuario permanentemente"""
    try:
        usuario_actual = session.get('usuario')

        if username == 'admin':
            auth_system.registrar_auditoria(
                usuario=usuario_actual,
                modulo='sistema',
                accion='borrar_admin_bloqueado',
                descripcion='Intento de borrar el usuario admin bloqueado por seguridad',
                resultado='DENEGADO',
                datos_antes={'username': 'admin', 'accion_intentada': 'borrar'}
            )
            return jsonify({
                'error': 'El usuario administrador esta protegido y no puede ser eliminado por motivos de seguridad.',
                'success': False
            }), 403

        if username == usuario_actual:
            return jsonify({'error': 'No puede eliminar su propio usuario'}), 400

        conn = get_db_connection()
        cursor = get_dict_cursor(conn)

        cursor.execute('SELECT * FROM usuarios_sistema WHERE username = %s', (username,))
        usuario_a_borrar = cursor.fetchone()

        if not usuario_a_borrar:
            return jsonify({'error': 'Usuario no encontrado'}), 404

        datos_usuario = dict(usuario_a_borrar)

        cursor.execute('''
            SELECT r.nombre FROM roles r
            JOIN usuario_roles ur ON r.id = ur.rol_id
            WHERE ur.usuario_id = %s
        ''', (datos_usuario['id'],))
        roles_usuario = [row['nombre'] for row in cursor.fetchall()]

        # Eliminar en orden para respetar las foreign keys
        cursor.execute('''
            DELETE FROM rol_permisos_botones
            WHERE rol_id IN (
                SELECT rol_id FROM usuario_roles WHERE usuario_id = %s
            )
        ''', (datos_usuario['id'],))

        cursor.execute('DELETE FROM usuario_roles WHERE usuario_id = %s', (datos_usuario['id'],))

        cursor.execute('DELETE FROM sesiones_activas WHERE usuario_id = (SELECT id FROM usuarios_sistema WHERE username = %s)', (username,))

        cursor.execute('DELETE FROM usuarios_sistema WHERE username = %s', (username,))

        if cursor.rowcount > 0:
            conn.commit()

            auth_system.registrar_auditoria(
                usuario=usuario_actual,
                modulo='sistema',
                accion='eliminar_usuario',
                descripcion=f'Usuario {username} eliminado permanentemente',
                datos_antes={
                    'username': username,
                    'nombre_completo': datos_usuario.get('nombre_completo'),
                    'departamento': datos_usuario.get('departamento'),
                    'roles': roles_usuario,
                    'activo': bool(datos_usuario.get('activo'))
                }
            )

            return jsonify({
                'success': True,
                'mensaje': f'Usuario {username} eliminado exitosamente'
            })
        else:
            return jsonify({'error': 'No se pudo eliminar el usuario'}), 500

    except Exception as e:
        logger.error(f"Error eliminando usuario: {e}")
        traceback.print_exc()
        return jsonify({'error': f'Error interno: {str(e)}'}), 500
    finally:
        if 'conn' in locals():
            conn.close()


# === GESTIoN DE ROLES ===

@bp.route('/listar_roles')
@auth_system.login_requerido_avanzado
@auth_system.requiere_permiso('sistema', 'usuarios')
def listar_roles():
    """Obtener lista de roles disponibles"""
    try:
        conn = get_db_connection()
        cursor = get_dict_cursor(conn)

        cursor.execute('''
            SELECT r.*, COUNT(ur.usuario_id) as total_usuarios
            FROM roles r
            LEFT JOIN usuario_roles ur ON r.id = ur.rol_id
            GROUP BY r.id
            ORDER BY r.nivel DESC, r.nombre
        ''')

        roles = cursor.fetchall()
        conn.close()
        return jsonify(roles)

    except Exception as e:
        logger.error(f"Error listando roles: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@bp.route('/obtener_permisos_rol/<int:rol_id>')
@auth_system.login_requerido_avanzado
@auth_system.requiere_permiso('sistema', 'usuarios')
def obtener_permisos_rol(rol_id):
    """Obtener permisos de un rol especifico"""
    try:
        conn = get_db_connection()
        cursor = get_dict_cursor(conn)

        cursor.execute('''
            SELECT p.modulo, p.accion, p.descripcion
            FROM permisos p
            JOIN rol_permisos rp ON p.id = rp.permiso_id
            WHERE rp.rol_id = %s AND p.activo = 1
            ORDER BY p.modulo, p.accion
        ''', (rol_id,))

        permisos = cursor.fetchall()
        conn.close()
        return jsonify(permisos)

    except Exception as e:
        logger.error(f"Error obteniendo permisos del rol: {e}")
        return jsonify({'error': str(e)}), 500


# === GESTIoN DE PERMISOS DE BOTONES/DROPDOWNS ===

@bp.route('/listar_permisos_dropdowns')
@auth_system.login_requerido_avanzado
@auth_system.requiere_permiso('sistema', 'usuarios')
def listar_permisos_dropdowns():
    """Obtener lista de todos los permisos de dropdowns disponibles agrupados por lista"""
    try:
        conn = get_db_connection()
        cursor = get_dict_cursor(conn)

        _ensure_extra_dropdown_permissions(cursor)
        conn.commit()

        cursor.execute('''
            SELECT pb.id, pb.pagina, pb.seccion, pb.boton, pb.descripcion, pb.activo
            FROM permisos_botones pb
            WHERE pb.activo = 1
            ORDER BY pb.pagina, pb.seccion, pb.boton
        ''')

        permisos = cursor.fetchall()
        conn.close()

        permisos_agrupados = {}
        for permiso in permisos:
            pagina = permiso['pagina']
            if pagina not in permisos_agrupados:
                permisos_agrupados[pagina] = {}

            seccion = permiso['seccion']
            if seccion not in permisos_agrupados[pagina]:
                permisos_agrupados[pagina][seccion] = []

            permisos_agrupados[pagina][seccion].append({
                'id': permiso['id'],
                'boton': permiso['boton'],
                'descripcion': permiso['descripcion']
            })

        return jsonify(permisos_agrupados)

    except Exception as e:
        logger.error(f"Error listando permisos de dropdowns: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@bp.route('/obtener_permisos_dropdowns_rol/<int:rol_id>')
@auth_system.login_requerido_avanzado
@auth_system.requiere_permiso('sistema', 'usuarios')
def obtener_permisos_dropdowns_rol(rol_id):
    """Obtener permisos de dropdowns de un rol especifico"""
    try:
        conn = get_db_connection()
        cursor = get_dict_cursor(conn)

        cursor.execute('''
            SELECT pb.id, pb.pagina, pb.seccion, pb.boton, pb.descripcion
            FROM permisos_botones pb
            JOIN rol_permisos_botones rpb ON pb.id = rpb.permiso_boton_id
            WHERE rpb.rol_id = %s AND pb.activo = 1
            ORDER BY pb.pagina, pb.seccion, pb.boton
        ''', (rol_id,))

        permisos = cursor.fetchall()
        conn.close()
        return jsonify(permisos)

    except Exception as e:
        logger.error(f"Error obteniendo permisos de dropdowns del rol: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@bp.route('/actualizar_permisos_dropdowns_rol', methods=['POST'])
@auth_system.login_requerido_avanzado
@auth_system.requiere_permiso('sistema', 'usuarios')
@requiere_superadmin
def actualizar_permisos_dropdowns_rol():
    """Actualizar permisos de dropdowns de un rol"""
    try:
        data = request.get_json()
        rol_id = data.get('rol_id')
        permisos_ids = data.get('permisos_ids', [])

        if not rol_id:
            return jsonify({'success': False, 'error': 'ID de rol requerido'}), 400

        conn = get_db_connection()
        cursor = get_dict_cursor(conn)

        cursor.execute('DELETE FROM rol_permisos_botones WHERE rol_id = %s', (rol_id,))

        for permiso_id in permisos_ids:
            cursor.execute('''
                INSERT INTO rol_permisos_botones (rol_id, permiso_boton_id)
                VALUES (%s, %s)
            ''', (rol_id, permiso_id))

        conn.commit()
        conn.close()
        auth_system.invalidar_cache_permisos_botones()

        auth_system.registrar_auditoria(
            usuario=session.get('usuario'),
            modulo='sistema',
            accion='actualizar_permisos_dropdowns',
            descripcion=f'Actualizo permisos de dropdowns para rol ID {rol_id}'
        )

        return jsonify({
            'success': True,
            'mensaje': 'Permisos de dropdowns actualizados exitosamente'
        })

    except Exception as e:
        logger.error(f"Error actualizando permisos de dropdowns: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/sincronizar_permisos_dropdowns', methods=['POST'])
@auth_system.login_requerido_avanzado
@auth_system.requiere_permiso('sistema', 'usuarios')
@requiere_superadmin
def sincronizar_permisos_dropdowns():
    """Sincronizar permisos de dropdowns desde archivos LISTAS"""
    import re
    from bs4 import BeautifulSoup

    try:
        listas_path = os.path.join('app', 'templates', 'LISTAS')

        if not os.path.exists(listas_path):
            return jsonify({'success': False, 'error': 'Carpeta LISTAS no encontrada'}), 400

        archivos_html = [f for f in os.listdir(listas_path)
                         if f.endswith('.html') and f != 'menu_sidebar.html']

        permisos_encontrados = []

        for archivo in archivos_html:
            archivo_path = os.path.join(listas_path, archivo)

            try:
                with open(archivo_path, 'r', encoding='utf-8') as f:
                    contenido = f.read()

                soup = BeautifulSoup(contenido, 'html.parser')

                elementos_con_permisos = soup.find_all(attrs={
                    'data-permiso-pagina': True,
                    'data-permiso-seccion': True,
                    'data-permiso-boton': True
                })

                for elemento in elementos_con_permisos:
                    pagina = elemento.get('data-permiso-pagina', '').strip()
                    seccion = elemento.get('data-permiso-seccion', '').strip()
                    boton = elemento.get('data-permiso-boton', '').strip()

                    if pagina and seccion and boton:
                        descripcion = elemento.get_text(strip=True)
                        if not descripcion:
                            descripcion = f"Acceso a {boton}"

                        if not any(p['pagina'] == pagina and p['seccion'] == seccion and p['boton'] == boton
                                  for p in permisos_encontrados):
                            permisos_encontrados.append({
                                'pagina': pagina,
                                'seccion': seccion,
                                'boton': boton,
                                'descripcion': descripcion
                            })

            except Exception as e:
                logger.error(f"Error procesando {archivo}: {e}")
                continue

        # Agregar permisos del modulo movil de embarques
        for permiso in get_shipping_permission_dropdown_catalog() + EXTRA_DROPDOWN_PERMISSIONS:
            if not any(
                p['pagina'] == permiso['pagina']
                and p['seccion'] == permiso['seccion']
                and p['boton'] == permiso['boton']
                for p in permisos_encontrados
            ):
                permisos_encontrados.append({
                    'pagina': permiso['pagina'],
                    'seccion': permiso['seccion'],
                    'boton': permiso['boton'],
                    'descripcion': permiso['descripcion'],
                })

        conn = get_db_connection()
        cursor = get_dict_cursor(conn)

        _ensure_extra_dropdown_permissions(cursor)

        cursor.execute('SELECT id, pagina, seccion, boton FROM permisos_botones WHERE activo = 1')
        permisos_bd = cursor.fetchall()
        permisos_bd_set = {(p['pagina'], p['seccion'], p['boton']) for p in permisos_bd}

        permisos_archivos_set = {(p['pagina'], p['seccion'], p['boton']) for p in permisos_encontrados}

        permisos_nuevos = permisos_archivos_set - permisos_bd_set
        permisos_obsoletos = permisos_bd_set - permisos_archivos_set

        for pagina, seccion, boton in permisos_nuevos:
            permiso_completo = next(p for p in permisos_encontrados
                                  if p['pagina'] == pagina and p['seccion'] == seccion and p['boton'] == boton)

            cursor.execute('''
                INSERT INTO permisos_botones (pagina, seccion, boton, descripcion, activo)
                VALUES (%s, %s, %s, %s, 1)
            ''', (pagina, seccion, boton, permiso_completo['descripcion']))

        # Mantener al rol superadmin con acceso total a los permisos recien sincronizados.
        cursor.execute('SELECT id FROM roles WHERE nombre = %s AND activo = 1', ('superadmin',))
        superadmin_role = cursor.fetchone()
        if superadmin_role:
            superadmin_role_id = superadmin_role['id']
            for pagina, seccion, boton in permisos_nuevos:
                cursor.execute('''
                    SELECT id FROM permisos_botones
                    WHERE pagina = %s AND seccion = %s AND boton = %s AND activo = 1
                ''', (pagina, seccion, boton))
                permiso_row = cursor.fetchone()
                if not permiso_row:
                    continue

                cursor.execute('''
                    SELECT 1
                    FROM rol_permisos_botones
                    WHERE rol_id = %s AND permiso_boton_id = %s
                    LIMIT 1
                ''', (superadmin_role_id, permiso_row['id']))

                if cursor.fetchone() is None:
                    cursor.execute('''
                        INSERT INTO rol_permisos_botones (rol_id, permiso_boton_id)
                        VALUES (%s, %s)
                    ''', (superadmin_role_id, permiso_row['id']))

        for pagina, seccion, boton in permisos_obsoletos:
            cursor.execute('''
                UPDATE permisos_botones
                SET activo = 0
                WHERE pagina = %s AND seccion = %s AND boton = %s
            ''', (pagina, seccion, boton))

        permisos_existentes = permisos_archivos_set & permisos_bd_set
        for pagina, seccion, boton in permisos_existentes:
            permiso_completo = next(p for p in permisos_encontrados
                                  if p['pagina'] == pagina and p['seccion'] == seccion and p['boton'] == boton)

            cursor.execute('''
                UPDATE permisos_botones
                SET descripcion = %s
                WHERE pagina = %s AND seccion = %s AND boton = %s AND activo = 1
            ''', (permiso_completo['descripcion'], pagina, seccion, boton))

        conn.commit()
        conn.close()
        auth_system.invalidar_cache_permisos_botones()

        try:
            auth_system.registrar_actividad(
                usuario_id=session.get('usuario_id'),
                accion='sincronizar_permisos_dropdowns',
                detalles=f'Nuevos: {len(permisos_nuevos)}, Desactivados: {len(permisos_obsoletos)}'
            )
        except:
            pass

        return jsonify({
            'success': True,
            'total_encontrados': len(permisos_encontrados),
            'nuevos_agregados': len(permisos_nuevos),
            'desactivados': len(permisos_obsoletos),
            'existentes_actualizados': len(permisos_existentes)
        })

    except Exception as e:
        logger.error(f"Error sincronizando permisos de dropdowns: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/listar_permisos_botones')
@auth_system.login_requerido_avanzado
@auth_system.requiere_permiso('sistema', 'usuarios')
def listar_permisos_botones():
    """Obtener lista de todos los permisos de botones disponibles"""
    try:
        conn = get_db_connection()
        cursor = get_dict_cursor(conn)

        cursor.execute('''
            SELECT * FROM permisos_botones
            WHERE activo = 1
            ORDER BY pagina, seccion, boton
        ''')

        permisos = cursor.fetchall()
        conn.close()
        return jsonify(permisos)

    except Exception as e:
        logger.error(f"Error listando permisos de botones: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/permisos_botones_rol/<int:rol_id>')
@auth_system.login_requerido_avanzado
@auth_system.requiere_permiso('sistema', 'usuarios')
def obtener_permisos_botones_rol(rol_id):
    """Obtener permisos de botones de un rol especifico"""
    try:
        conn = get_db_connection()
        cursor = get_dict_cursor(conn)

        cursor.execute('''
            SELECT pb.id, pb.pagina, pb.seccion, pb.boton, pb.descripcion
            FROM permisos_botones pb
            JOIN rol_permisos_botones rpb ON pb.id = rpb.permiso_boton_id
            WHERE rpb.rol_id = %s AND pb.activo = 1
            ORDER BY pb.pagina, pb.seccion, pb.boton
        ''', (rol_id,))

        permisos = cursor.fetchall()
        conn.close()
        return jsonify(permisos)

    except Exception as e:
        logger.error(f"Error obteniendo permisos de botones del rol: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/actualizar_permisos_botones_rol', methods=['POST'])
@auth_system.login_requerido_avanzado
@auth_system.requiere_permiso('sistema', 'usuarios')
def actualizar_permisos_botones_rol():
    """Actualizar permisos de botones para un rol"""
    try:
        data = request.get_json()
        rol_id = data.get('rol_id')
        permisos_botones_ids = data.get('permisos_botones_ids', [])
        usuario_actual = session.get('usuario')

        if not rol_id:
            return jsonify({'error': 'ID de rol requerido'}), 400

        conn = get_db_connection()
        cursor = get_dict_cursor(conn)

        cursor.execute('SELECT nombre FROM roles WHERE id = %s', (rol_id,))
        rol = cursor.fetchone()
        if not rol:
            return jsonify({'error': 'Rol no encontrado'}), 404

        cursor.execute('''
            SELECT pb.boton, pb.pagina, pb.seccion
            FROM permisos_botones pb
            JOIN rol_permisos_botones rpb ON pb.id = rpb.permiso_boton_id
            WHERE rpb.rol_id = %s
        ''', (rol_id,))
        permisos_anteriores = cursor.fetchall()

        cursor.execute('DELETE FROM rol_permisos_botones WHERE rol_id = %s', (rol_id,))

        for permiso_boton_id in permisos_botones_ids:
            cursor.execute('''
                INSERT INTO rol_permisos_botones (rol_id, permiso_boton_id)
                VALUES (%s, %s)
            ''', (rol_id, permiso_boton_id))

        cursor.execute('''
            SELECT pb.boton, pb.pagina, pb.seccion
            FROM permisos_botones pb
            JOIN rol_permisos_botones rpb ON pb.id = rpb.permiso_boton_id
            WHERE rpb.rol_id = %s
        ''', (rol_id,))
        permisos_nuevos = cursor.fetchall()

        conn.commit()

        auth_system.registrar_auditoria(
            usuario=usuario_actual,
            modulo='sistema',
            accion='actualizar_permisos_botones_rol',
            descripcion=f'Actualizo permisos de botones del rol {rol["nombre"]}',
            datos_antes={'permisos': permisos_anteriores},
            datos_despues={'permisos': permisos_nuevos}
        )

        conn.close()
        return jsonify({'success': True, 'mensaje': f'Permisos de botones del rol {rol["nombre"]} actualizados'})

    except Exception as e:
        logger.error(f"Error actualizando permisos de botones del rol: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/permisos_botones_usuario/<username>')
@auth_system.login_requerido_avanzado
@auth_system.requiere_permiso('sistema', 'usuarios')
def obtener_permisos_botones_usuario(username):
    """Obtener permisos de botones de un usuario especifico"""
    try:
        permisos_botones = auth_system.obtener_permisos_botones_usuario(username)
        return jsonify(permisos_botones)

    except Exception as e:
        logger.error(f"Error obteniendo permisos de botones del usuario: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/verificar_permiso_dropdown', methods=['POST'])
@auth_system.login_requerido_avanzado
def verificar_permiso_dropdown():
    """Verificar si el usuario actual tiene permiso para un dropdown especifico"""
    try:
        data = request.get_json()
        pagina = data.get('pagina')
        seccion = data.get('seccion')
        boton = data.get('boton')

        if not all([pagina, seccion, boton]):
            return jsonify({'error': 'Faltan parametros requeridos'}), 400

        username = session.get('usuario')
        if not username:
            return jsonify({'tiene_permiso': False, 'error': 'Usuario no autenticado'}), 401

        tiene_permiso = auth_system.verificar_permiso_boton(username, pagina, seccion, boton)

        return jsonify({'tiene_permiso': tiene_permiso})

    except Exception as e:
        logger.error(f"Error verificando permiso de dropdown: {e}")
        return jsonify({'tiene_permiso': False, 'error': str(e)}), 500


@bp.route('/obtener_permisos_usuario_actual')
@auth_system.login_requerido_avanzado
def obtener_permisos_usuario_actual():
    """Obtener todos los permisos de dropdowns del usuario actual"""
    try:
        username = session.get('usuario')
        if not username:
            return jsonify({'error': 'Usuario no autenticado'}), 401

        permisos = auth_system.obtener_permisos_botones_usuario(username)
        permisos_dict = {}
        total_permisos = 0
        for pagina, secciones in permisos.items():
            permisos_dict[pagina] = {}
            for seccion, botones in secciones.items():
                permisos_dict[pagina][seccion] = []
                for item in botones:
                    boton = item.get('boton') if isinstance(item, dict) else item
                    if not boton:
                        continue
                    permisos_dict[pagina][seccion].append(boton)
                    total_permisos += 1

        return jsonify({
            'permisos': permisos_dict,
            'usuario': username,
            'rol': auth_system.obtener_rol_principal_usuario(username),
            'total_permisos': total_permisos
        })

    except Exception as e:
        logger.error(f"Error obteniendo permisos del usuario actual: {e}")
        return jsonify({'error': str(e)}), 500


# === AUDITORIA Y LOGS ===

@bp.route('/buscar_auditoria')
@auth_system.login_requerido_avanzado
@auth_system.requiere_permiso('sistema', 'auditoria')
def buscar_auditoria():
    """Buscar registros de auditoria con filtros"""
    try:
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        usuario = request.args.get('usuario', '').strip()
        modulo = request.args.get('modulo', '').strip()
        accion = request.args.get('accion', '').strip()
        resultado = request.args.get('resultado', '').strip()
        limite = int(request.args.get('limite', 100))

        conn = get_db_connection()
        cursor = get_dict_cursor(conn)

        query = 'SELECT * FROM auditoria WHERE 1=1'
        params = []

        if fecha_inicio:
            query += ' AND DATE(fecha_hora) >= %s'
            params.append(fecha_inicio)

        if fecha_fin:
            query += ' AND DATE(fecha_hora) <= %s'
            params.append(fecha_fin)

        if usuario:
            query += ' AND usuario LIKE %s'
            params.append(f'%{usuario}%')

        if modulo:
            query += ' AND modulo = %s'
            params.append(modulo)

        if accion:
            query += ' AND accion LIKE %s'
            params.append(f'%{accion}%')

        if resultado:
            query += ' AND resultado = %s'
            params.append(resultado)

        query += ' ORDER BY fecha_hora DESC LIMIT %s'
        params.append(limite)

        cursor.execute(query, params)
        registros = cursor.fetchall()

        cursor.execute('''
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN resultado = 'EXITOSO' THEN 1 ELSE 0 END) as exitosos,
                SUM(CASE WHEN resultado = 'ERROR' THEN 1 ELSE 0 END) as errores,
                SUM(CASE WHEN resultado = 'DENEGADO' THEN 1 ELSE 0 END) as denegados
            FROM auditoria
            WHERE DATE(fecha_hora) = DATE('now')
        ''')

        stats = cursor.fetchone()
        conn.close()

        return jsonify({
            'registros': registros,
            'estadisticas': stats,
            'total_encontrados': len(registros)
        })

    except Exception as e:
        logger.error(f"Error buscando auditoria: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/detalle_auditoria/<int:id>')
@auth_system.login_requerido_avanzado
@auth_system.requiere_permiso('sistema', 'auditoria')
def detalle_auditoria(id):
    """Obtener detalles completos de un registro de auditoria"""
    try:
        conn = get_db_connection()
        cursor = get_dict_cursor(conn)

        cursor.execute('SELECT * FROM auditoria WHERE id = %s', (id,))
        registro = cursor.fetchone()

        if not registro:
            return jsonify({'error': 'Registro no encontrado'}), 404

        conn.close()

        detalle = dict(registro)

        if detalle['datos_antes']:
            try:
                detalle['datos_antes_json'] = json.loads(detalle['datos_antes'])
            except:
                detalle['datos_antes_json'] = None

        if detalle['datos_despues']:
            try:
                detalle['datos_despues_json'] = json.loads(detalle['datos_despues'])
            except:
                detalle['datos_despues_json'] = None

        return jsonify(detalle)

    except Exception as e:
        logger.error(f"Error obteniendo detalle de auditoria: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/estadisticas_auditoria')
@auth_system.login_requerido_avanzado
@auth_system.requiere_permiso('sistema', 'auditoria')
def estadisticas_auditoria():
    """Obtener estadisticas de auditoria para dashboard"""
    try:
        conn = get_db_connection()
        cursor = get_dict_cursor(conn)

        cursor.execute('''
            SELECT COUNT(*) as total
            FROM auditoria
            WHERE DATE(fecha_hora) = DATE('now')
        ''')
        acciones_hoy = cursor.fetchone()['total']

        cursor.execute('''
            SELECT COUNT(DISTINCT usuario) as total
            FROM auditoria
            WHERE DATE(fecha_hora) = DATE('now')
        ''')
        usuarios_activos = cursor.fetchone()['total']

        cursor.execute('''
            SELECT COUNT(*) as total
            FROM auditoria
            WHERE accion LIKE '%exportar%'
            AND fecha_hora >= DATE('now', '-7 days')
        ''')
        exportaciones = cursor.fetchone()['total']

        cursor.execute('''
            SELECT COUNT(*) as total
            FROM auditoria
            WHERE resultado = 'ERROR'
            AND fecha_hora >= DATE('now', '-7 days')
        ''')
        errores = cursor.fetchone()['total']

        cursor.execute('''
            SELECT modulo, COUNT(*) as total
            FROM auditoria
            WHERE fecha_hora >= DATE('now', '-7 days')
            GROUP BY modulo
            ORDER BY total DESC
        ''')
        actividad_modulos = cursor.fetchall()

        cursor.execute('''
            SELECT usuario, COUNT(*) as total
            FROM auditoria
            WHERE fecha_hora >= DATE('now', '-7 days')
            GROUP BY usuario
            ORDER BY total DESC
            LIMIT 10
        ''')
        usuarios_mas_activos = cursor.fetchall()

        conn.close()

        return jsonify({
            'acciones_hoy': acciones_hoy,
            'usuarios_activos_hoy': usuarios_activos,
            'exportaciones_semana': exportaciones,
            'errores_semana': errores,
            'actividad_por_modulo': actividad_modulos,
            'usuarios_mas_activos': usuarios_mas_activos
        })

    except Exception as e:
        logger.error(f"Error obteniendo estadisticas: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/exportar_auditoria')
@auth_system.login_requerido_avanzado
@auth_system.requiere_permiso('sistema', 'auditoria')
def exportar_auditoria():
    """Exportar registros de auditoria a Excel"""
    try:
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        usuario = request.args.get('usuario', '').strip()
        modulo = request.args.get('modulo', '').strip()

        conn = get_db_connection()
        cursor = get_dict_cursor(conn)

        query = '''
            SELECT
                fecha_hora, usuario, modulo, accion, descripcion,
                ip_address, resultado, duracion_ms, endpoint
            FROM auditoria WHERE 1=1
        '''
        params = []

        if fecha_inicio:
            query += ' AND DATE(fecha_hora) >= %s'
            params.append(fecha_inicio)

        if fecha_fin:
            query += ' AND DATE(fecha_hora) <= %s'
            params.append(fecha_fin)

        if usuario:
            query += ' AND usuario LIKE %s'
            params.append(f'%{usuario}%')

        if modulo:
            query += ' AND modulo = %s'
            params.append(modulo)

        query += ' ORDER BY fecha_hora DESC LIMIT 10000'

        cursor.execute(query, params)
        datos = cursor.fetchall()
        conn.close()

        if not datos:
            return jsonify({'error': 'No hay datos para exportar'}), 400

        df = pd.DataFrame(datos)

        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
            df.to_excel(tmp.name, index=False, sheet_name='Auditoria')

            auth_system.registrar_auditoria(
                usuario=session.get('usuario'),
                modulo='sistema',
                accion='exportar_auditoria',
                descripcion=f'Exporto {len(datos)} registros de auditoria'
            )

            return send_file(
                tmp.name,
                as_attachment=True,
                download_name=f'auditoria_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )

    except Exception as e:
        logger.error(f"Error exportando auditoria: {e}")
        return jsonify({'error': str(e)}), 500


# === FUNCIONES DE UTILIDAD ===

@bp.route('/actividad_reciente')
@auth_system.login_requerido_avanzado
@auth_system.requiere_permiso('sistema', 'auditoria')
def actividad_reciente():
    """Obtener actividad reciente para dashboard en tiempo real"""
    try:
        conn = get_db_connection()
        cursor = get_dict_cursor(conn)

        cursor.execute('''
            SELECT DISTINCT usuario,
                MAX(fecha_hora) as ultima_actividad,
                MAX(accion) as ultima_accion
            FROM auditoria
            WHERE fecha_hora >= DATE_SUB(NOW(), INTERVAL 15 MINUTE)
            GROUP BY usuario
            ORDER BY ultima_actividad DESC
        ''')

        usuarios_activos = []
        for row in cursor.fetchall():
            tiempo = datetime.fromisoformat(row['ultima_actividad'])
            hace = (auth_system.get_mexico_time().replace(tzinfo=None) - tiempo).total_seconds()
            if hace < 60:
                hace_texto = f"{int(hace)}s"
            else:
                hace_texto = f"{int(hace/60)}m"

            usuarios_activos.append({
                'usuario': row['usuario'],
                'ultima_accion': row['ultima_accion'],
                'hace': hace_texto
            })

        cursor.execute('''
            SELECT usuario, modulo, accion, descripcion, fecha_hora
            FROM auditoria
            ORDER BY fecha_hora DESC
            LIMIT 10
        ''')

        ultimas_acciones = cursor.fetchall()
        conn.close()

        return jsonify({
            'usuarios_activos': usuarios_activos,
            'ultimas_acciones': ultimas_acciones
        })

    except Exception as e:
        logger.error(f"Error obteniendo actividad reciente: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/verificar_permisos_usuario')
@auth_system.login_requerido_avanzado
def verificar_permisos_usuario():
    """Obtener todos los permisos de botones del usuario actual"""
    try:
        username = session.get('usuario')
        if not username:
            return jsonify({'error': 'Usuario no autenticado'}), 401

        conn = get_db_connection()
        cursor = get_dict_cursor(conn)

        cursor.execute('''
            SELECT r.nombre
            FROM usuarios_sistema u
            JOIN usuario_roles ur ON u.id = ur.usuario_id
            JOIN roles r ON ur.rol_id = r.id
            WHERE u.username = %s AND u.activo = 1 AND r.activo = 1
            ORDER BY r.nivel DESC
            LIMIT 1
        ''', (username,))

        usuario_rol = cursor.fetchone()
        if not usuario_rol:
            conn.close()
            return jsonify({'error': 'Usuario sin roles asignados'}), 403

        rol_nombre = usuario_rol[0]

        if rol_nombre == 'superadmin':
            permisos_estructurados = {
                'LISTA_DE_MATERIALES': {
                    'header': ['nuevo', 'editar', 'eliminar', 'exportar', 'importar'],
                    'tabla': ['ver', 'filtrar', 'ordenar'],
                    'acciones': ['guardar', 'cancelar', 'actualizar']
                },
                'CONTROL_MATERIAL': {
                    'header': ['nuevo', 'editar', 'eliminar', 'exportar'],
                    'tabla': ['ver', 'filtrar', 'ordenar'],
                    'acciones': ['guardar', 'cancelar']
                },
                'CONTROL_PRODUCCION': {
                    'header': ['nuevo', 'editar', 'eliminar', 'exportar'],
                    'tabla': ['ver', 'filtrar', 'ordenar'],
                    'acciones': ['guardar', 'cancelar']
                },
                'ADMIN': {
                    'usuarios': ['crear', 'editar', 'eliminar', 'ver'],
                    'roles': ['crear', 'editar', 'eliminar', 'ver'],
                    'permisos': ['asignar', 'revocar', 'ver']
                }
            }
        else:
            cursor.execute('''
                SELECT DISTINCT pb.pagina, pb.seccion, pb.boton
                FROM usuarios_sistema u
                JOIN usuario_roles ur ON u.id = ur.usuario_id
                JOIN rol_permisos_botones rpb ON ur.rol_id = rpb.rol_id
                JOIN permisos_botones pb ON rpb.permiso_boton_id = pb.id
                WHERE u.username = %s AND u.activo = 1 AND pb.activo = 1
                ORDER BY pb.pagina, pb.seccion, pb.boton
            ''', (username,))

            permisos_raw = cursor.fetchall()

            permisos_estructurados = {}
            for permiso in permisos_raw:
                pagina, seccion, boton = permiso

                if pagina not in permisos_estructurados:
                    permisos_estructurados[pagina] = {}

                if seccion not in permisos_estructurados[pagina]:
                    permisos_estructurados[pagina][seccion] = []

                permisos_estructurados[pagina][seccion].append(boton)

        conn.close()
        return jsonify(permisos_estructurados)

    except Exception as e:
        logger.error(f"Error verificando permisos del usuario: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/test_permisos_debug')
def test_permisos_debug():
    """Endpoint temporal para debuggear permisos (sin autenticacion)"""
    try:
        conn = get_db_connection()
        cursor = get_dict_cursor(conn)

        cursor.execute('SELECT id, username FROM usuarios_sistema WHERE username = %s', ('Yahir',))
        admin_result = cursor.fetchone()

        if not admin_result:
            return jsonify({'error': 'Usuario Yahir no encontrado'}), 404

        usuario_id, username = admin_result

        cursor.execute('''
            SELECT r.nombre
            FROM usuarios_sistema u
            JOIN usuario_roles ur ON u.id = ur.usuario_id
            JOIN roles r ON ur.rol_id = r.id
            WHERE u.username = %s AND u.activo = 1 AND r.activo = 1
            ORDER BY r.nivel DESC
            LIMIT 1
        ''', (username,))

        usuario_rol = cursor.fetchone()
        if not usuario_rol:
            return jsonify({'error': 'Usuario sin roles asignados'}), 403

        rol_nombre = usuario_rol[0]

        if rol_nombre == 'superadmin':
            permisos_test = {
                'usuario': username,
                'rol': rol_nombre,
                'tipo': 'superadmin_completo',
                'permisos': {
                    'LISTA_DE_MATERIALES': {
                        'header': ['nuevo', 'editar', 'eliminar', 'exportar', 'importar'],
                        'tabla': ['ver', 'filtrar', 'ordenar'],
                        'acciones': ['guardar', 'cancelar', 'actualizar']
                    },
                    'CONTROL_MATERIAL': {
                        'header': ['nuevo', 'editar', 'eliminar', 'exportar'],
                        'tabla': ['ver', 'filtrar', 'ordenar'],
                        'acciones': ['guardar', 'cancelar']
                    }
                }
            }
        else:
            cursor.execute('''
                SELECT DISTINCT rpb.pagina, rpb.seccion, rpb.boton
                FROM usuarios_sistema u
                JOIN usuario_roles ur ON u.id = ur.usuario_id
                JOIN rol_permisos_botones rpb ON ur.rol_id = rpb.rol_id
                WHERE u.username = %s AND u.activo = 1
                ORDER BY rpb.pagina, rpb.seccion, rpb.boton
                LIMIT 10
            ''', (username,))

            permisos_raw = cursor.fetchall()

            permisos_lista = []
            for permiso in permisos_raw:
                pagina, seccion, boton = permiso
                permisos_lista.append({
                    'pagina': pagina,
                    'seccion': seccion,
                    'boton': boton
                })

            permisos_test = {
                'usuario': username,
                'rol': rol_nombre,
                'tipo': 'permisos_especificos',
                'permisos_lista': permisos_lista
            }

        conn.close()

        return jsonify({
            'usuario_id': usuario_id,
            'total_permisos_muestra': len(permisos_test.get('permisos_lista', [])) if 'permisos_lista' in permisos_test else len(permisos_test.get('permisos', {})),
            'resultado': permisos_test,
            'status': 'debug_ok'
        })

    except Exception as e:
        return jsonify({'error': str(e), 'status': 'debug_error'}), 500


# === GESTIoN DE ROLES (CRUD) ===

@bp.route('/crear_rol', methods=['POST'])
@auth_system.login_requerido_avanzado
@auth_system.requiere_permiso('sistema', 'usuarios')
@requiere_superadmin
def crear_rol():
    """Crear un nuevo rol"""
    conn = None
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No se recibieron datos'}), 400

        if not data.get('nombre'):
            return jsonify({'error': 'El nombre del rol es requerido'}), 400

        if not data.get('descripcion'):
            return jsonify({'error': 'La descripcion del rol es requerida'}), 400

        nivel = data.get('nivel', 1)
        if not isinstance(nivel, int) or nivel < 1 or nivel > 10:
            return jsonify({'error': 'El nivel debe ser un numero entre 1 y 10'}), 400
        if nivel >= 8:
            return jsonify({'error': 'Los niveles 8-10 estan reservados para roles del sistema'}), 400

        conn = get_db_connection()
        cursor = get_dict_cursor(conn)

        cursor.execute('SELECT id FROM roles WHERE nombre = %s', (data['nombre'],))
        if cursor.fetchone():
            return jsonify({'error': 'Ya existe un rol con ese nombre'}), 400

        try:
            cursor.execute('''
                INSERT INTO roles (nombre, descripcion, nivel, activo)
                VALUES (%s, %s, %s, 1)
            ''', (data['nombre'], data['descripcion'], nivel))

            rol_id = cursor.lastrowid

            usuario_actual = session.get('usuario')
            logger.info(f"Usuario actual: {usuario_actual}")
            logger.info(f"Accion: crear_rol - Rol '{data['nombre']}' creado con nivel {nivel}")

            # TODO: Restaurar auditoria completa cuando se resuelva el problema de bloqueo de DB
            logger.info("Auditoria registrada (modo simplificado)")

            conn.commit()

            cursor.execute('''
                SELECT r.*, COUNT(ur.usuario_id) as total_usuarios
                FROM roles r
                LEFT JOIN usuario_roles ur ON r.id = ur.rol_id
                WHERE r.id = %s
                GROUP BY r.id
            ''', (rol_id,))

            nuevo_rol = cursor.fetchone()

            return jsonify({
                'success': True,
                'mensaje': f'Rol "{data["nombre"]}" creado exitosamente',
                'rol': nuevo_rol
            })

        except Exception as e:
            conn.rollback()
            logger.error(f"Error en transaccion creando rol: {e}")
            return jsonify({'error': f'Error creando rol: {str(e)}'}), 500

    except mysql.connector.Error as e:
        if "lock" in str(e).lower():
            logger.info(f"Base de datos bloqueada creando rol: {e}")
            return jsonify({'error': 'Base de datos temporalmente ocupada, intentalo de nuevo'}), 503
        else:
            logger.error(f"Error de base de datos creando rol: {e}")
            return jsonify({'error': f'Error de base de datos: {str(e)}'}), 500
    except Exception as e:
        logger.error(f"Error creando rol: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass


@bp.route('/eliminar_rol/<int:rol_id>', methods=['DELETE'])
@auth_system.login_requerido_avanzado
@auth_system.requiere_permiso('sistema', 'usuarios')
@requiere_superadmin
def eliminar_rol(rol_id):
    """Eliminar un rol"""
    conn = None
    try:
        logger.info(f"Iniciando eliminacion del rol ID: {rol_id}")
        conn = get_db_connection()
        cursor = get_dict_cursor(conn)

        cursor.execute('SELECT * FROM roles WHERE id = %s', (rol_id,))
        rol = cursor.fetchone()
        if not rol:
            logger.info(f"Rol ID {rol_id} no encontrado")
            conn.close()
            return jsonify({'error': 'Rol no encontrado'}), 404

        rol_dict = dict(rol)
        logger.info(f"Rol encontrado: {rol_dict['nombre']} (Nivel: {rol_dict['nivel']})")

        if rol_dict['nivel'] >= 8:
            logger.info(f"Intento de eliminar rol del sistema: {rol_dict['nombre']}")
            conn.close()
            return jsonify({'error': 'No se puede eliminar un rol del sistema'}), 400

        cursor.execute('SELECT COUNT(*) as total FROM usuario_roles WHERE rol_id = %s', (rol_id,))
        usuarios_asignados = cursor.fetchone()['total']
        logger.info(f"Usuarios asignados al rol: {usuarios_asignados}")

        if usuarios_asignados > 0:
            logger.info(f"No se puede eliminar: {usuarios_asignados} usuarios asignados")
            conn.close()
            return jsonify({
                'error': f'No se puede eliminar el rol. Tiene {usuarios_asignados} usuario(s) asignado(s)'
            }), 400

        try:
            logger.info("Eliminando permisos del rol...")
            cursor.execute('DELETE FROM rol_permisos WHERE rol_id = %s', (rol_id,))
            permisos_eliminados = cursor.rowcount
            logger.info(f"  - Permisos generales eliminados: {permisos_eliminados}")

            cursor.execute('DELETE FROM rol_permisos_botones WHERE rol_id = %s', (rol_id,))
            permisos_botones_eliminados = cursor.rowcount
            logger.info(f"  - Permisos de botones eliminados: {permisos_botones_eliminados}")

            logger.info("Eliminando el rol...")
            cursor.execute('DELETE FROM roles WHERE id = %s', (rol_id,))
            rol_eliminado = cursor.rowcount
            logger.info(f"  - Roles eliminados: {rol_eliminado}")

            if rol_eliminado == 0:
                logger.error("No se pudo eliminar el rol de la tabla")
                cursor.execute('ROLLBACK')
                return jsonify({'error': 'No se pudo eliminar el rol'}), 500

            logger.info("Registrando en auditoria...")
            usuario_actual = session.get('usuario')
            logger.info(f"Usuario actual: {usuario_actual}")
            logger.info(f"Accion: eliminar_rol - Rol '{rol_dict['nombre']}' eliminado por {usuario_actual}")

            logger.info("Auditoria registrada (modo simplificado)")

            conn.commit()
            logger.info(f"Rol '{rol_dict['nombre']}' eliminado exitosamente")

            return jsonify({
                'success': True,
                'mensaje': f'Rol "{rol_dict["nombre"]}" eliminado exitosamente'
            })

        except Exception as e:
            logger.error(f"Error en transaccion, haciendo rollback: {e}")
            conn.rollback()
            logger.error(f"Error en transaccion eliminando rol: {e}")
            return jsonify({'error': f'Error eliminando rol: {str(e)}'}), 500

    except mysql.connector.Error as e:
        if "lock" in str(e).lower():
            logger.info(f"Base de datos bloqueada eliminando rol {rol_id}: {e}")
            return jsonify({'error': 'Base de datos temporalmente ocupada, intentalo de nuevo'}), 503
        else:
            logger.error(f"Error de base de datos eliminando rol: {e}")
            return jsonify({'error': f'Error de base de datos: {str(e)}'}), 500
    except Exception as e:
        logger.error(f"Error general eliminando rol: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            try:
                conn.close()
                logger.info("Conexion cerrada")
            except:
                pass


@bp.route('/actualizar_rol/<int:rol_id>', methods=['PUT'])
@auth_system.login_requerido_avanzado
@auth_system.requiere_permiso('sistema', 'usuarios')
@requiere_superadmin
def actualizar_rol(rol_id):
    """Actualizar un rol existente"""
    conn = None
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No se recibieron datos'}), 400

        conn = get_db_connection()
        cursor = get_dict_cursor(conn)

        cursor.execute('SELECT * FROM roles WHERE id = %s', (rol_id,))
        rol = cursor.fetchone()
        if not rol:
            return jsonify({'error': 'Rol no encontrado'}), 404

        rol_dict = dict(rol)

        if rol_dict['nivel'] >= 8:
            if data.get('nombre') != rol_dict['nombre'] or data.get('nivel') != rol_dict['nivel']:
                return jsonify({'error': 'Solo se puede modificar la descripcion de roles del sistema'}), 400

        nombre = data.get('nombre', rol_dict['nombre'])
        descripcion = data.get('descripcion', rol_dict['descripcion'])
        nivel = data.get('nivel', rol_dict['nivel'])

        if not nombre:
            return jsonify({'error': 'El nombre del rol es requerido'}), 400

        if not isinstance(nivel, int) or nivel < 1 or nivel > 10:
            return jsonify({'error': 'El nivel debe ser un numero entre 1 y 10'}), 400
        if rol_dict['nivel'] < 8 and nivel >= 8:
            return jsonify({'error': 'Los niveles 8-10 estan reservados para roles del sistema'}), 400

        if nombre != rol_dict['nombre']:
            cursor.execute('SELECT id FROM roles WHERE nombre = %s AND id != %s', (nombre, rol_id))
            if cursor.fetchone():
                return jsonify({'error': 'Ya existe otro rol con ese nombre'}), 400

        try:
            cursor.execute('''
                UPDATE roles
                SET nombre = %s, descripcion = %s, nivel = %s
                WHERE id = %s
            ''', (nombre, descripcion, nivel, rol_id))

            usuario_actual = session.get('usuario')
            cambios = []
            if nombre != rol_dict['nombre']:
                cambios.append(f'nombre: "{rol_dict["nombre"]}" -> "{nombre}"')
            if descripcion != rol_dict['descripcion']:
                cambios.append('descripcion actualizada')
            if nivel != rol_dict['nivel']:
                cambios.append(f'nivel: {rol_dict["nivel"]} -> {nivel}')

            conn.commit()

            cursor.execute('''
                SELECT r.*, COUNT(ur.usuario_id) as total_usuarios
                FROM roles r
                LEFT JOIN usuario_roles ur ON r.id = ur.rol_id
                WHERE r.id = %s
                GROUP BY r.id
            ''', (rol_id,))

            rol_actualizado = cursor.fetchone()

            return jsonify({
                'success': True,
                'mensaje': f'Rol "{nombre}" actualizado exitosamente',
                'rol': rol_actualizado
            })

        except Exception as e:
            conn.rollback()
            raise e

    except Exception as e:
        logger.error(f"Error actualizando rol: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()
