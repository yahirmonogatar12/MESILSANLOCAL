"""Funciones de base de datos adaptadas para MySQL
Migración desde SQLite a MySQL para el hosting"""

import os
from .config_mysql import execute_query, test_connection
from datetime import datetime, timedelta
import json
import re
import unicodedata

import logging
logger = logging.getLogger(__name__)

def obtener_fecha_hora_mexico():
    """Obtener fecha y hora actual en zona horaria de México (GMT-6)"""
    try:
        # Calcular hora de México Central (GMT-6)
        utc_now = datetime.utcnow()
        mexico_time = utc_now - timedelta(hours=6)
        return mexico_time.strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:
        # Fallback a hora local
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# Importar pandas si está disponible
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    logger.warning(" Pandas no disponible - funciones de Excel limitadas")

# Verificar si MySQL está disponible
try:
    from .config_mysql import MYSQL_AVAILABLE
except ImportError:
    MYSQL_AVAILABLE = False

logger.info(f"Módulo db_mysql cargado - MySQL disponible: {MYSQL_AVAILABLE}")


def init_db():
    """Inicializar base de datos MySQL y crear tablas"""
    if not MYSQL_AVAILABLE:
        logger.warning(" MySQL no disponible - usando modo fallback")
        return False
        
    try:
        # Probar conexión
        if not test_connection():
            logger.error(" Error conectando a MySQL")
            return False
        
        # Verificar y reparar foreign keys existentes si es necesario
        # repair_foreign_keys()  # COMENTADO: Foreign keys deshabilitadas por solicitud del usuario
        
        # Crear tablas necesarias
        create_tables()
        
        # Agregar columna usuario_registro si no existe (migración)
        try:
            agregar_columna_usuario_registro()
        except Exception as e:
            logger.error(f" Error en migración usuario_registro: {e}")
        
        # MIGRAR TABLA MATERIALES (agregar nuevas columnas)
        logger.info(" Migrando tabla materiales...")
        migrar_tabla_materiales()
        
        # MIGRAR TABLA BOM (agregar columna posicion_assy)
        logger.info(" Migrando tabla bom...")
        migrar_tabla_bom()

        # Crear tablas/vista para ECOs de cambios de ingenieria.
        logger.info(" Inicializando tablas de ECOs...")
        from .api.informacion_basica.control_bom_data import crear_tablas_ecos

        crear_tablas_ecos()
        
        logger.info(" Base de datos MySQL inicializada correctamente")
        return True
    except Exception as e:
        logger.error(f"Error inicializando MySQL: {e}")
        return False


