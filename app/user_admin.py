"""
Administración de Usuarios - Complemento para ILSAN MES
Sistema completo de gestión de usuarios, roles y permisos
"""

from flask import Blueprint, request, jsonify, render_template, session, send_file, redirect, url_for, flash
from .auth_system import AuthSystem
from .db import get_db_connection
from datetime import datetime, timedelta
import json
import traceback
import tempfile
import os
import sqlite3
import pandas as pd
import io

# Crear Blueprint para las rutas de administración
user_admin_bp = Blueprint('user_admin', __name__)
auth_system = AuthSystem()

@user_admin_bp.route('/panel')
@auth_system.login_requerido_avanzado
@auth_system.requiere_permiso('sistema', 'usuarios')
def panel_administracion():
    """Panel principal de administración de usuarios"""
    usuario = session.get('usuario')
    return render_template('admin/panel_usuarios.html', usuario=usuario)

@user_admin_bp.route('/auditoria')
@auth_system.login_requerido_avanzado
@auth_system.requiere_permiso('sistema', 'auditoria')
def panel_auditoria():
    """Panel de auditoría y logs"""
    usuario = session.get('usuario')
    permisos = session.get('permisos', {})
    
    # Verificar si tiene permisos de administración de usuarios
    tiene_permisos_usuarios = False
    if isinstance(permisos, dict) and 'sistema' in permisos:
        tiene_permisos_usuarios = 'usuarios' in permisos['sistema']
    
    return render_template('admin/auditoria.html', 
                         usuario=usuario, 
                         tiene_permisos_usuarios=tiene_permisos_usuarios)

# === GESTIÓN DE USUARIOS ===

