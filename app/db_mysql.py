"""Funciones de base de datos adaptadas para MySQL
Migración desde SQLite a MySQL para el hosting"""

import os
from .config_mysql import execute_query, test_connection
from datetime import datetime, timedelta
import json
import re
import unicodedata

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
        print(f" Error en eliminación de foreign keys: {e}")

def init_db():
    """Inicializar base de datos MySQL y crear tablas"""
    if not MYSQL_AVAILABLE:
        print(" MySQL no disponible - usando modo fallback")
        return False
        
    try:
        # Probar conexión
        if not test_connection():
            print(" Error conectando a MySQL")
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
        
        # MIGRAR TABLA BOM (agregar columna posicion_assy)
        print(" Migrando tabla bom...")
        migrar_tabla_bom()

        # Crear tablas/vista para ICOS de cambios de ingenieria.
        print(" Inicializando tablas de ICOS...")
        crear_tablas_icos()
        
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
                    print(f" Limpiando foreign keys en tabla {table}...")
                    
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
        print(f" Error en reparación de foreign keys: {e}")

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
            print(f" Error creando tabla base {table_name}: {e}")
    
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
            print(f" Error creando tabla {table_name}: {e}")
    
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
                print(f" Tabla materiales no existe, no se pueden crear foreign keys")
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
            print(f" Verificación final antes de crear {fk['constraint']}...")
            
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
                print(f" Error de índice para {fk['constraint']}: {error_msg}")
            elif "1005" in error_msg:
                print(f" Error de definición para {fk['constraint']}: {error_msg}")
            elif "1091" in error_msg:
                print(f" Foreign key {fk['constraint']} ya fue procesada anteriormente")
                continue
            else:
                print(f" Error creando {fk['constraint']}: {error_msg}")
            
            # No fallar completamente, continuar con las siguientes
            continue
    
    print("🔗 Proceso de foreign keys completado DEFINITIVAMENTE")

def get_connection():
    """Obtener conexión a MySQL reutilizable desde el pool."""
    if not MYSQL_AVAILABLE:
        return None
    from .config_mysql import get_pooled_connection
    return get_pooled_connection()

# Alias para compatibilidad
get_db_connection = get_connection


# === FUNCIONES DE ICOS / CAMBIOS DE INGENIERIA ===

def crear_tablas_icos():
    """Crear tablas y vista canonica para ICOS aprobados."""
    try:
        execute_query("""
            CREATE TABLE IF NOT EXISTS engineering_changes (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                ico_no VARCHAR(64) NOT NULL,
                part_no VARCHAR(100) NOT NULL,
                bom_revision VARCHAR(64) NOT NULL,
                effective_at DATETIME NOT NULL,
                status ENUM('DRAFT','APPROVED','CANCELLED') NOT NULL DEFAULT 'DRAFT',
                notes TEXT NULL,
                created_by VARCHAR(100) NULL,
                approved_by VARCHAR(100) NULL,
                created_at DATETIME DEFAULT NOW(),
                approved_at DATETIME NULL,
                updated_at DATETIME DEFAULT NOW(),
                UNIQUE KEY uk_engineering_change (ico_no, part_no, bom_revision),
                INDEX idx_eng_part_status_effective (part_no, status, effective_at),
                INDEX idx_eng_status_effective (status, effective_at),
                INDEX idx_eng_ico_no (ico_no)
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        """)

        execute_query("""
            CREATE TABLE IF NOT EXISTS engineering_change_bom_items (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                engineering_change_id BIGINT NOT NULL,
                tipo_material VARCHAR(32) NOT NULL DEFAULT 'MAIN',
                posicion_assy VARCHAR(64) NOT NULL,
                location_text TEXT NULL,
                material_code VARCHAR(128) NOT NULL,
                numero_parte VARCHAR(128) NOT NULL,
                qty DECIMAL(10,4) NOT NULL DEFAULT 1,
                ubicacion VARCHAR(255) NULL,
                proveedor VARCHAR(255) NULL,
                side VARCHAR(50) NULL,
                classification VARCHAR(100) NULL,
                spec TEXT NULL,
                created_at DATETIME DEFAULT NOW(),
                INDEX idx_ec_items_change (engineering_change_id),
                INDEX idx_ec_items_material (material_code),
                INDEX idx_ec_items_position (posicion_assy)
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        """)

        extra_columns = [
            ('location_text', 'location_text TEXT NULL AFTER posicion_assy'),
            ('bom_level', 'bom_level VARCHAR(32) NULL'),
            ('item_seq', 'item_seq VARCHAR(64) NULL'),
            ('item_name', 'item_name VARCHAR(255) NULL'),
            ('item_name_en', 'item_name_en VARCHAR(255) NULL'),
            ('unit', 'unit VARCHAR(32) NULL'),
            ('maker', 'maker VARCHAR(255) NULL'),
            ('process_name', 'process_name VARCHAR(100) NULL'),
            ('item_process', 'item_process VARCHAR(100) NULL'),
            ('item_class', 'item_class VARCHAR(100) NULL'),
            ('valid_from', 'valid_from DATE NULL'),
            ('valid_to', 'valid_to DATE NULL'),
            ('status_name', "status_name VARCHAR(32) NULL DEFAULT '사용'"),
            ('is_alternate', 'is_alternate TINYINT(1) NOT NULL DEFAULT 0'),
            ('alt_item_no', 'alt_item_no VARCHAR(128) NULL'),
            ('alt_item_name', 'alt_item_name VARCHAR(255) NULL'),
            ('alt_spec', 'alt_spec TEXT NULL'),
            ('alt_maker', 'alt_maker VARCHAR(255) NULL'),
            ('child_bom_part_no', 'child_bom_part_no VARCHAR(128) NULL'),
            ('is_sub_bom', 'is_sub_bom TINYINT(1) NOT NULL DEFAULT 0'),
        ]
        for column_name, column_definition in extra_columns:
            _ico_add_column_if_missing('engineering_change_bom_items', column_name, column_definition)

        ico_bridge_columns = [
            ('ks_family_prefix', 'ks_family_prefix VARCHAR(128) NULL'),
            ('ks_hist_seq', 'ks_hist_seq BIGINT NULL'),
            ('item_name', 'item_name VARCHAR(255) NULL'),
        ]
        for column_name, column_definition in ico_bridge_columns:
            _ico_add_column_if_missing('engineering_changes', column_name, column_definition)

        execute_query("""
            CREATE TABLE IF NOT EXISTS engineering_change_diff (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                engineering_change_id BIGINT NOT NULL,
                action ENUM('ADD','REMOVE','MODIFY') NOT NULL,
                item_no VARCHAR(128) NULL,
                bom_level VARCHAR(64) NULL,
                ks_row_id BIGINT NULL,
                field_changed VARCHAR(64) NULL,
                old_value TEXT NULL,
                new_value TEXT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_ecd_change (engineering_change_id),
                INDEX idx_ecd_action (engineering_change_id, action),
                INDEX idx_ecd_item (engineering_change_id, item_no)
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        """)
        _ico_add_column_if_missing(
            'engineering_change_diff', 'part_no',
            'part_no VARCHAR(128) NULL AFTER engineering_change_id'
        )
        _ico_add_index_if_missing(
            'engineering_change_diff', 'idx_ecd_part',
            '(engineering_change_id, part_no)'
        )

        execute_query("""
            CREATE TABLE IF NOT EXISTS engineering_change_scope (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                engineering_change_id BIGINT NOT NULL,
                part_no VARCHAR(128) NOT NULL,
                family_prefix VARCHAR(128) NULL,
                bom_revision VARCHAR(64) NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uk_ecs_change_part (engineering_change_id, part_no),
                INDEX idx_ecs_change (engineering_change_id),
                INDEX idx_ecs_family (family_prefix)
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        """)

        _ico_add_column_if_missing(
            'engineering_changes', 'scope_kind',
            "scope_kind ENUM('SINGLE','FAMILY') NOT NULL DEFAULT 'SINGLE'"
        )
        _ico_add_column_if_missing(
            'engineering_changes', 'family_prefix',
            'family_prefix VARCHAR(128) NULL'
        )
        _ico_add_index_if_missing(
            'engineering_changes',
            'idx_eng_ks_ecn',
            '(ks_family_prefix, ks_hist_seq)'
        )

        execute_query("""
            CREATE OR REPLACE VIEW v_mes_ico_bom_items AS
            SELECT
                ec.id AS engineering_change_id,
                ec.ico_no,
                ec.part_no,
                ec.bom_revision,
                ec.effective_at,
                ec.status,
                ec.updated_at AS source_updated_at,
                i.id AS item_id,
                UPPER(COALESCE(NULLIF(i.tipo_material, ''), 'MAIN')) AS tipo_material,
                i.posicion_assy,
                COALESCE(NULLIF(i.location_text, ''), i.ubicacion, i.posicion_assy) AS location_text,
                COALESCE(NULLIF(i.material_code, ''), i.numero_parte) AS material_code,
                COALESCE(NULLIF(i.numero_parte, ''), i.material_code) AS numero_parte,
                i.qty,
                i.ubicacion,
                i.proveedor,
                i.side,
                i.classification,
                i.spec,
                i.bom_level,
                i.item_seq,
                i.item_name,
                i.item_name_en,
                i.unit,
                i.maker,
                i.process_name,
                i.item_process,
                i.item_class,
                i.valid_from,
                i.valid_to,
                i.status_name,
                i.is_alternate,
                i.alt_item_no,
                i.alt_item_name,
                i.alt_spec,
                i.alt_maker,
                i.child_bom_part_no,
                i.is_sub_bom
            FROM engineering_changes ec
            INNER JOIN engineering_change_bom_items i
                ON i.engineering_change_id = ec.id
            WHERE ec.status = 'APPROVED'
        """)

        execute_query("""
            CREATE OR REPLACE VIEW v_icos_with_ks_ecn AS
            SELECT
                ec.id              AS ico_id,
                ec.ico_no,
                ec.part_no,
                ec.bom_revision,
                ec.effective_at,
                ec.status,
                ec.created_by,
                ec.approved_by,
                ec.approved_at,
                ec.ks_family_prefix,
                ec.ks_hist_seq,
                ke.family_prefix   AS ecn_family_prefix,
                ke.hist_seq        AS ecn_hist_seq,
                ke.item_no         AS ecn_item_no,
                ke.item_seq        AS ecn_item_seq,
                ke.sb_date         AS ecn_sb_date,
                ke.work_no         AS ecn_work_no,
                ke.chg_remark      AS ecn_chg_remark,
                ke.cause           AS ecn_cause,
                ke.step_result     AS ecn_step_result,
                ke.bom_emp_name    AS ecn_bom_emp_name,
                ke.dev_emp_name    AS ecn_dev_emp_name,
                ke.synced_at       AS ecn_synced_at
            FROM engineering_changes ec
            LEFT JOIN ks_engineering_changes ke
                ON ke.family_prefix = ec.ks_family_prefix COLLATE utf8mb4_0900_ai_ci
               AND ke.hist_seq      = ec.ks_hist_seq
        """)

        execute_query("""
            CREATE OR REPLACE VIEW v_icos_historial_unificado AS
            SELECT
                CAST(ec.id AS CHAR) COLLATE utf8mb4_0900_ai_ci AS id,
                ec.ico_no               COLLATE utf8mb4_0900_ai_ci AS ico_no,
                ec.part_no              COLLATE utf8mb4_0900_ai_ci AS part_no,
                ec.bom_revision         COLLATE utf8mb4_0900_ai_ci AS bom_revision,
                ec.effective_at         AS effective_at,
                ec.status               COLLATE utf8mb4_0900_ai_ci AS status,
                ec.created_by           COLLATE utf8mb4_0900_ai_ci AS created_by,
                ec.approved_by          COLLATE utf8mb4_0900_ai_ci AS approved_by,
                ec.approved_at          AS approved_at,
                ec.created_at           AS created_at,
                ec.updated_at           AS updated_at,
                'MES'                   COLLATE utf8mb4_0900_ai_ci AS origen,
                CAST(NULL AS UNSIGNED)  AS ks_hist_seq,
                CAST(NULL AS CHAR)      COLLATE utf8mb4_0900_ai_ci AS ks_family_prefix
            FROM engineering_changes ec

            UNION ALL

            SELECT
                CONCAT('ks-', ke.hist_seq) COLLATE utf8mb4_0900_ai_ci AS id,
                CONCAT('KS#', ke.hist_seq) COLLATE utf8mb4_0900_ai_ci AS ico_no,
                COALESCE(ke.item_no, ke.family_prefix) COLLATE utf8mb4_0900_ai_ci AS part_no,
                '-'                     COLLATE utf8mb4_0900_ai_ci AS bom_revision,
                ke.sb_date              AS effective_at,
                'APPROVED'              COLLATE utf8mb4_0900_ai_ci AS status,
                ke.dev_emp_name         COLLATE utf8mb4_0900_ai_ci AS created_by,
                ke.bom_emp_name         COLLATE utf8mb4_0900_ai_ci AS approved_by,
                ke.synced_at            AS approved_at,
                ke.synced_at            AS created_at,
                ke.synced_at            AS updated_at,
                'KS'                    COLLATE utf8mb4_0900_ai_ci AS origen,
                ke.hist_seq             AS ks_hist_seq,
                ke.family_prefix        COLLATE utf8mb4_0900_ai_ci AS ks_family_prefix
            FROM ks_engineering_changes ke
        """)

        print(" Tablas/vista de ICOS listas")
        return True
    except Exception as e:
        print(f" Error creando tablas/vista de ICOS: {e}")
        return False