def create_tables():
    """Crear tablas necesarias en MySQL - ORDEN IMPORTANTE"""
    
    # PASO 1: Crear tablas base sin foreign keys primero
    base_tables = {
        'usuarios': '''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(255) UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                area VARCHAR(255),
                activo BOOLEAN DEFAULT TRUE,
                fecha_creacion DATETIME DEFAULT NOW()
            )
        ''',
        'materiales': '''
            CREATE TABLE IF NOT EXISTS materiales (
                id INT AUTO_INCREMENT PRIMARY KEY,
                codigo_material VARCHAR(512) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
                numero_parte VARCHAR(512) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci UNIQUE NOT NULL,
                propiedad_material VARCHAR(512),
                classification VARCHAR(512),
                especificacion_material TEXT,
                unidad_empaque VARCHAR(100),
                ubicacion_material VARCHAR(512),
                vendedor VARCHAR(512),
                prohibido_sacar VARCHAR(50),
                reparable VARCHAR(50),
                nivel_msl VARCHAR(100),
                espesor_msl VARCHAR(100),
                fecha_registro DATETIME DEFAULT NOW(),
                usuario_registro VARCHAR(255),
                descripcion TEXT,
                categoria VARCHAR(255),
                ubicacion VARCHAR(255),
                stock_minimo INT DEFAULT 0,
                stock_maximo INT DEFAULT 0,
                unidad_medida VARCHAR(50),
                proveedor VARCHAR(255),
                fecha_creacion DATETIME DEFAULT NOW(),
                INDEX idx_numero_parte (numero_parte(255)),
                INDEX idx_codigo_material (codigo_material(255)),
                INDEX idx_usuario_registro (usuario_registro)
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        ''',
        'configuracion': '''
            CREATE TABLE IF NOT EXISTS configuracion (
                id INT AUTO_INCREMENT PRIMARY KEY,
                clave VARCHAR(255) UNIQUE NOT NULL,
                valor TEXT,
                fecha_actualizacion DATETIME DEFAULT NOW()
            )
        '''
    }
    
    # Crear tablas base primero
    logger.info(" Creando tablas base...")
    for table_name, create_sql in base_tables.items():
        try:
            execute_query(create_sql)
            logger.info(f" Tabla base {table_name} creada/verificada")
        except Exception as e:
            logger.error(f" Error creando tabla base {table_name}: {e}")
    
    # PASO 2: Crear tablas que dependen de materiales (SIN foreign keys primero)
    dependent_tables_no_fk = {
        'inventario': '''
            CREATE TABLE IF NOT EXISTS inventario (
                id INT AUTO_INCREMENT PRIMARY KEY,
                numero_parte VARCHAR(512) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci UNIQUE NOT NULL,
                cantidad_actual INT DEFAULT 0,
                ultima_actualizacion DATETIME DEFAULT NOW()
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        ''',
        'movimientos_inventario': '''
            CREATE TABLE IF NOT EXISTS movimientos_inventario (
                id INT AUTO_INCREMENT PRIMARY KEY,
                numero_parte VARCHAR(512) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
                tipo_movimiento VARCHAR(50) NOT NULL,
                cantidad INT NOT NULL,
                comentarios TEXT,
                fecha_movimiento DATETIME DEFAULT NOW(),
                usuario VARCHAR(255)
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        ''',
        'bom': '''
            CREATE TABLE IF NOT EXISTS bom (
                id INT AUTO_INCREMENT PRIMARY KEY,
                modelo VARCHAR(255) NOT NULL,
                numero_parte VARCHAR(512) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
                descripcion TEXT,
                cantidad INT DEFAULT 1,
                side VARCHAR(50),
                ubicacion VARCHAR(255),
                categoria VARCHAR(255),
                proveedor VARCHAR(255),
                fecha_registro DATETIME DEFAULT NOW(),
                UNIQUE KEY unique_bom (modelo, numero_parte(255), side)
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        '''
    }
    
    # Crear tablas dependientes SIN foreign keys
    logger.info(" Creando tablas dependientes (sin foreign keys)...")
    for table_name, create_sql in dependent_tables_no_fk.items():
        try:
            execute_query(create_sql)
            logger.info(f" Tabla {table_name} creada/verificada")
        except Exception as e:
            logger.error(f" Error creando tabla {table_name}: {e}")
    return True

def get_connection():
    """Obtener conexión a MySQL reutilizable desde el pool."""
    if not MYSQL_AVAILABLE:
        return None
    from .config_mysql import get_pooled_connection
    return get_pooled_connection()

# Alias para compatibilidad
get_db_connection = get_connection


# === FUNCIONES DE USUARIOS ===

def crear_usuario(username, password_hash, area=''):
    """Crear usuario en MySQL"""
    try:
        query = "INSERT INTO usuarios_sistema (username, password_hash, departamento) VALUES (%s, %s, %s)"
        result = execute_query(query, (username, password_hash, area))
        return result > 0
    except Exception as e:
        logger.error(f"Error creando usuario: {e}")
        return False

def obtener_usuario(username):
    """Obtener usuario por username"""
    try:
        query = "SELECT * FROM usuarios_sistema WHERE username = %s AND activo = 1"
        return execute_query(query, (username,), fetch='one')
    except Exception as e:
        logger.error(f"Error obteniendo usuario: {e}")
        return None

def verificar_usuario(username, password_hash):
    """Verificar credenciales de usuario"""
    try:
        query = "SELECT * FROM usuarios_sistema WHERE username = %s AND password_hash = %s AND activo = 1"
        return execute_query(query, (username, password_hash), fetch='one')
    except Exception as e:
        logger.error(f"Error verificando usuario: {e}")
        return None

# === FUNCIONES DE MATERIALES ===

