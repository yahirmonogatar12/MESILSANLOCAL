# -*- coding: utf-8 -*-
"""
Rutas de Autenticación
Login, logout, permisos y gestión de sesiones
"""

from flask import Blueprint, request, render_template, redirect, url_for, session, jsonify
from functools import wraps
from .utils import obtener_fecha_hora_mexico, cargar_usuarios, login_requerido
from ..core.auth_system import AuthSystem
from ..database.db_mysql import get_mysql_connection

auth_bp = Blueprint('auth', __name__)

# Inicializar sistema de autenticación
auth_system = AuthSystem()


def render_landing_page(login_error=None, login_username=None):
    """Renderiza la landing page con o sin sesión activa."""
    authenticated = 'usuario' in session
    nombre_completo = None
    permisos = {}
    roles = []

    if authenticated:
        usuario = session.get('usuario')
        nombre_completo = session.get('nombre_completo', usuario)
        permisos = session.get('permisos', {})

        try:
            conn = get_mysql_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT DISTINCT r.nombre
                FROM usuarios_sistema u
                JOIN usuario_roles ur ON u.id = ur.usuario_id
                JOIN roles r ON ur.rol_id = r.id
                WHERE u.username = %s AND u.activo = 1 AND r.activo = 1
            ''', (usuario,))
            roles = [row[0] for row in cursor.fetchall()]
        except Exception as e:
            print(f"⚠️ Error obteniendo roles: {e}")
        finally:
            try:
                if 'cursor' in locals() and cursor:
                    cursor.close()
                if 'conn' in locals() and conn:
                    conn.close()
            except Exception:
                pass

    upcoming_apps = [
        {
            'name': 'Más Herramientas',
            'description': 'Expansión futura',
            'long_description': 'Nuevas aplicaciones serán agregadas pronto.',
            'icon': 'rocket'
        }
    ]

    return render_template(
        'landing.html',
        nombre_usuario=nombre_completo,
        permisos=permisos,
        roles=roles,
        upcoming_apps=upcoming_apps,
        usuario_autenticado=authenticated,
        login_error=login_error,
        login_username=login_username
    )


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Endpoint de login"""
    if request.method == 'GET':
        return redirect(url_for('vistas.inicio'))

    is_ajax = (
        request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        or 'application/json' in request.headers.get('Accept', '')
    )

    user = request.form.get('username', '').strip()
    pw = request.form.get('password', '')
    print(f"🔐 Intento de login: {user}")
        
    # PRIORIDAD 1: Intentar con el nuevo sistema de BD
    resultado_auth = auth_system.verificar_usuario(user, pw)

    if isinstance(resultado_auth, tuple):
        auth_success, auth_message = resultado_auth
    else:
        auth_success = resultado_auth.get('success', False) if isinstance(resultado_auth, dict) else False
        auth_message = resultado_auth.get('message', 'Error desconocido') if isinstance(resultado_auth, dict) else str(resultado_auth)

    if auth_success:
        print(f"✅ Login exitoso con sistema BD: {user}")
        session['usuario'] = user

        # Obtener información completa del usuario
        info_usuario = auth_system.obtener_informacion_usuario(user)
        if info_usuario:
            session['nombre_completo'] = info_usuario['nombre_completo']
            session['email'] = info_usuario['email']
            session['departamento'] = info_usuario['departamento']
        else:
            session['nombre_completo'] = user

        # Registrar auditoría
        auth_system.registrar_auditoria(
            usuario=user,
            modulo='sistema',
            accion='login',
            descripcion='Inicio de sesión exitoso',
            resultado='EXITOSO'
        )

        # Obtener permisos del usuario
        permisos_resultado = auth_system.obtener_permisos_usuario(user)
        if isinstance(permisos_resultado, tuple):
            permisos, rol_id = permisos_resultado
        else:
            permisos = permisos_resultado

        session['permisos'] = permisos

        redirect_url = url_for('vistas.inicio')
        if is_ajax:
            return jsonify({'success': True, 'redirect': redirect_url})
        return redirect(redirect_url)

    # FALLBACK: Sistema antiguo (usuarios.json)
    try:
        usuarios_json = cargar_usuarios()
        if user in usuarios_json and usuarios_json[user] == pw:
            print(f"✅ Login exitoso con sistema JSON (fallback): {user}")
            session['usuario'] = user
            session['nombre_completo'] = user
            session['email'] = ''
            session['departamento'] = ''

            auth_system.registrar_auditoria(
                usuario=user,
                modulo='sistema', 
                accion='login_json',
                descripcion='Inicio de sesión con sistema JSON (fallback)',
                resultado='EXITOSO'
            )

            redirect_url = url_for('vistas.inicio')
            if is_ajax:
                return jsonify({'success': True, 'redirect': redirect_url})
            return redirect(redirect_url)
    except Exception as e:
        print(f"❌ Error en fallback JSON: {e}")

    # Login falló
    print(f"❌ Login falló: {user} ({auth_message})")
    auth_system.registrar_auditoria(
        usuario=user,
        modulo='sistema',
        accion='login_failed',
        descripcion='Intento de login fallido - credenciales incorrectas',
        resultado='ERROR'
    )

    error_message = "Usuario o contraseña incorrectos. Por favor, intente de nuevo"

    if is_ajax:
        return jsonify({'success': False, 'message': error_message}), 401

    return render_landing_page(login_error=error_message, login_username=user)


@auth_bp.route('/logout')
def logout():
    """Cerrar sesión"""
    usuario = session.get('usuario', 'unknown')
    
    if usuario != 'unknown':
        auth_system.registrar_auditoria(
            usuario=usuario,
            modulo='sistema',
            accion='logout', 
            descripcion='Cierre de sesión',
            resultado='EXITOSO'
        )
        print(f"🚪 Logout exitoso: {usuario}")
    
    session.clear()
    return redirect(url_for('vistas.inicio'))


@auth_bp.route('/verificar_permiso_dropdown', methods=['POST'])
def verificar_permiso_dropdown():
    """Verificar si el usuario tiene permiso para un dropdown específico"""
    try:
        if 'usuario' not in session:
            return jsonify({'tiene_permiso': False, 'error': 'Usuario no autenticado'}), 401
        
        data = request.get_json()
        if not data:
            return jsonify({'tiene_permiso': False, 'error': 'Datos JSON requeridos'}), 400
            
        pagina = data.get('pagina', '').strip()
        seccion = data.get('seccion', '').strip() 
        boton = data.get('boton', '').strip()
        
        if not all([pagina, seccion, boton]):
            return jsonify({'tiene_permiso': False, 'error': 'Parámetros incompletos'}), 400
        
        username = session['usuario']
        conn = get_mysql_connection()
        cursor = conn.cursor()
        
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
            return jsonify({'tiene_permiso': False, 'error': 'Usuario no encontrado'}), 404
        
        rol_nombre = usuario_rol[0] if not isinstance(usuario_rol, dict) else usuario_rol['nombre']
        
        if rol_nombre == 'superadmin':
            conn.close()
            return jsonify({'tiene_permiso': True, 'motivo': 'superadmin'})
        
        cursor.execute('''
            SELECT COUNT(*) FROM usuarios_sistema u
            JOIN usuario_roles ur ON u.id = ur.usuario_id
            JOIN rol_permisos_botones rpb ON ur.rol_id = rpb.rol_id
            JOIN permisos_botones pb ON rpb.permiso_boton_id = pb.id
            WHERE u.username = %s AND pb.pagina = %s AND pb.seccion = %s AND pb.boton = %s
            AND u.activo = 1 AND pb.activo = 1
        ''', (username, pagina, seccion, boton))
        
        tiene_permiso = cursor.fetchone()[0] > 0
        conn.close()
        
        return jsonify({
            'tiene_permiso': tiene_permiso,
            'usuario': username,
            'rol': rol_nombre,
            'permiso': f"{pagina} > {seccion} > {boton}"
        })
        
    except Exception as e:
        print(f"❌ Error verificando permiso: {e}")
        return jsonify({'tiene_permiso': False, 'error': str(e)}), 500


@auth_bp.route('/obtener_permisos_usuario_actual', methods=['GET'])
@login_requerido
def obtener_permisos_usuario_actual():
    """Obtener todos los permisos del usuario actual"""
    try:
        if 'usuario' not in session:
            return jsonify({'permisos': [], 'error': 'Usuario no autenticado'}), 401
        
        username = session['usuario']
        conn = get_mysql_connection()
        cursor = conn.cursor()
        
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
            return jsonify({'permisos': {}, 'error': 'Usuario no encontrado'}), 404
        
        rol_nombre = usuario_rol['nombre'] if isinstance(usuario_rol, dict) else usuario_rol[0]
        
        if rol_nombre == 'superadmin':
            cursor.execute('SELECT pagina, seccion, boton FROM permisos_botones WHERE activo = 1')
            permisos = cursor.fetchall()
        else:
            cursor.execute('''
                SELECT pb.pagina, pb.seccion, pb.boton 
                FROM usuarios_sistema u
                JOIN usuario_roles ur ON u.id = ur.usuario_id
                JOIN rol_permisos_botones rpb ON ur.rol_id = rpb.rol_id
                JOIN permisos_botones pb ON rpb.permiso_boton_id = pb.id
                WHERE u.username = %s AND u.activo = 1 AND pb.activo = 1
            ''', (username,))
            permisos = cursor.fetchall()
        
        conn.close()
        
        permisos_jerarquicos = {}
        total_permisos = 0
        
        for permiso in permisos:
            if isinstance(permiso, dict):
                pagina, seccion, boton = permiso['pagina'], permiso['seccion'], permiso['boton']
            else:
                pagina, seccion, boton = permiso
            
            if pagina not in permisos_jerarquicos:
                permisos_jerarquicos[pagina] = {}
            if seccion not in permisos_jerarquicos[pagina]:
                permisos_jerarquicos[pagina][seccion] = []
            
            permisos_jerarquicos[pagina][seccion].append(boton)
            total_permisos += 1
        
        return jsonify({
            'permisos': permisos_jerarquicos,
            'usuario': username,
            'rol': rol_nombre,
            'total_permisos': total_permisos
        })
        
    except Exception as e:
        print(f"❌ Error obteniendo permisos: {e}")
        return jsonify({'permisos': [], 'error': str(e)}), 500