def _ico_normalize_text(value, default=''):
    text = str(value if value is not None else default).strip()
    return text


def _ico_legacy_position(value):
    return _ico_normalize_text(value)[:64]


def _ico_normalize_upper(value, default=''):
    return _ico_normalize_text(value, default).upper()


def _ico_normalize_datetime(value):
    text = _ico_normalize_text(value)
    if not text:
        return ''
    text = text.replace('T', ' ')
    if len(text) == 16:
        text += ':00'
    return text


def _ico_normalize_date(value, default=''):
    if value is None or value == '':
        return default
    if hasattr(value, 'strftime'):
        return value.strftime('%Y-%m-%d')
    text = _ico_normalize_text(value)
    if not text:
        return default
    text = text.replace('T', ' ')
    return text.split(' ')[0]


def _ico_plant_date():
    try:
        return (datetime.utcnow() - timedelta(hours=6)).strftime('%Y-%m-%d')
    except Exception:
        return datetime.now().strftime('%Y-%m-%d')


def _ico_parse_qty(value, default=1.0):
    try:
        if value is None or str(value).strip() == '':
            return default
        qty = float(value)
        return qty if qty > 0 else default
    except Exception:
        return default


def _ico_parse_bool(value):
    text = _ico_normalize_text(value).lower()
    return 1 if text in ('1', 'true', 'yes', 'si', 'sí', 'y', 'x') else 0


def _ico_position_is_valid(posicion):
    text = _ico_normalize_text(posicion).upper()
    if not text:
        return False
    if re.fullmatch(r"\d+", text):
        return True
    return re.search(r"POSICION\s*\d+", text) is not None


def _ico_add_column_if_missing(table_name, column_name, column_definition):
    try:
        existing = execute_query(
            f"SHOW COLUMNS FROM {table_name} LIKE %s",
            (column_name,),
            fetch='one'
        )
        if not existing:
            execute_query(f"ALTER TABLE {table_name} ADD COLUMN {column_definition}")
    except Exception as e:
        print(f"Error asegurando columna {table_name}.{column_name}: {e}")


def _ico_add_index_if_missing(table_name, index_name, index_definition):
    try:
        existing = execute_query(
            f"SHOW INDEX FROM {table_name} WHERE Key_name = %s",
            (index_name,),
            fetch='one'
        )
        if not existing:
            execute_query(f"ALTER TABLE {table_name} ADD KEY {index_name} {index_definition}")
    except Exception as e:
        print(f"Error asegurando indice {table_name}.{index_name}: {e}")


def _ks_family_prefix(part_no):
    text = _ico_normalize_upper(part_no)
    return text[:-2] if len(text) > 2 else text


def _ks_part_catalog_lookup(part_no):
    """Buscar metadatos KS para un part_no en ks_part_catalog.

    Devuelve dict con item_name, family_prefix, root_part_no, bom_kind,
    spec, unit, bom_suffix; o None si no existe.
    """
    text = _ico_normalize_upper(part_no)
    if not text:
        return None
    try:
        row = execute_query(
            """
            SELECT item_name, family_prefix, root_part_no, bom_kind,
                   spec, unit, bom_suffix
            FROM ks_part_catalog
            WHERE part_no = %s
            LIMIT 1
            """,
            (text,),
            fetch='one'
        )
        return row or None
    except Exception as e:
        print(f"Error consultando ks_part_catalog para {part_no}: {e}")
        return None


def _ks_parse_suffixes(suffixes):
    """Normaliza una lista o string de sufijos. Acepta 'a,b,c' o ['a','b']."""
    if suffixes is None:
        return []
    if isinstance(suffixes, str):
        parts = re.split(r'[,;\s]+', suffixes)
    else:
        parts = list(suffixes)
    out = []
    seen = set()
    for p in parts:
        text = _ico_normalize_upper(p)
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out


def resolver_familia(family_prefix, suffixes):
    """Resolver una familia + sufijos a una lista de part_no existentes en ks_part_catalog.

    Devuelve: {family, suffixes, parts:[{part_no, item_name, family_prefix, bom_kind}], missing:[suffix...]}
    """
    family = _ico_normalize_upper(family_prefix)
    suf_list = _ks_parse_suffixes(suffixes)
    if not family:
        return {"family": "", "suffixes": suf_list, "parts": [], "missing": suf_list}
    if not suf_list:
        return {"family": family, "suffixes": [], "parts": [], "missing": []}

    found_parts = []
    found_suffixes = set()
    try:
        candidates = [f"{family}{s}" for s in suf_list]
        placeholders = ','.join(['%s'] * len(candidates))
        rows = execute_query(
            f"""
            SELECT part_no, item_name, family_prefix, root_part_no, bom_kind
            FROM ks_part_catalog
            WHERE part_no IN ({placeholders})
            """,
            tuple(candidates),
            fetch='all'
        ) or []
        for row in rows:
            pn = _ico_normalize_upper(row.get('part_no'))
            found_parts.append({
                'part_no': pn,
                'item_name': row.get('item_name'),
                'family_prefix': row.get('family_prefix'),
                'root_part_no': row.get('root_part_no'),
                'bom_kind': row.get('bom_kind'),
            })
            if pn.startswith(family):
                found_suffixes.add(pn[len(family):])
    except Exception as e:
        print(f"Error resolviendo familia {family}: {e}")

    missing = [s for s in suf_list if s not in found_suffixes]
    return {
        "family": family,
        "suffixes": suf_list,
        "parts": found_parts,
        "missing": missing,
    }


def _ks_fetch_bom_items_multi(part_numbers, bom_revision=None):
    """Obtener items de BOM vigente para varios part_no.
    Retorna dict: {part_no: [rows]}.
    """
    result = {}
    for pn in part_numbers:
        rows = _ks_fetch_current_bom_items(pn, bom_revision) or []
        if not rows and bom_revision:
            rows = _ks_fetch_current_bom_items(pn) or []
        result[_ico_normalize_upper(pn)] = rows
    return result


def _ks_process_value(*values):
    for value in values:
        text = _ico_normalize_upper(value)
        if text:
            return text
    return 'MAIN'


def _ks_bom_kind_from_items(items):
    processes = {_ks_process_value(i.get('item_process'), i.get('process_name'), i.get('tipo_material')) for i in items}
    if processes == {'SMD'}:
        return 'SMD'
    if processes == {'IMD'}:
        return 'IMD'
    return 'MASTER'


def _ks_fetch_current_bom_items(part_no, bom_revision=None):
    plant_date = _ico_plant_date()
    if not bom_revision:
        latest = execute_query(
            """
            SELECT bom_rev
            FROM v_icos_bom_current
            WHERE UPPER(bom_part_no) = UPPER(%s)
              AND (status_name IS NULL OR status_name = '' OR status_name = '사용')
              AND (valid_from IS NULL OR valid_from <= %s)
              AND (valid_to IS NULL OR valid_to >= %s)
            GROUP BY bom_rev
            ORDER BY MAX(header_synced_at) DESC, bom_rev DESC
            LIMIT 1
            """,
            (part_no, plant_date, plant_date),
            fetch='one'
        )
        bom_revision = latest.get('bom_rev') if latest else None
        if not bom_revision:
            return []

    params = [part_no, plant_date, plant_date]
    where = """
        UPPER(bom_part_no) = UPPER(%s)
        AND (status_name IS NULL OR status_name = '' OR status_name = '사용')
        AND (valid_from IS NULL OR valid_from <= %s)
        AND (valid_to IS NULL OR valid_to >= %s)
    """
    where += " AND UPPER(bom_rev) = UPPER(%s)"
    params.append(bom_revision)
    try:
        return execute_query(
            f"""
            SELECT *
            FROM v_icos_bom_current
            WHERE {where}
            ORDER BY header_synced_at DESC, bom_rev DESC, item_seq
            """,
            tuple(params),
            fetch='all'
        ) or []
    except Exception as e:
        print(f"Error leyendo v_icos_bom_current para {part_no}: {e}")
        return []


def _ico_get_by_id(ico_id):
    return execute_query(
        "SELECT * FROM engineering_changes WHERE id = %s",
        (ico_id,),
        fetch='one'
    )


def _ico_list_filters(status=None, part_no=None, origen=None, ico_no=None, date_from=None, date_to=None):
    where = ["1=1"]
    params = []
    if status:
        where.append("h.status = %s")
        params.append(_ico_normalize_upper(status))
    if part_no:
        part_filter = _ico_normalize_upper(part_no)
        where.append("""
            (
                UPPER(h.part_no) = %s
                OR UPPER(h.ks_family_prefix) = %s
                OR EXISTS (
                    SELECT 1
                    FROM engineering_change_scope es
                    WHERE h.origen = 'MES'
                      AND CAST(es.engineering_change_id AS CHAR) = h.id
                      AND UPPER(es.part_no) = %s
                )
            )
        """)
        params.extend([part_filter, part_filter, part_filter])
    if origen:
        where.append("h.origen = %s")
        params.append(_ico_normalize_upper(origen))
    if ico_no:
        ico_filter = _ico_normalize_upper(ico_no)
        clean_filter = ico_filter.replace('KS#', '').replace('KS-', '')
        like_filter = f"%{ico_filter}%"
        where.append("""
            (
                UPPER(h.ico_no) LIKE %s
                OR UPPER(h.id) LIKE %s
                OR REPLACE(UPPER(h.ico_no), 'KS#', '') = %s
                OR REPLACE(UPPER(h.id), 'KS-', '') = %s
            )
        """)
        params.extend([like_filter, like_filter, clean_filter, clean_filter])
    if date_from:
        where.append("DATE(h.effective_at) >= %s")
        params.append(_ico_normalize_date(date_from))
    if date_to:
        where.append("DATE(h.effective_at) <= %s")
        params.append(_ico_normalize_date(date_to))
    return where, params


def contar_icos(status=None, part_no=None, origen=None, ico_no=None, date_from=None, date_to=None):
    """Contar ICOS para paginacion."""
    try:
        crear_tablas_icos()
        where, params = _ico_list_filters(status, part_no, origen, ico_no, date_from, date_to)
        row = execute_query(
            f"""
            SELECT COUNT(*) AS total
            FROM v_icos_historial_unificado h
            WHERE {' AND '.join(where)}
            """,
            tuple(params),
            fetch='one'
        ) or {}
        return int(row.get('total') or 0)
    except Exception as e:
        print(f"Error contando ICOS: {e}")
        return 0


def listar_icos(status=None, part_no=None, limit=100, origen=None, ico_no=None, date_from=None, date_to=None, offset=0):
    """Listar historial unificado de ICOs (MES) + ECN (K-system).

    origen: 'MES' | 'KS' | None (todos)
    """
    try:
        crear_tablas_icos()
        where, params = _ico_list_filters(status, part_no, origen, ico_no, date_from, date_to)
        limit_clause = ""
        if limit is not None:
            safe_limit = max(1, min(int(limit or 100), 500))
            safe_offset = max(0, int(offset or 0))
            limit_clause = f"LIMIT {safe_limit} OFFSET {safe_offset}"
        query = f"""
            SELECT h.*,
                   COALESCE(c.item_count, 0) AS item_count,
                   COALESCE(s.scope_count, CASE WHEN h.origen = 'MES' THEN 1 ELSE 0 END) AS scope_count,
                   s.scope_parts
            FROM v_icos_historial_unificado h
            LEFT JOIN (
                SELECT engineering_change_id, COUNT(*) AS item_count
                FROM engineering_change_bom_items
                GROUP BY engineering_change_id
            ) c ON h.origen = 'MES' AND CAST(c.engineering_change_id AS CHAR) = h.id
            LEFT JOIN (
                SELECT engineering_change_id,
                       COUNT(*) AS scope_count,
                       GROUP_CONCAT(part_no ORDER BY part_no SEPARATOR ', ') AS scope_parts
                FROM engineering_change_scope
                GROUP BY engineering_change_id
            ) s ON h.origen = 'MES' AND CAST(s.engineering_change_id AS CHAR) = h.id
            WHERE {' AND '.join(where)}
            ORDER BY COALESCE(h.effective_at, h.updated_at) DESC, h.updated_at DESC
            {limit_clause}
        """
        return execute_query(query, tuple(params), fetch='all') or []
    except Exception as e:
        print(f"Error listando ICOS: {e}")
        return []


