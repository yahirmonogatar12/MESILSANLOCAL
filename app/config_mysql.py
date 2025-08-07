"""Configuración de conexión a MySQL para el hosting
Adaptado para usar las credenciales proporcionadas por el hosting"""

import os
from contextlib import contextmanager
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()
try:
    import pymysql
    pymysql.install_as_MySQLdb()
    import MySQLdb
    MYSQL_AVAILABLE = True
    print("✅ pymysql disponible para config_mysql")
except ImportError:
    MYSQL_AVAILABLE = False
    print("⚠️ pymysql no disponible para config_mysql - usando modo fallback")

def get_mysql_connection_string():
    """Construir cadena de conexión para MySQL"""
    if not MYSQL_AVAILABLE:
        print("⚠️ MySQL no disponible - retornando None")
        return None
        
    host = os.getenv('MYSQL_HOST', 'localhost')
    port = int(os.getenv('MYSQL_PORT', '3306'))
    database = os.getenv('MYSQL_DATABASE', '')
    username = os.getenv('MYSQL_USERNAME', '')
    password = os.getenv('MYSQL_PASSWORD', '')
    
    return {
        'host': host,
        'port': port,
        'user': username,
        'passwd': password,
        'db': database,
        'charset': 'utf8mb4',
        'autocommit': True,
        'ssl_disabled': False,
        'connect_timeout': 60,
        'read_timeout': 60,
        'write_timeout': 60
    }

# Configuración global de MySQL
MYSQL_CONFIG = {
    'host': os.getenv('MYSQL_HOST', 'localhost'),
    'port': int(os.getenv('MYSQL_PORT', '3306')),
    'user': os.getenv('MYSQL_USERNAME', ''),
    'passwd': os.getenv('MYSQL_PASSWORD', ''),
    'db': os.getenv('MYSQL_DATABASE', ''),
    'charset': 'utf8mb4',
    'autocommit': True,
    'ssl_disabled': False,
    'connect_timeout': 60,
    'read_timeout': 60,
    'write_timeout': 60
}

def get_mysql_connection():
    """Obtener conexión a MySQL"""
    if not MYSQL_AVAILABLE:
        print("⚠️ MySQL no disponible - retornando None")
        return None
        
    try:
        conn_params = get_mysql_connection_string()
        if conn_params:
            connection = MySQLdb.connect(**conn_params)
            return connection
        return None
    except Exception as e:
        print(f"Error conectando a MySQL: {e}")
        return None

@contextmanager
def get_db_connection():
    """Context manager para conexión a MySQL"""
    if not MYSQL_AVAILABLE:
        print("⚠️ MySQL no disponible - retornando None")
        yield None
        return
        
    connection = None
    try:
        connection = get_mysql_connection()
        yield connection
    except Exception as e:
        print(f"Error en conexión MySQL: {e}")
        if connection:
            connection.rollback()
        yield None
    finally:
        if connection:
            connection.close()

def execute_query(query, params=None, fetch=None):
    """Ejecutar consulta en MySQL"""
    if not MYSQL_AVAILABLE:
        print("⚠️ MySQL no disponible - retornando valores por defecto")
        if fetch == 'one':
            return None
        elif fetch == 'all':
            return []
        else:
            return 0
            
    with get_db_connection() as conn:
        if conn is None:
            print("⚠️ Conexión MySQL no disponible - retornando valores por defecto")
            if fetch == 'one':
                return None
            elif fetch == 'all':
                return []
            else:
                return 0
                
        try:
            cursor = conn.cursor(MySQLdb.cursors.DictCursor)
            
            # Convertir consulta de SQLite a MySQL si es necesario
            mysql_query = convert_sqlite_to_mysql(query)
            
            if params:
                cursor.execute(mysql_query, params)
            else:
                cursor.execute(mysql_query)
            
            if fetch == 'one':
                result = cursor.fetchone()
                cursor.close()
                return result
            elif fetch == 'all':
                result = cursor.fetchall()
                cursor.close()
                return result
            else:
                # Para INSERT, UPDATE, DELETE
                affected_rows = cursor.rowcount
                conn.commit()
                cursor.close()
                return affected_rows
                
        except Exception as e:
            print(f"Error ejecutando consulta MySQL: {e}")
            print(f"Consulta: {query}")
            print(f"Parámetros: {params}")
            if fetch == 'one':
                return None
            elif fetch == 'all':
                return []
            else:
                return 0

def convert_sqlite_to_mysql(query):
    """Convertir consultas de SQLite a MySQL"""
    mysql_query = query
    
    # Reemplazar tipos de datos SQLite por MySQL
    mysql_query = mysql_query.replace('INTEGER PRIMARY KEY AUTOINCREMENT', 'INT AUTO_INCREMENT PRIMARY KEY')
    mysql_query = mysql_query.replace('AUTOINCREMENT', 'AUTO_INCREMENT')
    mysql_query = mysql_query.replace('TEXT', 'TEXT')
    mysql_query = mysql_query.replace('REAL', 'DECIMAL(10,2)')
    mysql_query = mysql_query.replace('BLOB', 'LONGBLOB')
    
    # Reemplazar funciones SQLite por MySQL
    mysql_query = mysql_query.replace('datetime(\'now\')', 'NOW()')
    mysql_query = mysql_query.replace('CURRENT_TIMESTAMP', 'NOW()')
    
    # Reemplazar LIMIT con OFFSET por sintaxis MySQL
    if 'LIMIT' in mysql_query and 'OFFSET' in mysql_query:
        # SQLite: LIMIT count OFFSET offset
        # MySQL: LIMIT offset, count
        import re
        pattern = r'LIMIT\s+(\d+)\s+OFFSET\s+(\d+)'
        match = re.search(pattern, mysql_query)
        if match:
            count = match.group(1)
            offset = match.group(2)
            mysql_query = re.sub(pattern, f'LIMIT {offset}, {count}', mysql_query)
    
    return mysql_query

def test_connection():
    """Probar conexión a MySQL"""
    try:
        with get_db_connection() as conn:
            if conn is None:
                return False
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            return True
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Probando conexión a MySQL...")
    if test_connection():
        print("✅ Conexión exitosa")
    else:
        print("❌ Error de conexión")