def obtener_materiales():
    """Obtener lista de materiales desde MySQL - FORMATO COMPLETO"""
    try:
        query = "SELECT * FROM materiales ORDER BY numero_parte"
        result = execute_query(query, fetch='all') or []
        
        # Mapear a formato esperado por el frontend
        materiales_formateados = []
        for row in result:
            material = {
                'id': row.get('id'),
                'codigoMaterial': row.get('codigo_material', ''),
                'numeroParte': row.get('numero_parte', ''),
                'propiedadMaterial': row.get('propiedad_material', ''),
                'classification': row.get('classification', ''),
                'especificacionMaterial': row.get('especificacion_material', ''),
                'unidadEmpaque': row.get('unidad_empaque', ''),
                'ubicacionMaterial': row.get('ubicacion_material', ''),
                'vendedor': row.get('vendedor', ''),
                'prohibidoSacar': row.get('prohibido_sacar', ''),
                'reparable': row.get('reparable', ''),
                'nivelMsl': row.get('nivel_msl', ''),
                'espesorMsl': row.get('espesor_msl', ''),
                'fechaRegistro': row.get('fecha_registro', ''),
                'usuarioRegistro': row.get('usuario_registro', ''),  # Agregar usuario que registró
                'descripcion': row.get('descripcion', ''),
                'categoria': row.get('categoria', ''),
                'ubicacion': row.get('ubicacion', ''),
                'stockMinimo': row.get('stock_minimo', 0),
                'stockMaximo': row.get('stock_maximo', 0),
                'unidadMedida': row.get('unidad_medida', ''),
                'proveedor': row.get('proveedor', ''),
                'fechaCreacion': row.get('fecha_creacion', '')
            }
            materiales_formateados.append(material)
            
        return materiales_formateados
    except Exception as e:
        logger.error(f"Error obteniendo materiales: {e}")
        return []


def guardar_material(data, usuario_registro=None):
    """Guardar material en MySQL - FORMATO COMPLETO CON DEBUG MEJORADO"""
    try:
        # VALIDACIONES PREVIAS CON LOGS DETALLADOS
        numero_parte = data.get('numero_parte', '').strip()
        if not numero_parte:
            logger.error(f" ERROR: numero_parte vacío o None en data: {data}")
            return False
        
        # Información de registro
        usuario_registro = usuario_registro or 'SISTEMA'
        
        query = """
            INSERT INTO materiales (
                codigo_material, numero_parte, propiedad_material, classification, 
                especificacion_material, unidad_empaque, ubicacion_material, vendedor,
                prohibido_sacar, reparable, nivel_msl, espesor_msl,
                usuario_registro
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                codigo_material = VALUES(codigo_material),
                propiedad_material = VALUES(propiedad_material),
                classification = VALUES(classification),
                especificacion_material = VALUES(especificacion_material),
                unidad_empaque = VALUES(unidad_empaque),
                ubicacion_material = VALUES(ubicacion_material),
                vendedor = VALUES(vendedor),
                prohibido_sacar = VALUES(prohibido_sacar),
                reparable = VALUES(reparable),
                nivel_msl = VALUES(nivel_msl),
                espesor_msl = VALUES(espesor_msl),
                usuario_registro = VALUES(usuario_registro)
        """
        
        params = (
            data.get('codigo_material', ''),
            numero_parte,
            data.get('propiedad_material', ''),
            data.get('classification', ''),
            data.get('especificacion_material', ''),
            data.get('unidad_empaque', ''),
            data.get('ubicacion_material', ''),
            data.get('vendedor', ''),
            data.get('prohibido_sacar', ''),
            data.get('reparable', ''),
            data.get('nivel_msl', ''),
            data.get('espesor_msl', ''),
            usuario_registro
        )
        
        # DEBUG: Mostrar el valor específico de unidad_empaque
        # Validar longitudes de campos antes de insertar
        validaciones = [
            ('codigo_material', params[0], 512),  # Actualizado a 512 caracteres
            ('numero_parte', params[1], 512),     # Actualizado a 512 caracteres  
            ('propiedad_material', params[2], 512), # Actualizado a 512 caracteres
            ('classification', params[3], 512),    # Actualizado a 512 caracteres
            ('unidad_empaque', params[5], 100),   # Mantenido en 100
            ('ubicacion_material', params[6], 512), # Actualizado a 512 caracteres
            ('vendedor', params[7], 512),         # Actualizado a 512 caracteres
            ('prohibido_sacar', params[8], 50),   # Mantenido en 50
            ('reparable', params[9], 50),         # Mantenido en 50
            ('nivel_msl', params[10], 100),       # Mantenido en 100
            ('espesor_msl', params[11], 100),     # Mantenido en 100
            ('usuario_registro', params[12], 255)  # Usuario de registro
        ]
        
        for campo, valor, max_len in validaciones:
            if valor and len(str(valor)) > max_len:
                logger.warning(f" ADVERTENCIA: Campo '{campo}' demasiado largo ({len(str(valor))} > {max_len}): {str(valor)[:50]}...")
                # Truncar el valor
                if campo == 'numero_parte':
                    params = list(params)
                    params[1] = str(valor)[:max_len]
                    params = tuple(params)
                    logger.info(f"🔧 Campo '{campo}' truncado a: {params[1]}")
        
        result = execute_query(query, params)
        
        if result and result > 0:
            logger.info(f" Material guardado exitosamente: {numero_parte} - Usuario: {usuario_registro}")
            return True
        else:
            logger.info(f" execute_query retornó: {result} para {numero_parte}")
            return False
            
    except Exception as e:
        error_msg = str(e)
        logger.error(f" ERROR DETALLADO guardando material '{data.get('numero_parte', 'UNKNOWN')}': {error_msg}")
        
        # Errores específicos de MySQL
        if "1062" in error_msg:
            logger.error(f" Error de duplicado - numero_parte ya existe: {data.get('numero_parte')}")
        elif "1406" in error_msg:
            logger.error(f" Error de longitud de campo - datos demasiado largos")
        elif "1364" in error_msg:
            logger.error(f" Error de campo requerido - falta valor para campo NOT NULL")
        elif "1054" in error_msg:
            logger.error(f" Error de columna desconocida - verifica estructura de tabla")
        else:
            logger.error(f" Error MySQL genérico: {error_msg}")
            
        return False