def obtener_ico_detalle(ico_id):
    """Obtener ICO con sus items."""
    try:
        crear_tablas_icos()
        ico = _ico_get_by_id(ico_id)
        if not ico:
            return None
        items = execute_query(
            """
            SELECT * FROM engineering_change_bom_items
            WHERE engineering_change_id = %s
            ORDER BY COALESCE(NULLIF(location_text, ''), posicion_assy), material_code
            """,
            (ico_id,),
            fetch='all'
        ) or []
        ico['items'] = items
        return ico
    except Exception as e:
        print(f"Error obteniendo ICO: {e}")
        return None


def obtener_ecn_ks(hist_seq):
    """Obtener detalle de un ECN sincronizado desde K-system."""
    try:
        row = execute_query(
            """
            SELECT
                family_prefix, hist_seq, item_no, item_seq, sb_date,
                ord1, decide1, ord2, decide2,
                chg_remark, change_context, cause, step_result,
                bom_emp_seq, bom_emp_name, dev_emp_seq, dev_emp_name,
                remark, seongcheolsa, work_no, synced_at
            FROM ks_engineering_changes
            WHERE hist_seq = %s
            LIMIT 1
            """,
            (int(hist_seq),),
            fetch='one'
        )
        return row
    except Exception as e:
        print(f"Error obteniendo ECN KS {hist_seq}: {e}")
        return None


