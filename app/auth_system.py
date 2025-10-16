"""
Sistema de Autenticación y Autorización Avanzado
Complemento para el sistema ILSAN MES
"""

import hashlib
import secrets
import json
import os
import threading
import time
from functools import wraps
from flask import session, jsonify, request, redirect, url_for, g, current_app
from datetime import datetime, timedelta, timezone
import traceback
from .db_mysql import get_db_connection
from werkzeug.security import generate_password_hash, check_password_hash

# Importar MySQLdb para cursores de diccionario
try:
    import pymysql
    pymysql.install_as_MySQLdb()
    import MySQLdb
    MYSQLDB_AVAILABLE = True
except ImportError:
    MYSQLDB_AVAILABLE = False
    print("MySQLdb no disponible para auth_system")

class AuthSystem:
    def __init__(self, app=None):
        self.app = app
        if app:
            self.init_app(app)
    
    @staticmethod
    def get_mexico_time():
        """Obtener la hora actual de México (GMT-6)"""
        import os
        # Establecer zona horaria para Windows
        os.environ['TZ'] = 'CST6CDT'
        
        # Crear timezone para México (GMT-6)
        mexico_tz = timezone(timedelta(hours=-6))
        return datetime.now(mexico_tz)
    
    @staticmethod  
    def get_mexico_time_iso():
        """Obtener la hora actual de México en formato ISO sin zona horaria"""
        # Retornar sin información de timezone para compatibilidad con SQLite
        mexico_time = AuthSystem.get_mexico_time()
        return mexico_time.replace(tzinfo=None).isoformat()
    
    @staticmethod
    def get_mexico_time_mysql():
        """Obtener la hora actual de México en formato compatible con MySQL"""
        # Formato YYYY-MM-DD HH:MM:SS compatible con MySQL DATETIME
        mexico_time = AuthSystem.get_mexico_time()
        return mexico_time.replace(tzinfo=None).strftime('%Y-%m-%d %H:%M:%S')
    
    def init_app(self, app):
        """Inicializar el sistema de autenticación con la app Flask"""
        self.app = app
        self.init_database()
        self.create_default_admin()
    
    def init_database(self):
        """Inicializar todas las tablas del sistema de usuarios"""
        from .db import MYSQL_AVAILABLE
        
        if MYSQL_AVAILABLE:
            # Usar MySQL - las tablas se crean automáticamente
            print(" Sistema de autenticación usando MySQL")
            return
        
        # Fallback a SQLite
        conn = get_db_connection()
        if conn is None:
            print("❌ Error: No se pudo obtener conexión a la base de datos")
            return
            
        cursor = conn.cursor()
        
        try:
            # Tabla de usuarios mejorada
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS usuarios_sistema (
                    id INT AUTO_INCREMENT PRIMARY KEY,
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
                    id INT AUTO_INCREMENT PRIMARY KEY,
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
                    id INT AUTO_INCREMENT PRIMARY KEY,
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
                    id INT AUTO_INCREMENT PRIMARY KEY,
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
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    usuario TEXT NOT NULL,
                    token_sesion TEXT UNIQUE NOT NULL,
                    ip_address TEXT,
                    user_agent TEXT,
                    fecha_inicio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    fecha_ultima_actividad TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    activa INTEGER DEFAULT 1
                )
            ''')
            
            # Tabla de permisos específicos por página/botón
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS permisos_botones (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    pagina TEXT NOT NULL,
                    seccion TEXT NOT NULL,
                    boton TEXT NOT NULL,
                    descripcion TEXT,
                    activo INTEGER DEFAULT 1,
                    UNIQUE(pagina, seccion, boton)
                )
            ''')
            
            # Tabla de permisos de botones por rol
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS rol_permisos_botones (
                    rol_id INTEGER NOT NULL,
                    permiso_boton_id INTEGER NOT NULL,
                    fecha_asignacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (rol_id, permiso_boton_id),
                    FOREIGN KEY (rol_id) REFERENCES roles(id),
                    FOREIGN KEY (permiso_boton_id) REFERENCES permisos_botones(id)
                )
            ''')
            
            # Insertar roles predeterminados
            self._crear_roles_default(cursor)
            
            # Insertar permisos predeterminados  
            # self._crear_permisos_default(cursor)  # COMENTADO: Solo usar permisos de botones
            
            # Insertar permisos de botones predeterminados
            self._crear_permisos_botones_default(cursor)
            
            # Asignar permisos a roles
            # self._asignar_permisos_roles(cursor)  # COMENTADO: Solo usar permisos de botones
            
            # Asignar permisos de botones a roles
            self._asignar_permisos_botones_roles(cursor)
            
            conn.commit()
            print(" Sistema de usuarios inicializado correctamente")
            
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
                VALUES (%s, %s, %s)
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
                VALUES (%s, %s, %s)
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
                    VALUES (%s, %s)
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
                    VALUES (%s, %s)
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
        cursor.execute('SELECT id FROM roles WHERE nombre = %s', (rol_nombre,))
        rol_id = cursor.fetchone()
        if rol_id:
            for modulo, accion in permisos:
                cursor.execute('SELECT id FROM permisos WHERE modulo = %s AND accion = %s', (modulo, accion))
                permiso_id = cursor.fetchone()
                if permiso_id:
                    cursor.execute('''
                        INSERT OR IGNORE INTO rol_permisos (rol_id, permiso_id)
                        VALUES (%s, %s)
                    ''', (rol_id[0], permiso_id[0]))
    
    def _crear_permisos_botones_default(self, cursor):
        """Crear permisos específicos de botones para las páginas LISTAS"""
        permisos_botones = [
            # LISTA DE MATERIALES - Control de material
            ('LISTA_DE_MATERIALES', 'Control de material', 'Control de material de almacén', 'Acceso al control de material de almacén'),
            ('LISTA_DE_MATERIALES', 'Control de material', 'Control de salida', 'Acceso al control de salida de material'),
            ('LISTA_DE_MATERIALES', 'Control de material', 'Control de material retorno', 'Acceso al control de retorno de material'),
            ('LISTA_DE_MATERIALES', 'Control de material', 'Recibo y pago del material', 'Acceso a recibo y pago del material'),
            ('LISTA_DE_MATERIALES', 'Control de material', 'Historial de material', 'Acceso al historial de material'),
            ('LISTA_DE_MATERIALES', 'Control de material', 'Estatus de material', 'Acceso al estatus de material'),
            ('LISTA_DE_MATERIALES', 'Control de material', 'Material sustituto', 'Acceso a material sustituto'),
            ('LISTA_DE_MATERIALES', 'Control de material', 'Consultar PEPS', 'Acceso a consulta PEPS'),
            ('LISTA_DE_MATERIALES', 'Control de material', 'Control de Long-Term Inventory', 'Acceso a control de inventario de largo plazo'),
            ('LISTA_DE_MATERIALES', 'Control de material', 'Registro de material real', 'Acceso a registro de material real'),
            ('LISTA_DE_MATERIALES', 'Control de material', 'Historial de inventario real', 'Acceso al historial de inventario real'),
            ('LISTA_DE_MATERIALES', 'Control de material', 'Inventario de rollos SMD', 'Acceso al inventario de rollos SMD'),
            ('LISTA_DE_MATERIALES', 'Control de material', 'Ajuste de número de parte', 'Acceso a ajuste de número de parte'),
            
            # LISTA DE MATERIALES - Control de material MSL
            ('LISTA_DE_MATERIALES', 'Control de material MSL', 'Control total de material', 'Acceso al control total de material MSL'),
            ('LISTA_DE_MATERIALES', 'Control de material MSL', 'Control de entrada y salida de material', 'Control de entrada y salida de material MSL'),
            ('LISTA_DE_MATERIALES', 'Control de material MSL', 'Estatus de material MSL', 'Acceso al estatus de material MSL'),
            
            # LISTA DE MATERIALES - Control de refacciones
            ('LISTA_DE_MATERIALES', 'Control de refacciones', 'Estándares sobre refacciones', 'Acceso a estándares sobre refacciones'),
            ('LISTA_DE_MATERIALES', 'Control de refacciones', 'Control de recibo de refacciones', 'Acceso al control de recibo de refacciones'),
            ('LISTA_DE_MATERIALES', 'Control de refacciones', 'Control de salida de refacciones', 'Acceso al control de salida de refacciones'),
            ('LISTA_DE_MATERIALES', 'Control de refacciones', 'Estatus de inventario de refacciones', 'Acceso al estatus de inventario de refacciones'),
            
            # LISTA INFORMACIÓN BÁSICA - Información básica
            ('LISTA_INFORMACIONBASICA', 'Información básica', 'Gestión de departamentos', 'Acceso a gestión de departamentos'),
            ('LISTA_INFORMACIONBASICA', 'Información básica', 'Gestión de empleados', 'Acceso a gestión de empleados'),
            ('LISTA_INFORMACIONBASICA', 'Información básica', 'Gestión de proveedores', 'Acceso a gestión de proveedores'),
            ('LISTA_INFORMACIONBASICA', 'Información básica', 'Gestión de clientes', 'Acceso a gestión de clientes'),
            ('LISTA_INFORMACIONBASICA', 'Información básica', 'Administracion de itinerario', 'Acceso a administración de itinerario'),
            ('LISTA_INFORMACIONBASICA', 'Información básica', 'Consultar licencias', 'Acceso a consultar licencias'),
            
            # LISTA INFORMACIÓN BÁSICA - Control de Proceso
            ('LISTA_INFORMACIONBASICA', 'Control de Proceso', 'Control de departamento', 'Acceso al control de departamento'),
            ('LISTA_INFORMACIONBASICA', 'Control de Proceso', 'Control de proceso', 'Acceso al control de proceso'),
            
            # LISTA CONTROL DE PRODUCCIÓN - Información básica
            ('LISTA_CONTROLDEPRODUCCION', 'Información básica', 'Información básica', 'Acceso a información básica de producción'),
            
            # LISTA CONTROL DE PRODUCCIÓN - Control de proceso  
            ('LISTA_CONTROLDEPRODUCCION', 'Control de proceso', 'Control de proceso', 'Acceso al control de proceso de producción'),
            
            # LISTA CONTROL DE PRODUCCIÓN - Control de calidad
            ('LISTA_CONTROLDEPRODUCCION', 'Control de calidad', 'Control de calidad', 'Acceso al control de calidad de producción'),
            
            # LISTA CONTROL DE PRODUCCIÓN - Gestión
            ('LISTA_CONTROLDEPRODUCCION', 'Gestión', 'Gestión', 'Acceso a gestión de producción'),
            
            # LISTA CONTROL DE PRODUCCIÓN - Configuración
            ('LISTA_CONTROLDEPRODUCCION', 'Configuración', 'Configuración', 'Acceso a configuración de producción'),
            
            # LISTA CONTROL DE PROCESO - Control de produccion
            ('LISTA_CONTROL_DE_PROCESO', 'Control de produccion', 'Historial de operacion por proceso', 'Acceso al historial de operación por proceso'),
            ('LISTA_CONTROL_DE_PROCESO', 'Control de produccion', 'BOM Management By Process', 'Acceso a BOM Management por proceso'),
            
            # LISTA CONTROL DE PROCESO - Reporte diario de inspeccion
            ('LISTA_CONTROL_DE_PROCESO', 'Reporte diario de inspeccion', 'Reporte diario de inspeccion', 'Acceso a reporte diario de inspección'),
            
            # LISTA CONTROL DE PROCESO - Control de otras identificaciones
            ('LISTA_CONTROL_DE_PROCESO', 'Control de otras identificaciones', 'Registro de movimiento de identificacion', 'Acceso a registro de movimiento de identificación'),
            ('LISTA_CONTROL_DE_PROCESO', 'Control de otras identificaciones', 'Control de otras identificaciones', 'Acceso al control de otras identificaciones'),
            
            # LISTA CONTROL DE PROCESO - Control de N/S
            ('LISTA_CONTROL_DE_PROCESO', 'Control de N/S', 'Control de movimiento de N/S de producto', 'Acceso al control de movimiento de N/S de producto'),
            ('LISTA_CONTROL_DE_PROCESO', 'Control de N/S', 'Model S/N Management', 'Acceso a Model S/N Management'),
            
            # LISTA CONTROL DE PROCESO - Control de material Scrap
            ('LISTA_CONTROL_DE_PROCESO', 'Control de material Scrap', 'Control de Scrap', 'Acceso al control de Scrap'),
            
            # LISTA CONTROL DE PROCESO - Inventario IMD Terminado
            ('LISTA_CONTROL_DE_PROCESO', 'Inventario', 'IMD-SMD TERMINADO', 'Acceso al inventario de productos IMD terminados'),
            
            # LISTA CONTROL DE CALIDAD - Control de calidad  
            ('LISTA_CONTROL_DE_CALIDAD', 'Control de calidad', 'Inspección de entrada', 'Acceso a inspección de entrada'),
            ('LISTA_CONTROL_DE_CALIDAD', 'Control de calidad', 'Inspección en proceso', 'Acceso a inspección en proceso'),
            ('LISTA_CONTROL_DE_CALIDAD', 'Control de calidad', 'Inspección final', 'Acceso a inspección final'),
            ('LISTA_CONTROL_DE_CALIDAD', 'Control de calidad', 'Control de calibracion', 'Acceso al control de calibración'),
            ('LISTA_CONTROL_DE_CALIDAD', 'Control de calidad', 'Reportes de calidad', 'Acceso a reportes de calidad'),
            
            # LISTA DE CONTROL DE RESULTADOS
            ('LISTA_DE_CONTROL_DE_RESULTADOS', 'Control de resultados', 'Análisis de resultados', 'Acceso al análisis de resultados'),
            ('LISTA_DE_CONTROL_DE_RESULTADOS', 'Control de resultados', 'Reportes estadísticos', 'Acceso a reportes estadísticos'),
            ('LISTA_DE_CONTROL_DE_RESULTADOS', 'Control de resultados', 'Gráficos de tendencia', 'Acceso a gráficos de tendencia'),
            
            # LISTA DE CONTROL DE REPORTE
            ('LISTA_DE_CONTROL_DE_REPORTE', 'Control de reporte', 'Generación de reportes', 'Acceso a generación de reportes'),
            ('LISTA_DE_CONTROL_DE_REPORTE', 'Control de reporte', 'Configuración de reportes', 'Acceso a configuración de reportes'),
            ('LISTA_DE_CONTROL_DE_REPORTE', 'Control de reporte', 'Programación de reportes', 'Acceso a programación de reportes'),
            
            # LISTA DE CONFIGPG
            ('LISTA_DE_CONFIGPG', 'Configuración', 'Configuración general', 'Acceso a configuración general del sistema'),
            ('LISTA_DE_CONFIGPG', 'Configuración', 'Configuración de usuarios', 'Acceso a configuración de usuarios'),
            ('LISTA_DE_CONFIGPG', 'Configuración', 'Configuración de impresión', 'Acceso a configuración de impresión'),
            ('LISTA_DE_CONFIGPG', 'Configuración', 'Configuración de red', 'Acceso a configuración de red')
        ]
        
        for pagina, seccion, boton, descripcion in permisos_botones:
            cursor.execute('''
                INSERT OR IGNORE INTO permisos_botones (pagina, seccion, boton, descripcion)
                VALUES (%s, %s, %s, %s)
            ''', (pagina, seccion, boton, descripcion))
    
    def _asignar_permisos_botones_roles(self, cursor):
        """Asignar permisos de botones a roles"""
        
        # Super Admin - todos los permisos de botones
        cursor.execute('SELECT id FROM roles WHERE nombre = "superadmin"')
        superadmin_id = cursor.fetchone()
        if superadmin_id:
            cursor.execute('SELECT id FROM permisos_botones WHERE activo = 1')
            todos_permisos_botones = cursor.fetchall()
            for permiso in todos_permisos_botones:
                cursor.execute('''
                    INSERT OR IGNORE INTO rol_permisos_botones (rol_id, permiso_boton_id)
                    VALUES (%s, %s)
                ''', (superadmin_id[0], permiso[0]))
        
        # Admin - todos excepto configuración crítica
        cursor.execute('SELECT id FROM roles WHERE nombre = "admin"')
        admin_id = cursor.fetchone()
        if admin_id:
            cursor.execute('''
                SELECT id FROM permisos_botones 
                WHERE activo = 1 AND NOT (seccion = 'Configuración' AND boton LIKE '%crítico%')
            ''')
            permisos_admin_botones = cursor.fetchall()
            for permiso in permisos_admin_botones:
                cursor.execute('''
                    INSERT OR IGNORE INTO rol_permisos_botones (rol_id, permiso_boton_id)
                    VALUES (%s, %s)
                ''', (admin_id[0], permiso[0]))
        
        # Supervisor Almacén - solo materiales y control de almacén
        self._asignar_permisos_botones_especificos(cursor, 'supervisor_almacen', [
            'LISTA_DE_MATERIALES', 'LISTA_INFORMACIONBASICA'
        ], [
            'Control de material', 'Control de material MSL', 'Información básica'
        ])
        
        # Operador Almacén - solo funciones básicas de almacén
        self._asignar_permisos_botones_especificos(cursor, 'operador_almacen', [
            'LISTA_DE_MATERIALES'
        ], [
            'Control de material'
        ])
        
        # Control de Calidad - solo funciones de calidad
        self._asignar_permisos_botones_especificos(cursor, 'calidad', [
            'LISTA_CONTROL_DE_CALIDAD', 'LISTA_INFORMACIONBASICA'
        ], [
            'Control de calidad', 'Información básica'
        ])
        
        # Consulta - solo ver, sin modificar
        self._asignar_permisos_botones_especificos(cursor, 'consulta', [
            'LISTA_DE_MATERIALES', 'LISTA_CONTROL_DE_CALIDAD', 'LISTA_CONTROL_DE_PROCESO', 'LISTA_INFORMACIONBASICA'
        ], [
            'Información básica'
        ])
    
    def _asignar_permisos_botones_especificos(self, cursor, rol_nombre, paginas_permitidas, secciones_permitidas):
        """Asignar permisos específicos de botones a un rol"""
        cursor.execute('SELECT id FROM roles WHERE nombre = %s', (rol_nombre,))
        rol_id = cursor.fetchone()
        if rol_id:
            # Crear placeholders para la consulta IN
            paginas_placeholders = ','.join('?' * len(paginas_permitidas))
            secciones_placeholders = ','.join('?' * len(secciones_permitidas))
            
            cursor.execute(f'''
                SELECT id FROM permisos_botones 
                WHERE pagina IN ({paginas_placeholders}) 
                AND seccion IN ({secciones_placeholders})
                AND activo = 1
            ''', paginas_permitidas + secciones_permitidas)
            
            permisos_botones = cursor.fetchall()
            for permiso in permisos_botones:
                cursor.execute('''
                    INSERT OR IGNORE INTO rol_permisos_botones (rol_id, permiso_boton_id)
                    VALUES (%s, %s)
                ''', (rol_id[0], permiso[0]))
    
    def create_default_admin(self):
        """Crear usuario administrador por defecto"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Verificar si ya existe un superadmin
            cursor.execute('SELECT COUNT(*) FROM usuarios_sistema WHERE username = %s', ('admin',))
            existe = cursor.fetchone()[0]
            
            if existe == 0:
                # Crear usuario admin por defecto
                password_hash = self.hash_password('admin123')
                cursor.execute('''
                    INSERT INTO usuarios_sistema (
                        username, password_hash, nombre_completo, 
                        departamento, cargo, creado_por
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                ''', (
                    'admin', password_hash, 'Administrador Sistema',
                    'Sistemas', 'Administrador', 'sistema'
                ))
                
                admin_id = cursor.lastrowid
                
                # Asignar rol de superadmin
                cursor.execute('SELECT id FROM roles WHERE nombre = %s', ('superadmin',))
                rol_superadmin = cursor.fetchone()
                if rol_superadmin:
                    cursor.execute('''
                        INSERT INTO usuario_roles (usuario_id, rol_id, asignado_por)
                        VALUES (%s, %s, %s)
                    ''', (admin_id, rol_superadmin[0], 'sistema'))
                
                conn.commit()
                print(" Usuario administrador creado: admin/admin123")
            
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
        cursor = conn.cursor(MySQLdb.cursors.DictCursor)
        
        try:
            # Verificar si el usuario está bloqueado
            cursor.execute('''
                SELECT id, username, password_hash, activo, intentos_fallidos,
                       bloqueado_hasta, nombre_completo, departamento
                FROM usuarios_sistema 
                WHERE username = %s
            ''', (username,))
            
            usuario = cursor.fetchone()
            
            if not usuario:
                return False, "Usuario no encontrado"
            
            # Verificar si está bloqueado
            if usuario['bloqueado_hasta'] and isinstance(usuario['bloqueado_hasta'], str):
                bloqueado_hasta = datetime.fromisoformat(usuario['bloqueado_hasta'])
                ahora_mexico = AuthSystem.get_mexico_time().replace(tzinfo=None)
                    
                if ahora_mexico < bloqueado_hasta:
                    return False, f"Usuario bloqueado hasta {bloqueado_hasta.strftime('%H:%M:%S')}"
                else:
                    # Desbloquear usuario
                    cursor.execute('''
                        UPDATE usuarios_sistema 
                        SET bloqueado_hasta = NULL, intentos_fallidos = 0
                        WHERE id = %s
                    ''', (usuario['id'],))
            
            if usuario['activo'] != 1:
                return False, "Usuario inactivo"
            
            # Verificar contraseña
            if usuario['password_hash'] == self.hash_password(password):
                # Login exitoso - resetear intentos fallidos
                # Usar hora local de México en formato compatible con MySQL
                cursor.execute('''
                    UPDATE usuarios_sistema 
                    SET ultimo_acceso = %s, intentos_fallidos = 0,
                        bloqueado_hasta = NULL
                    WHERE id = %s
                ''', (self.get_mexico_time_mysql(), usuario['id']))
                
                # Registrar sesión activa
                token_sesion = secrets.token_hex(32)
                ip_address = request.remote_addr if request else 'sistema'
                user_agent = request.headers.get('User-Agent', 'sistema') if request else 'sistema'
                
                cursor.execute('''
                    INSERT INTO sesiones_activas (
                        usuario_id, token, ip_address, user_agent, fecha_expiracion
                    ) VALUES (%s, %s, %s, %s, DATE_ADD(NOW(), INTERVAL 24 HOUR))
                ''', (usuario['id'], token_sesion, ip_address, user_agent))
                
                conn.commit()
                return True, "Login exitoso"
            else:
                # Password incorrecto - incrementar intentos fallidos
                intentos = usuario['intentos_fallidos'] + 1
                bloqueado_hasta = None
                
                if intentos >= 5:  # Bloquear después de 5 intentos
                    bloqueado_hasta = (AuthSystem.get_mexico_time() + timedelta(minutes=30)).replace(tzinfo=None).isoformat()
                    cursor.execute('''
                        UPDATE usuarios_sistema 
                        SET intentos_fallidos = %s, bloqueado_hasta = %s
                        WHERE id = %s
                    ''', (intentos, bloqueado_hasta, usuario['id']))
                    mensaje = "Usuario bloqueado por 30 minutos debido a múltiples intentos fallidos"
                else:
                    cursor.execute('''
                        UPDATE usuarios_sistema 
                        SET intentos_fallidos = %s
                        WHERE id = %s
                    ''', (intentos, usuario['id']))
                    mensaje = f"Contraseña incorrecta. Intentos restantes: {5 - intentos}"
                
                conn.commit()
                return False, mensaje
                
        except Exception as e:
            print(f"Error en verificación de usuario: {e}")
            return False, "Error interno del sistema"
        finally:
            conn.close()
    
    def obtener_informacion_usuario(self, username):
        """Obtener información completa del usuario"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT id, username, nombre_completo, email, departamento, activo
                FROM usuarios_sistema 
                WHERE username = %s
            ''', (username,))
            
            usuario = cursor.fetchone()
            
            if usuario:
                return {
                    'id': usuario['id'],
                    'username': usuario['username'],
                    'nombre_completo': usuario['nombre_completo'],
                    'email': usuario['email'],
                    'departamento': usuario['departamento'],
                    'activo': usuario['activo']
                }
            else:
                return None
                
        except Exception as e:
            print(f"Error obteniendo información del usuario: {e}")
            return None
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
                WHERE u.username = %s AND u.activo = 1 AND r.activo = 1 AND p.activo = 1
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
    
    def obtener_permisos_botones_usuario(self, username, pagina=None):
        """Obtener permisos específicos de botones para un usuario"""
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            if pagina:
                # Obtener permisos de una página específica
                cursor.execute('''
                    SELECT DISTINCT pb.pagina, pb.seccion, pb.boton, pb.descripcion
                    FROM usuarios_sistema u
                    JOIN usuario_roles ur ON u.id = ur.usuario_id
                    JOIN rol_permisos_botones rpb ON ur.rol_id = rpb.rol_id
                    JOIN permisos_botones pb ON rpb.permiso_boton_id = pb.id
                    WHERE u.username = %s AND pb.pagina = %s AND pb.activo = 1
                    ORDER BY pb.seccion, pb.boton
                ''', (username, pagina))
            else:
                # Obtener todos los permisos de botones
                cursor.execute('''
                    SELECT DISTINCT pb.pagina, pb.seccion, pb.boton, pb.descripcion
                    FROM usuarios_sistema u
                    JOIN usuario_roles ur ON u.id = ur.usuario_id
                    JOIN rol_permisos_botones rpb ON ur.rol_id = rpb.rol_id
                    JOIN permisos_botones pb ON rpb.permiso_boton_id = pb.id
                    WHERE u.username = %s AND pb.activo = 1
                    ORDER BY pb.pagina, pb.seccion, pb.boton
                ''', (username,))
            
            permisos_botones = {}
            for row in cursor.fetchall():
                pagina_nombre = row[0]
                seccion = row[1] 
                boton = row[2]
                descripcion = row[3]
                
                if pagina_nombre not in permisos_botones:
                    permisos_botones[pagina_nombre] = {}
                
                if seccion not in permisos_botones[pagina_nombre]:
                    permisos_botones[pagina_nombre][seccion] = []
                    
                permisos_botones[pagina_nombre][seccion].append({
                    'boton': boton,
                    'descripcion': descripcion
                })
            
            return permisos_botones
            
        except Exception as e:
            print(f"Error obteniendo permisos de botones: {e}")
            return {}
        finally:
            if conn is not None:
                conn.close()
    
    def verificar_permiso_boton(self, username, pagina, seccion, boton):
        """Verificar si un usuario tiene permiso para un botón específico"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT COUNT(*) as count
                FROM usuarios_sistema u
                JOIN usuario_roles ur ON u.id = ur.usuario_id
                JOIN rol_permisos_botones rpb ON ur.rol_id = rpb.rol_id
                JOIN permisos_botones pb ON rpb.permiso_boton_id = pb.id
                WHERE u.username = %s 
                AND pb.pagina = %s 
                AND pb.seccion = %s 
                AND pb.boton = %s 
                AND pb.activo = 1
            ''', (username, pagina, seccion, boton))
            
            result = cursor.fetchone()
            return result[0] > 0
            
        except Exception as e:
            print(f"Error verificando permiso de botón: {e}")
            return False
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
                    duracion_ms, endpoint, metodo_http, fecha_hora
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                usuario, modulo, accion, descripcion[:1000], 
                datos_antes, datos_despues, ip_address, 
                user_agent, resultado, duracion_ms, endpoint, metodo_http,
                self.get_mexico_time_mysql()
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
                        print(f" Permiso encontrado: {modulo}.{accion}")
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
                
                print(f" Permiso concedido: {modulo}.{accion}")
                
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
                # Solo loguear si NO es una petición AJAX esperada de permisos
                if not (request.is_json or '/obtener_permisos' in request.path):
                    print(f"❌ No hay usuario en sesión para acceder a {request.endpoint}")
                if request.is_json:
                    return jsonify({'error': 'No autenticado'}), 401
                return redirect('/login')  # Usar ruta absoluta en lugar de url_for
            
            # Solo loguear accesos exitosos en modo verbose
            # print(f"✓ Usuario {session.get('usuario')} accediendo a {request.endpoint}")
            # Actualizar última actividad
            self._actualizar_actividad_sesion(session.get('usuario'))
            
            return f(*args, **kwargs)
            
        return decorated_function
    
    def _actualizar_actividad_sesion(self, usuario):
        """Actualizar última actividad del usuario"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Actualizar fecha de expiración para mantener la sesión activa
            cursor.execute('''
                UPDATE sesiones_activas 
                SET fecha_expiracion = DATE_ADD(NOW(), INTERVAL 24 HOUR)
                WHERE usuario_id = (SELECT id FROM usuarios_sistema WHERE username = %s) AND activa = 1
            ''', (usuario,))
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error actualizando actividad: {e}")
            
    def agregar_permiso_boton(self, nombre_boton, descripcion, pagina, seccion="Botones"):
        """Agregar un permiso de botón individual"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR IGNORE INTO permisos_botones 
                (pagina, seccion, boton, descripcion) 
                VALUES (%s, %s, %s, ?)
            ''', (pagina, seccion, nombre_boton, descripcion))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error agregando permiso de botón: {e}")
            return False
    
    def asignar_permiso_boton_a_rol(self, rol_nombre, nombre_boton):
        """Asignar un permiso de botón a un rol específico"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Verificar si el permiso y el rol existen
            cursor.execute('SELECT id FROM permisos_botones WHERE boton = %s', (nombre_boton,))
            permiso = cursor.fetchone()
            if not permiso:
                raise Exception(f"Permiso de botón '{nombre_boton}' no encontrado")
            
            cursor.execute('SELECT id FROM roles WHERE nombre = %s', (rol_nombre,))
            rol = cursor.fetchone()
            if not rol:
                raise Exception(f"Rol '{rol_nombre}' no encontrado")
            
            # Asignar el permiso
            cursor.execute('''
                INSERT IGNORE INTO rol_permisos_botones 
                (rol_id, permiso_boton_id) 
                VALUES (%s, %s)
            ''', (rol[0], permiso[0]))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error asignando permiso de botón a rol: {e}")
            return False

# Instancia global del sistema de autenticación
auth_system = AuthSystem()
