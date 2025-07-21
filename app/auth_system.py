"""
Sistema de Autenticación y Autorización Avanzado
Complemento para el sistema ILSAN MES
"""

import hashlib
import secrets
import json
import os
import sqlite3
import threading
import time
from functools import wraps
from flask import session, jsonify, request, redirect, url_for, g, current_app
from datetime import datetime, timedelta
import traceback
from .db import get_db_connection

class AuthSystem:
    def __init__(self, app=None):
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Inicializar el sistema de autenticación con la app Flask"""
        self.app = app
        self.init_database()
        self.create_default_admin()
    
    def init_database(self):
        """Inicializar todas las tablas del sistema de usuarios"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Tabla de usuarios mejorada
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS usuarios_sistema (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    email TEXT,
                    nombre_completo TEXT,
                    departamento TEXT,
                    cargo TEXT,
                    activo INTEGER DEFAULT 1,
                    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ultimo_acceso TIMESTAMP,
                    intentos_fallidos INTEGER DEFAULT 0,
                    bloqueado_hasta TIMESTAMP,
                    creado_por TEXT,
                    modificado_por TEXT,
                    fecha_modificacion TIMESTAMP
                )
            ''')
            
            # Tabla de roles
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS roles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT UNIQUE NOT NULL,
                    descripcion TEXT,
                    nivel INTEGER DEFAULT 1,
                    activo INTEGER DEFAULT 1,
                    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tabla de permisos
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS permisos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    modulo TEXT NOT NULL,
                    accion TEXT NOT NULL,
                    descripcion TEXT,
                    activo INTEGER DEFAULT 1,
                    UNIQUE(modulo, accion)
                )
            ''')
            
            # Relación usuarios-roles
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS usuario_roles (
                    usuario_id INTEGER,
                    rol_id INTEGER,
                    fecha_asignacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    asignado_por TEXT,
                    PRIMARY KEY (usuario_id, rol_id),
                    FOREIGN KEY (usuario_id) REFERENCES usuarios_sistema(id),
                    FOREIGN KEY (rol_id) REFERENCES roles(id)
                )
            ''')
            
            # Relación roles-permisos
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS rol_permisos (
                    rol_id INTEGER,
                    permiso_id INTEGER,
                    fecha_asignacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (rol_id, permiso_id),
                    FOREIGN KEY (rol_id) REFERENCES roles(id),
                    FOREIGN KEY (permiso_id) REFERENCES permisos(id)
                )
            ''')
            
            # Tabla de auditoría completa
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS auditoria (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario TEXT NOT NULL,
                    modulo TEXT NOT NULL,
                    accion TEXT NOT NULL,
                    descripcion TEXT,
                    datos_antes TEXT,
                    datos_despues TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    resultado TEXT DEFAULT 'EXITOSO',
                    duracion_ms INTEGER,
                    endpoint TEXT,
                    metodo_http TEXT,
                    fecha_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tabla de sesiones activas
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sesiones_activas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario TEXT NOT NULL,
                    token_sesion TEXT UNIQUE NOT NULL,
                    ip_address TEXT,
                    user_agent TEXT,
                    fecha_inicio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    fecha_ultima_actividad TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    activa INTEGER DEFAULT 1
                )
            ''')
            
            # Insertar roles predeterminados
            self._crear_roles_default(cursor)
            
            # Insertar permisos predeterminados  
            self._crear_permisos_default(cursor)
            
            # Asignar permisos a roles
            self._asignar_permisos_roles(cursor)
            
            conn.commit()
            print("✅ Sistema de usuarios inicializado correctamente")
            
        except Exception as e:
            print(f"❌ Error inicializando base de datos: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def _crear_roles_default(self, cursor):
        """Crear roles predeterminados"""
        roles_default = [
            ('superadmin', 'Super Administrador con acceso total', 10),
            ('admin', 'Administrador del sistema', 9),
            ('supervisor_almacen', 'Supervisor de almacén', 8),
            ('supervisor_produccion', 'Supervisor de producción', 7),
            ('operador_almacen', 'Operador de almacén', 5),
            ('operador_produccion', 'Operador de producción', 4),
            ('calidad', 'Personal de calidad', 3),
            ('consulta', 'Usuario de consulta', 2),
            ('invitado', 'Usuario invitado', 1)
        ]
        
        for nombre, descripcion, nivel in roles_default:
            cursor.execute('''
                INSERT OR IGNORE INTO roles (nombre, descripcion, nivel) 
                VALUES (?, ?, ?)
            ''', (nombre, descripcion, nivel))
    
    def _crear_permisos_default(self, cursor):
        """Crear permisos predeterminados"""
        permisos_default = [
            # Sistema
            ('sistema', 'acceso', 'Acceso al sistema'),
            ('sistema', 'configurar', 'Configurar sistema'),
            ('sistema', 'usuarios', 'Gestionar usuarios'),
            ('sistema', 'auditoria', 'Ver logs de auditoría'),
            ('sistema', 'respaldos', 'Crear y restaurar respaldos'),
            
            # Material
            ('material', 'ver', 'Ver información de materiales'),
            ('material', 'crear', 'Crear nuevos materiales'),
            ('material', 'editar', 'Editar materiales existentes'),
            ('material', 'eliminar', 'Eliminar materiales'),
            ('material', 'exportar', 'Exportar datos de materiales'),
            ('material', 'importar', 'Importar datos de materiales'),
            
            # Almacén
            ('almacen', 'ver', 'Ver control de almacén'),
            ('almacen', 'entrada', 'Registrar entradas de material'),
            ('almacen', 'salida', 'Registrar salidas de material'),
            ('almacen', 'imprimir', 'Imprimir etiquetas'),
            ('almacen', 'exportar', 'Exportar datos de almacén'),
            ('almacen', 'inventario', 'Gestionar inventario'),
            
            # BOM (Bill of Materials)
            ('bom', 'ver', 'Ver lista de materiales BOM'),
            ('bom', 'crear', 'Crear BOM'),
            ('bom', 'editar', 'Editar BOM'),
            ('bom', 'eliminar', 'Eliminar BOM'),
            ('bom', 'importar', 'Importar BOM'),
            ('bom', 'exportar', 'Exportar BOM'),
            
            # Producción
            ('produccion', 'ver', 'Ver datos de producción'),
            ('produccion', 'planificar', 'Planificar producción'),
            ('produccion', 'ejecutar', 'Ejecutar órdenes de producción'),
            ('produccion', 'reportar', 'Reportar producción'),
            
            # Calidad
            ('calidad', 'ver', 'Ver controles de calidad'),
            ('calidad', 'inspeccionar', 'Realizar inspecciones'),
            ('calidad', 'aprobar', 'Aprobar materiales'),
            ('calidad', 'rechazar', 'Rechazar materiales'),
            
            # Reportes
            ('reportes', 'ver', 'Ver reportes'),
            ('reportes', 'crear', 'Crear reportes personalizados'),
            ('reportes', 'exportar', 'Exportar reportes'),
            ('reportes', 'programar', 'Programar reportes automáticos'),
        ]
        
        for modulo, accion, descripcion in permisos_default:
            cursor.execute('''
                INSERT OR IGNORE INTO permisos (modulo, accion, descripcion) 
                VALUES (?, ?, ?)
            ''', (modulo, accion, descripcion))
    
    def _asignar_permisos_roles(self, cursor):
        """Asignar permisos a roles"""
        # Super Admin - todos los permisos
        cursor.execute('SELECT id FROM roles WHERE nombre = "superadmin"')
        superadmin_id = cursor.fetchone()
        if superadmin_id:
            cursor.execute('SELECT id FROM permisos')
            todos_permisos = cursor.fetchall()
            for permiso in todos_permisos:
                cursor.execute('''
                    INSERT OR IGNORE INTO rol_permisos (rol_id, permiso_id)
                    VALUES (?, ?)
                ''', (superadmin_id[0], permiso[0]))
        
        # Admin - casi todos excepto algunos críticos
        cursor.execute('SELECT id FROM roles WHERE nombre = "admin"')
        admin_id = cursor.fetchone()
        if admin_id:
            cursor.execute('''
                SELECT p.id FROM permisos p 
                WHERE NOT (p.modulo = 'sistema' AND p.accion IN ('respaldos', 'usuarios'))
            ''')
            permisos_admin = cursor.fetchall()
            for permiso in permisos_admin:
                cursor.execute('''
                    INSERT OR IGNORE INTO rol_permisos (rol_id, permiso_id)
                    VALUES (?, ?)
                ''', (admin_id[0], permiso[0]))
        
        # Supervisor Almacén
        permisos_supervisor_almacen = [
            ('sistema', 'acceso'), ('material', 'ver'), ('material', 'crear'), 
            ('material', 'editar'), ('material', 'exportar'), ('almacen', 'ver'), 
            ('almacen', 'entrada'), ('almacen', 'salida'), ('almacen', 'imprimir'),
            ('almacen', 'exportar'), ('almacen', 'inventario'), ('reportes', 'ver'),
            ('reportes', 'exportar')
        ]
        self._asignar_permisos_especificos(cursor, 'supervisor_almacen', permisos_supervisor_almacen)
        
        # Operador Almacén
        permisos_operador_almacen = [
            ('sistema', 'acceso'), ('material', 'ver'), ('almacen', 'ver'),
            ('almacen', 'entrada'), ('almacen', 'salida'), ('almacen', 'imprimir')
        ]
        self._asignar_permisos_especificos(cursor, 'operador_almacen', permisos_operador_almacen)
        
        # Usuario de Consulta
        permisos_consulta = [
            ('sistema', 'acceso'), ('material', 'ver'), ('almacen', 'ver'),
            ('bom', 'ver'), ('produccion', 'ver'), ('calidad', 'ver'),
            ('reportes', 'ver')
        ]
        self._asignar_permisos_especificos(cursor, 'consulta', permisos_consulta)
    
    def _asignar_permisos_especificos(self, cursor, rol_nombre, permisos):
        """Asignar permisos específicos a un rol"""
        cursor.execute('SELECT id FROM roles WHERE nombre = ?', (rol_nombre,))
        rol_id = cursor.fetchone()
        if rol_id:
            for modulo, accion in permisos:
                cursor.execute('SELECT id FROM permisos WHERE modulo = ? AND accion = ?', (modulo, accion))
                permiso_id = cursor.fetchone()
                if permiso_id:
                    cursor.execute('''
                        INSERT OR IGNORE INTO rol_permisos (rol_id, permiso_id)
                        VALUES (?, ?)
                    ''', (rol_id[0], permiso_id[0]))
    
    def create_default_admin(self):
        """Crear usuario administrador por defecto"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Verificar si ya existe un superadmin
            cursor.execute('SELECT COUNT(*) FROM usuarios_sistema WHERE username = "admin"')
            existe = cursor.fetchone()[0]
            
            if existe == 0:
                # Crear usuario admin por defecto
                password_hash = self.hash_password('admin123')
                cursor.execute('''
                    INSERT INTO usuarios_sistema (
                        username, password_hash, nombre_completo, 
                        departamento, cargo, creado_por
                    ) VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    'admin', password_hash, 'Administrador Sistema',
                    'Sistemas', 'Administrador', 'sistema'
                ))
                
                admin_id = cursor.lastrowid
                
                # Asignar rol de superadmin
                cursor.execute('SELECT id FROM roles WHERE nombre = "superadmin"')
                rol_superadmin = cursor.fetchone()
                if rol_superadmin:
                    cursor.execute('''
                        INSERT INTO usuario_roles (usuario_id, rol_id, asignado_por)
                        VALUES (?, ?, ?)
                    ''', (admin_id, rol_superadmin[0], 'sistema'))
                
                conn.commit()
                print("✅ Usuario administrador creado: admin/admin123")
            
            conn.close()
        except Exception as e:
            print(f"❌ Error creando admin por defecto: {e}")
    
    @staticmethod
    def hash_password(password):
        """Hashear contraseña de forma segura"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def verificar_usuario(self, username, password):
        """Verificar credenciales de usuario con protección contra ataques"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Verificar si el usuario está bloqueado
            cursor.execute('''
                SELECT id, username, password_hash, activo, intentos_fallidos,
                       bloqueado_hasta, nombre_completo, departamento
                FROM usuarios_sistema 
                WHERE username = ?
            ''', (username,))
            
            usuario = cursor.fetchone()
            
            if not usuario:
                return False, "Usuario no encontrado"
            
            # Verificar si está bloqueado
            if usuario['bloqueado_hasta']:
                bloqueado_hasta = datetime.fromisoformat(usuario['bloqueado_hasta'])
                if datetime.now() < bloqueado_hasta:
                    return False, f"Usuario bloqueado hasta {bloqueado_hasta.strftime('%H:%M:%S')}"
                else:
                    # Desbloquear usuario
                    cursor.execute('''
                        UPDATE usuarios_sistema 
                        SET bloqueado_hasta = NULL, intentos_fallidos = 0
                        WHERE id = ?
                    ''', (usuario['id'],))
            
            if usuario['activo'] != 1:
                return False, "Usuario inactivo"
            
            # Verificar contraseña
            if usuario['password_hash'] == self.hash_password(password):
                # Login exitoso - resetear intentos fallidos
                cursor.execute('''
                    UPDATE usuarios_sistema 
                    SET ultimo_acceso = CURRENT_TIMESTAMP, intentos_fallidos = 0,
                        bloqueado_hasta = NULL
                    WHERE id = ?
                ''', (usuario['id'],))
                
                # Registrar sesión activa
                token_sesion = secrets.token_hex(32)
                ip_address = request.remote_addr if request else 'sistema'
                user_agent = request.headers.get('User-Agent', 'sistema') if request else 'sistema'
                
                cursor.execute('''
                    INSERT INTO sesiones_activas (
                        usuario, token_sesion, ip_address, user_agent
                    ) VALUES (?, ?, ?, ?)
                ''', (username, token_sesion, ip_address, user_agent))
                
                conn.commit()
                return True, "Login exitoso"
            else:
                # Password incorrecto - incrementar intentos fallidos
                intentos = usuario['intentos_fallidos'] + 1
                bloqueado_hasta = None
                
                if intentos >= 5:  # Bloquear después de 5 intentos
                    bloqueado_hasta = datetime.now() + timedelta(minutes=30)
                    cursor.execute('''
                        UPDATE usuarios_sistema 
                        SET intentos_fallidos = ?, bloqueado_hasta = ?
                        WHERE id = ?
                    ''', (intentos, bloqueado_hasta.isoformat(), usuario['id']))
                    mensaje = "Usuario bloqueado por 30 minutos debido a múltiples intentos fallidos"
                else:
                    cursor.execute('''
                        UPDATE usuarios_sistema 
                        SET intentos_fallidos = ?
                        WHERE id = ?
                    ''', (intentos, usuario['id']))
                    mensaje = f"Contraseña incorrecta. Intentos restantes: {5 - intentos}"
                
                conn.commit()
                return False, mensaje
                
        except Exception as e:
            print(f"Error en verificación de usuario: {e}")
            return False, "Error interno del sistema"
        finally:
            conn.close()
    
    def obtener_permisos_usuario(self, username):
        """Obtener todos los permisos de un usuario basado en sus roles"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT DISTINCT p.modulo, p.accion, r.nivel
                FROM usuarios_sistema u
                JOIN usuario_roles ur ON u.id = ur.usuario_id
                JOIN roles r ON ur.rol_id = r.id
                JOIN rol_permisos rp ON r.id = rp.rol_id
                JOIN permisos p ON rp.permiso_id = p.id
                WHERE u.username = ? AND u.activo = 1 AND r.activo = 1 AND p.activo = 1
                ORDER BY r.nivel DESC
            ''', (username,))
            
            permisos = cursor.fetchall()
            
            # Convertir a diccionario para fácil acceso
            permisos_dict = {}
            max_nivel = 0
            
            for permiso in permisos:
                modulo = permiso['modulo']
                accion = permiso['accion']
                nivel = permiso['nivel']
                
                if modulo not in permisos_dict:
                    permisos_dict[modulo] = []
                permisos_dict[modulo].append(accion)
                
                max_nivel = max(max_nivel, nivel)
            
            return permisos_dict, max_nivel
            
        except Exception as e:
            print(f"Error obteniendo permisos: {e}")
            return {}, 0
        finally:
            conn.close()
    
    def registrar_auditoria(self, usuario, modulo, accion, descripcion='', 
                           datos_antes=None, datos_despues=None, resultado='EXITOSO',
                           duracion_ms=None):
        """Registrar acción en el historial de auditoría"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Obtener información de la petición
            ip_address = request.remote_addr if request else 'Sistema'
            user_agent = request.headers.get('User-Agent', 'Sistema')[:500] if request else 'Sistema'
            endpoint = request.endpoint if request else 'sistema'
            metodo_http = request.method if request else 'SISTEMA'
            
            # Convertir datos a JSON si es necesario
            if datos_antes and not isinstance(datos_antes, str):
                datos_antes = json.dumps(datos_antes, ensure_ascii=False, default=str)
            if datos_despues and not isinstance(datos_despues, str):
                datos_despues = json.dumps(datos_despues, ensure_ascii=False, default=str)
            
            cursor.execute('''
                INSERT INTO auditoria (
                    usuario, modulo, accion, descripcion, datos_antes, 
                    datos_despues, ip_address, user_agent, resultado,
                    duracion_ms, endpoint, metodo_http
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                usuario, modulo, accion, descripcion[:1000], 
                datos_antes, datos_despues, ip_address, 
                user_agent, resultado, duracion_ms, endpoint, metodo_http
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"Error registrando auditoría: {e}")
    
    def requiere_permiso(self, modulo, accion):
        """Decorador para verificar permisos en endpoints"""
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                if 'usuario' not in session:
                    if request.is_json:
                        return jsonify({'error': 'No autenticado', 'codigo': 401}), 401
                    return redirect('/login')
                
                usuario = session.get('usuario')
                permisos = session.get('permisos', {})
                
                print(f"🔍 Verificando permisos para {usuario}: {modulo}.{accion}")
                print(f"🔍 Permisos en sesión: {permisos}")
                
                # Verificar si el usuario tiene el permiso requerido
                # FORMATO ESPERADO: permisos = {'sistema': ['usuarios', 'auditoria'], 'material': ['ver', 'crear']}
                tiene_permiso = False
                
                if isinstance(permisos, dict):
                    if modulo in permisos and accion in permisos[modulo]:
                        tiene_permiso = True
                        print(f"✅ Permiso encontrado: {modulo}.{accion}")
                    else:
                        print(f"❌ Permiso no encontrado: {modulo}.{accion} en {permisos.get(modulo, 'módulo no encontrado')}")
                else:
                    print(f"❌ Formato de permisos incorrecto: {type(permisos)}")
                
                if not tiene_permiso:
                    print(f"❌ Permiso denegado: {modulo}.{accion}")
                    # Registrar intento no autorizado
                    self.registrar_auditoria(
                        usuario=usuario,
                        modulo=modulo,
                        accion=accion,
                        descripcion=f'Intento de acceso no autorizado a {modulo}.{accion}',
                        resultado='DENEGADO'
                    )
                    
                    if request.is_json:
                        return jsonify({
                            'error': 'No tiene permisos para esta acción', 
                            'codigo': 403,
                            'requerido': f'{modulo}.{accion}'
                        }), 403
                    
                    return redirect('/login')
                
                print(f"✅ Permiso concedido: {modulo}.{accion}")
                
                # Registrar inicio de acción
                inicio = datetime.now()
                
                try:
                    resultado = f(*args, **kwargs)
                    
                    # Calcular duración
                    duracion = int((datetime.now() - inicio).total_seconds() * 1000)
                    
                    # Registrar éxito para acciones importantes
                    if request.method in ['POST', 'PUT', 'DELETE']:
                        self.registrar_auditoria(
                            usuario=usuario,
                            modulo=modulo,
                            accion=accion,
                            descripcion=f'Acción ejecutada: {request.endpoint}',
                            resultado='EXITOSO',
                            duracion_ms=duracion
                        )
                    
                    return resultado
                    
                except Exception as e:
                    # Registrar error
                    duracion = int((datetime.now() - inicio).total_seconds() * 1000)
                    self.registrar_auditoria(
                        usuario=usuario,
                        modulo=modulo,
                        accion=accion,
                        descripcion=f'Error en {request.endpoint}: {str(e)}',
                        resultado='ERROR',
                        duracion_ms=duracion
                    )
                    raise
                    
            return decorated_function
        return decorator
    
    def login_requerido_avanzado(self, f):
        """Decorador mejorado con auditoría automática"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'usuario' not in session:
                print(f"❌ No hay usuario en sesión para acceder a {request.endpoint}")
                if request.is_json:
                    return jsonify({'error': 'No autenticado'}), 401
                return redirect('/login')  # Usar ruta absoluta en lugar de url_for
            
            print(f"✅ Usuario {session.get('usuario')} accediendo a {request.endpoint}")
            # Actualizar última actividad
            self._actualizar_actividad_sesion(session.get('usuario'))
            
            return f(*args, **kwargs)
            
        return decorated_function
    
    def _actualizar_actividad_sesion(self, usuario):
        """Actualizar última actividad del usuario"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE sesiones_activas 
                SET fecha_ultima_actividad = CURRENT_TIMESTAMP
                WHERE usuario = ? AND activa = 1
            ''', (usuario,))
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error actualizando actividad: {e}")

# Instancia global del sistema de autenticación
auth_system = AuthSystem()