def crear_ico(data, created_by='desconocido'):
    """Crear ICO en borrador y opcionalmente copiar el BOM actual del modelo."""
    crear_tablas_icos()
    ico_no = _ico_normalize_upper(data.get('ico_no'))
    part_no = _ico_normalize_upper(data.get('part_no'))
    bom_revision = _ico_normalize_upper(data.get('bom_revision'))
    effective_at = _ico_normalize_datetime(data.get('effective_at'))
    notes = _ico_normalize_text(data.get('notes'))
    item_name_input = _ico_normalize_text(data.get('item_name'))
    copy_current_bom = data.get('copy_current_bom', True)

    if not ico_no or not part_no or not bom_revision or not effective_at:
        raise ValueError("ico_no, part_no, bom_revision y effective_at son requeridos")

    if not item_name_input:
        catalog = _ks_part_catalog_lookup(part_no) or {}
        item_name_input = _ico_normalize_text(catalog.get('item_name'))

    conn = get_connection()
    if conn is None:
        raise RuntimeError("No hay conexion MySQL disponible")

    cursor = conn.cursor()
    try:
        try:
            conn.autocommit(False)
        except Exception:
            pass
        cursor.execute(
            """
            INSERT INTO engineering_changes
                (ico_no, part_no, bom_revision, effective_at, status, notes, created_by, item_name)
            VALUES (%s, %s, %s, %s, 'DRAFT', %s, %s, %s)
            """,
            (ico_no, part_no, bom_revision, effective_at, notes, created_by, item_name_input or None)
        )
        ico_id = cursor.lastrowid

        if copy_current_bom:
            current_items = _ks_fetch_current_bom_items(part_no, bom_revision)
            if not current_items:
                current_items = _ks_fetch_current_bom_items(part_no)
            values = []
            for item in current_items:
                material = _ico_normalize_upper(item.get('item_no'))
                numero_parte = material
                location_text = _ico_normalize_text(item.get('location_text'))
                process_value = _ks_process_value(item.get('item_process'), item.get('process_name'))
                values.append((
                    ico_id,
                    process_value,
                    _ico_legacy_position(location_text),
                    location_text,
                    material,
                    numero_parte,
                    _ico_parse_qty(item.get('qty')),
                    location_text,
                    _ico_normalize_text(item.get('supplier') or item.get('maker')),
                    '',
                    _ico_normalize_text(item.get('item_class')),
                    _ico_normalize_text(item.get('spec')),
                    _ico_normalize_text(item.get('bom_level')),
                    _ico_normalize_text(item.get('item_seq')),
                    _ico_normalize_text(item.get('item_name')),
                    _ico_normalize_text(item.get('item_name_en')),
                    _ico_normalize_text(item.get('unit')),
                    _ico_normalize_text(item.get('maker')),
                    _ico_normalize_text(item.get('process_name')),
                    process_value,
                    _ico_normalize_text(item.get('item_class')),
                    _ico_normalize_date(item.get('valid_from'), _ico_normalize_date(effective_at)),
                    _ico_normalize_date(item.get('valid_to')) or None,
                    _ico_normalize_text(item.get('status_name'), '사용') or '사용',
                    _ico_parse_bool(item.get('is_alternate')),
                    _ico_normalize_upper(item.get('alt_item_no')),
                    _ico_normalize_text(item.get('alt_item_name')),
                    _ico_normalize_text(item.get('alt_spec')),
                    _ico_normalize_text(item.get('alt_maker')),
                    _ico_normalize_upper(item.get('child_bom_part_no')),
                    _ico_parse_bool(item.get('is_sub_bom')),
                ))
            if values:
                cursor.executemany(
                    """
                    INSERT INTO engineering_change_bom_items
                        (engineering_change_id, tipo_material, posicion_assy, location_text, material_code,
                         numero_parte, qty, ubicacion, proveedor, side, classification, spec,
                         bom_level, item_seq, item_name, item_name_en, unit, maker,
                         process_name, item_process, item_class, valid_from, valid_to,
                         status_name, is_alternate, alt_item_no, alt_item_name, alt_spec,
                         alt_maker, child_bom_part_no, is_sub_bom)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    values
                )

        conn.commit()
        return obtener_ico_detalle(ico_id)
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            conn.autocommit(True)
        except Exception:
            pass
        cursor.close()
        conn.close()


_ICO_DIFF_CRITICAL_FIELDS = (
    'item_no', 'qty', 'location_text', 'supplier', 'item_class',
    'alt_item_no', 'valid_from', 'valid_to', 'is_alternate',
)


def _ico_diff_normalize(value):
    """Normalizar valor para comparar campos del diff (None/str/numero)."""
    if value is None:
        return ''
    if hasattr(value, 'strftime'):
        try:
            return value.strftime('%Y-%m-%d')
        except Exception:
            return str(value)
    text = str(value).strip()
    if text.lower() in ('nan', 'none', 'null'):
        return ''
    return text


def _ico_diff_normalize_qty(value):
    try:
        if value is None or str(value).strip() == '':
            return ''
        return f"{float(value):g}"
    except (TypeError, ValueError):
        return _ico_diff_normalize(value)


def _ico_diff_normalize_bool(value):
    if value is None or str(value).strip() == '':
        return '0'
    return '1' if _ico_parse_bool(value) else '0'


def _ico_diff_field_value(item, field):
    if field == 'qty':
        return _ico_diff_normalize_qty(item.get('qty'))
    if field == 'is_alternate':
        return _ico_diff_normalize_bool(item.get('is_alternate'))
    if field in ('valid_from', 'valid_to'):
        return _ico_diff_normalize(item.get(field))
    return _ico_diff_normalize(item.get(field))


def crear_ico_desde_excel(metadata, excel_rows, created_by='desconocido'):
    """Crear ICO DRAFT desde un Excel modificado de BOM.

    metadata: dict con ico_no, part_no, bom_revision, effective_at, item_name?, notes?
    excel_rows: lista de dicts con keys segun BOM_EXCEL_COLUMNS (sin '__row_id' es addición; con id existente es modificacion).

    Retorna: {success, ico_id, diff:{added,removed,modified}, errors}
    """
    crear_tablas_icos()
    ico_no = _ico_normalize_upper(metadata.get('ico_no'))
    part_no = _ico_normalize_upper(metadata.get('part_no'))
    bom_revision = _ico_normalize_upper(metadata.get('bom_revision'))
    effective_at = _ico_normalize_datetime(metadata.get('effective_at'))
    notes = _ico_normalize_text(metadata.get('notes'))
    item_name_input = _ico_normalize_text(metadata.get('item_name'))

    errors = []
    if not ico_no: errors.append("ico_no requerido")
    if not part_no: errors.append("part_no requerido")
    if not bom_revision: errors.append("bom_revision requerido")
    if not effective_at: errors.append("effective_at requerido")
    if not excel_rows: errors.append("El Excel no tiene filas")
    if errors:
        return {"success": False, "errors": errors}

    if not item_name_input:
        catalog = _ks_part_catalog_lookup(part_no) or {}
        item_name_input = _ico_normalize_text(catalog.get('item_name'))

    current_items = _ks_fetch_current_bom_items(part_no, bom_revision) or []
    if not current_items:
        current_items = _ks_fetch_current_bom_items(part_no) or []
    current_by_id = {}
    for row in current_items:
        rid = row.get('id')
        if rid is not None:
            current_by_id[int(rid)] = row

    seen_levels = set()
    seen_ids = set()
    parsed_rows = []
    for idx, raw in enumerate(excel_rows, start=1):
        row_id_raw = raw.get('__row_id')
        try:
            row_id = int(row_id_raw) if row_id_raw not in (None, '', 'nan', 'None') else None
        except (TypeError, ValueError):
            row_id = None

        item_no = _ico_normalize_upper(raw.get('item_no'))
        if not item_no:
            errors.append(f"Fila {idx}: item_no vacio")
            continue

        qty_raw = raw.get('qty')
        try:
            qty = float(qty_raw) if qty_raw not in (None, '') else 0
        except (TypeError, ValueError):
            errors.append(f"Fila {idx} ({item_no}): qty no es numero ('{qty_raw}')")
            continue
        if qty <= 0:
            errors.append(f"Fila {idx} ({item_no}): qty debe ser > 0")
            continue

        bom_level = _ico_normalize_text(raw.get('bom_level')) or f"01-{idx:02d}"
        if bom_level in seen_levels:
            errors.append(f"Fila {idx} ({item_no}): bom_level '{bom_level}' duplicado")
        seen_levels.add(bom_level)

        if row_id is not None:
            if row_id in seen_ids:
                errors.append(f"Fila {idx} ({item_no}): __row_id {row_id} duplicado")
            seen_ids.add(row_id)
            if row_id not in current_by_id:
                errors.append(f"Fila {idx} ({item_no}): __row_id {row_id} no existe en BOM actual")

        parsed_rows.append({
            '__row_id': row_id,
            'item_no': item_no,
            'item_name': _ico_normalize_text(raw.get('item_name')),
            'spec': _ico_normalize_text(raw.get('spec')),
            'qty': qty,
            'unit': _ico_normalize_text(raw.get('unit')) or 'EA',
            'location_text': _ico_normalize_text(raw.get('location_text')),
            'maker': _ico_normalize_text(raw.get('maker')),
            'supplier': _ico_normalize_text(raw.get('supplier')),
            'item_class': _ico_normalize_text(raw.get('item_class')),
            'item_process': _ico_normalize_text(raw.get('item_process')),
            'process_name': _ico_normalize_text(raw.get('process_name')),
            'valid_from': _ico_normalize_date(raw.get('valid_from')) or None,
            'valid_to': _ico_normalize_date(raw.get('valid_to')) or None,
            'is_alternate': _ico_parse_bool(raw.get('is_alternate')),
            'alt_item_no': _ico_normalize_upper(raw.get('alt_item_no')),
            'alt_item_name': _ico_normalize_text(raw.get('alt_item_name')),
            'alt_spec': _ico_normalize_text(raw.get('alt_spec')),
            'alt_maker': _ico_normalize_text(raw.get('alt_maker')),
            'remark': _ico_normalize_text(raw.get('remark')),
            'bom_level': bom_level,
            'item_seq': _ico_normalize_text(raw.get('item_seq')) or str(idx),
        })

    if errors:
        return {"success": False, "errors": errors}

    diff_added = []
    diff_removed = []
    diff_modified = []

    for row in parsed_rows:
        if row['__row_id'] is None:
            diff_added.append(row)
        else:
            original = current_by_id.get(row['__row_id'])
            if original is None:
                continue
            field_diffs = []
            for field in _ICO_DIFF_CRITICAL_FIELDS:
                old_val = _ico_diff_field_value(original, field)
                new_val = _ico_diff_field_value(row, field)
                if old_val != new_val:
                    field_diffs.append({
                        'field': field,
                        'old': old_val,
                        'new': new_val,
                    })
            if field_diffs:
                diff_modified.append({
                    'row_id': row['__row_id'],
                    'item_no': row['item_no'],
                    'bom_level': row['bom_level'],
                    'changes': field_diffs,
                })

    excel_ids = {row['__row_id'] for row in parsed_rows if row['__row_id'] is not None}
    for rid, original in current_by_id.items():
        if rid not in excel_ids:
            diff_removed.append({
                'row_id': rid,
                'item_no': _ico_diff_normalize(original.get('item_no')),
                'bom_level': _ico_diff_normalize(original.get('bom_level')),
            })

    if not (diff_added or diff_removed or diff_modified):
        return {"success": False, "errors": ["El Excel no contiene cambios respecto al BOM actual"]}

    conn = get_connection()
    if conn is None:
        return {"success": False, "errors": ["No hay conexion MySQL disponible"]}

    cursor = conn.cursor()
    try:
        try:
            conn.autocommit(False)
        except Exception:
            pass

        cursor.execute(
            """
            INSERT INTO engineering_changes
                (ico_no, part_no, bom_revision, effective_at, status, notes, created_by, item_name)
            VALUES (%s, %s, %s, %s, 'DRAFT', %s, %s, %s)
            """,
            (ico_no, part_no, bom_revision, effective_at, notes, created_by, item_name_input or None)
        )
        ico_id = cursor.lastrowid

        item_values = []
        for row in parsed_rows:
            item_values.append((
                ico_id,
                _ks_process_value(row.get('item_process'), 'MAIN'),
                _ico_legacy_position(row['location_text']),
                row['location_text'],
                row['item_no'],
                row['item_no'],
                row['qty'],
                row['location_text'],
                row['supplier'] or row['maker'],
                '',
                row['item_class'],
                row['spec'],
                row['bom_level'],
                row['item_seq'],
                row['item_name'] or row['item_no'],
                '',
                row['unit'],
                row['maker'],
                row['process_name'] or row['item_process'],
                row['item_process'],
                row['item_class'],
                row['valid_from'],
                row['valid_to'],
                '사용',
                row['is_alternate'],
                row['alt_item_no'],
                row['alt_item_name'],
                row['alt_spec'],
                row['alt_maker'],
                '',
                0,
            ))
        if item_values:
            cursor.executemany(
                """
                INSERT INTO engineering_change_bom_items
                    (engineering_change_id, tipo_material, posicion_assy, location_text, material_code,
                     numero_parte, qty, ubicacion, proveedor, side, classification, spec,
                     bom_level, item_seq, item_name, item_name_en, unit, maker,
                     process_name, item_process, item_class, valid_from, valid_to,
                     status_name, is_alternate, alt_item_no, alt_item_name, alt_spec,
                     alt_maker, child_bom_part_no, is_sub_bom)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                item_values
            )

        diff_rows = []
        for r in diff_added:
            diff_rows.append((ico_id, 'ADD', r['item_no'], r['bom_level'], None, None, None, None))
        for r in diff_removed:
            diff_rows.append((ico_id, 'REMOVE', r['item_no'], r['bom_level'], r['row_id'], None, None, None))
        for r in diff_modified:
            for change in r['changes']:
                diff_rows.append((
                    ico_id, 'MODIFY', r['item_no'], r['bom_level'], r['row_id'],
                    change['field'], change['old'] or None, change['new'] or None,
                ))
        if diff_rows:
            cursor.executemany(
                """
                INSERT INTO engineering_change_diff
                    (engineering_change_id, action, item_no, bom_level, ks_row_id,
                     field_changed, old_value, new_value)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                diff_rows
            )

        conn.commit()
        return {
            "success": True,
            "ico_id": ico_id,
            "diff": {
                "added": len(diff_added),
                "removed": len(diff_removed),
                "modified": len(diff_modified),
                "modified_fields": sum(len(r['changes']) for r in diff_modified),
            },
            "errors": [],
        }
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        print(f"Error creando ICO desde Excel: {e}")
        return {"success": False, "errors": [str(e)]}
    finally:
        try:
            conn.autocommit(True)
        except Exception:
            pass
        cursor.close()
        conn.close()


def obtener_diff_ico(ico_id):
    """Obtener el diff persistido de un ICO."""
    try:
        rows = execute_query(
            """
            SELECT id, part_no, action, item_no, bom_level, ks_row_id,
                   field_changed, old_value, new_value, created_at
            FROM engineering_change_diff
            WHERE engineering_change_id = %s
            ORDER BY FIELD(action, 'ADD', 'MODIFY', 'REMOVE'), part_no, bom_level, item_no, field_changed
            """,
            (int(ico_id),),
            fetch='all'
        ) or []
        return rows
    except Exception as e:
        print(f"Error obteniendo diff ICO {ico_id}: {e}")
        return []


def obtener_scope_ico(ico_id):
    """Obtener la lista de part_no afectados por un ICO de familia."""
    try:
        rows = execute_query(
            """
            SELECT part_no, family_prefix, bom_revision
            FROM engineering_change_scope
            WHERE engineering_change_id = %s
            ORDER BY part_no
            """,
            (int(ico_id),),
            fetch='all'
        ) or []
        return rows
    except Exception as e:
        print(f"Error obteniendo scope ICO {ico_id}: {e}")
        return []


def crear_ico_familia_desde_excel(metadata, excel_rows, scope_parts, created_by='desconocido'):
    """Crear ICO de familia desde Excel multi-modelo.

    metadata: ico_no, family_prefix, bom_revision, effective_at, item_name?, notes?
    excel_rows: lista de dicts con __row_key, modelos_afectados, item_no, bom_level y demas campos.
    scope_parts: lista de part_no del scope (resuelta antes).

    Retorna: {success, ico_id, diff, errors}
    """
    crear_tablas_icos()
    ico_no = _ico_normalize_upper(metadata.get('ico_no'))
    family_prefix = _ico_normalize_upper(metadata.get('family_prefix'))
    bom_revision = _ico_normalize_upper(metadata.get('bom_revision'))
    effective_at = _ico_normalize_datetime(metadata.get('effective_at'))
    notes = _ico_normalize_text(metadata.get('notes'))
    item_name_input = _ico_normalize_text(metadata.get('item_name'))
    scope_parts = [_ico_normalize_upper(p) for p in scope_parts if p]

    errors = []
    if not ico_no: errors.append("ico_no requerido")
    if not family_prefix: errors.append("family_prefix requerido")
    if not bom_revision: errors.append("bom_revision requerido")
    if not effective_at: errors.append("effective_at requerido")
    if not scope_parts: errors.append("scope_parts vacio")
    if not excel_rows: errors.append("El Excel no tiene filas")
    if errors:
        return {"success": False, "errors": errors}

    # Construir BOM vigente por modelo
    bom_by_part = _ks_fetch_bom_items_multi(scope_parts, bom_revision)
    bom_by_part_key = {}  # {part_no: {row_key: row}}
    for pn, rows in bom_by_part.items():
        idx = {}
        for r in rows:
            key = f"{(r.get('item_no') or '').upper()}|{(r.get('bom_level') or '').strip()}"
            if key.strip('|'):
                idx[key] = r
        bom_by_part_key[pn] = idx

    # Parsear filas del Excel
    parsed_rows = []
    seen_keys = set()
    for idx, raw in enumerate(excel_rows, start=1):
        row_key = _ico_normalize_text(raw.get('__row_key'))
        if not row_key or '|' not in row_key:
            errors.append(f"Fila {idx}: __row_key invalido ('{row_key}')")
            continue
        if row_key in seen_keys:
            errors.append(f"Fila {idx}: __row_key '{row_key}' duplicado")
            continue
        seen_keys.add(row_key)

        item_no = _ico_normalize_upper(raw.get('item_no'))
        if not item_no:
            errors.append(f"Fila {idx}: item_no vacio")
            continue

        qty_raw = raw.get('qty')
        try:
            qty = float(qty_raw) if qty_raw not in (None, '') else 0
        except (TypeError, ValueError):
            errors.append(f"Fila {idx} ({item_no}): qty no es numero ('{qty_raw}')")
            continue
        if qty <= 0:
            errors.append(f"Fila {idx} ({item_no}): qty debe ser > 0")
            continue

        modelos_raw = _ico_normalize_text(raw.get('modelos_afectados'))
        modelos = _ks_parse_suffixes(modelos_raw) if modelos_raw else []
        modelos = [m for m in modelos if m in scope_parts]
        if not modelos:
            # Si no especifica, asumir todos los del scope
            modelos = list(scope_parts)

        bom_level = _ico_normalize_text(raw.get('bom_level')) or row_key.split('|', 1)[1]

        parsed_rows.append({
            '__row_key': row_key,
            'item_no': item_no,
            'item_name': _ico_normalize_text(raw.get('item_name')),
            'spec': _ico_normalize_text(raw.get('spec')),
            'qty': qty,
            'unit': _ico_normalize_text(raw.get('unit')) or 'EA',
            'location_text': _ico_normalize_text(raw.get('location_text')),
            'maker': _ico_normalize_text(raw.get('maker')),
            'supplier': _ico_normalize_text(raw.get('supplier')),
            'item_class': _ico_normalize_text(raw.get('item_class')),
            'item_process': _ico_normalize_text(raw.get('item_process')),
            'process_name': _ico_normalize_text(raw.get('process_name')),
            'valid_from': _ico_normalize_date(raw.get('valid_from')) or None,
            'valid_to': _ico_normalize_date(raw.get('valid_to')) or None,
            'is_alternate': _ico_parse_bool(raw.get('is_alternate')),
            'alt_item_no': _ico_normalize_upper(raw.get('alt_item_no')),
            'alt_item_name': _ico_normalize_text(raw.get('alt_item_name')),
            'alt_spec': _ico_normalize_text(raw.get('alt_spec')),
            'alt_maker': _ico_normalize_text(raw.get('alt_maker')),
            'remark': _ico_normalize_text(raw.get('remark')),
            'bom_level': bom_level,
            'item_seq': _ico_normalize_text(raw.get('item_seq')) or str(idx),
            'modelos_afectados': modelos,
        })

    if errors:
        return {"success": False, "errors": errors}

    # Calcular diff por modelo
    diff_added = []  # [{part_no, row, ...}]
    diff_removed = []
    diff_modified = []

    excel_keys = {r['__row_key'] for r in parsed_rows}

    for row in parsed_rows:
        key = row['__row_key']
        for pn in row['modelos_afectados']:
            current = bom_by_part_key.get(pn, {}).get(key)
            if current is None:
                # El usuario quiere aplicar este item a un modelo donde no existe
                # ADD: aceptable. Lo importante es que no hagamos MODIFY sobre algo inexistente.
                diff_added.append({
                    'part_no': pn,
                    'row': row,
                })
            else:
                field_diffs = []
                for field in _ICO_DIFF_CRITICAL_FIELDS:
                    old_val = _ico_diff_field_value(current, field)
                    new_val = _ico_diff_field_value(row, field)
                    if old_val != new_val:
                        field_diffs.append({
                            'field': field,
                            'old': old_val,
                            'new': new_val,
                        })
                if field_diffs:
                    diff_modified.append({
                        'part_no': pn,
                        'row_id': current.get('id'),
                        'item_no': row['item_no'],
                        'bom_level': row['bom_level'],
                        'changes': field_diffs,
                        'row': row,
                    })

    # REMOVE: items en BOM vigente que no aparecen en el Excel (por modelo)
    for pn, idx in bom_by_part_key.items():
        for key, original in idx.items():
            if key not in excel_keys:
                diff_removed.append({
                    'part_no': pn,
                    'row_id': original.get('id'),
                    'item_no': original.get('item_no'),
                    'bom_level': original.get('bom_level'),
                })

    if not (diff_added or diff_removed or diff_modified):
        return {"success": False, "errors": ["El Excel no contiene cambios respecto al BOM actual"]}

    # Bloquear si una fila MODIFY apunta a un modelo donde el item no existe
    # (Eso se detectaria como ADD; pero si el usuario listo el modelo en modelos_afectados
    #  con la intencion de modificar, debe existir. Verificamos: si una row con cambios criticos
    #  termino como ADD en un modelo donde NO existia, lo permitimos solo si TODOS los campos
    #  son nuevos. Aqui aceptamos ADD libremente; el bloqueo lo dejamos a si el usuario manda
    #  un modelo no presente en scope_parts -> ya filtrado arriba.)

    # Tomar metadatos del catalog para usar el primer part_no como representante
    representative_part = scope_parts[0]
    if not item_name_input:
        catalog = _ks_part_catalog_lookup(representative_part) or {}
        item_name_input = _ico_normalize_text(catalog.get('item_name'))

    conn = get_connection()
    if conn is None:
        return {"success": False, "errors": ["No hay conexion MySQL disponible"]}

    cursor = conn.cursor()
    try:
        try:
            conn.autocommit(False)
        except Exception:
            pass

        cursor.execute(
            """
            INSERT INTO engineering_changes
                (ico_no, part_no, bom_revision, effective_at, status, notes,
                 created_by, item_name, scope_kind, family_prefix)
            VALUES (%s, %s, %s, %s, 'DRAFT', %s, %s, %s, 'FAMILY', %s)
            """,
            (ico_no, representative_part, bom_revision, effective_at, notes,
             created_by, item_name_input or None, family_prefix)
        )
        ico_id = cursor.lastrowid

        scope_values = [(ico_id, pn, family_prefix, bom_revision) for pn in scope_parts]
        cursor.executemany(
            """
            INSERT INTO engineering_change_scope
                (engineering_change_id, part_no, family_prefix, bom_revision)
            VALUES (%s, %s, %s, %s)
            """,
            scope_values
        )

        # Items del ICO: guardamos UN registro por fila del Excel (no replicamos por modelo).
        # El detalle "a qué modelo aplica cada cambio" vive en engineering_change_diff.
        item_values = []
        for row in parsed_rows:
            item_values.append((
                ico_id,
                _ks_process_value(row.get('item_process'), 'MAIN'),
                _ico_legacy_position(row['location_text']),
                row['location_text'],
                row['item_no'],
                row['item_no'],
                row['qty'],
                row['location_text'],
                row['supplier'] or row['maker'],
                '',
                row['item_class'],
                row['spec'],
                row['bom_level'],
                row['item_seq'],
                row['item_name'] or row['item_no'],
                '',
                row['unit'],
                row['maker'],
                row['process_name'] or row['item_process'],
                row['item_process'],
                row['item_class'],
                row['valid_from'],
                row['valid_to'],
                '사용',
                row['is_alternate'],
                row['alt_item_no'],
                row['alt_item_name'],
                row['alt_spec'],
                row['alt_maker'],
                '',
                0,
            ))
        if item_values:
            cursor.executemany(
                """
                INSERT INTO engineering_change_bom_items
                    (engineering_change_id, tipo_material, posicion_assy, location_text, material_code,
                     numero_parte, qty, ubicacion, proveedor, side, classification, spec,
                     bom_level, item_seq, item_name, item_name_en, unit, maker,
                     process_name, item_process, item_class, valid_from, valid_to,
                     status_name, is_alternate, alt_item_no, alt_item_name, alt_spec,
                     alt_maker, child_bom_part_no, is_sub_bom)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                item_values
            )

        diff_rows = []
        for d in diff_added:
            diff_rows.append((ico_id, d['part_no'], 'ADD', d['row']['item_no'], d['row']['bom_level'], None, None, None, None))
        for d in diff_removed:
            diff_rows.append((ico_id, d['part_no'], 'REMOVE', d['item_no'], d['bom_level'], d['row_id'], None, None, None))
        for d in diff_modified:
            for change in d['changes']:
                diff_rows.append((
                    ico_id, d['part_no'], 'MODIFY', d['item_no'], d['bom_level'], d['row_id'],
                    change['field'], change['old'] or None, change['new'] or None,
                ))
        if diff_rows:
            cursor.executemany(
                """
                INSERT INTO engineering_change_diff
                    (engineering_change_id, part_no, action, item_no, bom_level,
                     ks_row_id, field_changed, old_value, new_value)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                diff_rows
            )

        conn.commit()

        # Resumen por modelo
        per_part = {}
        for d in diff_added:
            per_part.setdefault(d['part_no'], {'added': 0, 'modified': 0, 'removed': 0})['added'] += 1
        for d in diff_modified:
            per_part.setdefault(d['part_no'], {'added': 0, 'modified': 0, 'removed': 0})['modified'] += 1
        for d in diff_removed:
            per_part.setdefault(d['part_no'], {'added': 0, 'modified': 0, 'removed': 0})['removed'] += 1

        return {
            "success": True,
            "ico_id": ico_id,
            "scope_kind": "FAMILY",
            "scope_parts": scope_parts,
            "diff": {
                "added": len(diff_added),
                "removed": len(diff_removed),
                "modified": len(diff_modified),
                "modified_fields": sum(len(d['changes']) for d in diff_modified),
                "per_part": per_part,
            },
            "errors": [],
        }
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        print(f"Error creando ICO familia: {e}")
        return {"success": False, "errors": [str(e)]}
    finally:
        try:
            conn.autocommit(True)
        except Exception:
            pass
        cursor.close()
        conn.close()


def importar_items_ico_desde_dataframe(ico_id, df):
    """Reemplazar items de un ICO DRAFT desde Excel."""
    crear_tablas_icos()
    ico = _ico_get_by_id(ico_id)
    if not ico:
        raise ValueError("ICO no encontrado")
    if ico.get('status') != 'DRAFT':
        raise ValueError("Solo se pueden importar items en ICOS DRAFT")

    columnas_disponibles = df.columns.tolist()

    def normalizar_columna(nombre):
        texto = str(nombre or '')
        texto = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode('ascii')
        texto = texto.strip().lower()
        texto = re.sub(r'[^a-z0-9]+', ' ', texto)
        return ' '.join(texto.split())

    columnas_normalizadas = {col: normalizar_columna(col) for col in columnas_disponibles}

    def buscar_columna(variaciones_exactas=None, variaciones_contiene=None):
        variaciones_exactas = variaciones_exactas or []
        variaciones_contiene = variaciones_contiene or []
        for var in variaciones_exactas:
            var_norm = normalizar_columna(var)
            for col, col_norm in columnas_normalizadas.items():
                if col_norm == var_norm:
                    return col
        for var in variaciones_contiene:
            var_norm = normalizar_columna(var)
            for col, col_norm in columnas_normalizadas.items():
                if var_norm and var_norm in col_norm:
                    return col
        return None

    col_numero_parte = buscar_columna(
        ['numero de parte', 'numero_parte', 'part number', 'material'],
        ['numero parte', 'part number']
    )
    col_material = buscar_columna(
        ['codigo de material', 'codigo_material', 'material code'],
        ['codigo material', 'material code']
    )
    col_posicion = buscar_columna(
        ['posicion assy', 'posicion_assy', 'posicion', 'position'],
        ['posicion', 'position']
    )
    col_qty = buscar_columna(['cantidad total', 'cantidad', 'qty'], ['cantidad', 'qty'])
    col_tipo = buscar_columna(['tipo de material', 'tipo_material', 'material type'], ['tipo de material', 'material type'])
    col_ubicacion = buscar_columna(['ubicacion', 'location'], ['ubicacion', 'location'])
    col_proveedor = buscar_columna(['proveedor', 'vendor', 'vender', 'supplier'], ['proveedor', 'vendor', 'supplier'])
    col_side = buscar_columna(['side', 'lado'], ['side', 'lado'])
    col_classification = buscar_columna(['classification', 'clasificacion', 'categoria'], ['classification', 'clasificacion', 'categoria'])
    col_spec = buscar_columna(['especificacion', 'especificacion material', 'description', 'descripcion'], ['especificacion', 'description', 'descripcion'])
    col_bom_level = buscar_columna(['bom_level', 'bom level', 'nivel bom'], ['bom level', 'nivel'])
    col_item_seq = buscar_columna(['item_seq', 'item seq', 'secuencia'], ['item seq', 'secuencia'])
    col_item_name = buscar_columna(['item_name', 'item name', 'nombre item', 'descripcion material'], ['item name', 'nombre item'])
    col_item_name_en = buscar_columna(['item_name_en', 'item name en', 'nombre ingles'], ['name en', 'ingles'])
    col_unit = buscar_columna(['unit', 'unidad'], ['unit', 'unidad'])
    col_maker = buscar_columna(['maker', 'fabricante'], ['maker', 'fabricante'])
    col_process_name = buscar_columna(['process_name', 'process name', 'proceso'], ['process name', 'proceso'])
    col_item_process = buscar_columna(['item_process', 'item process', 'tipo proceso'], ['item process', 'tipo proceso'])
    col_item_class = buscar_columna(['item_class', 'item class', 'classification'], ['item class', 'classification'])
    col_valid_from = buscar_columna(['valid_from', 'valid from', 'fecha efectiva', 'effective date'], ['valid from', 'fecha efectiva', 'effective'])
    col_valid_to = buscar_columna(['valid_to', 'valid to', 'fecha fin'], ['valid to', 'fecha fin'])
    col_status_name = buscar_columna(['status_name', 'status name', 'estado'], ['status name', 'estado'])
    col_is_alternate = buscar_columna(['is_alternate', 'is alternate', 'alterno'], ['is alternate', 'alterno'])
    col_alt_item_no = buscar_columna(['alt_item_no', 'alternate item no', 'material alterno', 'material sustituto'], ['alt item', 'alternate', 'sustituto'])
    col_alt_item_name = buscar_columna(['alt_item_name', 'alternate item name', 'nombre alterno'], ['alt name', 'alterno nombre'])
    col_alt_spec = buscar_columna(['alt_spec', 'alternate spec', 'spec alterno'], ['alt spec', 'spec alterno'])
    col_alt_maker = buscar_columna(['alt_maker', 'alternate maker', 'maker alterno'], ['alt maker', 'maker alterno'])
    col_child_bom_part_no = buscar_columna(['child_bom_part_no', 'child bom part no', 'sub bom'], ['child bom', 'sub bom'])
    col_is_sub_bom = buscar_columna(['is_sub_bom', 'is sub bom'], ['is sub bom'])

    if not col_numero_parte and not col_material:
        raise ValueError("El Excel debe incluir Numero de Parte o Codigo de Material")

    values = []
    omitidos = 0
    for _, row in df.iterrows():
        numero_parte = _ico_normalize_upper(row.get(col_numero_parte) if col_numero_parte else '')
        material = _ico_normalize_upper(row.get(col_material) if col_material else '')
        if not numero_parte and not material:
            omitidos += 1
            continue
        if not material:
            material = numero_parte
        if not numero_parte:
            numero_parte = material
        location_text = _ico_normalize_text(row.get(col_posicion) if col_posicion else '')
        if not location_text:
            location_text = _ico_normalize_text(row.get(col_ubicacion) if col_ubicacion else '')
        item_process = _ks_process_value(
            row.get(col_item_process) if col_item_process else '',
            row.get(col_tipo) if col_tipo else ''
        )
        process_name = _ico_normalize_text(row.get(col_process_name) if col_process_name else item_process)
        values.append((
            ico_id,
            item_process,
            _ico_legacy_position(location_text),
            location_text,
            material,
            numero_parte,
            _ico_parse_qty(row.get(col_qty) if col_qty else 1),
            location_text,
            _ico_normalize_text(row.get(col_proveedor) if col_proveedor else ''),
            _ico_normalize_text(row.get(col_side) if col_side else ''),
            _ico_normalize_text(row.get(col_classification) if col_classification else ''),
            _ico_normalize_text(row.get(col_spec) if col_spec else ''),
            _ico_normalize_text(row.get(col_bom_level) if col_bom_level else ''),
            _ico_normalize_text(row.get(col_item_seq) if col_item_seq else ''),
            _ico_normalize_text(row.get(col_item_name) if col_item_name else ''),
            _ico_normalize_text(row.get(col_item_name_en) if col_item_name_en else ''),
            _ico_normalize_text(row.get(col_unit) if col_unit else 'EA') or 'EA',
            _ico_normalize_text(row.get(col_maker) if col_maker else ''),
            process_name,
            item_process,
            _ico_normalize_text(row.get(col_item_class) if col_item_class else row.get(col_classification) if col_classification else ''),
            _ico_normalize_date(row.get(col_valid_from) if col_valid_from else ico.get('effective_at')),
            _ico_normalize_date(row.get(col_valid_to) if col_valid_to else '') or None,
            _ico_normalize_text(row.get(col_status_name) if col_status_name else '사용') or '사용',
            _ico_parse_bool(row.get(col_is_alternate) if col_is_alternate else 0),
            _ico_normalize_upper(row.get(col_alt_item_no) if col_alt_item_no else ''),
            _ico_normalize_text(row.get(col_alt_item_name) if col_alt_item_name else ''),
            _ico_normalize_text(row.get(col_alt_spec) if col_alt_spec else ''),
            _ico_normalize_text(row.get(col_alt_maker) if col_alt_maker else ''),
            _ico_normalize_upper(row.get(col_child_bom_part_no) if col_child_bom_part_no else ''),
            _ico_parse_bool(row.get(col_is_sub_bom) if col_is_sub_bom else 0),
        ))

    if not values:
        raise ValueError("No se encontraron filas validas para importar")

    conn = get_connection()
    if conn is None:
        raise RuntimeError("No hay conexion MySQL disponible")
    cursor = conn.cursor()
    try:
        try:
            conn.autocommit(False)
        except Exception:
            pass
        cursor.execute("DELETE FROM engineering_change_bom_items WHERE engineering_change_id = %s", (ico_id,))
        cursor.executemany(
            """
            INSERT INTO engineering_change_bom_items
                (engineering_change_id, tipo_material, posicion_assy, location_text, material_code,
                 numero_parte, qty, ubicacion, proveedor, side, classification, spec,
                 bom_level, item_seq, item_name, item_name_en, unit, maker,
                 process_name, item_process, item_class, valid_from, valid_to,
                 status_name, is_alternate, alt_item_no, alt_item_name, alt_spec,
                 alt_maker, child_bom_part_no, is_sub_bom)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            values
        )
        conn.commit()
        return {"insertados": len(values), "omitidos": omitidos}
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            conn.autocommit(True)
        except Exception:
            pass
        cursor.close()
        conn.close()


