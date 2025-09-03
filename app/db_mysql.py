"""Funciones de base de datos adaptadas para MySQL
Migración desde SQLite a MySQL para el hosting"""

import os
from .config_mysql import execute_query, test_connection
from datetime import datetime, timedelta
import json

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
    print(" Pandas no disponible - funciones de Excel limitadas")

# Verificar si MySQL está disponible
try:
    from .config_mysql import MYSQL_AVAILABLE
except ImportError:
    MYSQL_AVAILABLE = False

print(f"Módulo db_mysql cargado - MySQL disponible: {MYSQL_AVAILABLE}")

# Cache para saber si la tabla BOM contiene columna 'descripcion'
_BOM_HAS_DESCRIPCION = None
_BOM_COLUMNS = None

def _get_bom_columns():
    """Obtener y cachear las columnas de la tabla BOM."""
    global _BOM_COLUMNS
    if _BOM_COLUMNS is None:
        try:
            result = execute_query("SHOW COLUMNS FROM bom", fetch='all') or []
            _BOM_COLUMNS = {row['Field'] for row in result}
        except Exception as e:
            print(f"Error verificando columnas de BOM: {e}")
            _BOM_COLUMNS = set()
    return _BOM_COLUMNS



def eliminar_foreign_keys_materiales():
    """Eliminar todas las foreign keys que referencian a la tabla materiales"""
    print("🗑️ Eliminando foreign keys hacia materiales...")
    
    try:
        # Foreign keys a eliminar
        foreign_keys_to_drop = [
            {'table': 'inventario', 'constraint': 'fk_inventario_numero_parte'},
            {'table': 'movimientos_inventario', 'constraint': 'fk_movimientos_numero_parte'},
            {'table': 'bom', 'constraint': 'fk_bom_numero_parte'}
        ]
        
        for fk in foreign_keys_to_drop:
            try:
                # Verificar si existe la foreign key antes de eliminarla
                check_query = """
                    SELECT COUNT(*) as count
                    FROM information_schema.TABLE_CONSTRAINTS 
                    WHERE TABLE_SCHEMA = DATABASE() 
                    AND TABLE_NAME = %s 
                    AND CONSTRAINT_NAME = %s
                    AND CONSTRAINT_TYPE = 'FOREIGN KEY'
                """
                
                result = execute_query(check_query, (fk['table'], fk['constraint']), fetch='one')
                exists = result.get('count', 0) if result else 0
                
                if exists > 0:
                    drop_query = f"ALTER TABLE {fk['table']} DROP FOREIGN KEY {fk['constraint']}"
                    execute_query(drop_query)
                    print(f" Foreign key {fk['constraint']} eliminada de {fk['table']}")
                else:
                    print(f" Foreign key {fk['constraint']} no existe en {fk['table']}")
                    
            except Exception as e:
                print(f" Error eliminando foreign key {fk['constraint']}: {e}")
                continue
        
        print(" Eliminación de foreign keys completada")
        
    except Exception as e:
        print(f"❌ Error en eliminación de foreign keys: {e}")

def init_db():
    """Inicializar base de datos MySQL y crear tablas"""
    if not MYSQL_AVAILABLE:
        print(" MySQL no disponible - usando modo fallback")
        return False
        
    try:
        # Probar conexión
        if not test_connection():
            print("❌ Error conectando a MySQL")
            return False
        
        # Verificar y reparar foreign keys existentes si es necesario
        # repair_foreign_keys()  # COMENTADO: Foreign keys deshabilitadas por solicitud del usuario
        
        # Crear tablas necesarias
        create_tables()
        
        # Agregar columna usuario_registro si no existe (migración)
        try:
            agregar_columna_usuario_registro()
        except Exception as e:
            print(f" Error en migración usuario_registro: {e}")
        
        # MIGRAR TABLA MATERIALES (agregar nuevas columnas)
        print(" Migrando tabla materiales...")
        migrar_tabla_materiales()
        
        print(" Base de datos MySQL inicializada correctamente")
        return True
    except Exception as e:
        print(f"Error inicializando MySQL: {e}")
        return False

def repair_foreign_keys():
    """Reparar foreign keys problemáticas - ELIMINAR TODAS Y RECREAR"""
    print("🔧 Verificando y reparando foreign keys...")
    
    try:
        # Verificar si existe índice en materiales.numero_parte
        check_index_query = """
            SHOW INDEX FROM materiales WHERE Column_name = 'numero_parte'
        """
        
        indices = execute_query(check_index_query, fetch='all')
        
        if not indices:
            print(" Creando índice faltante en materiales.numero_parte...")
            add_index_query = "ALTER TABLE materiales ADD INDEX idx_numero_parte (numero_parte(255))"
            try:
                execute_query(add_index_query)
                print(" Índice creado exitosamente")
            except Exception as e:
                print(f" Error creando índice (puede que ya exista): {e}")
        else:
            print(" Índice en materiales.numero_parte ya existe")
        
        # ELIMINAR TODAS LAS FOREIGN KEYS existentes hacia materiales
        print("🗑️ Eliminando TODAS las foreign keys existentes hacia materiales...")
        problema_tables = ['inventario', 'movimientos_inventario', 'bom']
        
        for table in problema_tables:
            try:
                # Verificar si la tabla existe
                check_table = f"SHOW TABLES LIKE '{table}'"
                table_exists = execute_query(check_table, fetch='one')
                
                if table_exists:
                    print(f"🔍 Limpiando foreign keys en tabla {table}...")
                    
                    # Obtener TODAS las foreign keys existentes hacia materiales
                    fk_query = f"""
                        SELECT CONSTRAINT_NAME 
                        FROM information_schema.KEY_COLUMN_USAGE 
                        WHERE TABLE_SCHEMA = DATABASE() 
                        AND TABLE_NAME = '{table}' 
                        AND REFERENCED_TABLE_NAME = 'materiales'
                    """
                    
                    fks = execute_query(fk_query, fetch='all')
                    
                    # Eliminar TODAS las foreign keys encontradas
                    if fks:
                        for fk in fks:
                            fk_name = fk['CONSTRAINT_NAME']
                            drop_fk_query = f"ALTER TABLE {table} DROP FOREIGN KEY {fk_name}"
                            try:
                                execute_query(drop_fk_query)
                                print(f"🗑️ Foreign key {fk_name} eliminada de {table}")
                            except Exception as e:
                                print(f" Error eliminando FK {fk_name}: {e}")
                    else:
                        print(f" No hay foreign keys existentes en {table}")
                            
            except Exception as e:
                print(f" Error verificando tabla {table}: {e}")
        
        print("🔧 Limpieza completa de foreign keys completada")
        
    except Exception as e:
        print(f"❌ Error en reparación de foreign keys: {e}")

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
    print(" Creando tablas base...")
    for table_name, create_sql in base_tables.items():
        try:
            execute_query(create_sql)
            print(f" Tabla base {table_name} creada/verificada")
        except Exception as e:
            print(f"❌ Error creando tabla base {table_name}: {e}")
    
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
    print(" Creando tablas dependientes (sin foreign keys)...")
    for table_name, create_sql in dependent_tables_no_fk.items():
        try:
            execute_query(create_sql)
            print(f" Tabla {table_name} creada/verificada")
        except Exception as e:
            print(f"❌ Error creando tabla {table_name}: {e}")
    
    # PASO 3: Agregar foreign keys después de que todas las tablas existen
    print(" Intentando agregar foreign keys...")
    add_foreign_keys()  # Función internamente deshabilitada

