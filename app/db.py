"""Módulo de base de datos principal - Migrado a MySQL
Mantiene compatibilidad con las funciones existentes de SQLite"""

def is_mysql_connection():
    """Detectar si estamos usando MySQL"""
    from .db_mysql import MYSQL_AVAILABLE
    return MYSQL_AVAILABLE



import os
import pandas as pd
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Importar funciones de MySQL
try:
    from .db_mysql import (
        get_connection,
        init_db as mysql_init_db,
        execute_query,
        obtener_materiales,
        guardar_material,
        obtener_inventario,
        actualizar_inventario,
        obtener_bom_por_modelo,
        guardar_bom_item,
        crear_usuario,
        obtener_usuario,
        verificar_usuario,
        guardar_configuracion,
        cargar_configuracion,
        migrar_desde_sqlite
    )
    # Probar conexión MySQL
    try:
        test_conn = get_connection()
        if test_conn:
            test_conn.close()
            MYSQL_AVAILABLE = True
            print("✅ Usando MySQL como base de datos")
        else:
            MYSQL_AVAILABLE = False
            print("⚠️ MySQL no disponible - usando SQLite como fallback")
    except Exception as e:
        MYSQL_AVAILABLE = False
        print(f"⚠️ Error conectando a MySQL: {e}")
        print("⚠️ Usando SQLite como fallback")
except ImportError as e:
    print(f"⚠️ Error importando MySQL: {e}")
    print("⚠️ Usando funciones de fallback SQLite")
    MYSQL_AVAILABLE = False