@user_admin_bp.route('/listar_usuarios')
@auth_system.login_requerido_avanzado
@auth_system.requiere_permiso('sistema', 'usuarios')
def listar_usuarios():
    """Obtener lista completa de usuarios con sus roles"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
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
            usuario = dict(row)
            usuario['roles'] = row['roles'].split(',') if row['roles'] else []
            usuario['bloqueado'] = bool(row['bloqueado_hasta'] and 
                                      datetime.fromisoformat(row['bloqueado_hasta']) > auth_system.get_mexico_time().replace(tzinfo=None))
            usuarios.append(usuario)
        
        conn.close()
        
        # No registrar en auditoría - consulta muy frecuente
        return jsonify(usuarios)
        
    except Exception as e:
        print(f"Error listando usuarios: {e}")
        return jsonify({'error': str(e)}), 500

@user_admin_bp.route('/obtener_usuario/<username>')
@auth_system.login_requerido_avanzado
@auth_system.requiere_permiso('sistema', 'usuarios')
def obtener_usuario(username):
    """Obtener datos detallados de un usuario"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM usuarios_sistema WHERE username = ?
        ''', (username,))
        
        usuario = cursor.fetchone()
        if not usuario:
            return jsonify({'error': 'Usuario no encontrado'}), 404
        
        # Obtener roles del usuario
        cursor.execute('''
            SELECT r.id, r.nombre, r.descripcion
            FROM roles r
            JOIN usuario_roles ur ON r.id = ur.rol_id
            WHERE ur.usuario_id = ?
        ''', (usuario['id'],))
        
        roles = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        usuario_dict = dict(usuario)
        usuario_dict['roles'] = roles
        
        return jsonify(usuario_dict)
        
    except Exception as e:
        print(f"Error obteniendo usuario: {e}")
        return jsonify({'error': str(e)}), 500

@user_admin_bp.route('/guardar_usuario', methods=['POST'])
@auth_system.login_requerido_avanzado
@auth_system.requiere_permiso('sistema', 'usuarios')
def guardar_usuario():
    """Crear o actualizar un usuario"""
    try:
        data = request.get_json()
        usuario_actual = session.get('usuario')
        
        # PROTECCIÓN: Bloquear modificación del usuario admin
        if data.get('username') == 'admin':
            auth_system.registrar_auditoria(
                usuario=usuario_actual,
                modulo='sistema',
                accion='guardar_usuario_bloqueado',
                descripcion=f'Intento de modificar usuario admin bloqueado por seguridad',
                resultado='DENEGADO',
                datos_antes={'username': 'admin', 'accion': 'modificacion_bloqueada'}
            )
            return jsonify({
                'error': 'El usuario administrador está protegido y no puede ser modificado por motivos de seguridad.',
                'success': False
            }), 403
        
        # Validaciones
        if not data.get('username'):
            return jsonify({'error': 'Username es requerido'}), 400
        
        if not data.get('nombre_completo'):
            return jsonify({'error': 'Nombre completo es requerido'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar si es nuevo o actualización
        cursor.execute('SELECT id FROM usuarios_sistema WHERE username = ?', (data['username'],))
        existe = cursor.fetchone()
        
        datos_antes = None
        if existe:
            # Obtener datos anteriores para auditoría
            cursor.execute('SELECT * FROM usuarios_sistema WHERE id = ?', (existe['id'],))
            datos_antes = dict(cursor.fetchone())
        
        if existe:
            # Actualizar usuario existente
            params = [
                data.get('nombre_completo'),
                data.get('email', ''),
                data.get('departamento', ''),
                data.get('cargo', ''),
                data.get('activo', 1),
                usuario_actual,
                auth_system.get_mexico_time_iso(),
                data['username']
            ]
            
            if data.get('password') and data['password'].strip():
                # Actualizar con nueva contraseña
                cursor.execute('''
                    UPDATE usuarios_sistema SET
                        password_hash = ?,
                        nombre_completo = ?,
                        email = ?,
                        departamento = ?,
                        cargo = ?,
                        activo = ?,
                        modificado_por = ?,
                        fecha_modificacion = ?,
                        intentos_fallidos = 0,
                        bloqueado_hasta = NULL
                    WHERE username = ?
                ''', [auth_system.hash_password(data['password'])] + params)
            else:
                # Actualizar sin cambiar contraseña
                cursor.execute('''
                    UPDATE usuarios_sistema SET
                        nombre_completo = ?,
                        email = ?,
                        departamento = ?,
                        cargo = ?,
                        activo = ?,
                        modificado_por = ?,
                        fecha_modificacion = ?
                    WHERE username = ?
                ''', params)
            
            usuario_id = existe['id']
            accion = 'actualizar_usuario'
            mensaje = f'Usuario {data["username"]} actualizado'
        else:
            # Crear nuevo usuario
            if not data.get('password'):
                return jsonify({'error': 'Password es requerido para nuevos usuarios'}), 400
            
            cursor.execute('''
                INSERT INTO usuarios_sistema (
                    username, password_hash, nombre_completo,
                    email, departamento, cargo, activo, creado_por
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
        cursor.execute('DELETE FROM usuario_roles WHERE usuario_id = ?', (usuario_id,))
        
        for rol_nombre in data.get('roles', []):
            cursor.execute('SELECT id FROM roles WHERE nombre = ?', (rol_nombre,))
            rol = cursor.fetchone()
            if rol:
                cursor.execute('''
                    INSERT INTO usuario_roles (usuario_id, rol_id, asignado_por)
                    VALUES (?, ?, ?)
                ''', (usuario_id, rol['id'], usuario_actual))
        
        conn.commit()
        
        # Registrar en auditoría
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
        print(f"Error guardando usuario: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@user_admin_bp.route('/cambiar_estado_usuario', methods=['POST'])
@auth_system.login_requerido_avanzado
@auth_system.requiere_permiso('sistema', 'usuarios')
def cambiar_estado_usuario():
    """Activar/desactivar usuario"""
    try:
        data = request.get_json()
        username = data.get('username')
        activo = data.get('activo', True)
        usuario_actual = session.get('usuario')
        
        # PROTECCIÓN: Bloquear modificación del usuario admin
        if username == 'admin':
            auth_system.registrar_auditoria(
                usuario=usuario_actual,
                modulo='sistema',
                accion='cambiar_estado_admin_bloqueado',
                descripcion=f'Intento de cambiar estado del usuario admin bloqueado por seguridad',
                resultado='DENEGADO',
                datos_antes={'username': 'admin', 'accion_intentada': 'cambiar_estado'}
            )
            return jsonify({
                'error': 'El usuario administrador está protegido y no puede ser desactivado por motivos de seguridad.',
                'success': False
            }), 403
        
        if username == usuario_actual:
            return jsonify({'error': 'No puede desactivar su propio usuario'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener datos antes del cambio
        cursor.execute('SELECT * FROM usuarios_sistema WHERE username = ?', (username,))
        datos_antes = dict(cursor.fetchone())
        
        cursor.execute('''
            UPDATE usuarios_sistema 
            SET activo = ?, modificado_por = ?, fecha_modificacion = CURRENT_TIMESTAMP
            WHERE username = ?
        ''', (1 if activo else 0, usuario_actual, username))
        
        if cursor.rowcount > 0:
            # Si se desactivó, cerrar sesiones activas
            if not activo:
                cursor.execute('''
                    UPDATE sesiones_activas 
                    SET activa = 0 
                    WHERE usuario = ?
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
        print(f"Error cambiando estado: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

@user_admin_bp.route('/desbloquear_usuario', methods=['POST'])
@auth_system.login_requerido_avanzado
@auth_system.requiere_permiso('sistema', 'usuarios')
def desbloquear_usuario():
    """Desbloquear usuario manualmente"""
    try:
        data = request.get_json()
        username = data.get('username')
        usuario_actual = session.get('usuario')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE usuarios_sistema 
            SET intentos_fallidos = 0, bloqueado_hasta = NULL,
                modificado_por = ?, fecha_modificacion = CURRENT_TIMESTAMP
            WHERE username = ?
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
        print(f"Error desbloqueando usuario: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

# === GESTIÓN DE ROLES ===

@user_admin_bp.route('/listar_roles')
@auth_system.login_requerido_avanzado
@auth_system.requiere_permiso('sistema', 'usuarios')
def listar_roles():
    """Obtener lista de roles disponibles"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT r.*, COUNT(ur.usuario_id) as total_usuarios
            FROM roles r
            LEFT JOIN usuario_roles ur ON r.id = ur.rol_id
            GROUP BY r.id
            ORDER BY r.nivel DESC, r.nombre
        ''')
        
        roles = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify(roles)
        
    except Exception as e:
        print(f"Error listando roles: {e}")
        return jsonify({'error': str(e)}), 500

@user_admin_bp.route('/obtener_permisos_rol/<int:rol_id>')
@auth_system.login_requerido_avanzado
@auth_system.requiere_permiso('sistema', 'usuarios')
def obtener_permisos_rol(rol_id):
    """Obtener permisos de un rol específico"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT p.modulo, p.accion, p.descripcion
            FROM permisos p
            JOIN rol_permisos rp ON p.id = rp.permiso_id
            WHERE rp.rol_id = ? AND p.activo = 1
            ORDER BY p.modulo, p.accion
        ''', (rol_id,))
        
        permisos = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify(permisos)
        
    except Exception as e:
        print(f"Error obteniendo permisos del rol: {e}")
        return jsonify({'error': str(e)}), 500

# === GESTIÓN DE PERMISOS DE BOTONES/DROPDOWNS ===

@user_admin_bp.route('/listar_permisos_dropdowns')
@auth_system.login_requerido_avanzado
@auth_system.requiere_permiso('sistema', 'usuarios')
def listar_permisos_dropdowns():
    """Obtener lista de todos los permisos de dropdowns disponibles agrupados por lista"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT pb.id, pb.pagina, pb.seccion, pb.boton, pb.descripcion, pb.activo
            FROM permisos_botones pb
            WHERE pb.activo = 1
            ORDER BY pb.pagina, pb.seccion, pb.boton
        ''')
        
        permisos = cursor.fetchall()
        conn.close()
        
        # Agrupar por página (lista)
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
        print(f"Error listando permisos de dropdowns: {e}")
        return jsonify({'error': str(e)}), 500

@user_admin_bp.route('/obtener_permisos_dropdowns_rol/<int:rol_id>')
@auth_system.login_requerido_avanzado
@auth_system.requiere_permiso('sistema', 'usuarios')
def obtener_permisos_dropdowns_rol(rol_id):
    """Obtener permisos de dropdowns de un rol específico"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT pb.id, pb.pagina, pb.seccion, pb.boton, pb.descripcion
            FROM permisos_botones pb
            JOIN rol_permisos_botones rpb ON pb.id = rpb.permiso_boton_id
            WHERE rpb.rol_id = ? AND pb.activo = 1
            ORDER BY pb.pagina, pb.seccion, pb.boton
        ''', (rol_id,))
        
        permisos = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify(permisos)
        
    except Exception as e:
        print(f"Error obteniendo permisos de dropdowns del rol: {e}")
        return jsonify({'error': str(e)}), 500

@user_admin_bp.route('/actualizar_permisos_dropdowns_rol', methods=['POST'])
@auth_system.login_requerido_avanzado
@auth_system.requiere_permiso('sistema', 'usuarios')
def actualizar_permisos_dropdowns_rol():
    """Actualizar permisos de dropdowns de un rol"""
    try:
        data = request.get_json()
        rol_id = data.get('rol_id')
        permisos_ids = data.get('permisos_ids', [])
        
        if not rol_id:
            return jsonify({'success': False, 'error': 'ID de rol requerido'}), 400
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Eliminar permisos actuales del rol
        cursor.execute('DELETE FROM rol_permisos_botones WHERE rol_id = ?', (rol_id,))
        
        # Agregar nuevos permisos
        for permiso_id in permisos_ids:
            cursor.execute('''
                INSERT INTO rol_permisos_botones (rol_id, permiso_boton_id)
                VALUES (?, ?)
            ''', (rol_id, permiso_id))
        
        conn.commit()
        conn.close()
        
        # Registrar auditoría
        auth_system.registrar_auditoria(
            usuario=session.get('usuario'),
            modulo='sistema',
            accion='actualizar_permisos_dropdowns',
            descripcion=f'Actualizó permisos de dropdowns para rol ID {rol_id}'
        )
        
        return jsonify({
            'success': True, 
            'mensaje': f'Permisos de dropdowns actualizados exitosamente'
        })
        
    except Exception as e:
        print(f"Error actualizando permisos de dropdowns: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@user_admin_bp.route('/listar_permisos_botones')
@auth_system.login_requerido_avanzado
@auth_system.requiere_permiso('sistema', 'usuarios')
def listar_permisos_botones():
    """Obtener lista de todos los permisos de botones disponibles"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM permisos_botones 
            WHERE activo = 1
            ORDER BY pagina, seccion, boton
        ''')
        
        permisos = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify(permisos)
        
    except Exception as e:
        print(f"Error listando permisos de botones: {e}")
        return jsonify({'error': str(e)}), 500

@user_admin_bp.route('/permisos_botones_rol/<int:rol_id>')
@auth_system.login_requerido_avanzado
@auth_system.requiere_permiso('sistema', 'usuarios')
def obtener_permisos_botones_rol(rol_id):
    """Obtener permisos de botones de un rol específico"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT pb.id, pb.pagina, pb.seccion, pb.boton, pb.descripcion
            FROM permisos_botones pb
            JOIN rol_permisos_botones rpb ON pb.id = rpb.permiso_boton_id
            WHERE rpb.rol_id = ? AND pb.activo = 1
            ORDER BY pb.pagina, pb.seccion, pb.boton
        ''', (rol_id,))
        
        permisos = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify(permisos)
        
    except Exception as e:
        print(f"Error obteniendo permisos de botones del rol: {e}")
        return jsonify({'error': str(e)}), 500

@user_admin_bp.route('/actualizar_permisos_botones_rol', methods=['POST'])
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
        cursor = conn.cursor()
        
        # Obtener nombre del rol para auditoría
        cursor.execute('SELECT nombre FROM roles WHERE id = ?', (rol_id,))
        rol = cursor.fetchone()
        if not rol:
            return jsonify({'error': 'Rol no encontrado'}), 404
        
        # Obtener permisos anteriores para auditoría
        cursor.execute('''
            SELECT pb.boton, pb.pagina, pb.seccion
            FROM permisos_botones pb
            JOIN rol_permisos_botones rpb ON pb.id = rpb.permiso_boton_id
            WHERE rpb.rol_id = ?
        ''', (rol_id,))
        permisos_anteriores = [dict(row) for row in cursor.fetchall()]
        
        # Eliminar permisos existentes
        cursor.execute('DELETE FROM rol_permisos_botones WHERE rol_id = ?', (rol_id,))
        
        # Insertar nuevos permisos
        for permiso_boton_id in permisos_botones_ids:
            cursor.execute('''
                INSERT INTO rol_permisos_botones (rol_id, permiso_boton_id)
                VALUES (?, ?)
            ''', (rol_id, permiso_boton_id))
        
        # Obtener permisos nuevos para auditoría
        cursor.execute('''
            SELECT pb.boton, pb.pagina, pb.seccion
            FROM permisos_botones pb
            JOIN rol_permisos_botones rpb ON pb.id = rpb.permiso_boton_id
            WHERE rpb.rol_id = ?
        ''', (rol_id,))
        permisos_nuevos = [dict(row) for row in cursor.fetchall()]
        
        conn.commit()
        
        # Registrar en auditoría
        auth_system.registrar_auditoria(
            usuario=usuario_actual,
            modulo='sistema',
            accion='actualizar_permisos_botones_rol',
            descripcion=f'Actualizó permisos de botones del rol {rol["nombre"]}',
            datos_antes={'permisos': permisos_anteriores},
            datos_despues={'permisos': permisos_nuevos}
        )
        
        conn.close()
        return jsonify({'success': True, 'mensaje': f'Permisos de botones del rol {rol["nombre"]} actualizados'})
        
    except Exception as e:
        print(f"Error actualizando permisos de botones del rol: {e}")
        return jsonify({'error': str(e)}), 500

@user_admin_bp.route('/permisos_botones_usuario/<username>')
@auth_system.login_requerido_avanzado  
@auth_system.requiere_permiso('sistema', 'usuarios')
def obtener_permisos_botones_usuario(username):
    """Obtener permisos de botones de un usuario específico"""
    try:
        permisos_botones = auth_system.obtener_permisos_botones_usuario(username)
        return jsonify(permisos_botones)
        
    except Exception as e:
        print(f"Error obteniendo permisos de botones del usuario: {e}")
        return jsonify({'error': str(e)}), 500

@user_admin_bp.route('/verificar_permiso_dropdown', methods=['POST'])
@auth_system.login_requerido_avanzado
def verificar_permiso_dropdown():
    """Verificar si el usuario actual tiene permiso para un dropdown específico"""
    try:
        data = request.get_json()
        pagina = data.get('pagina')
        seccion = data.get('seccion')
        boton = data.get('boton')
        
        if not all([pagina, seccion, boton]):
            return jsonify({'error': 'Faltan parámetros requeridos'}), 400
        
        username = session.get('usuario')
        if not username:
            return jsonify({'tiene_permiso': False, 'error': 'Usuario no autenticado'}), 401
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar si el usuario tiene el permiso específico
        cursor.execute('''
            SELECT COUNT(*) as tiene_permiso
            FROM usuarios_sistema u
            JOIN usuario_roles ur ON u.id = ur.usuario_id
            JOIN rol_permisos_botones rpb ON ur.rol_id = rpb.rol_id
            JOIN permisos_botones pb ON rpb.permiso_boton_id = pb.id
            WHERE u.username = ? AND pb.pagina = ? AND pb.seccion = ? AND pb.boton = ?
            AND u.activo = 1 AND pb.activo = 1
        ''', (username, pagina, seccion, boton))
        
        resultado = cursor.fetchone()
        tiene_permiso = resultado['tiene_permiso'] > 0
        
        conn.close()
        
        return jsonify({'tiene_permiso': tiene_permiso})
        
    except Exception as e:
        print(f"Error verificando permiso de dropdown: {e}")
        return jsonify({'tiene_permiso': False, 'error': str(e)}), 500

@user_admin_bp.route('/obtener_permisos_usuario_actual')
@auth_system.login_requerido_avanzado
def obtener_permisos_usuario_actual():
    """Obtener todos los permisos de dropdowns del usuario actual"""
    try:
        username = session.get('usuario')
        if not username:
            return jsonify({'error': 'Usuario no autenticado'}), 401
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener todos los permisos de botones del usuario
        cursor.execute('''
            SELECT DISTINCT pb.pagina, pb.seccion, pb.boton
            FROM usuarios_sistema u
            JOIN usuario_roles ur ON u.id = ur.usuario_id
            JOIN rol_permisos_botones rpb ON ur.rol_id = rpb.rol_id
            JOIN permisos_botones pb ON rpb.permiso_boton_id = pb.id
            WHERE u.username = ? AND u.activo = 1 AND pb.activo = 1
            ORDER BY pb.pagina, pb.seccion, pb.boton
        ''', (username,))
        
        permisos = cursor.fetchall()
        conn.close()
        
        # Organizar permisos para fácil consulta en frontend
        permisos_dict = {}
        for permiso in permisos:
            pagina = permiso['pagina']
            if pagina not in permisos_dict:
                permisos_dict[pagina] = {}
            
            seccion = permiso['seccion']
            if seccion not in permisos_dict[pagina]:
                permisos_dict[pagina][seccion] = []
            
            permisos_dict[pagina][seccion].append(permiso['boton'])
        
        return jsonify({
            'permisos': permisos_dict,
            'usuario': username,
            'total_permisos': len(permisos)
        })
        
    except Exception as e:
        print(f"Error obteniendo permisos del usuario actual: {e}")
        return jsonify({'error': str(e)}), 500

# === AUDITORÍA Y LOGS ===

@user_admin_bp.route('/buscar_auditoria')
@auth_system.login_requerido_avanzado
@auth_system.requiere_permiso('sistema', 'auditoria')
def buscar_auditoria():
    """Buscar registros de auditoría con filtros"""
    try:
        # Obtener filtros
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        usuario = request.args.get('usuario', '').strip()
        modulo = request.args.get('modulo', '').strip()
        accion = request.args.get('accion', '').strip()
        resultado = request.args.get('resultado', '').strip()
        limite = int(request.args.get('limite', 100))
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = '''
            SELECT * FROM auditoria WHERE 1=1
        '''
        params = []
        
        if fecha_inicio:
            query += ' AND DATE(fecha_hora) >= ?'
            params.append(fecha_inicio)
        
        if fecha_fin:
            query += ' AND DATE(fecha_hora) <= ?'
            params.append(fecha_fin)
        
        if usuario:
            query += ' AND usuario LIKE ?'
            params.append(f'%{usuario}%')
        
        if modulo:
            query += ' AND modulo = ?'
            params.append(modulo)
        
        if accion:
            query += ' AND accion LIKE ?'
            params.append(f'%{accion}%')
        
        if resultado:
            query += ' AND resultado = ?'
            params.append(resultado)
        
        query += ' ORDER BY fecha_hora DESC LIMIT ?'
        params.append(limite)
        
        cursor.execute(query, params)
        registros = [dict(row) for row in cursor.fetchall()]
        
        # Obtener estadísticas
        cursor.execute('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN resultado = 'EXITOSO' THEN 1 ELSE 0 END) as exitosos,
                SUM(CASE WHEN resultado = 'ERROR' THEN 1 ELSE 0 END) as errores,
                SUM(CASE WHEN resultado = 'DENEGADO' THEN 1 ELSE 0 END) as denegados
            FROM auditoria 
            WHERE DATE(fecha_hora) = DATE('now')
        ''')
        
        stats = dict(cursor.fetchone())
        
        conn.close()
        
        return jsonify({
            'registros': registros,
            'estadisticas': stats,
            'total_encontrados': len(registros)
        })
        
    except Exception as e:
        print(f"Error buscando auditoría: {e}")
        return jsonify({'error': str(e)}), 500

@user_admin_bp.route('/detalle_auditoria/<int:id>')
@auth_system.login_requerido_avanzado
@auth_system.requiere_permiso('sistema', 'auditoria')
def detalle_auditoria(id):
    """Obtener detalles completos de un registro de auditoría"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM auditoria WHERE id = ?', (id,))
        registro = cursor.fetchone()
        
        if not registro:
            return jsonify({'error': 'Registro no encontrado'}), 404
        
        conn.close()
        
        detalle = dict(registro)
        
        # Parsear datos JSON si existen
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
        print(f"Error obteniendo detalle de auditoría: {e}")
        return jsonify({'error': str(e)}), 500

@user_admin_bp.route('/estadisticas_auditoria')
@auth_system.login_requerido_avanzado
@auth_system.requiere_permiso('sistema', 'auditoria')
def estadisticas_auditoria():
    """Obtener estadísticas de auditoría para dashboard"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Acciones hoy
        cursor.execute('''
            SELECT COUNT(*) as total
            FROM auditoria 
            WHERE DATE(fecha_hora) = DATE('now')
        ''')
        acciones_hoy = cursor.fetchone()['total']
        
        # Usuarios activos hoy
        cursor.execute('''
            SELECT COUNT(DISTINCT usuario) as total
            FROM auditoria 
            WHERE DATE(fecha_hora) = DATE('now')
        ''')
        usuarios_activos = cursor.fetchone()['total']
        
        # Exportaciones últimos 7 días
        cursor.execute('''
            SELECT COUNT(*) as total
            FROM auditoria 
            WHERE accion LIKE '%exportar%' 
            AND fecha_hora >= DATE('now', '-7 days')
        ''')
        exportaciones = cursor.fetchone()['total']
        
        # Errores últimos 7 días
        cursor.execute('''
            SELECT COUNT(*) as total
            FROM auditoria 
            WHERE resultado = 'ERROR' 
            AND fecha_hora >= DATE('now', '-7 days')
        ''')
        errores = cursor.fetchone()['total']
        
        # Actividad por módulo (últimos 7 días)
        cursor.execute('''
            SELECT modulo, COUNT(*) as total
            FROM auditoria 
            WHERE fecha_hora >= DATE('now', '-7 days')
            GROUP BY modulo
            ORDER BY total DESC
        ''')
        actividad_modulos = [dict(row) for row in cursor.fetchall()]
        
        # Usuarios más activos (últimos 7 días)
        cursor.execute('''
            SELECT usuario, COUNT(*) as total
            FROM auditoria 
            WHERE fecha_hora >= DATE('now', '-7 days')
            GROUP BY usuario
            ORDER BY total DESC
            LIMIT 10
        ''')
        usuarios_mas_activos = [dict(row) for row in cursor.fetchall()]
        
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
        print(f"Error obteniendo estadísticas: {e}")
        return jsonify({'error': str(e)}), 500

@user_admin_bp.route('/exportar_auditoria')
@auth_system.login_requerido_avanzado
@auth_system.requiere_permiso('sistema', 'auditoria')
def exportar_auditoria():
    """Exportar registros de auditoría a Excel"""
    try:
        import pandas as pd
        from datetime import datetime
        
        # Obtener mismos filtros que buscar_auditoria
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        usuario = request.args.get('usuario', '').strip()
        modulo = request.args.get('modulo', '').strip()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = '''
            SELECT 
                fecha_hora, usuario, modulo, accion, descripcion,
                ip_address, resultado, duracion_ms, endpoint
            FROM auditoria WHERE 1=1
        '''
        params = []
        
        if fecha_inicio:
            query += ' AND DATE(fecha_hora) >= ?'
            params.append(fecha_inicio)
        
        if fecha_fin:
            query += ' AND DATE(fecha_hora) <= ?'
            params.append(fecha_fin)
        
        if usuario:
            query += ' AND usuario LIKE ?'
            params.append(f'%{usuario}%')
        
        if modulo:
            query += ' AND modulo = ?'
            params.append(modulo)
        
        query += ' ORDER BY fecha_hora DESC LIMIT 10000'  # Límite para evitar archivos muy grandes
        
        cursor.execute(query, params)
        datos = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        if not datos:
            return jsonify({'error': 'No hay datos para exportar'}), 400
        
        # Crear DataFrame
        df = pd.DataFrame(datos)
        
        # Crear archivo temporal
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
            df.to_excel(tmp.name, index=False, sheet_name='Auditoría')
            
            # Registrar exportación
            auth_system.registrar_auditoria(
                usuario=session.get('usuario'),
                modulo='sistema',
                accion='exportar_auditoria',
                descripcion=f'Exportó {len(datos)} registros de auditoría'
            )
            
            return send_file(
                tmp.name,
                as_attachment=True,
                download_name=f'auditoria_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            
    except Exception as e:
        print(f"Error exportando auditoría: {e}")
        return jsonify({'error': str(e)}), 500

# === FUNCIONES DE UTILIDAD ===

@user_admin_bp.route('/actividad_reciente')
@auth_system.login_requerido_avanzado
@auth_system.requiere_permiso('sistema', 'auditoria')
def actividad_reciente():
    """Obtener actividad reciente para dashboard en tiempo real"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Usuarios activos en los últimos 15 minutos
        cursor.execute('''
            SELECT DISTINCT usuario, 
                MAX(fecha_hora) as ultima_actividad,
                MAX(accion) as ultima_accion
            FROM auditoria 
            WHERE fecha_hora >= datetime('now', '-15 minutes')
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
        
        # Últimas 10 acciones
        cursor.execute('''
            SELECT usuario, modulo, accion, descripcion, fecha_hora
            FROM auditoria 
            ORDER BY fecha_hora DESC
            LIMIT 10
        ''')
        
        ultimas_acciones = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({
            'usuarios_activos': usuarios_activos,
            'ultimas_acciones': ultimas_acciones
        })
        
    except Exception as e:
        print(f"Error obteniendo actividad reciente: {e}")
        return jsonify({'error': str(e)}), 500

def init_admin_routes(app):
    """Inicializar las rutas de administración en la app"""
    app.register_blueprint(user_admin_bp)
    print("✅ Rutas de administración de usuarios registradas")