def add_foreign_keys():
    """Agregar foreign keys después de crear todas las tablas - MÉTODO DEFINITIVO"""
    # FUNCIÓN DESHABILITADA: Foreign keys eliminadas por solicitud del usuario
    print(" Función add_foreign_keys() DESHABILITADA - No se crearán foreign keys hacia materiales")
    return  # Salir inmediatamente sin crear foreign keys
    
    # CÓDIGO COMENTADO - NO SE EJECUTARÁ
    """
    print("🔗 Creando foreign keys con verificación DEFINITIVA...")
    
    foreign_keys = [
        {
            'table': 'inventario',
            'constraint': 'fk_inventario_numero_parte',
            'query': 'ALTER TABLE inventario ADD CONSTRAINT fk_inventario_numero_parte FOREIGN KEY (numero_parte) REFERENCES materiales(numero_parte)'
        },
        {
            'table': 'movimientos_inventario', 
            'constraint': 'fk_movimientos_numero_parte',
            'query': 'ALTER TABLE movimientos_inventario ADD CONSTRAINT fk_movimientos_numero_parte FOREIGN KEY (numero_parte) REFERENCES materiales(numero_parte)'
        },
        {
            'table': 'bom',
            'constraint': 'fk_bom_numero_parte', 
            'query': 'ALTER TABLE bom ADD CONSTRAINT fk_bom_numero_parte FOREIGN KEY (numero_parte) REFERENCES materiales(numero_parte)'
        }
    ]"""
    
    for fk in foreign_keys:
        try:
            print(f" Procesando foreign key para tabla {fk['table']}...")
            
            # PASO 1: Verificar que la tabla existe
            check_table_query = f"SHOW TABLES LIKE '{fk['table']}'"
            table_exists = execute_query(check_table_query, fetch='one')
            
            if not table_exists:
                print(f" Tabla {fk['table']} no existe, omitiendo...")
                continue
            
            # PASO 2: Verificar que la tabla materiales existe
            check_materiales = "SHOW TABLES LIKE 'materiales'"
            materiales_exists = execute_query(check_materiales, fetch='one')
            
            if not materiales_exists:
                print(f"❌ Tabla materiales no existe, no se pueden crear foreign keys")
                break
            
            # PASO 3: VERIFICACIÓN TRIPLE - Verificar de 3 formas distintas si existe la FK
            
            # Verificación 1: Por nombre específico del constraint
            check_constraint_name = f"""
                SELECT COUNT(*) as constraint_count
                FROM information_schema.TABLE_CONSTRAINTS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = '{fk['table']}' 
                AND CONSTRAINT_NAME = '{fk['constraint']}'
                AND CONSTRAINT_TYPE = 'FOREIGN KEY'
            """
            
            constraint_result = execute_query(check_constraint_name, fetch='one')
            constraint_exists = constraint_result.get('constraint_count', 0) if constraint_result else 0
            
            # Verificación 2: Por referencia hacia materiales
            check_any_fk = f"""
                SELECT COUNT(*) as fk_count
                FROM information_schema.KEY_COLUMN_USAGE 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = '{fk['table']}' 
                AND REFERENCED_TABLE_NAME = 'materiales'
                AND REFERENCED_COLUMN_NAME = 'numero_parte'
            """
            
            fk_result = execute_query(check_any_fk, fetch='one')
            any_fk_exists = fk_result.get('fk_count', 0) if fk_result else 0
            
            # Verificación 3: Por nombre exacto en KEY_COLUMN_USAGE
            check_specific_fk = f"""
                SELECT COUNT(*) as specific_count
                FROM information_schema.KEY_COLUMN_USAGE 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = '{fk['table']}' 
                AND CONSTRAINT_NAME = '{fk['constraint']}'
            """
            
            specific_result = execute_query(check_specific_fk, fetch='one')
            specific_exists = specific_result.get('specific_count', 0) if specific_result else 0
            
            # SI CUALQUIERA de las 3 verificaciones encuentra la FK, NO crearla
            if constraint_exists > 0 or any_fk_exists > 0 or specific_exists > 0:
                print(f" Foreign key {fk['constraint']} ya existe (Verificaciones: constraint={constraint_exists}, any_fk={any_fk_exists}, specific={specific_exists})")
                continue
            
            # PASO 4: Verificar índice en materiales antes de crear FK
            check_index = """
                SELECT COUNT(*) as index_count
                FROM information_schema.STATISTICS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'materiales' 
                AND COLUMN_NAME = 'numero_parte'
            """
            
            index_result = execute_query(check_index, fetch='one')
            index_count = index_result.get('index_count', 0) if index_result else 0
            
            if index_count == 0:
                print(f"🔧 Creando índice requerido en materiales...")
                create_index = "ALTER TABLE materiales ADD INDEX idx_numero_parte (numero_parte(255))"
                execute_query(create_index)
                print(f" Índice creado")
            
            # PASO 5: DOBLE VERIFICACIÓN antes de crear
            print(f"🔍 Verificación final antes de crear {fk['constraint']}...")
            
            # Verificar UNA VEZ MÁS que no existe
            final_check = f"""
                SELECT COUNT(*) as final_count
                FROM information_schema.TABLE_CONSTRAINTS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = '{fk['table']}' 
                AND CONSTRAINT_NAME = '{fk['constraint']}'
            """
            
            final_result = execute_query(final_check, fetch='one')
            final_exists = final_result.get('final_count', 0) if final_result else 0
            
            if final_exists > 0:
                print(f" Foreign key {fk['constraint']} detectada en verificación final - OMITIENDO creación")
                continue
            
            # PASO 6: Crear la foreign key SOLO si todas las verificaciones son negativas
            print(f"🔗 Creando foreign key {fk['constraint']} (todas las verificaciones pasaron)...")
            execute_query(fk['query'])
            print(f" Foreign key {fk['constraint']} creada exitosamente")
                
        except Exception as e:
            error_msg = str(e)
            
            # Manejo específico de errores - TODOS los 1826 se consideran éxito
            if "1826" in error_msg:
                print(f" Foreign key {fk['constraint']} ya existía (confirmado por MySQL) - CORRECTO")
                continue  # Este NO es un error, es confirmación de que ya existe
            elif "1822" in error_msg:
                print(f"❌ Error de índice para {fk['constraint']}: {error_msg}")
            elif "1005" in error_msg:
                print(f"❌ Error de definición para {fk['constraint']}: {error_msg}")
            elif "1091" in error_msg:
                print(f" Foreign key {fk['constraint']} ya fue procesada anteriormente")
                continue
            else:
                print(f"❌ Error creando {fk['constraint']}: {error_msg}")
            
            # No fallar completamente, continuar con las siguientes
            continue
    
    print("🔗 Proceso de foreign keys completado DEFINITIVAMENTE")

def get_connection():
    """Obtener conexión a MySQL"""
    if not MYSQL_AVAILABLE:
        return None
    from .config_mysql import get_mysql_connection
    return get_mysql_connection()

# === FUNCIONES DE USUARIOS ===

def crear_usuario(username, password_hash, area=''):
    """Crear usuario en MySQL"""
    try:
        query = "INSERT INTO usuarios_sistema (username, password_hash, departamento) VALUES (%s, %s, %s)"
        result = execute_query(query, (username, password_hash, area))
        return result > 0
    except Exception as e:
        print(f"Error creando usuario: {e}")
        return False

def obtener_usuario(username):
    """Obtener usuario por username"""
    try:
        query = "SELECT * FROM usuarios_sistema WHERE username = %s AND activo = 1"
        return execute_query(query, (username,), fetch='one')
    except Exception as e:
        print(f"Error obteniendo usuario: {e}")
        return None

def verificar_usuario(username, password_hash):
    """Verificar credenciales de usuario"""
    try:
        query = "SELECT * FROM usuarios_sistema WHERE username = %s AND password_hash = %s AND activo = 1"
        return execute_query(query, (username, password_hash), fetch='one')
    except Exception as e:
        print(f"Error verificando usuario: {e}")
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
        print(f"Error obteniendo materiales: {e}")
        return []

def validar_registro_antes_insercion(row_data):
    """Validar un registro antes de intentar insertarlo"""
    errores = []
    warnings = []
    
    # Verificar campos requeridos
    if not row_data.get('numero_parte') or str(row_data.get('numero_parte')).strip() == '':
        errores.append("numero_parte está vacío o es NULL")
    
    # Verificar longitudes de campos
    campos_longitud = {
        'numero_parte': 512,           # Actualizado a 512 caracteres
        'codigo_material': 512,        # Actualizado a 512 caracteres
        'propiedad_material': 512,     # Actualizado a 512 caracteres
        'classification': 512,         # Actualizado a 512 caracteres
        'especificacion_material': 65535, # TEXT field
        'ubicacion_material': 512      # Actualizado a 512 caracteres
    }
    
    for campo, max_len in campos_longitud.items():
        valor = str(row_data.get(campo, ''))
        if len(valor) > max_len:
            errores.append(f"{campo} demasiado largo: {len(valor)} caracteres (máximo {max_len})")
    
    # Verificar caracteres problemáticos
    for campo in ['numero_parte', 'propiedad_material', 'classification']:
        valor = str(row_data.get(campo, ''))
        if '\\' in valor or '"' in valor:
            warnings.append(f"{campo} contiene caracteres especiales: {valor[:50]}...")
    
    # Verificar valores numéricos
    try:
        cantidad = row_data.get('cantidad_inicial', 0)
        if cantidad is not None and cantidad != '':
            float(cantidad)
    except (ValueError, TypeError):
        warnings.append(f"cantidad_inicial no es numérica: {cantidad}")
    
    return errores, warnings

