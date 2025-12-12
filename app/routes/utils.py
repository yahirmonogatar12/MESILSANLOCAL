# -*- coding: utf-8 -*-
"""
Utilidades compartidas para todos los módulos de rutas
"""

import os
import json
from functools import wraps
from datetime import datetime, timedelta
from flask import session, redirect, url_for, jsonify, request

# Importar sistema de autenticación
from ..core.auth_system import AuthSystem
from ..database.db_mysql import execute_query

# Inicializar sistema de autenticación
auth_system = AuthSystem()


def obtener_fecha_hora_mexico():
    """Obtener fecha y hora actual en zona horaria de México (GMT-6)"""
    try:
        utc_now = datetime.utcnow()
        mexico_time = utc_now - timedelta(hours=6)
        return mexico_time
    except Exception:
        return datetime.now()


def login_requerido(f):
    """Decorador para verificar autenticación"""
    @wraps(f)
    def decorada(*args, **kwargs):
        if 'usuario' not in session:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'error': 'No autenticado', 'redirect': '/login'}), 401
            return redirect(url_for('vistas.inicio'))
        
        usuario = session.get('usuario')
        auth_system._actualizar_actividad_sesion(usuario)
        return f(*args, **kwargs)
    return decorada


def requiere_permiso_dropdown(pagina, seccion, boton):
    """Decorador para verificar permisos específicos de dropdowns"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'usuario' not in session:
                return jsonify({'error': 'Usuario no autenticado', 'redirect': '/login'}), 401
            
            try:
                username = session['usuario']
                
                query_rol = '''
                    SELECT r.nombre
                    FROM usuarios_sistema u
                    JOIN usuario_roles ur ON u.id = ur.usuario_id
                    JOIN roles r ON ur.rol_id = r.id
                    WHERE u.username = %s AND u.activo = 1 AND r.activo = 1
                    ORDER BY r.nivel DESC
                    LIMIT 1
                '''
                
                usuario_rol = execute_query(query_rol, (username,), fetch='one')
                
                if not usuario_rol:
                    return jsonify({'error': 'Usuario sin roles asignados'}), 403
                
                if isinstance(usuario_rol, dict):
                    rol_nombre = usuario_rol['nombre']
                else:
                    rol_nombre = usuario_rol[0]
                
                # Verificar permiso específico
                query_permiso = '''
                    SELECT COUNT(*) FROM usuarios_sistema u
                    JOIN usuario_roles ur ON u.id = ur.usuario_id
                    JOIN rol_permisos_botones rpb ON ur.rol_id = rpb.rol_id
                    JOIN permisos_botones pb ON rpb.permiso_boton_id = pb.id
                    WHERE u.username = %s AND pb.pagina = %s AND pb.seccion = %s AND pb.boton = %s
                '''
                
                resultado = execute_query(query_permiso, (username, pagina, seccion, boton), fetch='one')
                
                if isinstance(resultado, dict):
                    tiene_permiso = resultado.get('COUNT(*)', 0) > 0
                else:
                    tiene_permiso = resultado[0] > 0 if resultado else False
                
                if not tiene_permiso:
                    return jsonify({'error': f'No tiene permiso para {boton}'}), 403
                
                return f(*args, **kwargs)
                
            except Exception as e:
                print(f"❌ Error verificando permisos: {e}")
                return jsonify({'error': 'Error al verificar permisos'}), 500
                
        return decorated_function
    return decorator


def tiene_permiso_boton(nombre_boton):
    """Verifica si el usuario tiene permiso para un botón específico"""
    if 'usuario' not in session:
        return False
    
    try:
        username = session['usuario']
        query = '''
            SELECT COUNT(*) as count FROM usuarios_sistema u
            JOIN usuario_roles ur ON u.id = ur.usuario_id
            JOIN rol_permisos_botones rpb ON ur.rol_id = rpb.rol_id
            JOIN permisos_botones pb ON rpb.permiso_boton_id = pb.id
            WHERE u.username = %s AND pb.boton = %s
        '''
        resultado = execute_query(query, (username, nombre_boton), fetch='one')
        
        if isinstance(resultado, dict):
            return resultado.get('count', 0) > 0
        return resultado[0] > 0 if resultado else False
        
    except Exception as e:
        print(f"❌ Error verificando permiso botón: {e}")
        return False


def cargar_usuarios():
    """Función deprecada - se mantiene para compatibilidad"""
    ruta = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'usuarios.json')
    ruta = os.path.abspath(ruta)
    try:
        with open(ruta, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