def validar_ico_para_aprobacion(ico_id):
    """Validar que un ICO DRAFT pueda aprobarse."""
    ico = obtener_ico_detalle(ico_id)
    errors = []
    if not ico:
        return ["ICO no encontrado"]
    if ico.get('status') != 'DRAFT':
        errors.append("Solo se pueden aprobar ICOS DRAFT")
    for field in ('ico_no', 'part_no', 'bom_revision', 'effective_at'):
        if not ico.get(field):
            errors.append(f"Campo requerido faltante: {field}")
    items = ico.get('items') or []
    if not items:
        errors.append("El ICO no tiene items de BOM")
    for idx, item in enumerate(items, start=1):
        material = item.get('material_code') or item.get('numero_parte')
        if not material:
            errors.append(f"Item {idx}: material_code/numero_parte requerido")
        if _ico_parse_qty(item.get('qty'), 0) <= 0:
            errors.append(f"Item {idx}: qty debe ser mayor a 0")
    return errors


def _ico_item_key(item_no, bom_level):
    return f"{_ico_normalize_upper(item_no)}|{_ico_normalize_text(bom_level)}"


def _ico_component_tuple(part_no, bom_rev, item, effective_date, ico, idx):
    item_no = _ico_normalize_upper(item.get('material_code') or item.get('numero_parte') or item.get('item_no'))
    item_process = _ks_process_value(item.get('item_process'), item.get('tipo_material'), item.get('process_name'))
    process_name = _ico_normalize_text(item.get('process_name')) or item_process
    location_text = _ico_normalize_text(item.get('location_text') or item.get('ubicacion') or item.get('posicion_assy'))
    return (
        part_no,
        bom_rev,
        _ico_normalize_text(item.get('bom_level')) or f"01-{idx:02d}",
        _ico_normalize_text(item.get('item_seq')) or str(idx),
        item_no,
        _ico_normalize_text(item.get('item_name')) or item_no,
        _ico_normalize_text(item.get('item_name_en')),
        _ico_normalize_text(item.get('spec')),
        _ico_parse_qty(item.get('qty')),
        _ico_normalize_text(item.get('unit'), 'EA') or 'EA',
        location_text,
        _ico_normalize_text(item.get('maker') or item.get('proveedor') or item.get('supplier')),
        process_name,
        item_process,
        _ico_normalize_text(item.get('proveedor') or item.get('supplier')),
        _ico_normalize_text(item.get('item_class') or item.get('classification')),
        _ico_normalize_date(item.get('valid_from'), effective_date),
        _ico_normalize_date(item.get('valid_to')) or None,
        '사용',
        _ico_parse_bool(item.get('is_alternate')),
        _ico_normalize_upper(item.get('alt_item_no')),
        _ico_normalize_text(item.get('alt_item_name')),
        _ico_normalize_text(item.get('alt_spec')),
        _ico_normalize_text(item.get('alt_maker')),
        _ico_normalize_upper(item.get('child_bom_part_no')),
        _ico_parse_bool(item.get('is_sub_bom')),
        f"ICO {ico.get('ico_no')}",
        _ico_normalize_text(ico.get('notes')),
    )