def guardar_material(data, usuario_registro=None):
    """Guardar material en MySQL - FORMATO COMPLETO CON DEBUG MEJORADO"""
    try:
        # VALIDACIONES PREVIAS CON LOGS DETALLADOS
        numero_parte = data.get('numero_parte', '').strip()
        if not numero_parte:
            print(f"❌ ERROR: numero_parte vacío o None en data: {data}")
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
                print(f" ADVERTENCIA: Campo '{campo}' demasiado largo ({len(str(valor))} > {max_len}): {str(valor)[:50]}...")
                # Truncar el valor
                if campo == 'numero_parte':
                    params = list(params)
                    params[1] = str(valor)[:max_len]
                    params = tuple(params)
                    print(f"🔧 Campo '{campo}' truncado a: {params[1]}")
        
        result = execute_query(query, params)
        
        if result and result > 0:
            print(f" Material guardado exitosamente: {numero_parte} - Usuario: {usuario_registro}")
            return True
        else:
            print(f" execute_query retornó: {result} para {numero_parte}")
            return False
            
    except Exception as e:
        error_msg = str(e)
        print(f"❌ ERROR DETALLADO guardando material '{data.get('numero_parte', 'UNKNOWN')}': {error_msg}")
        
        # Errores específicos de MySQL
        if "1062" in error_msg:
            print(f"🔍 Error de duplicado - numero_parte ya existe: {data.get('numero_parte')}")
        elif "1406" in error_msg:
            print(f"🔍 Error de longitud de campo - datos demasiado largos")
        elif "1364" in error_msg:
            print(f"🔍 Error de campo requerido - falta valor para campo NOT NULL")
        elif "1054" in error_msg:
            print(f"🔍 Error de columna desconocida - verifica estructura de tabla")
        else:
            print(f"🔍 Error MySQL genérico: {error_msg}")
            
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
                print(f"  - Mapeando {campo_frontend} -> {campo_db} = {valor}")
        
        if not campos_update:
            print("❌ No hay campos para actualizar")
            return {'success': False, 'error': 'No hay campos para actualizar'}
        
        # Agregar el código original para la condición WHERE
        valores.append(codigo_original)
        
        # Construir y ejecutar la consulta
        query = f"UPDATE materiales SET {', '.join(campos_update)} WHERE codigo_material = %s"
        
        result = execute_query(query, valores)
        
        if result and result > 0:
            print(f" Material {codigo_original} actualizado exitosamente")
            return {'success': True, 'message': 'Material actualizado exitosamente'}
        else:
            print(f" UPDATE ejecutado pero 0 filas afectadas para {codigo_original}")
            return {'success': False, 'error': 'No se pudo actualizar el material - 0 filas afectadas'}
            
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Error actualizando material completo {codigo_original}: {error_msg}")
        return {'success': False, 'error': f'Error de base de datos: {error_msg}'}

def obtener_material_por_numero(numero_parte):
    """Obtener material por número de parte"""
    try:
        query = "SELECT * FROM materiales WHERE numero_parte = %s"
        return execute_query(query, (numero_parte,), fetch='one')
    except Exception as e:
        print(f"Error obteniendo material: {e}")
        return None

def insertar_materiales_desde_excel(df, usuario_importacion=None):
    """Insertar materiales desde DataFrame de Excel con mapeo correcto y DEBUG MEJORADO"""
    try:
        if not PANDAS_AVAILABLE:
            print("❌ Pandas no disponible para importar Excel")
            return {'insertados': 0, 'omitidos': 0, 'error': 'Pandas no disponible'}
            
        insertados = 0
        omitidos = 0
        errores_detallados = []
        
        # Información del usuario que importa
        usuario_importacion = usuario_importacion or 'USUARIO_EXCEL'
        print(f" Importación iniciada por usuario: {usuario_importacion}")
        
        # Mapeo de columnas del Excel a la base de datos
        column_mapping = {
            'Codigo de material': 'codigo_material',
            'Numero de parte': 'numero_parte', 
            'Propiedad de material': 'propiedad_material',
            'Classification': 'classification',
            'Especificacion de material': 'especificacion_material',
            'Unidad de empaque ': 'unidad_empaque',  # Nota el espacio extra
            'Ubicacion de material': 'ubicacion_material',
            'Vendedor': 'vendedor',
            'Prohibido sacar ': 'prohibido_sacar',  # Nota el espacio extra
            'Reparable': 'reparable',
            'Nivel de MSL': 'nivel_msl',
            'Espesor de MSL ': 'espesor_msl',  # Nota el espacio extra
            'Fecha de registro': 'fecha_registro'
        }
        
        print(f"📊 Procesando {len(df)} filas del Excel...")
        print(f"🔍 Columnas disponibles en Excel: {list(df.columns)}")
        
        for index, row in df.iterrows():
            try:
                fila_numero = index + 1
                print(f"\n🔍 === PROCESANDO FILA {fila_numero} ===")
                
                # Mapear datos desde Excel
                data = {}
                
                for excel_col, db_col in column_mapping.items():
                    if excel_col in row:
                        value = str(row[excel_col]).strip() if pd.notna(row[excel_col]) else ''
                        data[db_col] = value
                        print(f"🔍 {db_col}: '{value[:50]}{'...' if len(value) > 50 else ''}'")
                    else:
                        data[db_col] = ''
                        print(f" Columna '{excel_col}' no encontrada en Excel")
                
                # Validar que tenga al menos número de parte
                if not data.get('numero_parte'):
                    error_msg = f"Fila {fila_numero}: Sin número de parte"
                    print(f" {error_msg}")
                    errores_detallados.append(error_msg)
                    omitidos += 1
                    continue
                
                # Guardar material con logging detallado e información del usuario
                print(f"🔍 Intentando guardar material fila {fila_numero} - Usuario: {usuario_importacion}...")
                if guardar_material(data, usuario_registro=usuario_importacion):
                    insertados += 1
                    print(f" Fila {fila_numero} guardada exitosamente por {usuario_importacion}")
                    if insertados % 100 == 0:  # Log cada 100 insertados
                        print(f" Procesados {insertados} materiales por {usuario_importacion}...")
                else:
                    error_msg = f"Fila {fila_numero}: Error al guardar en base de datos"
                    print(f"❌ {error_msg}")
                    errores_detallados.append(error_msg)
                    omitidos += 1
                    
            except Exception as e:
                fila_numero = index + 1
                error_msg = f"Fila {fila_numero}: {str(e)}"
                print(f"❌ Error procesando fila {fila_numero}: {e}")
                errores_detallados.append(error_msg)
                omitidos += 1
                continue
        
        print(f"\n Importación completada por {usuario_importacion}: {insertados} insertados, {omitidos} omitidos")
        if errores_detallados:
            print(f"🔍 Errores detallados:")
            for error in errores_detallados:
                print(f"  - {error}")
        
        return {
            'insertados': insertados,
            'omitidos': omitidos,
            'total': len(df),
            'errores': errores_detallados,
            'usuario_importacion': usuario_importacion
        }
        
    except Exception as e:
        print(f"❌ Error importando materiales desde Excel: {e}")
        return {
            'insertados': 0,
            'omitidos': len(df) if df is not None else 0,
            'error': str(e)
        }

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
        print(f"Error obteniendo inventario: {e}")
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
        print(f"Error actualizando inventario: {e}")
        return False

def obtener_movimientos_inventario(numero_parte=None, limit=100):
    """Obtener movimientos de inventario"""
    try:
        if numero_parte:
            query = """
                SELECT * FROM movimientos_inventario 
                WHERE numero_parte = %s 
                ORDER BY fecha_movimiento DESC 
                LIMIT %s
            """
            return execute_query(query, (numero_parte, limit), fetch='all') or []
        else:
            query = """
                SELECT * FROM movimientos_inventario 
                ORDER BY fecha_movimiento DESC 
                LIMIT %s
            """
            return execute_query(query, (limit,), fetch='all') or []
    except Exception as e:
        print(f"Error obteniendo movimientos: {e}")
        return []

# === FUNCIONES DE BOM ===

def obtener_bom_por_modelo(modelo):
    """Obtener BOM por modelo desde MySQL"""
    try:
        query = "SELECT * FROM bom WHERE modelo = %s ORDER BY numero_parte"
        return execute_query(query, (modelo,), fetch='all') or []
    except Exception as e:
        print(f"Error obteniendo BOM: {e}")
        return []