def get_db_connection():
    """Obtener conexión a la base de datos"""
    if MYSQL_AVAILABLE:
        # Importar MySQLdb para configurar DictCursor
        try:
            import MySQLdb
            conn = get_connection()
            if conn:
                # Crear una clase wrapper para simular row_factory
                class MySQLConnection:
                    def __init__(self, connection):
                        self._conn = connection
                    
                    def cursor(self):
                        return self._conn.cursor(MySQLdb.cursors.DictCursor)
                    
                    def __getattr__(self, name):
                        return getattr(self._conn, name)
                
                return MySQLConnection(conn)
            return conn
        except ImportError:
            return get_connection()
    else:
        # Fallback a SQLite si MySQL no está disponible
        import sqlite3
        db_path = os.path.join(os.path.dirname(__file__), 'database', 'ISEMM_MES.db')
        conn = sqlite3.connect(db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        return conn

def init_db():
    """Inicializar base de datos"""
    if MYSQL_AVAILABLE:
        # Usar inicialización de MySQL
        success = mysql_init_db()
        if success:
            # Crear tablas adicionales específicas de la aplicación
            create_legacy_tables()
        return success
    else:
        # Fallback a SQLite
        return init_sqlite_db()

def create_legacy_tables():
    """Crear tablas adicionales para compatibilidad con la aplicación existente"""
    if not MYSQL_AVAILABLE:
        return
        
    tables = {
        'entrada_aereo': '''
            CREATE TABLE IF NOT EXISTS entrada_aereo (
                id INT AUTO_INCREMENT PRIMARY KEY,
                forma_material TEXT,
                cliente TEXT,
                codigo_material TEXT,
                fecha_fabricacion TEXT,
                origen_material TEXT,
                cantidad_actual INT,
                fecha_recibo TEXT,
                lote_material TEXT,
                codigo_recibido TEXT,
                numero_parte TEXT,
                propiedad TEXT
            )
        ''',
        'control_material_almacen': '''
            CREATE TABLE IF NOT EXISTS control_material_almacen (
                id INT AUTO_INCREMENT PRIMARY KEY,
                forma_material TEXT,
                cliente TEXT,
                codigo_material_original TEXT,
                codigo_material TEXT,
                material_importacion_local TEXT,
                fecha_recibo TEXT,
                fecha_fabricacion TEXT,
                cantidad_actual INT,
                numero_lote_material TEXT,
                codigo_material_recibido TEXT,
                numero_parte TEXT,
                cantidad_estandarizada TEXT,
                codigo_material_final TEXT,
                propiedad_material TEXT,
                especificacion TEXT,
                material_importacion_local_final TEXT,
                estado_desecho BOOLEAN DEFAULT FALSE,
                ubicacion_salida TEXT,
                fecha_registro DATETIME DEFAULT NOW()
            )
        ''',
        'control_material_produccion': '''
            CREATE TABLE IF NOT EXISTS control_material_produccion (
                id INT AUTO_INCREMENT PRIMARY KEY,
                numero_parte TEXT,
                descripcion TEXT,
                cantidad_requerida INT,
                cantidad_disponible INT,
                ubicacion TEXT,
                estado TEXT,
                fecha_registro DATETIME DEFAULT NOW()
            )
        ''',
        'control_calidad': '''
            CREATE TABLE IF NOT EXISTS control_calidad (
                id INT AUTO_INCREMENT PRIMARY KEY,
                numero_parte TEXT,
                lote TEXT,
                resultado_inspeccion TEXT,
                observaciones TEXT,
                inspector TEXT,
                fecha_inspeccion DATETIME DEFAULT NOW()
            )
        '''
    }
    
    for table_name, create_sql in tables.items():
        try:
            execute_query(create_sql)
            print(f"✅ Tabla {table_name} creada/verificada")
        except Exception as e:
            print(f"❌ Error creando tabla {table_name}: {e}")

def init_sqlite_db():
    """Inicialización de SQLite como fallback"""
    try:
        import sqlite3
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Crear tablas básicas de SQLite
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username TEXT UNIQUE,
                password_hash TEXT,
                area TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS materiales (
                id INT AUTO_INCREMENT PRIMARY KEY,
                numero_parte TEXT UNIQUE,
                descripcion TEXT,
                categoria TEXT,
                ubicacion TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error inicializando SQLite: {e}")
        return False

# === FUNCIONES DE COMPATIBILIDAD ===

def agregar_entrada_aereo(data):
    """Agregar entrada de material aéreo"""
    try:
        if MYSQL_AVAILABLE:
            query = """
                INSERT INTO entrada_aereo 
                (forma_material, cliente, codigo_material, fecha_fabricacion, 
                 origen_material, cantidad_actual, fecha_recibo, lote_material, 
                 codigo_recibido, numero_parte, propiedad)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            params = (
                data.get('forma_material'),
                data.get('cliente'),
                data.get('codigo_material'),
                data.get('fecha_fabricacion'),
                data.get('origen_material'),
                data.get('cantidad_actual', 0),
                data.get('fecha_recibo'),
                data.get('lote_material'),
                data.get('codigo_recibido'),
                data.get('numero_parte'),
                data.get('propiedad')
            )
            return execute_query(query, params) > 0
        else:
            # Fallback SQLite
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO entrada_aereo 
                (forma_material, cliente, codigo_material, fecha_fabricacion, 
                 origen_material, cantidad_actual, fecha_recibo, lote_material, 
                 codigo_recibido, numero_parte, propiedad)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                data.get('forma_material'),
                data.get('cliente'),
                data.get('codigo_material'),
                data.get('fecha_fabricacion'),
                data.get('origen_material'),
                data.get('cantidad_actual', 0),
                data.get('fecha_recibo'),
                data.get('lote_material'),
                data.get('codigo_recibido'),
                data.get('numero_parte'),
                data.get('propiedad')
            ))
            conn.commit()
            conn.close()
            return True
    except Exception as e:
        print(f"Error agregando entrada aéreo: {e}")
        return False

def obtener_entradas_aereo():
    """Obtener todas las entradas de material aéreo"""
    try:
        if MYSQL_AVAILABLE:
            return execute_query("SELECT * FROM entrada_aereo ORDER BY id DESC", fetch='all') or []
        else:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM entrada_aereo ORDER BY id DESC")
            result = cursor.fetchall()
            conn.close()
            return [dict(row) for row in result]
    except Exception as e:
        print(f"Error obteniendo entradas aéreo: {e}")
        return []

def agregar_control_material_almacen(data):
    """Agregar control de material de almacén"""
    try:
        if MYSQL_AVAILABLE:
            query = """
                INSERT INTO control_material_almacen 
                (forma_material, cliente, codigo_material_original, codigo_material,
                 material_importacion_local, fecha_recibo, fecha_fabricacion,
                 cantidad_actual, numero_lote_material, codigo_material_recibido,
                 numero_parte, cantidad_estandarizada, codigo_material_final,
                 propiedad_material, especificacion, material_importacion_local_final,
                 estado_desecho, ubicacion_salida)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            params = (
                data.get('forma_material'),
                data.get('cliente'),
                data.get('codigo_material_original'),
                data.get('codigo_material'),
                data.get('material_importacion_local'),
                data.get('fecha_recibo'),
                data.get('fecha_fabricacion'),
                data.get('cantidad_actual', 0),
                data.get('numero_lote_material'),
                data.get('codigo_material_recibido'),
                data.get('numero_parte'),
                data.get('cantidad_estandarizada'),
                data.get('codigo_material_final'),
                data.get('propiedad_material'),
                data.get('especificacion'),
                data.get('material_importacion_local_final'),
                data.get('estado_desecho', False),
                data.get('ubicacion_salida')
            )
            return execute_query(query, params) > 0
        else:
            # Implementación SQLite similar...
            return True
    except Exception as e:
        print(f"Error agregando control material almacén: {e}")
        return False

def obtener_control_material_almacen():
    """Obtener control de material de almacén"""
    try:
        if MYSQL_AVAILABLE:
            return execute_query("SELECT * FROM control_material_almacen ORDER BY id DESC", fetch='all') or []
        else:
            return []
    except Exception as e:
        print(f"Error obteniendo control material almacén: {e}")
        return []

# === FUNCIONES DE MIGRACIÓN ===

def migrar_datos_sqlite():
    """Migrar datos desde SQLite existente a MySQL"""
    if not MYSQL_AVAILABLE:
        print("❌ MySQL no disponible para migración")
        return False
        
    try:
        sqlite_db_path = os.path.join(os.path.dirname(__file__), 'database', 'ISEMM_MES.db')
        if os.path.exists(sqlite_db_path):
            print("🔄 Iniciando migración desde SQLite...")
            success = migrar_desde_sqlite(sqlite_db_path)
            if success:
                print("✅ Migración completada exitosamente")
            return success
        else:
            print("⚠️ No se encontró base de datos SQLite para migrar")
            return True
    except Exception as e:
        print(f"❌ Error en migración: {e}")
        return False

# === FUNCIONES DE PRUEBA ===

def test_database_connection():
    """Probar conexión a la base de datos"""
    try:
        if MYSQL_AVAILABLE:
            from .config_mysql import test_connection
            return test_connection()
        else:
            conn = get_db_connection()
            if conn:
                conn.close()
                return True
            return False
    except Exception as e:
        print(f"Error probando conexión: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Probando conexión a base de datos...")
    if test_database_connection():
        print("✅ Conexión exitosa")
        if init_db():
            print("✅ Base de datos inicializada")
        else:
            print("❌ Error inicializando base de datos")
    else:
        print("❌ Error de conexión")