def _aprobar_ico_familia(ico_id, approved_by, ico):
    """Aprobar un ICO de familia publicando una revision completa por modelo."""
    items = ico.get('items') or []
    effective_date = _ico_normalize_date(ico.get('effective_at'), _ico_plant_date())
    bom_rev = _ico_normalize_upper(ico.get('bom_revision'))
    family_prefix = _ico_normalize_upper(ico.get('family_prefix'))

    scope = obtener_scope_ico(ico_id)
    if not scope:
        return {"success": False, "errors": ["El ICO de familia no tiene scope definido"]}

    # Indexar items del ICO por __row_key = item_no|bom_level
    items_by_key = {}
    for it in items:
        key = _ico_item_key(it.get('material_code') or it.get('numero_parte') or it.get('item_no'), it.get('bom_level'))
        if key.strip('|'):
            items_by_key[key] = it

    # Cargar diff completo agrupado por part_no
    diff_rows = execute_query(
        """
        SELECT part_no, action, item_no, bom_level, ks_row_id,
               field_changed, old_value, new_value
        FROM engineering_change_diff
        WHERE engineering_change_id = %s
        """,
        (int(ico_id),),
        fetch='all'
    ) or []
    diff_by_part = {}
    for r in diff_rows:
        pn = _ico_normalize_upper(r.get('part_no'))
        diff_by_part.setdefault(pn, []).append(r)

    conn = get_connection()
    if conn is None:
        return {"success": False, "errors": ["No hay conexion MySQL disponible"]}
    cursor = conn.cursor()
    try:
        try:
            conn.autocommit(False)
        except Exception:
            pass

        applied_summary = {}
        insert_sql = """
            INSERT INTO ks_bom_components
                (parent_part_no, bom_rev, bom_level, item_seq, item_no,
                 item_name, item_name_en, spec, qty, unit, location_text,
                 maker, process_name, item_process, supplier, item_class,
                 valid_from, valid_to, status_name, is_alternate,
                 alt_item_no, alt_item_name, alt_spec, alt_maker,
                 child_bom_part_no, is_sub_bom, remark, item_remark, synced_at)
            VALUES
                (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                 %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """
        current_by_part = _ks_fetch_bom_items_multi([entry.get('part_no') for entry in scope], None)

        for entry in scope:
            part_no = _ico_normalize_upper(entry.get('part_no'))
            if not part_no:
                continue

            catalog = _ks_part_catalog_lookup(part_no) or {}
            cat_item_name = _ico_normalize_text(catalog.get('item_name')) if catalog else ''
            cat_spec = _ico_normalize_text(catalog.get('spec')) if catalog else ''
            cat_unit = _ico_normalize_text(catalog.get('unit')) if catalog else ''
            cat_family = _ico_normalize_text(catalog.get('family_prefix')) if catalog else ''
            cat_root = _ico_normalize_text(catalog.get('root_part_no')) if catalog else ''
            cat_kind = _ico_normalize_upper(catalog.get('bom_kind')) if catalog else ''
            cat_suffix = _ico_normalize_text(catalog.get('bom_suffix')) if catalog else ''

            target_rows = {}
            for current in current_by_part.get(part_no, []):
                key = _ico_item_key(current.get('item_no'), current.get('bom_level'))
                if key.strip('|'):
                    target_rows[key] = dict(current)

            part_diffs = diff_by_part.get(part_no, [])
            adds = [d for d in part_diffs if d.get('action') == 'ADD']
            removes = [d for d in part_diffs if d.get('action') == 'REMOVE']
            modifies = [d for d in part_diffs if d.get('action') == 'MODIFY']

            for d in removes:
                target_rows.pop(_ico_item_key(d.get('item_no'), d.get('bom_level')), None)

            modify_keys = set()
            for d in modifies:
                new_key = _ico_item_key(d.get('item_no'), d.get('bom_level'))
                old_key = new_key
                if d.get('field_changed') == 'item_no' and d.get('old_value'):
                    old_key = _ico_item_key(d.get('old_value'), d.get('bom_level'))
                if old_key != new_key:
                    target_rows.pop(old_key, None)
                modify_keys.add(new_key)

            for key in modify_keys:
                src = items_by_key.get(key)
                if src:
                    target_rows[key] = dict(src)

            for d in adds:
                key = _ico_item_key(d.get('item_no'), d.get('bom_level'))
                src = items_by_key.get(key)
                if src:
                    target_rows[key] = dict(src)

            cursor.execute(
                "DELETE FROM ks_bom_components WHERE parent_part_no = %s AND bom_rev = %s",
                (part_no, bom_rev)
            )

            ordered_items = sorted(
                target_rows.values(),
                key=lambda row: (
                    _ico_normalize_text(row.get('item_seq')).zfill(12),
                    _ico_normalize_text(row.get('bom_level')),
                    _ico_normalize_upper(row.get('material_code') or row.get('numero_parte') or row.get('item_no')),
                )
            )
            component_values = [
                _ico_component_tuple(part_no, bom_rev, item, effective_date, ico, idx)
                for idx, item in enumerate(ordered_items, start=1)
            ]
            if component_values:
                cursor.executemany(insert_sql, component_values)

            comp_count = len(component_values)
            cursor.execute(
                """
                INSERT INTO ks_bom_headers
                    (part_no, item_seq, item_name, spec, unit, bom_rev, root_part_no,
                     family_prefix, bom_suffix, bom_kind, component_count,
                     source_updated_at, synced_at)
                VALUES (%s, NULL, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                ON DUPLICATE KEY UPDATE
                    item_name = VALUES(item_name),
                    spec = VALUES(spec),
                    unit = VALUES(unit),
                    root_part_no = VALUES(root_part_no),
                    family_prefix = VALUES(family_prefix),
                    bom_suffix = VALUES(bom_suffix),
                    bom_kind = VALUES(bom_kind),
                    component_count = VALUES(component_count),
                    source_updated_at = NOW(),
                    synced_at = NOW()
                """,
                (
                    part_no,
                    cat_item_name or part_no,
                    cat_spec or None,
                    cat_unit or None,
                    bom_rev,
                    cat_root or part_no,
                    cat_family or family_prefix or _ks_family_prefix(part_no),
                    cat_suffix or None,
                    cat_kind or _ks_bom_kind_from_items(items),
                    comp_count,
                )
            )

            applied_summary[part_no] = {
                'added': len(adds),
                'modified': len(modify_keys),
                'removed': len(removes),
                'total_components': comp_count,
            }

        cursor.execute(
            """
            UPDATE engineering_changes
            SET status = 'APPROVED',
                approved_by = %s,
                approved_at = NOW(),
                updated_at = NOW()
            WHERE id = %s AND status = 'DRAFT'
            """,
            (approved_by, ico_id)
        )

        conn.commit()
        return {
            "success": True,
            "errors": [],
            "scope_kind": "FAMILY",
            "applied": applied_summary,
        }
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        print(f"Error aprobando ICO familia {ico_id}: {e}")
        return {"success": False, "errors": [str(e)]}
    finally:
        try:
            conn.autocommit(True)
        except Exception:
            pass
        cursor.close()
        conn.close()