def guardar_bom_item(data):
    """Guardar item de BOM en MySQL"""
    try:
        cols = _get_bom_columns()

        campos = ['modelo', 'numero_parte']
        valores = [data.get('modelo'), data.get('numero_parte')]
        updates = []

        # Agregar todas las columnas disponibles
        campos_adicionales = {
            'codigo_material': data.get('codigo_material', ''),
            'side': data.get('side', ''),
            'tipo_material': data.get('tipo_material', ''),
            'ubicacion': data.get('ubicacion', ''),
            'classification': data.get('categoria', ''),  # categoria -> classification
            'vender': data.get('proveedor', ''),          # proveedor -> vender
            'material_original': data.get('material_original', ''),
            'material_sustituto': data.get('material_sustituto', ''),
            'cantidad_total': data.get('cantidad_total', 1),
            'cantidad_original': data.get('cantidad_original', 1)
        }
        
        # Usar especificacion_material en lugar de descripcion
        if 'especificacion_material' in cols:
            campos_adicionales['especificacion_material'] = data.get('descripcion', '')

        # Agregar solo las columnas que existen en la tabla
        for campo, valor in campos_adicionales.items():
            if campo in cols:
                campos.append(campo)
                valores.append(valor)
                updates.append(f'{campo} = VALUES({campo})')

        placeholders = ', '.join(['%s'] * len(campos))
        query = f"""
            INSERT INTO bom ({', '.join(campos)})
            VALUES ({placeholders})
            ON DUPLICATE KEY UPDATE {', '.join(updates)}
        """

        result = execute_query(query, tuple(valores))
        
        # Interpretar resultado correctamente
        if result is not None and result >= 0:
            return True
        else:
            return False
            
    except Exception as e:
        print(f"DEBUG: ❌ ERROR en guardar_bom_item: {e}")
        return False

def obtener_modelos_bom():
    """Obtener lista de modelos en BOM"""
    try:
        query = "SELECT DISTINCT modelo FROM bom ORDER BY modelo"
        result = execute_query(query, fetch='all') or []
        # Devolver objetos con propiedad 'modelo' para compatibilidad con template
        return [{'modelo': row['modelo']} for row in result]
    except Exception as e:
        print(f"Error obteniendo modelos BOM: {e}")
        return []

def listar_bom_por_modelo(modelo):
    """Listar BOM por modelo específico o todos"""
    try:
        if modelo == 'todos':
            query = "SELECT * FROM bom ORDER BY modelo, numero_parte"
            resultados = execute_query(query, fetch='all') or []
        else:
            query = "SELECT * FROM bom WHERE modelo = %s ORDER BY numero_parte"
            resultados = execute_query(query, (modelo,), fetch='all') or []
        
        # Mapear nombres de columnas de la BD a nombres esperados por el frontend
        datos_mapeados = []
        for row in resultados:
            item_mapeado = {
                'id': row.get('id'),
                'modelo': row.get('modelo'),
                'codigoMaterial': row.get('codigo_material'),
                'numeroParte': row.get('numero_parte'),
                'side': row.get('side'),
                'tipoMaterial': row.get('tipo_material'),
                'classification': row.get('classification'),
                'especificacionMaterial': row.get('especificacion_material'),
                'vender': row.get('vender'),
                'cantidadTotal': row.get('cantidad_total'),
                'cantidadOriginal': row.get('cantidad_original'),
                'ubicacion': row.get('ubicacion'),
                'materialSustituto': row.get('material_sustituto'),
                'materialOriginal': row.get('material_original'),
                'registrador': row.get('registrador'),
                'fechaRegistro': row.get('fecha_registro')
            }
            datos_mapeados.append(item_mapeado)
        
        return datos_mapeados
        
    except Exception as e:
        print(f"Error listando BOM por modelo: {e}")
        return []

def insertar_bom_desde_dataframe(df, registrador):
    """Insertar datos de BOM desde un DataFrame de pandas con CARGA MASIVA OPTIMIZADA"""
    import time
    start_time = time.time()
    
    try:
        cols = _get_bom_columns()
        
        insertados = 0
        omitidos = 0
        
        # Crear un mapeo flexible de columnas
        columnas_disponibles = df.columns.tolist()
        print(f"DEBUG: Columnas en el DataFrame: {columnas_disponibles}")
        
        # Función auxiliar para buscar columna por variaciones
        def buscar_columna(variaciones, columnas):
            for var in variaciones:
                for col in columnas:
                    if var.lower() in col.lower():
                        return col
            return None
        
        # Mapear las columnas principales
        col_modelo = buscar_columna(['modelo'], columnas_disponibles)
        col_numero_parte = buscar_columna(['numero de parte', 'número de parte', 'numero_parte', 'n de parte', 'part number'], columnas_disponibles)
        col_codigo_material = buscar_columna(['codigo de material', 'código de material', 'codigo_material', 'material code'], columnas_disponibles)
        col_side = buscar_columna(['side', 'lado'], columnas_disponibles)
        col_tipo_material = buscar_columna(['tipo de material', 'tipo_material', 'material type'], columnas_disponibles)
        col_ubicacion = buscar_columna(['ubicacion', 'ubicación', 'location'], columnas_disponibles)
        col_categoria = buscar_columna(['categoria', 'categoría', 'tipo', 'classification'], columnas_disponibles)
        col_proveedor = buscar_columna(['proveedor', 'vendor', 'vender', 'supplier'], columnas_disponibles)
        col_cantidad = buscar_columna(['cantidad', 'quantity', 'qty'], columnas_disponibles)
        col_cantidad_total = buscar_columna(['cantidad total', 'cantidad_total', 'total quantity'], columnas_disponibles)
        col_cantidad_original = buscar_columna(['cantidad original', 'cantidad_original', 'original quantity'], columnas_disponibles)
        col_descripcion = buscar_columna(['descripcion', 'descripción', 'description', 'especificacion', 'especificación'], columnas_disponibles)
        col_material_original = buscar_columna(['material original', 'material_original', 'original material'], columnas_disponibles)
        col_material_sustituto = buscar_columna(['material sustituto', 'material_sustituto', 'substitute material'], columnas_disponibles)
        
        print(f"DEBUG: Preparando carga masiva para {len(df)} filas...")
        print(f"DEBUG: Usuario registrador: {registrador}")
        
        # PREPARAR TODOS LOS DATOS EN MEMORIA PRIMERO
        datos_para_insertar = []
        
        for index, row in df.iterrows():
            try:
                # Verificar que tenga al menos modelo y número de parte
                modelo = str(row.get(col_modelo, '')).strip() if col_modelo else ''
                numero_parte = str(row.get(col_numero_parte, '')).strip() if col_numero_parte else ''
                
                if not modelo or not numero_parte:
                    omitidos += 1
                    continue
                
                # Preparar cantidades
                cantidad_total = 1.0
                if col_cantidad_total:
                    try:
                        cantidad_total = float(row.get(col_cantidad_total, 1) or 1)
                    except (ValueError, TypeError):
                        cantidad_total = 1.0
                elif col_cantidad:
                    try:
                        cantidad_total = float(row.get(col_cantidad, 1) or 1)
                    except (ValueError, TypeError):
                        cantidad_total = 1.0
                        
                cantidad_original = cantidad_total
                if col_cantidad_original:
                    try:
                        cantidad_original = float(row.get(col_cantidad_original, cantidad_total) or cantidad_total)
                    except (ValueError, TypeError):
                        cantidad_original = cantidad_total
                
                # Preparar fila para inserción masiva
                fila_datos = (
                    modelo,
                    numero_parte,
                    str(row.get(col_codigo_material, '') if col_codigo_material else '').strip(),
                    str(row.get(col_side, '') if col_side else '').strip(),
                    str(row.get(col_tipo_material, '') if col_tipo_material else '').strip(),
                    str(row.get(col_ubicacion, '') if col_ubicacion else '').strip(),
                    str(row.get(col_categoria, '') if col_categoria else '').strip(),
                    str(row.get(col_proveedor, '') if col_proveedor else '').strip(),
                    str(row.get(col_material_original, '') if col_material_original else '').strip(),
                    str(row.get(col_material_sustituto, '') if col_material_sustituto else '').strip(),
                    cantidad_total,
                    cantidad_original,
                    str(row.get(col_descripcion, '') if col_descripcion else '').strip(),
                    registrador  # Agregar el usuario que está importando
                )
                
                datos_para_insertar.append(fila_datos)
                insertados += 1
                
            except Exception as e:
                print(f"DEBUG: Error procesando fila {index+1}: {e}")
                omitidos += 1
                continue
        
        print(f"DEBUG: Datos preparados: {len(datos_para_insertar)} filas válidas")
        
        # INSERCIÓN MASIVA
        if datos_para_insertar:
            print(f"DEBUG: Ejecutando inserción masiva...")
            
            # Construir consulta para inserción masiva
            campos_insert = [
                'modelo', 'numero_parte', 'codigo_material', 'side', 'tipo_material',
                'ubicacion', 'classification', 'vender', 'material_original', 
                'material_sustituto', 'cantidad_total', 'cantidad_original', 'especificacion_material',
                'registrador'
            ]
            
            # Filtrar solo campos que existen en la tabla
            campos_finales = [campo for campo in campos_insert if campo in cols]
            
            placeholders = ', '.join(['%s'] * len(campos_finales))
            updates = ', '.join([f'{campo} = VALUES({campo})' for campo in campos_finales])
            
            query_masiva = f"""
                INSERT INTO bom ({', '.join(campos_finales)})
                VALUES ({placeholders})
                ON DUPLICATE KEY UPDATE {updates}
            """
            
            # Ejecutar en lotes para evitar problemas de memoria
            batch_size = 100
            total_insertados = 0
            
            for i in range(0, len(datos_para_insertar), batch_size):
                batch = datos_para_insertar[i:i + batch_size]
                print(f"DEBUG: Procesando lote {i//batch_size + 1} ({len(batch)} filas)...")
                
                try:
                    # Ejecutar inserción del lote usando executemany
                    connection = get_connection()
                    cursor = connection.cursor()
                    
                    cursor.executemany(query_masiva, batch)
                    connection.commit()
                    
                    filas_afectadas = cursor.rowcount
                    total_insertados += filas_afectadas
                    
                    print(f"DEBUG: Lote completado - {filas_afectadas} filas afectadas")
                    
                    cursor.close()
                    connection.close()
                    
                except Exception as e:
                    print(f"DEBUG: Error en lote {i//batch_size + 1}: {e}")
                    continue
            
            print(f"DEBUG: ✅ Inserción masiva completada - {total_insertados} filas procesadas")
        
        # Información detallada para el frontend
        tiempo_total = time.time() - start_time
        resultado_detallado = {
            'insertados': len(datos_para_insertar),
            'omitidos': omitidos,
            'total_procesado': len(df),
            'filas_bd_afectadas': total_insertados,
            'tiempo_proceso': f"{tiempo_total:.2f}s"
        }
        
        print(f"DEBUG: Resultado detallado: {resultado_detallado}")
        
        return resultado_detallado
        
    except Exception as e:
        print(f"Error insertando BOM desde DataFrame: {e}")
        import traceback
        traceback.print_exc()
        return {
            'insertados': 0,
            'omitidos': len(df) if df is not None else 0
        }

