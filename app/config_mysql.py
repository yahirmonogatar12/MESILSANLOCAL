"""Configuración de conexión a MySQL para el hosting
Adaptado para usar las credenciales proporcionadas por el hosting
Usa connection pooling para evitar 'Too many connections'"""

import logging
import os
import threading
from contextlib import contextmanager
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

logger = logging.getLogger(__name__)

try:
    import pymysql
    pymysql.install_as_MySQLdb()
    import MySQLdb
    import MySQLdb.cursors
    MYSQL_AVAILABLE = True
    logger.debug("pymysql disponible para config_mysql")
except ImportError:
    MYSQL_AVAILABLE = False
    logger.warning("pymysql no disponible para config_mysql - usando modo fallback")

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

# Imprimir config una sola vez al cargar el módulo (sin password).
logger.info(
    "MySQL Config: host=%s port=%s db=%s user=%s",
    MYSQL_CONFIG['host'], MYSQL_CONFIG['port'], MYSQL_CONFIG['db'], MYSQL_CONFIG['user'],
)

# ============ CONNECTION POOL ============
_pool = []
_pool_lock = threading.Lock()
_MAX_POOL_SIZE = max(1, int(os.getenv('MYSQL_POOL_SIZE', '3')))  # Máximo de conexiones reutilizables en el pool


class PooledMySQLConnection:
    """Proxy que devuelve la conexión al pool cuando se llama close()."""

    def __init__(self, connection):
        self._connection = connection
        self._released = False

    def cursor(self, *args, **kwargs):
        if self._connection is None:
            raise RuntimeError("La conexión del pool ya fue liberada")
        return self._connection.cursor(*args, **kwargs)

    def close(self):
        if self._released or self._connection is None:
            return
        connection = self._connection
        self._connection = None
        self._released = True
        _return_to_pool(connection)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is not None:
            try:
                self.rollback()
            except Exception:
                pass
        self.close()

    def __getattr__(self, name):
        if self._connection is None:
            raise RuntimeError("La conexión del pool ya fue liberada")
        return getattr(self._connection, name)

def _create_connection():
    """Crear una nueva conexión MySQL"""
    if not MYSQL_AVAILABLE:
        return None
    try:
        connection = MySQLdb.connect(**MYSQL_CONFIG)
        return connection
    except Exception as e:
        logger.error("Error conectando a MySQL: %s", e)
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


def get_pooled_connection():
    """Obtener una conexión reutilizable; close() la regresa al pool."""
    raw_connection = _get_pooled_connection()
    if raw_connection is None:
        return None
    return PooledMySQLConnection(raw_connection)

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
        logger.error("Error en conexion MySQL: %s", e)
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
    """Ejecutar consulta en MySQL.

    Politica de errores (fail-loud, 2026-05-29):
      - DML / SELECT: si la consulta falla, se loguea con stack y se RE-LANZA.
        Antes se devolvia []/None/0 y el fallo se confundia con "sin
        resultados" / "0 filas afectadas" (perdida silenciosa de datos).
        El errorhandler global en app.routes lo convierte en un 500 visible.
      - DDL (ALTER/CREATE/DROP): conserva el manejo tolerante historico para
        no romper el arranque idempotente: 1060/1061 (columna/clave duplicada)
        se re-lanzan para que el llamador los maneje; otros errores de DDL se
        loguean y se tragan.
      - Sin driver MySQL o sin conexion disponible: se RE-LANZA (RuntimeError)
        en vez de simular un resultado vacio.
    """
    if not MYSQL_AVAILABLE:
        raise RuntimeError(
            "MySQL no disponible (pymysql/MySQLdb no se pudo importar)."
        )

    conn = _get_pooled_connection()
    if conn is None:
        raise RuntimeError("Conexion MySQL no disponible (pool sin conexiones).")

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
        # Devolver conexión al pool antes de propagar.
        try:
            _return_to_pool(conn)
        except Exception:
            pass

        query_upper = query.strip().upper()
        is_ddl = query_upper.startswith(('ALTER ', 'CREATE ', 'DROP '))

        if is_ddl:
            # DDL idempotente: 1060 (Duplicate column) / 1061 (Duplicate key)
            # se re-lanzan para que el llamador los maneje; el resto se traga
            # para no romper el arranque.
            if any(code in error_str for code in ['1060', '1061']):
                raise
            logger.warning("Error (tolerado) ejecutando DDL MySQL: %s", e)
            if fetch == 'one':
                return None
            elif fetch == 'all':
                return []
            else:
                return 0

        # DML / SELECT: fail-loud.
        logger.error("Error ejecutando consulta MySQL: %s", e, exc_info=True)
        raise

def convert_sqlite_to_mysql(query):
    """Pass-through. (Antes hacia conversiones SQLite -> MySQL.)

    Se neutralizo el 2026-05-29. La version anterior aplicaba reemplazos
    de SUBSTRING ciegos (`REAL`->`DECIMAL`, `BLOB`->`LONGBLOB`,
    `CURRENT_TIMESTAMP`->`NOW()`, `AUTOINCREMENT`->...) que podian corromper
    queries cuando esas cadenas aparecian dentro de identificadores o
    literales (p.ej. una columna que contiene "REAL", o el valor
    'CURRENT_TIMESTAMP'). El comentario en cuchillas_corte.py ("sin
    conversion automatica REAL->DECIMAL") evidencia que ya habia causado
    problemas.

    Motivos para eliminar la conversion en vez de "arreglarla":
      - El unico backend es MySQL; ya no se generan queries en sintaxis
        SQLite. Una busqueda en el repo confirma que NINGUN query usa
        AUTOINCREMENT, datetime('now'), ni tipos REAL/BLOB.
      - MySQL soporta de forma nativa `CURRENT_TIMESTAMP` y la sintaxis
        `LIMIT count OFFSET offset`, asi que esas reescrituras eran
        innecesarias.

    Se conserva la funcion (en vez de borrar las llamadas) para no tocar
    `execute_query` y por si en el futuro se quisiera reintroducir una
    conversion ROBUSTA (tokenizando SQL, no con str.replace).
    """
    return query

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
        logger.error("Error de conexion: %s", e)
        return False

if __name__ == "__main__":
    logger.info(" Probando conexión a MySQL...")
    if test_connection():
        logger.info(" Conexión exitosa")
    else:
        logger.error(" Error de conexión")
