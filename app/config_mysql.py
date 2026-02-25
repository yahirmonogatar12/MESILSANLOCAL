"""Configuración de conexión a MySQL para el hosting
Adaptado para usar las credenciales proporcionadas por el hosting
Usa connection pooling para evitar 'Too many connections'"""

import os
import threading
from contextlib import contextmanager
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()
try:
    import pymysql
    pymysql.install_as_MySQLdb()
    import MySQLdb
    import MySQLdb.cursors
    MYSQL_AVAILABLE = True
    print(" pymysql disponible para config_mysql")
except ImportError:
    MYSQL_AVAILABLE = False
    print(" pymysql no disponible para config_mysql - usando modo fallback")

# Configuración global de MySQL
MYSQL_CONFIG = {
    'host': os.getenv('MYSQL_HOST', 'localhost'),
    'port': int(os.getenv('MYSQL_PORT', '3306')),
    'user': os.getenv('MYSQL_USER') or os.getenv('MYSQL_USERNAME', ''),
    'passwd': os.getenv('MYSQL_PASSWORD', ''),
    'db': os.getenv('MYSQL_DATABASE', ''),
    'charset': 'utf8mb4',
    'autocommit': True,
    'ssl_disabled': False,
    'connect_timeout': int(os.getenv('MYSQL_CONNECT_TIMEOUT', '10')),
    'read_timeout': int(os.getenv('MYSQL_READ_TIMEOUT', '10')),
    'write_timeout': int(os.getenv('MYSQL_WRITE_TIMEOUT', '10'))
}

# Imprimir config una sola vez al cargar el módulo
print(f"🔧 MySQL Config: host={MYSQL_CONFIG['host']}, port={MYSQL_CONFIG['port']}, db={MYSQL_CONFIG['db']}, user={MYSQL_CONFIG['user']}")

# ============ CONNECTION POOL ============
_pool = []
_pool_lock = threading.Lock()
_MAX_POOL_SIZE = max(1, int(os.getenv('MYSQL_POOL_SIZE', '3')))  # Máximo de conexiones reutilizables en el pool

def _create_connection():
    """Crear una nueva conexión MySQL"""
    if not MYSQL_AVAILABLE:
        return None
    try:
        connection = MySQLdb.connect(**MYSQL_CONFIG)
        return connection
    except Exception as e:
        print(f"Error conectando a MySQL: {e}")
        return None

def _get_pooled_connection():
    """Obtener conexión del pool o crear una nueva"""
    with _pool_lock:
        # Intentar reutilizar una conexión del pool
        while _pool:
            conn = _pool.pop()
            try:
                conn.ping(True)  # Verificar que sigue viva, reconectar si no
                return conn
            except Exception:
                # Conexión muerta, descartarla
                try:
                    conn.close()
                except Exception:
                    pass
    # No hay conexiones disponibles en el pool, crear una nueva
    return _create_connection()

def _return_to_pool(conn):
    """Devolver conexión al pool para reutilizarla"""
    if conn is None:
        return
    with _pool_lock:
        if len(_pool) < _MAX_POOL_SIZE:
            try:
                conn.ping(True)
                _pool.append(conn)
                return
            except Exception:
                pass
    # Pool lleno o conexión muerta, cerrarla
    try:
        conn.close()
    except Exception:
        pass

def get_mysql_connection_string():
    """Construir cadena de conexión para MySQL"""
    if not MYSQL_AVAILABLE:
        return None
    return dict(MYSQL_CONFIG)

def get_mysql_connection():
    """Obtener conexión a MySQL (nueva, no del pool)"""
    return _create_connection()

@contextmanager
def get_db_connection():
    """Context manager para conexión a MySQL (usa pool)"""
    if not MYSQL_AVAILABLE:
        yield None
        return

    connection = None
    try:
        connection = _get_pooled_connection()
        yield connection
    except Exception as e:
        print(f"Error en conexión MySQL: {e}")
        if connection:
            try:
                connection.rollback()
            except Exception:
                pass
            # Conexión con error, no devolverla al pool
            try:
                connection.close()
            except Exception:
                pass
            connection = None
        yield None
    finally:
        if connection:
            _return_to_pool(connection)

def execute_query(query, params=None, fetch=None):
    """Ejecutar consulta en MySQL"""
    if not MYSQL_AVAILABLE:
        if fetch == 'one':
            return None
        elif fetch == 'all':
            return []
        else:
            return 0

    conn = _get_pooled_connection()
    if conn is None:
        print(" Conexión MySQL no disponible - retornando valores por defecto")
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
            _return_to_pool(conn)
            return result
        elif fetch == 'all':
            result = cursor.fetchall()
            cursor.close()
            _return_to_pool(conn)
            return result
        else:
            # Para INSERT, UPDATE, DELETE
            affected_rows = cursor.rowcount
            conn.commit()
            cursor.close()
            _return_to_pool(conn)
            return affected_rows

    except Exception as e:
        error_str = str(e)
        # Devolver conexión al pool antes de hacer raise
        try:
            _return_to_pool(conn)
        except Exception:
            pass
        # Para DDL (ALTER/CREATE/DROP), re-lanzar errores esperados como 1060 (Duplicate column)
        # y 1061 (Duplicate key name) para que el código que llama pueda manejarlos
        query_upper = query.strip().upper()
        if query_upper.startswith(('ALTER ', 'CREATE ', 'DROP ')):
            if any(code in error_str for code in ['1060', '1061']):
                raise
        print(f"Error ejecutando consulta MySQL: {e}")
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
            cursor.fetchone()
            return True
    except Exception as e:
        print(f" Error de conexión: {e}")
        return False

if __name__ == "__main__":
    print(" Probando conexión a MySQL...")
    if test_connection():
        print(" Conexión exitosa")
    else:
        print(" Error de conexión")