def aprobar_ico(ico_id, approved_by='desconocido'):
    """Aprobar un ICO DRAFT y publicar la revision en tablas KS."""
    errors = validar_ico_para_aprobacion(ico_id)
    if errors:
        return {"success": False, "errors": errors}
    ico = obtener_ico_detalle(ico_id)

    if _ico_normalize_upper(ico.get('scope_kind')) == 'FAMILY':
        return _aprobar_ico_familia(ico_id, approved_by, ico)

    items = ico.get('items') or []
    effective_date = _ico_normalize_date(ico.get('effective_at'), _ico_plant_date())
    part_no = _ico_normalize_upper(ico.get('part_no'))
    bom_rev = _ico_normalize_upper(ico.get('bom_revision'))

    catalog = _ks_part_catalog_lookup(part_no) or {}
    catalog_item_name = _ico_normalize_text(catalog.get('item_name')) if catalog else ''
    catalog_spec = _ico_normalize_text(catalog.get('spec')) if catalog else ''
    catalog_unit = _ico_normalize_text(catalog.get('unit')) if catalog else ''
    catalog_family = _ico_normalize_text(catalog.get('family_prefix')) if catalog else ''
    catalog_root = _ico_normalize_text(catalog.get('root_part_no')) if catalog else ''
    catalog_kind = _ico_normalize_upper(catalog.get('bom_kind')) if catalog else ''
    catalog_suffix = _ico_normalize_text(catalog.get('bom_suffix')) if catalog else ''

    header_item_name = (
        _ico_normalize_text(ico.get('item_name'))
        or catalog_item_name
        or part_no
    )
    header_spec = catalog_spec or None
    header_unit = catalog_unit or None
    header_family = catalog_family or _ks_family_prefix(part_no)
    header_root = catalog_root or part_no
    header_suffix = catalog_suffix or None
    header_bom_kind = catalog_kind or _ks_bom_kind_from_items(items)

    conn = get_connection()
    if conn is None:
        return {"success": False, "errors": ["No hay conexion MySQL disponible"]}

    cursor = conn.cursor()
    try:
        try:
            conn.autocommit(False)
        except Exception:
            pass

        cursor.execute(
            """
            INSERT INTO ks_bom_headers
                (part_no, item_seq, item_name, spec, unit, bom_rev, root_part_no,
                 family_prefix, bom_suffix, bom_kind, component_count,
                 source_updated_at, synced_at)
            VALUES (%s, NULL, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            ON DUPLICATE KEY UPDATE
                item_name = VALUES(item_name),
                spec = VALUES(spec),
                unit = VALUES(unit),
                root_part_no = VALUES(root_part_no),
                family_prefix = VALUES(family_prefix),
                bom_suffix = VALUES(bom_suffix),
                bom_kind = VALUES(bom_kind),
                component_count = VALUES(component_count),
                source_updated_at = NOW(),
                synced_at = NOW()
            """,
            (
                part_no,
                header_item_name,
                header_spec,
                header_unit,
                bom_rev,
                header_root,
                header_family,
                header_suffix,
                header_bom_kind,
                len(items),
            )
        )

        cursor.execute(
            "DELETE FROM ks_bom_components WHERE parent_part_no = %s AND bom_rev = %s",
            (part_no, bom_rev)
        )

        component_values = []
        for idx, item in enumerate(items, start=1):
            item_no = _ico_normalize_upper(item.get('material_code') or item.get('numero_parte'))
            if not item_no:
                continue
            item_process = _ks_process_value(item.get('item_process'), item.get('tipo_material'))
            process_name = _ico_normalize_text(item.get('process_name')) or item_process
            location_text = _ico_normalize_text(item.get('location_text') or item.get('ubicacion') or item.get('posicion_assy'))
            component_values.append((
                part_no,
                bom_rev,
                _ico_normalize_text(item.get('bom_level')) or f"01-{idx:02d}",
                _ico_normalize_text(item.get('item_seq')) or str(idx),
                item_no,
                _ico_normalize_text(item.get('item_name')) or item_no,
                _ico_normalize_text(item.get('item_name_en')),
                _ico_normalize_text(item.get('spec')),
                _ico_parse_qty(item.get('qty')),
                _ico_normalize_text(item.get('unit'), 'EA') or 'EA',
                location_text,
                _ico_normalize_text(item.get('maker') or item.get('proveedor')),
                process_name,
                item_process,
                _ico_normalize_text(item.get('proveedor')),
                _ico_normalize_text(item.get('item_class') or item.get('classification')),
                _ico_normalize_date(item.get('valid_from'), effective_date),
                _ico_normalize_date(item.get('valid_to')) or None,
                '사용',
                _ico_parse_bool(item.get('is_alternate')),
                _ico_normalize_upper(item.get('alt_item_no')),
                _ico_normalize_text(item.get('alt_item_name')),
                _ico_normalize_text(item.get('alt_spec')),
                _ico_normalize_text(item.get('alt_maker')),
                _ico_normalize_upper(item.get('child_bom_part_no')),
                _ico_parse_bool(item.get('is_sub_bom')),
                f"ICO {ico.get('ico_no')}",
                _ico_normalize_text(ico.get('notes')),
            ))

        if component_values:
            cursor.executemany(
                """
                INSERT INTO ks_bom_components
                    (parent_part_no, bom_rev, bom_level, item_seq, item_no,
                     item_name, item_name_en, spec, qty, unit, location_text,
                     maker, process_name, item_process, supplier, item_class,
                     valid_from, valid_to, status_name, is_alternate,
                     alt_item_no, alt_item_name, alt_spec, alt_maker,
                     child_bom_part_no, is_sub_bom, remark, item_remark, synced_at)
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                     %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                """,
                component_values
            )

        ks_family_prefix = _ks_family_prefix(part_no) or None
        ks_hist_seq = ico.get('ks_hist_seq')
        try:
            ks_hist_seq = int(ks_hist_seq) if ks_hist_seq not in (None, '', 0) else None
        except (TypeError, ValueError):
            ks_hist_seq = None

        if ks_hist_seq is None and ks_family_prefix:
            item_numbers = [
                _ico_normalize_upper(item.get('material_code') or item.get('numero_parte'))
                for item in items
            ]
            item_numbers = [x for x in item_numbers if x]
            if item_numbers:
                placeholders = ','.join(['%s'] * len(item_numbers))
                cursor.execute(
                    f"""
                    SELECT hist_seq
                    FROM ks_engineering_changes
                    WHERE family_prefix = %s COLLATE utf8mb4_0900_ai_ci
                      AND UPPER(item_no) IN ({placeholders}) COLLATE utf8mb4_0900_ai_ci
                    ORDER BY sb_date DESC, hist_seq DESC
                    LIMIT 2
                    """,
                    (ks_family_prefix, *item_numbers)
                )
                rows = cursor.fetchall() or []
                if len(rows) == 1:
                    ks_hist_seq = rows[0][0] if isinstance(rows[0], (list, tuple)) else rows[0].get('hist_seq')

        cursor.execute(
            """
            UPDATE engineering_changes
            SET status = 'APPROVED',
                approved_by = %s,
                approved_at = NOW(),
                ks_family_prefix = %s,
                ks_hist_seq = %s,
                updated_at = NOW()
            WHERE id = %s AND status = 'DRAFT'
            """,
            (approved_by, ks_family_prefix, ks_hist_seq, ico_id)
        )

        conn.commit()
        return {"success": True, "errors": [], "published_items": len(component_values)}
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        return {"success": False, "errors": [str(e)]}
    finally:
        try:
            conn.autocommit(True)
        except Exception:
            pass
        cursor.close()
        conn.close()


def cancelar_ico(ico_id, cancelled_by='desconocido'):
    """Cancelar un ICO DRAFT. Los ICOS aprobados son inmutables."""
    ico = _ico_get_by_id(ico_id)
    if not ico:
        return {"success": False, "error": "ICO no encontrado"}
    if ico.get('status') == 'APPROVED':
        return {"success": False, "error": "Un ICO aprobado es inmutable"}
    result = execute_query(
        """
        UPDATE engineering_changes
        SET status = 'CANCELLED',
            notes = CONCAT(COALESCE(notes, ''), %s),
            updated_at = NOW()
        WHERE id = %s AND status = 'DRAFT'
        """,
        (f"\nCancelado por {cancelled_by}", ico_id)
    )
    return {"success": bool(result)}


def eliminar_ico(ico_id):
    """Eliminar fisicamente un ICO que no este aprobado."""
    ico = _ico_get_by_id(ico_id)
    if not ico:
        return {"success": False, "error": "ICO no encontrado"}
    if ico.get('status') == 'APPROVED':
        return {"success": False, "error": "Un ICO aprobado es inmutable; no se puede borrar"}

    execute_query(
        "DELETE FROM engineering_change_bom_items WHERE engineering_change_id = %s",
        (ico_id,)
    )
    result = execute_query(
        "DELETE FROM engineering_changes WHERE id = %s AND status <> 'APPROVED'",
        (ico_id,)
    )
    return {"success": bool(result)}

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
            print(f" ERROR: numero_parte vacío o None en data: {data}")
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
        print(f" ERROR DETALLADO guardando material '{data.get('numero_parte', 'UNKNOWN')}': {error_msg}")
        
        # Errores específicos de MySQL
        if "1062" in error_msg:
            print(f" Error de duplicado - numero_parte ya existe: {data.get('numero_parte')}")
        elif "1406" in error_msg:
            print(f" Error de longitud de campo - datos demasiado largos")
        elif "1364" in error_msg:
            print(f" Error de campo requerido - falta valor para campo NOT NULL")
        elif "1054" in error_msg:
            print(f" Error de columna desconocida - verifica estructura de tabla")
        else:
            print(f" Error MySQL genérico: {error_msg}")
            
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
            print(" No hay campos para actualizar")
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
        print(f" Error actualizando material completo {codigo_original}: {error_msg}")
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
            print(" Pandas no disponible para importar Excel")
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
        
        print(f" Procesando {len(df)} filas del Excel...")
        print(f" Columnas disponibles en Excel: {list(df.columns)}")
        
        for index, row in df.iterrows():
            try:
                fila_numero = index + 1
                print(f"\n === PROCESANDO FILA {fila_numero} ===")
                
                # Mapear datos desde Excel
                data = {}
                
                for excel_col, db_col in column_mapping.items():
                    if excel_col in row:
                        value = str(row[excel_col]).strip() if pd.notna(row[excel_col]) else ''
                        data[db_col] = value
                        print(f" {db_col}: '{value[:50]}{'...' if len(value) > 50 else ''}'")
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
                print(f" Intentando guardar material fila {fila_numero} - Usuario: {usuario_importacion}...")
                if guardar_material(data, usuario_registro=usuario_importacion):
                    insertados += 1
                    print(f" Fila {fila_numero} guardada exitosamente por {usuario_importacion}")
                    if insertados % 100 == 0:  # Log cada 100 insertados
                        print(f" Procesados {insertados} materiales por {usuario_importacion}...")
                else:
                    error_msg = f"Fila {fila_numero}: Error al guardar en base de datos"
                    print(f" {error_msg}")
                    errores_detallados.append(error_msg)
                    omitidos += 1
                    
            except Exception as e:
                fila_numero = index + 1
                error_msg = f"Fila {fila_numero}: {str(e)}"
                print(f" Error procesando fila {fila_numero}: {e}")
                errores_detallados.append(error_msg)
                omitidos += 1
                continue
        
        print(f"\n Importación completada por {usuario_importacion}: {insertados} insertados, {omitidos} omitidos")
        if errores_detallados:
            print(f" Errores detallados:")
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
        print(f" Error importando materiales desde Excel: {e}")
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
    """Obtener BOM por modelo desde la vista canonica KS/ICOS."""
    return listar_bom_por_modelo(modelo)

def guardar_bom_item(data):
    """La edicion directa de bom quedo deshabilitada; usar Crear ICO."""
    print("guardar_bom_item bloqueado: use Crear ICO para publicar en KS")
    return False

def obtener_modelos_bom():
    """Obtener lista de modelos en BOM"""
    try:
        plant_date = _ico_plant_date()
        query = """
            SELECT DISTINCT bom_part_no AS modelo
            FROM v_icos_bom_current
            WHERE (status_name IS NULL OR status_name = '' OR status_name = '사용')
              AND (valid_from IS NULL OR valid_from <= %s)
              AND (valid_to IS NULL OR valid_to >= %s)
            ORDER BY bom_part_no
        """
        result = execute_query(query, (plant_date, plant_date), fetch='all') or []
        return [{'modelo': row['modelo']} for row in result]
    except Exception as e:
        print(f"Error obteniendo modelos BOM desde v_icos_bom_current: {e}")
        return []


def _map_ks_bom_row(row):
    process_value = _ks_process_value(row.get('item_process'), row.get('process_name'))
    supplier = row.get('supplier') or row.get('maker')
    return {
        'id': row.get('id') or row.get('item_seq'),
        'modelo': row.get('bom_part_no'),
        'codigoMaterial': row.get('item_no'),
        'numeroParte': row.get('item_no'),
        'side': '',
        'tipoMaterial': process_value,
        'classification': row.get('item_class'),
        'especificacionMaterial': row.get('spec'),
        'vender': supplier,
        'cantidadTotal': row.get('qty'),
        'cantidadOriginal': row.get('qty'),
        'ubicacion': row.get('location_text'),
        'posicionAssy': row.get('location_text'),
        'materialSustituto': row.get('alt_item_no'),
        'materialOriginal': None,
        'registrador': 'KS',
        'fechaRegistro': row.get('component_synced_at') or row.get('header_synced_at'),
        'bomRevision': row.get('bom_rev'),
    }


def listar_bom_por_modelo(modelo, classification=None):
    """Listar BOM desde v_icos_bom_current con shape legacy para la pantalla."""
    try:
        plant_date = _ico_plant_date()
        where = [
            "(status_name IS NULL OR status_name = '' OR status_name = '사용')",
            "(valid_from IS NULL OR valid_from <= %s)",
            "(valid_to IS NULL OR valid_to >= %s)",
        ]
        params = [plant_date, plant_date]

        if modelo and modelo != 'todos':
            where.append("UPPER(bom_part_no) = UPPER(%s)")
            params.append(modelo)
            latest = execute_query(
                """
                SELECT bom_rev
                FROM v_icos_bom_current
                WHERE UPPER(bom_part_no) = UPPER(%s)
                  AND (status_name IS NULL OR status_name = '' OR status_name = '사용')
                  AND (valid_from IS NULL OR valid_from <= %s)
                  AND (valid_to IS NULL OR valid_to >= %s)
                GROUP BY bom_rev
                ORDER BY MAX(header_synced_at) DESC, bom_rev DESC
                LIMIT 1
                """,
                (modelo, plant_date, plant_date),
                fetch='one'
            )
            if latest and latest.get('bom_rev'):
                where.append("UPPER(bom_rev) = UPPER(%s)")
                params.append(latest.get('bom_rev'))

        if classification and classification != 'TODOS':
            where.append("""
                (
                    UPPER(COALESCE(NULLIF(item_process, ''), NULLIF(process_name, ''), 'MAIN')) = UPPER(%s)
                    OR UPPER(COALESCE(item_class, '')) = UPPER(%s)
                )
            """)
            params.extend([classification, classification])

        query = f"""
            SELECT *
            FROM v_icos_bom_current
            WHERE {' AND '.join(where)}
            ORDER BY bom_part_no, header_synced_at DESC, bom_rev DESC, item_seq, item_no
        """
        result = execute_query(query, tuple(params), fetch='all') or []
        print(f" Query BOM KS: modelo={modelo}, classification={classification}, resultados={len(result)}")
        return [_map_ks_bom_row(row) for row in result]
    except Exception as e:
        print(f"Error listando BOM por modelo: {e}")
        return []