def actualizar_material_completo(codigo_original, nuevos_datos):
    """Actualizar todos los campos de un material existente"""
    try:
        # Buscar el material primero para verificar que existe
        query_verificar = "SELECT codigo_material, numero_parte FROM materiales WHERE codigo_material = %s LIMIT 1"
        material_existente = execute_query(query_verificar, (codigo_original,), fetch='one')
        
        if not material_existente:
            return {'success': False, 'error': 'No se encontró el material para actualizar'}
        
        # Construir la consulta UPDATE dinámicamente
        campos_update = []
        valores = []
        
        # Lista de campos permitidos para actualizar con mapeo correcto
        mapeo_campos = {
            'codigoMaterial': 'codigo_material',
            'numeroParte': 'numero_parte', 
            'propiedadMaterial': 'propiedad_material',
            'classification': 'classification',
            'especificacionMaterial': 'especificacion_material',
            'unidadEmpaque': 'unidad_empaque',
            'ubicacionMaterial': 'ubicacion_material',
            'vendedor': 'vendedor',
            'prohibidoSacar': 'prohibido_sacar',
            'reparable': 'reparable',
            'nivelMsl': 'nivel_msl',  # Mapeo corregido
            'espesorMsl': 'espesor_msl'  # Mapeo corregido
        }
        
        for campo_frontend, campo_db in mapeo_campos.items():
            if campo_frontend in nuevos_datos:
                campos_update.append(f"{campo_db} = %s")
                valor = nuevos_datos[campo_frontend]
                
                # Convertir valores booleanos para campos específicos
                if campo_frontend in ['prohibidoSacar', 'reparable']:
                    valor = 1 if valor else 0
                    
                valores.append(valor)
                logger.info(f"  - Mapeando {campo_frontend} -> {campo_db} = {valor}")
        
        if not campos_update:
            logger.info(" No hay campos para actualizar")
            return {'success': False, 'error': 'No hay campos para actualizar'}
        
        # Agregar el código original para la condición WHERE
        valores.append(codigo_original)
        
        # Construir y ejecutar la consulta
        query = f"UPDATE materiales SET {', '.join(campos_update)} WHERE codigo_material = %s"
        
        result = execute_query(query, valores)
        
        if result and result > 0:
            logger.info(f" Material {codigo_original} actualizado exitosamente")
            return {'success': True, 'message': 'Material actualizado exitosamente'}
        else:
            logger.info(f" UPDATE ejecutado pero 0 filas afectadas para {codigo_original}")
            return {'success': False, 'error': 'No se pudo actualizar el material - 0 filas afectadas'}
            
    except Exception as e:
        error_msg = str(e)
        logger.error(f" Error actualizando material completo {codigo_original}: {error_msg}")
        return {'success': False, 'error': f'Error de base de datos: {error_msg}'}