# === FUNCIONES DE CONFIGURACIÓN ===

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
        print(f"Error guardando configuración: {e}")
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
        print(f"Error cargando configuración: {e}")
        return valor_por_defecto

# === FUNCIONES ESPECÍFICAS DE CONTROL DE SALIDA ===

def buscar_material_por_codigo_mysql(codigo_recibido):
    """Buscar material en control_material_almacen por código usando MySQL"""
    try:
        query = """
            SELECT * FROM control_material_almacen 
            WHERE codigo_material_recibido = %s
        """
        return execute_query(query, (codigo_recibido,), fetch='one')
    except Exception as e:
        print(f"Error buscando material por código: {e}")
        return None

def obtener_total_salidas_material(codigo_recibido):
    """Obtener total de salidas para un código específico usando MySQL"""
    try:
        query = """
            SELECT COALESCE(SUM(cantidad_salida), 0) as total_salidas
            FROM control_material_salida 
            WHERE codigo_material_recibido = %s
        """
        result = execute_query(query, (codigo_recibido,), fetch='one')
        return float(result['total_salidas']) if result else 0.0
    except Exception as e:
        print(f"Error obteniendo total de salidas: {e}")
        return 0.0

def registrar_salida_material_mysql(data):
    """
    Registrar salida de material - VERSIÓN MEJORADA
    Determina automáticamente el proceso destino basado en la especificación del material
    """
    try:
        fecha_registro = obtener_fecha_hora_mexico()
        
        # Extraer numero_parte del codigo_material_recibido (antes de la coma)
        codigo_material = data['codigo_material_recibido']
        numero_parte = codigo_material.split(',')[0] if ',' in codigo_material else codigo_material
        
        # PASO 1: Obtener especificación del material original desde control_material_almacen
        query_especificacion = """
            SELECT especificacion, propiedad_material
            FROM control_material_almacen 
            WHERE codigo_material_recibido = %s
            ORDER BY id DESC LIMIT 1
        """
        
        result_spec = execute_query(query_especificacion, (codigo_material,), fetch='one')
        
        especificacion_original = ""
        propiedad_material = ""
        
        if result_spec:
            especificacion_original = result_spec.get('especificacion', '')
            propiedad_material = result_spec.get('propiedad_material', '')
            print(f"📋 Material encontrado - Especificación: {especificacion_original}, Propiedad: {propiedad_material}")
        else:
            print(f"⚠️ No se encontró el material {codigo_material} en almacén")
        
        # PASO 2: Validar que se especifique un proceso destino
        # VALIDACIÓN: No permitir salidas sin proceso específico
        proceso_input = data.get('proceso_salida', '').strip()
        if not proceso_input or proceso_input.upper() == 'AUTO':
            print(f"❌ ERROR: No se puede procesar salida sin especificar proceso destino")
            print(f"   - proceso_salida recibido: '{proceso_input}'")
            print(f"   - Se requiere un proceso específico (PRODUCCION, SMD, IMD, etc.)")
            return {
                'success': False, 
                'error': 'Debe especificar un proceso de salida específico. No se permite AUTO o vacío.'
            }
        
        # Usar el proceso especificado directamente
        if proceso_input == 'SMT 1st SIDE':
            proceso_salida = 'SMD'
        else:
            proceso_salida = proceso_input
        print(f"🎯 Proceso destino especificado: {proceso_salida}")
        
        # PASO 3: Insertar en control_material_salida
        query = """
            INSERT INTO control_material_salida (
                codigo_material_recibido, numero_parte, numero_lote, modelo, depto_salida,
                proceso_salida, cantidad_salida, fecha_salida, fecha_registro, especificacion_material
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        # Determinar especificación final
        especificacion_final = especificacion_original or data.get('especificacion_material', '')
        print(f"🔍 Debug especificación:")
        print(f"   - especificacion_original: '{especificacion_original}'")
        print(f"   - data.get('especificacion_material', ''): '{data.get('especificacion_material', '')}'")
        print(f"   - especificacion_final: '{especificacion_final}'")
        
        # Manejar fecha de salida
        fecha_salida = data.get('fecha_salida', '')
        if not fecha_salida or fecha_salida.strip() == '':
            fecha_salida = None
        
        params = (
            data['codigo_material_recibido'],
            numero_parte,
            data.get('numero_lote', ''),
            data.get('modelo', ''),
            data.get('depto_salida', ''),
            proceso_salida,  # Proceso determinado automáticamente
            data['cantidad_salida'],
            fecha_salida,
            fecha_registro,
            especificacion_final  # Usar especificación determinada
        )
        
        print(f"🔍 Debug query completa:")
        print(f"   - Query: {query}")
        print(f"   - Params: {params}")
        print(f"   - Tipo de cada parámetro:")
        for i, param in enumerate(params):
            print(f"     [{i}]: {type(param)} = {repr(param)}")
        
        result = execute_query(query, params)
        
        # Verificar inmediatamente qué se insertó
        if result > 0:
            verify_query = """
            SELECT especificacion_material 
            FROM control_material_salida 
            WHERE codigo_material_recibido = %s
            ORDER BY fecha_registro DESC 
            LIMIT 1
            """
            verify_result = execute_query(verify_query, (data['codigo_material_recibido'],), fetch='one')
            if verify_result:
                actual_spec = verify_result.get('especificacion_material', '')
                print(f"🔍 Verificación inmediata - Especificación en BD: '{actual_spec}'")
                if actual_spec != especificacion_final:
                    print(f"⚠️ PROBLEMA: Se envió '{especificacion_final}' pero se guardó '{actual_spec}'")
        
        if result > 0:
            print(f"✅ Salida registrada exitosamente - Proceso: {proceso_salida}")
            
            # PASO 4: Actualizar inventario general
            try:
                cantidad_salida = float(data.get('cantidad_salida', 0))
                actualizar_inventario_general_salida_mysql(numero_parte, cantidad_salida)
            except Exception as e:
                print(f"⚠️ Error actualizando inventario general: {e}")
            
            # PASO 5: Actualizar inventario específico según proceso_salida
            try:
                actualizar_inventario_especifico_salida(numero_parte, codigo_material, cantidad_salida, proceso_salida)
            except Exception as e:
                print(f"⚠️ Error actualizando inventario específico: {e}")
            
            # Devolver información del proceso determinado
            return {
                'success': True,
                'proceso_destino': proceso_salida,
                'especificacion_usada': especificacion_original
            }
        else:
            print(f"❌ Error al registrar salida")
            return {'success': False, 'error': 'Error al insertar en base de datos'}
            
    except Exception as e:
        print(f"❌ Error en registrar_salida_material_mysql: {e}")
        return {'success': False, 'error': str(e)}

def buscar_material_por_numero_parte_mysql(numero_parte):
    """Buscar material por número de parte usando MySQL"""
    try:
        query = """
            SELECT * FROM control_material_almacen 
            WHERE numero_parte = %s
        """
        return execute_query(query, (numero_parte,), fetch='all') or []
    except Exception as e:
        print(f"Error buscando material por número de parte: {e}")
        return []

def calcular_inventario_general_mysql(numero_parte):
    """Calcular inventario general para un número de parte usando MySQL"""
    try:
        # Obtener todas las entradas para este número de parte
        query_entradas = """
            SELECT SUM(cantidad_actual) as total_entradas
            FROM control_material_almacen 
            WHERE numero_parte = %s
        """
        entradas_result = execute_query(query_entradas, (numero_parte,), fetch='one')
        total_entradas = float(entradas_result['total_entradas']) if entradas_result and entradas_result['total_entradas'] else 0.0
        
        # Obtener todas las salidas para este número de parte
        query_salidas = """
            SELECT SUM(cms.cantidad_salida) as total_salidas
            FROM control_material_salida cms
            JOIN control_material_almacen cma ON cms.codigo_material_recibido = cma.codigo_material_recibido
            WHERE cma.numero_parte = %s
        """
        salidas_result = execute_query(query_salidas, (numero_parte,), fetch='one')
        total_salidas = float(salidas_result['total_salidas']) if salidas_result and salidas_result['total_salidas'] else 0.0
        
        inventario_actual = total_entradas - total_salidas
        
        return {
            'numero_parte': numero_parte,
            'total_entradas': total_entradas,
            'total_salidas': total_salidas,
            'inventario_actual': inventario_actual
        }
    except Exception as e:
        print(f"Error calculando inventario general: {e}")
        return None

def actualizar_inventario_especifico_salida(numero_parte, codigo_material, cantidad_salida, proceso_salida):
    """Actualizar inventario específico según el proceso de salida"""
    try:
        # Determinar tabla destino según proceso_salida
        tabla_inventario = None
        
        # Mapear proceso_salida a tabla específica
        if proceso_salida.upper() in ['SMD', 'PRODUCCION_SMD', 'SMT 1st SIDE']:
            tabla_inventario = 'InventarioRollosSMD'
        elif proceso_salida.upper() in ['IMD', 'PRODUCCION_IMD']:
            tabla_inventario = 'InventarioRollosIMD'
        elif proceso_salida.upper() in ['MAIN', 'PRODUCCION_MAIN', 'THROUGH_HOLE']:
            tabla_inventario = 'InventarioRollosMAIN'
        else:
            # Para otros procesos como PRODUCCION general, no hay tabla específica
            print(f"ℹ️ Proceso {proceso_salida} no requiere inventario específico")
            return True
        
        print(f"🎯 Actualizando inventario específico en {tabla_inventario}")
        
        # Buscar rollo específico por código de barras (codigo_material)
        query_buscar = f"""
            SELECT id, cantidad_actual 
            FROM {tabla_inventario} 
            WHERE codigo_barras = %s AND estado IN ('ACTIVO', 'EN_USO')
            ORDER BY fecha_entrada ASC
            LIMIT 1
        """
        
        rollo_encontrado = execute_query(query_buscar, (codigo_material,), fetch='one')
        
        if rollo_encontrado:
            # Solo registrar el movimiento, NO descontar cantidad
            # La cantidad se descontará después cuando se use en la máquina
            print(f"✅ Rollo encontrado en {tabla_inventario} - No se descuenta cantidad aquí")
            
            # Registrar movimiento de traslado a proceso específico
            registrar_movimiento_historico_especifico(tabla_inventario, rollo_encontrado['id'], 
                                                    cantidad_salida, proceso_salida, 'TRASLADO_A_PROCESO')
            return True
        else:
            print(f"⚠️ No se encontró rollo activo con código {codigo_material} en {tabla_inventario}")
            # Crear entrada nueva con la cantidad completa disponible
            return crear_entrada_inventario_especifico(tabla_inventario, numero_parte, codigo_material, cantidad_salida)
            
    except Exception as e:
        print(f"❌ Error en actualizar_inventario_especifico_salida: {e}")
        return False

def registrar_movimiento_historico_especifico(tabla_inventario, rollo_id, cantidad, proceso_salida, tipo_movimiento='SALIDA_PRODUCCION'):
    """Registrar movimiento en historial específico"""
    try:
        # Determinar tabla de historial
        tabla_historial = tabla_inventario.replace('Inventario', 'HistorialMovimientos')
        
        query_historial = f"""
            INSERT INTO {tabla_historial} (
                rollo_id, tipo_movimiento, descripcion, cantidad_despues, 
                usuario, fecha_movimiento
            ) VALUES (%s, %s, %s, 
                (SELECT cantidad_actual FROM {tabla_inventario} WHERE id = %s),
                %s, NOW())
        """
        
        descripcion = f'Traslado a proceso {proceso_salida} - Cantidad trasladada: {cantidad}' if tipo_movimiento == 'TRASLADO_A_PROCESO' else f'Salida a proceso {proceso_salida} - Cantidad: {cantidad}'
        
        execute_query(query_historial, (
            rollo_id, 
            tipo_movimiento, 
            descripcion,
            rollo_id,
            'SISTEMA'
        ))
        
        print(f"📝 Movimiento registrado en {tabla_historial}: {tipo_movimiento}")
        return True
        
    except Exception as e:
        print(f"⚠️ Error registrando movimiento histórico: {e}")
        return False

def crear_entrada_inventario_especifico(tabla_inventario, numero_parte, codigo_material, cantidad_salida):
    """Crear entrada en inventario específico si no existe"""
    try:
        print(f"🔄 Creando entrada faltante en {tabla_inventario}")
        
        # Obtener datos del material desde almacen
        query_material = """
            SELECT especificacion, propiedad_material, numero_lote_material 
            FROM control_material_almacen 
            WHERE codigo_material_recibido = %s 
            LIMIT 1
        """
        material_info = execute_query(query_material, (codigo_material,), fetch='one')
        
        if material_info:
            # Determinar área según tabla
            area = 'smd' if 'SMD' in tabla_inventario else ('imd' if 'IMD' in tabla_inventario else 'main')
            
            query_crear = f"""
                INSERT INTO {tabla_inventario} (
                    numero_parte, codigo_barras, lote, area_{area}, fecha_entrada,
                    origen_almacen, estado, cantidad_inicial, cantidad_actual,
                    usuario_responsable, creado_en, actualizado_en
                ) VALUES (%s, %s, %s, %s, NOW(), %s, %s, %s, %s, %s, NOW(), NOW())
            """
            
            # Cantidad inicial = cantidad que sale de almacén
            # Cantidad actual = misma cantidad (NO se descuenta aquí)
            cantidad_inicial = cantidad_salida
            cantidad_actual = cantidad_salida  # Queda disponible para usar en máquina
            estado_inicial = 'ACTIVO'  # Estado activo, listo para usar
            
            execute_query(query_crear, (
                numero_parte,
                codigo_material,
                material_info.get('numero_lote_material', ''),
                area.upper(),
                'ALMACEN',
                estado_inicial,
                cantidad_inicial,
                cantidad_actual,
                'SISTEMA'
            ))
            
            print(f"✅ Entrada creada en {tabla_inventario} - Cantidad disponible: {cantidad_actual}")
            return True
        else:
            print(f"❌ No se pudo obtener información del material {codigo_material}")
            return False
            
    except Exception as e:
        print(f"❌ Error creando entrada en inventario específico: {e}")
        return False

def actualizar_inventario_general_salida_mysql(numero_parte, cantidad_salida):
    """Actualizar inventario general después de una salida usando MySQL"""
    try:
        # Recalcular inventario completo
        inventario_info = calcular_inventario_general_mysql(numero_parte)
        
        if inventario_info:
            # Actualizar o insertar en la tabla inventario_general
            query = """
                INSERT INTO inventario_general (numero_parte, cantidad_total, fecha_actualizacion)
                VALUES (%s, %s, NOW())
                ON DUPLICATE KEY UPDATE
                    cantidad_total = %s,
                    fecha_actualizacion = NOW()
            """
            
            cantidad_actual = inventario_info['inventario_actual']
            result = execute_query(query, (numero_parte, cantidad_actual, cantidad_actual))
            
            print(f" Inventario actualizado para {numero_parte}: {cantidad_actual}")
            return result > 0
        
        return False
    except Exception as e:
        print(f"Error actualizando inventario general: {e}")
        return False

def listar_modelos_bom_mysql():
    """Listar modelos de BOM usando MySQL"""
    try:
        query = "SELECT DISTINCT modelo FROM bom ORDER BY modelo"
        return execute_query(query, fetch='all') or []
    except Exception as e:
        print(f"Error listando modelos BOM: {e}")
        return []

# === FUNCIONES DE MIGRACIÓN ===

def migrar_desde_sqlite(sqlite_db_path):
    """Migrar datos desde SQLite a MySQL"""
    try:
        import sqlite3
        
        # Conectar a SQLite
        sqlite_conn = sqlite3.connect(sqlite_db_path)
        sqlite_conn.row_factory = sqlite3.Row
        sqlite_cursor = sqlite_conn.cursor()
        
        print(" Iniciando migración desde SQLite...")
        
        # Migrar usuarios
        try:
            sqlite_cursor.execute("SELECT * FROM usuarios")
            usuarios = sqlite_cursor.fetchall()
            for usuario in usuarios:
                crear_usuario(usuario['username'], usuario['password_hash'], usuario.get('area', ''))
            print(f" Migrados {len(usuarios)} usuarios")
        except Exception as e:
            print(f" Error migrando usuarios: {e}")
        
        # Migrar materiales
        try:
            sqlite_cursor.execute("SELECT * FROM materiales")
            materiales = sqlite_cursor.fetchall()
            for material in materiales:
                data = {
                    'numero_parte': material['numero_parte'],
                    'descripcion': material.get('descripcion'),
                    'categoria': material.get('categoria'),
                    'ubicacion': material.get('ubicacion'),
                    'stock_minimo': material.get('stock_minimo', 0),
                    'stock_maximo': material.get('stock_maximo', 0),
                    'unidad_medida': material.get('unidad_medida'),
                    'proveedor': material.get('proveedor')
                }
                guardar_material(data)
            print(f" Migrados {len(materiales)} materiales")
        except Exception as e:
            print(f" Error migrando materiales: {e}")
        
        # Migrar inventario
        try:
            sqlite_cursor.execute("SELECT * FROM inventario")
            inventarios = sqlite_cursor.fetchall()
            for inv in inventarios:
                actualizar_inventario(
                    inv['numero_parte'], 
                    inv.get('cantidad_actual', 0),
                    'migración',
                    'Migrado desde SQLite'
                )
            print(f" Migrados {len(inventarios)} registros de inventario")
        except Exception as e:
            print(f" Error migrando inventario: {e}")
        
        sqlite_conn.close()
        print(" Migración completada exitosamente")
        return True
        
    except Exception as e:
        print(f"❌ Error en migración: {e}")
        return False

# === FUNCIONES DE PRUEBA ===

def migrar_tabla_materiales():
    """Migrar tabla materiales existente para agregar nuevas columnas"""
    print(" Migrando tabla materiales para agregar nuevas columnas...")
    
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
        
        # Verificar qué columnas ya existen
        check_columns = "SHOW COLUMNS FROM materiales"
        existing_columns = execute_query(check_columns, fetch='all')
        existing_names = [col['Field'] for col in existing_columns] if existing_columns else []
        
        print(f" Columnas existentes: {existing_names}")
        
        # Agregar columnas que no existen
        for col_name, col_definition in nuevas_columnas:
            if col_name not in existing_names:
                try:
                    alter_query = f"ALTER TABLE materiales ADD COLUMN {col_name} {col_definition}"
                    execute_query(alter_query)
                    print(f" Columna {col_name} agregada")
                except Exception as e:
                    print(f" Error agregando columna {col_name}: {e}")
            else:
                print(f" Columna {col_name} ya existe")
        
        # Agregar índice para codigo_material si no existe
        try:
            index_query = "ALTER TABLE materiales ADD INDEX idx_codigo_material (codigo_material(255))"
            execute_query(index_query)
            print(" Índice en codigo_material agregado")
        except Exception as e:
            if "1061" in str(e):  # Duplicate key name
                print(" Índice en codigo_material ya existe")
            else:
                print(f" Error agregando índice: {e}")
        
        print(" Migración de tabla materiales completada")
        return True
        
    except Exception as e:
        print(f"❌ Error en migración de tabla materiales: {e}")
        return False

def verificar_estructura_materiales():
    """Verificar estructura de tabla materiales"""
    try:
        query = "DESCRIBE materiales"
        columnas = execute_query(query, fetch='all')
        
        print(" ESTRUCTURA ACTUAL DE TABLA MATERIALES:")
        print("-" * 60)
        for col in columnas:
            print(f"  {col['Field']:<25} {col['Type']:<20} {col['Null']:<5} {col['Key']:<5}")
        print("-" * 60)
        
        return True
    except Exception as e:
        print(f" Error verificando estructura: {e}")
        return False

def reparar_tabla_materiales():
    """Reparar problemas comunes en la tabla materiales"""
    print(" === REPARANDO TABLA MATERIALES ===")
    
    try:
        # 1. Verificar y reparar la tabla
        print("🔧 Verificando integridad de tabla...")
        check_table = "CHECK TABLE materiales"
        try:
            check_result = execute_query(check_table, fetch='all')
            for result in check_result:
                print(f" {result['Table']}: {result['Msg_type']} - {result['Msg_text']}")
        except Exception as e:
            print(f" No se pudo verificar tabla: {e}")
        
        # 2. Reparar tabla si es necesario
        print("🔧 Reparando tabla...")
        repair_table = "REPAIR TABLE materiales"
        try:
            repair_result = execute_query(repair_table, fetch='all')
            for result in repair_result:
                print(f"🔧 {result['Table']}: {result['Msg_type']} - {result['Msg_text']}")
        except Exception as e:
            print(f" No se pudo reparar tabla: {e}")
        
        # 3. Optimizar tabla
        print("🔧 Optimizando tabla...")
        optimize_table = "OPTIMIZE TABLE materiales"
        try:
            optimize_result = execute_query(optimize_table, fetch='all')
            for result in optimize_result:
                print(f" {result['Table']}: {result['Msg_type']} - {result['Msg_text']}")
        except Exception as e:
            print(f" No se pudo optimizar tabla: {e}")
        
        # 4. Verificar constrains y foreign keys
        print("🔧 Verificando constraints...")
        fk_query = """
            SELECT CONSTRAINT_NAME, TABLE_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
            FROM information_schema.KEY_COLUMN_USAGE 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND REFERENCED_TABLE_NAME = 'materiales'
        """
        fks = execute_query(fk_query, fetch='all')
        print(f" Foreign keys encontradas: {len(fks)}")
        for fk in fks:
            print(f"  - {fk['TABLE_NAME']}.{fk['COLUMN_NAME']} -> {fk['REFERENCED_TABLE_NAME']}.{fk['REFERENCED_COLUMN_NAME']}")
        
        # 5. Verificar y agregar índices faltantes
        print("🔧 Verificando índices...")
        required_indexes = [
            ('idx_numero_parte', 'numero_parte'),
            ('idx_codigo_material', 'codigo_material')
        ]
        
        existing_indexes_query = "SHOW INDEX FROM materiales"
        existing_indexes = execute_query(existing_indexes_query, fetch='all')
        existing_index_names = [idx['Key_name'] for idx in existing_indexes]
        
        for idx_name, idx_column in required_indexes:
            if idx_name not in existing_index_names:
                try:
                    create_index_query = f"ALTER TABLE materiales ADD INDEX {idx_name} ({idx_column}(255))"
                    execute_query(create_index_query)
                    print(f" Índice {idx_name} creado")
                except Exception as e:
                    if "1061" in str(e):  # Duplicate key name
                        print(f"ℹ Índice {idx_name} ya existe")
                    else:
                        print(f" Error creando índice {idx_name}: {e}")
            else:
                print(f" Índice {idx_name} ya existe")
        
        print(" Reparación de tabla completada")
        return True
        
    except Exception as e:
        print(f" Error reparando tabla materiales: {e}")
        return False

def analizar_filas_problematicas():
    """Analizar patrones comunes en filas que fallan durante importación"""
    print("🔍 === ANÁLISIS DE FILAS PROBLEMÁTICAS ===")
    
    try:
        # Patrones comunes de filas problemáticas
        filas_problematicas = [6, 7, 28, 253]
        
        print(f" Filas reportadas como problemáticas: {filas_problematicas}")
        print("🔍 Posibles causas comunes:")
        print("  1. Datos demasiado largos para los campos")
        print("  2. Caracteres especiales o encoding incorrecto")
        print("  3. Números de parte duplicados")
        print("  4. Campos requeridos vacíos o NULL")
        print("  5. Formato de fecha incorrecto")
        print("  6. Problemas de encoding UTF-8")
        
        # Verificar duplicados comunes
        print("\n🔍 Verificando duplicados en la tabla...")
        duplicados_query = """
            SELECT numero_parte, COUNT(*) as count 
            FROM materiales 
            GROUP BY numero_parte 
            HAVING COUNT(*) > 1 
            LIMIT 10
        """
        
        duplicados = execute_query(duplicados_query, fetch='all')
        if duplicados:
            print(f" Se encontraron {len(duplicados)} números de parte duplicados:")
            for dup in duplicados:
                print(f"  - {dup['numero_parte']}: {dup['count']} veces")
        else:
            print(" No se encontraron duplicados")
        
        # Verificar tamaños de campos
        print("\n🔍 Verificando registros con campos muy largos...")
        campos_largos_query = """
            SELECT 
                numero_parte,
                LENGTH(propiedad_material) as len_prop,
                LENGTH(classification) as len_class,
                LENGTH(especificacion_material) as len_espec,
                LENGTH(ubicacion_material) as len_ubicacion
            FROM materiales 
            WHERE LENGTH(propiedad_material) > 200 
               OR LENGTH(classification) > 200 
               OR LENGTH(ubicacion_material) > 200
            LIMIT 5
        """
        
        campos_largos = execute_query(campos_largos_query, fetch='all')
        if campos_largos:
            print(f" Se encontraron {len(campos_largos)} registros con campos largos:")
            for campo in campos_largos:
                print(f"  - {campo['numero_parte']}: prop={campo['len_prop']}, class={campo['len_class']}, espec={campo['len_espec']}, ubic={campo['len_ubicacion']}")
        else:
            print(" No se encontraron campos excesivamente largos")
        
        # Verificar caracteres especiales
        print("\n🔍 Verificando caracteres especiales problemáticos...")
        especiales_query = """
            SELECT numero_parte, propiedad_material
            FROM materiales 
            WHERE propiedad_material LIKE '%\\\\%' 
               OR propiedad_material LIKE '%"%' 
               OR propiedad_material LIKE "%'%"
               OR propiedad_material REGEXP '[^[:print:]]'
            LIMIT 5
        """
        
        try:
            especiales = execute_query(especiales_query, fetch='all')
            if especiales:
                print(f" Se encontraron {len(especiales)} registros con caracteres especiales:")
                for esp in especiales:
                    print(f"  - {esp['numero_parte']}: '{esp['propiedad_material'][:50]}...'")
            else:
                print(" No se encontraron caracteres especiales problemáticos")
        except Exception as e:
            print(f" No se pudo verificar caracteres especiales: {e}")
        
        print("\n RECOMENDACIONES PARA FILAS PROBLEMÁTICAS:")
        print("  1. Verificar que 'numero_parte' no esté vacío")
        print("  2. Truncar campos largos antes de insertar")
        print("  3. Limpiar caracteres especiales")
        print("  4. Verificar encoding UTF-8 del archivo Excel")
        print("  5. Validar que no hay duplicados")
        
        return True
        
    except Exception as e:
        print(f"❌ Error analizando filas problemáticas: {e}")
        return False

def diagnosticar_problemas_importacion():
    """Diagnosticar problemas comunes en la importación de materiales"""
    print("\n🔍 === DIAGNÓSTICO DE PROBLEMAS DE IMPORTACIÓN ===")
    
    try:
        # 1. Verificar conexión a MySQL
        if not test_connection():
            print("❌ PROBLEMA: No hay conexión a MySQL")
            return False
        else:
            print(" Conexión MySQL OK")
        
        # 2. Verificar que existe la tabla materiales
        check_table = "SHOW TABLES LIKE 'materiales'"
        table_exists = execute_query(check_table, fetch='one')
        if not table_exists:
            print("❌ PROBLEMA: Tabla 'materiales' no existe")
            return False
        else:
            print(" Tabla 'materiales' existe")
        
        # 3. Verificar estructura de la tabla
        print("\n Verificando estructura de tabla...")
        verificar_estructura_materiales()
        
        # 4. Verificar índices
        check_indexes = "SHOW INDEX FROM materiales"
        indexes = execute_query(check_indexes, fetch='all')
        print(f"\n Índices existentes ({len(indexes)} encontrados):")
        for idx in indexes:
            print(f"  - {idx['Key_name']}: {idx['Column_name']}")
        
        # 5. Contar registros existentes
        count_query = "SELECT COUNT(*) as total FROM materiales"
        count_result = execute_query(count_query, fetch='one')
        total_materials = count_result['total'] if count_result else 0
        print(f"\n📊 Total de materiales en BD: {total_materials}")
        
        # 6. Verificar espacio disponible (estimado)
        size_query = """
            SELECT 
                ROUND(((data_length + index_length) / 1024 / 1024), 2) AS 'DB Size in MB' 
            FROM information_schema.tables 
            WHERE table_schema = DATABASE() AND table_name = 'materiales'
        """
        size_result = execute_query(size_query, fetch='one')
        if size_result:
            print(f"📊 Tamaño de tabla materiales: {size_result['DB Size in MB']} MB")
        
        # 7. Probar inserción de prueba
        print("\n🧪 Probando inserción de material de prueba...")
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
            print(" Inserción de prueba exitosa")
            # Eliminar el registro de prueba
            delete_query = "DELETE FROM materiales WHERE numero_parte = %s"
            execute_query(delete_query, (test_data['numero_parte'],))
            print(" Registro de prueba eliminado")
        else:
            print("❌ PROBLEMA: Falló la inserción de prueba")
        
        print("\n Diagnóstico completado")
        return True
        
    except Exception as e:
        print(f"❌ Error en diagnóstico: {e}")
        return False

def test_mysql_functions():
    """Probar funciones de MySQL CON DIAGNÓSTICO COMPLETO"""
    print("\n🧪 Probando funciones de MySQL...")
    
    try:
        # Probar conexión
        if test_connection():
            print(" Conexión MySQL OK")
        else:
            print("❌ Error en conexión MySQL")
            return False
        
        # Ejecutar diagnóstico completo
        print("\n🔍 Ejecutando diagnóstico completo...")
        diagnosticar_problemas_importacion()
        
        # Verificar estructura de materiales
        verificar_estructura_materiales()
        
        # Migrar tabla si es necesario
        print("\n Verificando migración de tabla...")
        migrar_tabla_materiales()
        
        # Inicializar base de datos
        if init_db():
            print(" Inicialización MySQL OK")
        else:
            print("❌ Error en inicialización MySQL")
        
        print(" Pruebas de MySQL completadas")
        return True
        
    except Exception as e:
        print(f"❌ Error en pruebas MySQL: {e}")
        return False

if __name__ == "__main__":
    test_mysql_functions()

def agregar_columna_usuario_registro():
    """Agregar columna usuario_registro a la tabla materiales si no existe"""
    conn = None
    cursor = None
    try:
        conn = get_mysql_connection()
        if not conn:
            print("❌ No se pudo conectar a MySQL")
            return False
            
        cursor = conn.cursor()
        
        # Verificar si la columna ya existe
        cursor.execute("SHOW COLUMNS FROM materiales LIKE 'usuario_registro'")
        result = cursor.fetchone()
        
        if result:
            print(" La columna usuario_registro ya existe")
            return True
            
        # Agregar la columna si no existe
        alter_query = "ALTER TABLE materiales ADD COLUMN usuario_registro VARCHAR(255) DEFAULT 'SISTEMA'"
        cursor.execute(alter_query)
        
        # Agregar índice para la nueva columna
        index_query = "ALTER TABLE materiales ADD INDEX idx_usuario_registro (usuario_registro)"
        cursor.execute(index_query)
        
        conn.commit()
        print(" Columna usuario_registro agregada exitosamente")
        return True
        
    except Exception as e:
        print(f"❌ Error agregando columna usuario_registro: {e}")
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def get_mysql_connection():
    """Obtener conexión MySQL simple para migraciones"""
    try:
        from .config_mysql import get_mysql_connection as config_get_connection
        return config_get_connection()
        
    except Exception as e:
        print(f"Error conectando a MySQL: {e}")
        return None