def insertar_bom_desde_dataframe(df, registrador):
    """La importacion directa a bom esta deshabilitada; usar importacion dentro de un ICO."""
    raise ValueError("La tabla legacy bom esta obsoleta. Use Control BOM -> Crear ICO -> Importar Excel y aprobar.")
    import time
    start_time = time.time()
    
    try:
        cols = _get_bom_columns()
        
        insertados = 0
        omitidos = 0
        
        # Crear un mapeo flexible de columnas
        columnas_disponibles = df.columns.tolist()
        print(f"DEBUG: Columnas en el DataFrame: {columnas_disponibles}")
        
        # Función auxiliar para buscar columna por variaciones de forma no ambigua
        def normalizar_columna(nombre):
            texto = str(nombre or '')
            texto = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode('ascii')
            texto = texto.strip().lower()
            texto = re.sub(r'[^a-z0-9]+', ' ', texto)
            return ' '.join(texto.split())

        columnas_normalizadas = {col: normalizar_columna(col) for col in columnas_disponibles}

        def buscar_columna(variaciones_exactas=None, variaciones_contiene=None, excluir=None):
            variaciones_exactas = variaciones_exactas or []
            variaciones_contiene = variaciones_contiene or []
            excluir = set(excluir or [])

            # 1) Priorizar match exacto normalizado (evita confundir "Tipo" con "Tipo de material")
            for var in variaciones_exactas:
                var_norm = normalizar_columna(var)
                for col, col_norm in columnas_normalizadas.items():
                    if col in excluir:
                        continue
                    if col_norm == var_norm:
                        return col

            # 2) Fallback por coincidencia parcial
            for var in variaciones_contiene:
                var_norm = normalizar_columna(var)
                for col, col_norm in columnas_normalizadas.items():
                    if col in excluir:
                        continue
                    if var_norm and var_norm in col_norm:
                        return col
            return None

        # Mapear las columnas principales
        col_modelo = buscar_columna(
            variaciones_exactas=['modelo'],
            variaciones_contiene=['modelo']
        )
        col_numero_parte = buscar_columna(
            variaciones_exactas=['numero de parte', 'número de parte', 'numero_parte', 'n de parte', 'part number'],
            variaciones_contiene=['numero parte', 'part number']
        )
        col_codigo_material = buscar_columna(
            variaciones_exactas=['codigo de material', 'código de material', 'codigo_material', 'material code'],
            variaciones_contiene=['codigo material', 'material code']
        )
        col_side = buscar_columna(
            variaciones_exactas=['side', 'lado'],
            variaciones_contiene=['side', 'lado']
        )
        col_tipo_material = buscar_columna(
            variaciones_exactas=['tipo de material', 'tipo_material', 'material type', 'smd/imd/main', 'smd imd main'],
            variaciones_contiene=['tipo de material', 'material type', 'smd imd main']
        )
        col_ubicacion = buscar_columna(
            variaciones_exactas=['ubicacion', 'ubicación', 'location'],
            variaciones_contiene=['ubicacion', 'location']
        )
        col_classification = buscar_columna(
            variaciones_exactas=['classification', 'clasificacion', 'clasificación', 'categoria', 'categoría', 'class'],
            variaciones_contiene=['classification', 'clasificacion', 'categoria'],
            excluir={col_tipo_material} if col_tipo_material else None
        )
        col_proveedor = buscar_columna(
            variaciones_exactas=['proveedor', 'vendor', 'vender', 'supplier'],
            variaciones_contiene=['proveedor', 'vendor', 'vender', 'supplier']
        )
        col_cantidad = buscar_columna(
            variaciones_exactas=['cantidad', 'quantity', 'qty'],
            variaciones_contiene=['cantidad', 'quantity', 'qty']
        )
        col_cantidad_total = buscar_columna(
            variaciones_exactas=['cantidad total', 'cantidad_total', 'total quantity'],
            variaciones_contiene=['cantidad total', 'total quantity']
        )
        col_cantidad_original = buscar_columna(
            variaciones_exactas=['cantidad original', 'cantidad_original', 'original quantity'],
            variaciones_contiene=['cantidad original', 'original quantity']
        )
        col_descripcion = buscar_columna(
            variaciones_exactas=['descripcion', 'descripción', 'description', 'especificacion', 'especificación'],
            variaciones_contiene=['descripcion', 'description', 'especificacion']
        )
        col_material_original = buscar_columna(
            variaciones_exactas=['material original', 'material_original', 'original material'],
            variaciones_contiene=['material original', 'original material']
        )
        col_material_sustituto = buscar_columna(
            variaciones_exactas=['material sustituto', 'material_sustituto', 'substitute material'],
            variaciones_contiene=['material sustituto', 'substitute material']
        )

        print(
            "DEBUG: Mapeo columnas BOM -> "
            f"modelo={col_modelo}, numero_parte={col_numero_parte}, "
            f"tipo_material={col_tipo_material}, classification={col_classification}"
        )
        
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
                
                # Preparar codigo_material: si no viene en Excel, usar numero_parte
                codigo_material = str(row.get(col_codigo_material, '') if col_codigo_material else '').strip()
                if not codigo_material:
                    codigo_material = numero_parte

                # Preparar fila para inserción masiva
                fila_datos = (
                    modelo,
                    numero_parte,
                    codigo_material,
                    str(row.get(col_side, '') if col_side else '').strip(),
                    str(row.get(col_tipo_material, '') if col_tipo_material else '').strip(),
                    str(row.get(col_ubicacion, '') if col_ubicacion else '').strip(),
                    str(row.get(col_classification, '') if col_classification else '').strip(),
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
        total_insertados = 0
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
            
            print(f"DEBUG:  Inserción masiva completada - {total_insertados} filas procesadas")
        
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
            print(f" ERROR: No se puede procesar salida sin especificar proceso destino")
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
        print(f" Debug especificación:")
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
        
        print(f" Debug query completa:")
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
                print(f" Verificación inmediata - Especificación en BD: '{actual_spec}'")
                if actual_spec != especificacion_final:
                    print(f"⚠️ PROBLEMA: Se envió '{especificacion_final}' pero se guardó '{actual_spec}'")
        
        if result > 0:
            print(f" Salida registrada exitosamente - Proceso: {proceso_salida}")
            
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
            print(f" Error al registrar salida")
            return {'success': False, 'error': 'Error al insertar en base de datos'}
            
    except Exception as e:
        print(f" Error en registrar_salida_material_mysql: {e}")
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
            print(f" Rollo encontrado en {tabla_inventario} - No se descuenta cantidad aquí")
            
            # Registrar movimiento de traslado a proceso específico
            registrar_movimiento_historico_especifico(tabla_inventario, rollo_encontrado['id'], 
                                                    cantidad_salida, proceso_salida, 'TRASLADO_A_PROCESO')
            return True
        else:
            print(f"⚠️ No se encontró rollo activo con código {codigo_material} en {tabla_inventario}")
            # Crear entrada nueva con la cantidad completa disponible
            return crear_entrada_inventario_especifico(tabla_inventario, numero_parte, codigo_material, cantidad_salida)
            
    except Exception as e:
        print(f" Error en actualizar_inventario_especifico_salida: {e}")
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
            
            print(f" Entrada creada en {tabla_inventario} - Cantidad disponible: {cantidad_actual}")
            return True
        else:
            print(f" No se pudo obtener información del material {codigo_material}")
            return False
            
    except Exception as e:
        print(f" Error creando entrada en inventario específico: {e}")
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
        print(f" Error en migración: {e}")
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
        
        # Agregar columnas que no existen (usa IF NOT EXISTS o captura error 1060)
        for col_name, col_definition in nuevas_columnas:
            try:
                alter_query = f"ALTER TABLE materiales ADD COLUMN {col_name} {col_definition}"
                execute_query(alter_query)
                print(f" Columna {col_name} agregada")
            except Exception as e:
                if "1060" in str(e):  # Duplicate column name
                    print(f" Columna {col_name} ya existe")
                else:
                    print(f" Error agregando columna {col_name}: {e}")
        
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
        print(f" Error en migración de tabla materiales: {e}")
        return False

def migrar_tabla_bom():
    """Migrar tabla bom para agregar columna posicion_assy"""
    print(" Migrando tabla bom para agregar columna posicion_assy...")
    
    try:
        # Agregar columna posicion_assy si no existe (captura error 1060 si ya existe)
        try:
            alter_query = "ALTER TABLE bom ADD COLUMN posicion_assy VARCHAR(255) AFTER ubicacion"
            execute_query(alter_query)
            print(" Columna posicion_assy agregada a tabla bom")
        except Exception as e:
            if "1060" in str(e):
                print(" Columna posicion_assy ya existe en tabla bom")
            else:
                print(f" Error agregando columna posicion_assy: {e}")
        
        print(" Migración de tabla bom completada")
        return True
        
    except Exception as e:
        print(f" Error en migración de tabla bom: {e}")
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
    print(" === ANÁLISIS DE FILAS PROBLEMÁTICAS ===")
    
    try:
        # Patrones comunes de filas problemáticas
        filas_problematicas = [6, 7, 28, 253]
        
        print(f" Filas reportadas como problemáticas: {filas_problematicas}")
        print(" Posibles causas comunes:")
        print("  1. Datos demasiado largos para los campos")
        print("  2. Caracteres especiales o encoding incorrecto")
        print("  3. Números de parte duplicados")
        print("  4. Campos requeridos vacíos o NULL")
        print("  5. Formato de fecha incorrecto")
        print("  6. Problemas de encoding UTF-8")
        
        # Verificar duplicados comunes
        print("\n Verificando duplicados en la tabla...")
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
        print("\n Verificando registros con campos muy largos...")
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
        print("\n Verificando caracteres especiales problemáticos...")
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
        print(f" Error analizando filas problemáticas: {e}")
        return False

def diagnosticar_problemas_importacion():
    """Diagnosticar problemas comunes en la importación de materiales"""
    print("\n === DIAGNÓSTICO DE PROBLEMAS DE IMPORTACIÓN ===")
    
    try:
        # 1. Verificar conexión a MySQL
        if not test_connection():
            print(" PROBLEMA: No hay conexión a MySQL")
            return False
        else:
            print(" Conexión MySQL OK")
        
        # 2. Verificar que existe la tabla materiales
        check_table = "SHOW TABLES LIKE 'materiales'"
        table_exists = execute_query(check_table, fetch='one')
        if not table_exists:
            print(" PROBLEMA: Tabla 'materiales' no existe")
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
        print(f"\n Total de materiales en BD: {total_materials}")
        
        # 6. Verificar espacio disponible (estimado)
        size_query = """
            SELECT 
                ROUND(((data_length + index_length) / 1024 / 1024), 2) AS 'DB Size in MB' 
            FROM information_schema.tables 
            WHERE table_schema = DATABASE() AND table_name = 'materiales'
        """
        size_result = execute_query(size_query, fetch='one')
        if size_result:
            print(f" Tamaño de tabla materiales: {size_result['DB Size in MB']} MB")
        
        # 7. Probar inserción de prueba
        print("\n Probando inserción de material de prueba...")
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
            print(" PROBLEMA: Falló la inserción de prueba")
        
        print("\n Diagnóstico completado")
        return True
        
    except Exception as e:
        print(f" Error en diagnóstico: {e}")
        return False

def test_mysql_functions():
    """Probar funciones de MySQL CON DIAGNÓSTICO COMPLETO"""
    print("\n Probando funciones de MySQL...")
    
    try:
        # Probar conexión
        if test_connection():
            print(" Conexión MySQL OK")
        else:
            print(" Error en conexión MySQL")
            return False
        
        # Ejecutar diagnóstico completo
        print("\n Ejecutando diagnóstico completo...")
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
            print(" Error en inicialización MySQL")
        
        print(" Pruebas de MySQL completadas")
        return True
        
    except Exception as e:
        print(f" Error en pruebas MySQL: {e}")
        return False

if __name__ == "__main__":
    test_mysql_functions()

def agregar_columna_usuario_registro():
    """Agregar columna usuario_registro a la tabla materiales si no existe"""
    try:
        execute_query("ALTER TABLE materiales ADD COLUMN usuario_registro VARCHAR(255) DEFAULT 'SISTEMA'")
        print(" Columna usuario_registro agregada exitosamente")
    except Exception as e:
        if "1060" in str(e):
            print(" La columna usuario_registro ya existe")
        else:
            print(f" Error agregando columna usuario_registro: {e}")
            return False

    try:
        execute_query("ALTER TABLE materiales ADD INDEX idx_usuario_registro (usuario_registro)")
    except Exception as e:
        if "1061" not in str(e):
            print(f" Error agregando índice usuario_registro: {e}")

    return True

def get_mysql_connection():
    """Obtener conexión MySQL simple para migraciones"""
    try:
        from .config_mysql import get_mysql_connection as config_get_connection
        return config_get_connection()
        
    except Exception as e:
        print(f"Error conectando a MySQL: {e}")
        return None