# === FUNCIONES DE INVENTARIO ===

def obtener_inventario():
    """Obtener inventario actual desde MySQL"""
    try:
        query = """
            SELECT m.*, COALESCE(i.cantidad_actual, 0) as cantidad_actual, 
                   i.ultima_actualizacion
            FROM materiales m
            LEFT JOIN inventario i ON m.numero_parte = i.numero_parte
            ORDER BY m.numero_parte
        """
        return execute_query(query, fetch='all') or []
    except Exception as e:
        logger.error(f"Error obteniendo inventario: {e}")
        return []

def actualizar_inventario(numero_parte, cantidad, tipo_movimiento='ajuste', comentarios='', usuario=''):
    """Actualizar inventario en MySQL"""
    try:
        # Actualizar inventario actual
        query_inventario = """
            INSERT INTO inventario (numero_parte, cantidad_actual, ultima_actualizacion)
            VALUES (%s, %s, NOW())
            ON DUPLICATE KEY UPDATE
                cantidad_actual = %s,
                ultima_actualizacion = NOW()
        """
        
        execute_query(query_inventario, (numero_parte, cantidad, cantidad))
        
        # Registrar movimiento
        query_movimiento = """
            INSERT INTO movimientos_inventario 
            (numero_parte, tipo_movimiento, cantidad, comentarios, fecha_movimiento, usuario)
            VALUES (%s, %s, %s, %s, NOW(), %s)
        """
        
        execute_query(query_movimiento, (numero_parte, tipo_movimiento, cantidad, comentarios, usuario))
        
        return True
    except Exception as e:
        logger.error(f"Error actualizando inventario: {e}")
        return False


def guardar_configuracion(clave, valor):
    """Guardar configuración en MySQL"""
    try:
        query = """
            INSERT INTO configuracion (clave, valor, fecha_actualizacion)
            VALUES (%s, %s, NOW())
            ON DUPLICATE KEY UPDATE
                valor = VALUES(valor),
                fecha_actualizacion = NOW()
        """
        
        # Convertir valor a JSON si es necesario
        if isinstance(valor, (dict, list)):
            valor = json.dumps(valor)
        
        result = execute_query(query, (clave, valor))
        return result > 0
    except Exception as e:
        logger.error(f"Error guardando configuración: {e}")
        return False

def cargar_configuracion(clave, valor_por_defecto=None):
    """Cargar configuración desde MySQL"""
    try:
        query = "SELECT valor FROM configuracion WHERE clave = %s"
        result = execute_query(query, (clave,), fetch='one')
        
        if result:
            valor = result['valor']
            # Intentar parsear JSON
            try:
                return json.loads(valor)
            except:
                return valor
        
        return valor_por_defecto
    except Exception as e:
        logger.error(f"Error cargando configuración: {e}")
        return valor_por_defecto

# === FUNCIONES ESPECÍFICAS DE CONTROL DE SALIDA ===


# === FUNCIONES DE MIGRACIÓN ===


# === FUNCIONES DE PRUEBA ===

def migrar_tabla_materiales():
    """Migrar tabla materiales existente para agregar nuevas columnas"""
    logger.info(" Migrando tabla materiales para agregar nuevas columnas...")
    
    try:
        # Lista de columnas nuevas a agregar
        nuevas_columnas = [
            ("codigo_material", "VARCHAR(512) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"),
            ("propiedad_material", "VARCHAR(512)"),
            ("classification", "VARCHAR(512)"),
            ("especificacion_material", "TEXT"),
            ("unidad_empaque", "VARCHAR(100)"),
            ("ubicacion_material", "VARCHAR(512)"),
            ("vendedor", "VARCHAR(512)"),
            ("prohibido_sacar", "VARCHAR(50)"),
            ("reparable", "VARCHAR(50)"),
            ("nivel_msl", "VARCHAR(100)"),
            ("espesor_msl", "VARCHAR(100)")
        ]
        
        # Agregar columnas que no existen (usa IF NOT EXISTS o captura error 1060)
        for col_name, col_definition in nuevas_columnas:
            try:
                alter_query = f"ALTER TABLE materiales ADD COLUMN {col_name} {col_definition}"
                execute_query(alter_query)
                logger.info(f" Columna {col_name} agregada")
            except Exception as e:
                if "1060" in str(e):  # Duplicate column name
                    logger.info(f" Columna {col_name} ya existe")
                else:
                    logger.error(f" Error agregando columna {col_name}: {e}")
        
        # Agregar índice para codigo_material si no existe
        try:
            index_query = "ALTER TABLE materiales ADD INDEX idx_codigo_material (codigo_material(255))"
            execute_query(index_query)
            logger.info(" Índice en codigo_material agregado")
        except Exception as e:
            if "1061" in str(e):  # Duplicate key name
                logger.info(" Índice en codigo_material ya existe")
            else:
                logger.error(f" Error agregando índice: {e}")
        
        logger.info(" Migración de tabla materiales completada")
        return True
        
    except Exception as e:
        logger.error(f" Error en migración de tabla materiales: {e}")
        return False

def migrar_tabla_bom():
    """Migrar tabla bom para agregar columna posicion_assy"""
    logger.info(" Migrando tabla bom para agregar columna posicion_assy...")
    
    try:
        # Agregar columna posicion_assy si no existe (captura error 1060 si ya existe)
        try:
            alter_query = "ALTER TABLE bom ADD COLUMN posicion_assy VARCHAR(255) AFTER ubicacion"
            execute_query(alter_query)
            logger.info(" Columna posicion_assy agregada a tabla bom")
        except Exception as e:
            if "1060" in str(e):
                logger.info(" Columna posicion_assy ya existe en tabla bom")
            else:
                logger.error(f" Error agregando columna posicion_assy: {e}")
        
        logger.info(" Migración de tabla bom completada")
        return True
        
    except Exception as e:
        logger.error(f" Error en migración de tabla bom: {e}")
        return False

def verificar_estructura_materiales():
    """Verificar estructura de tabla materiales"""
    try:
        query = "DESCRIBE materiales"
        columnas = execute_query(query, fetch='all')
        
        logger.info(" ESTRUCTURA ACTUAL DE TABLA MATERIALES:")
        logger.info("-" * 60)
        for col in columnas:
            logger.info(f"  {col['Field']:<25} {col['Type']:<20} {col['Null']:<5} {col['Key']:<5}")
        logger.info("-" * 60)
        
        return True
    except Exception as e:
        logger.error(f" Error verificando estructura: {e}")
        return False


def diagnosticar_problemas_importacion():
    """Diagnosticar problemas comunes en la importación de materiales"""
    logger.info("\n === DIAGNÓSTECO DE PROBLEMAS DE IMPORTACIÓN ===")
    
    try:
        # 1. Verificar conexión a MySQL
        if not test_connection():
            logger.info(" PROBLEMA: No hay conexión a MySQL")
            return False
        else:
            logger.info(" Conexión MySQL OK")
        
        # 2. Verificar que existe la tabla materiales
        check_table = "SHOW TABLES LIKE 'materiales'"
        table_exists = execute_query(check_table, fetch='one')
        if not table_exists:
            logger.info(" PROBLEMA: Tabla 'materiales' no existe")
            return False
        else:
            logger.info(" Tabla 'materiales' existe")
        
        # 3. Verificar estructura de la tabla
        logger.info("\n Verificando estructura de tabla...")
        verificar_estructura_materiales()
        
        # 4. Verificar índices
        check_indexes = "SHOW INDEX FROM materiales"
        indexes = execute_query(check_indexes, fetch='all')
        logger.info(f"\n Índices existentes ({len(indexes)} encontrados):")
        for idx in indexes:
            logger.info(f"  - {idx['Key_name']}: {idx['Column_name']}")
        
        # 5. Contar registros existentes
        count_query = "SELECT COUNT(*) as total FROM materiales"
        count_result = execute_query(count_query, fetch='one')
        total_materials = count_result['total'] if count_result else 0
        logger.info(f"\n Total de materiales en BD: {total_materials}")
        
        # 6. Verificar espacio disponible (estimado)
        size_query = """
            SELECT 
                ROUND(((data_length + index_length) / 1024 / 1024), 2) AS 'DB Size in MB' 
            FROM information_schema.tables 
            WHERE table_schema = DATABASE() AND table_name = 'materiales'
        """
        size_result = execute_query(size_query, fetch='one')
        if size_result:
            logger.info(f" Tamaño de tabla materiales: {size_result['DB Size in MB']} MB")
        
        # 7. Probar inserción de prueba
        logger.info("\n Probando inserción de material de prueba...")
        fecha_actual = obtener_fecha_hora_mexico().replace('-', '').replace(':', '').replace(' ', '_')
        test_data = {
            'codigo_material': 'TEST_DIAG_001',
            'numero_parte': f'TEST_DIAG_PART_{fecha_actual}',
            'propiedad_material': 'Test Material for Diagnostics',
            'classification': 'TEST',
            'especificacion_material': 'Material de prueba para diagnóstico',
            'unidad_empaque': '1',
            'ubicacion_material': 'TEST_LOCATION',
            'vendedor': 'TEST_VENDOR'
        }
        
        if guardar_material(test_data):
            logger.info(" Inserción de prueba exitosa")
            # Eliminar el registro de prueba
            delete_query = "DELETE FROM materiales WHERE numero_parte = %s"
            execute_query(delete_query, (test_data['numero_parte'],))
            logger.info(" Registro de prueba eliminado")
        else:
            logger.info(" PROBLEMA: Falló la inserción de prueba")
        
        logger.info("\n Diagnóstico completado")
        return True
        
    except Exception as e:
        logger.error(f" Error en diagnóstico: {e}")
        return False

def test_mysql_functions():
    """Probar funciones de MySQL CON DIAGNÓSTECO COMPLETO"""
    logger.info("\n Probando funciones de MySQL...")
    
    try:
        # Probar conexión
        if test_connection():
            logger.info(" Conexión MySQL OK")
        else:
            logger.error(" Error en conexión MySQL")
            return False
        
        # Ejecutar diagnóstico completo
        logger.info("\n Ejecutando diagnóstico completo...")
        diagnosticar_problemas_importacion()
        
        # Verificar estructura de materiales
        verificar_estructura_materiales()
        
        # Migrar tabla si es necesario
        logger.info("\n Verificando migración de tabla...")
        migrar_tabla_materiales()
        
        # Inicializar base de datos
        if init_db():
            logger.info(" Inicialización MySQL OK")
        else:
            logger.error(" Error en inicialización MySQL")
        
        logger.info(" Pruebas de MySQL completadas")
        return True
        
    except Exception as e:
        logger.error(f" Error en pruebas MySQL: {e}")
        return False

if __name__ == "__main__":
    test_mysql_functions()

def agregar_columna_usuario_registro():
    """Agregar columna usuario_registro a la tabla materiales si no existe"""
    try:
        execute_query("ALTER TABLE materiales ADD COLUMN usuario_registro VARCHAR(255) DEFAULT 'SISTEMA'")
        logger.info(" Columna usuario_registro agregada exitosamente")
    except Exception as e:
        if "1060" in str(e):
            logger.info(" La columna usuario_registro ya existe")
        else:
            logger.error(f" Error agregando columna usuario_registro: {e}")
            return False

    try:
        execute_query("ALTER TABLE materiales ADD INDEX idx_usuario_registro (usuario_registro)")
    except Exception as e:
        if "1061" not in str(e):
            logger.error(f" Error agregando índice usuario_registro: {e}")

    return True

def get_mysql_connection():
    """Obtener conexión MySQL simple para migraciones"""
    try:
        from .config_mysql import get_mysql_connection as config_get_connection
        return config_get_connection()
        
    except Exception as e:
        logger.error(f"Error conectando a MySQL: {e}")
        return None
