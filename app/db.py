"""Módulo de base de datos principal (solo MySQL).

Fachada de compatibilidad sobre db_mysql + config_mysql, heredada de la
migracion SQLite -> MySQL. El fallback a SQLite se elimino el 2026-05-29
(la app es MySQL-only); aqui solo quedan helpers de conexion/init."""

def is_mysql_connection():
    """Detectar si estamos usando MySQL"""
    from .db_mysql import MYSQL_AVAILABLE
    return MYSQL_AVAILABLE



from dotenv import load_dotenv

import logging
logger = logging.getLogger(__name__)

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
        crear_usuario,
        obtener_usuario,
        verificar_usuario,
        guardar_configuracion,
        cargar_configuracion,
    )
    from .api.informacion_basica.control_bom_data import (
        guardar_bom_item,
        obtener_bom_por_modelo,
    )
    # Probar conexión MySQL
    try:
        test_conn = get_connection()
        if test_conn:
            test_conn.close()
            MYSQL_AVAILABLE = True
            logger.info("Usando MySQL como base de datos")
        else:
            MYSQL_AVAILABLE = False
            logger.error("MySQL no disponible: no se obtuvo conexion al arrancar")
    except Exception as e:
        MYSQL_AVAILABLE = False
        logger.error("Error conectando a MySQL: %s", e)
except ImportError as e:
    logger.error("Error importando la capa MySQL: %s", e)
    MYSQL_AVAILABLE = False

def get_db_connection():
    """Conexion MySQL del pool con cursores tipo diccionario (DictCursor).

    Variante "dict-rows" de la conexion del pool: envuelve la conexion de
    db_mysql.get_connection() para que `.cursor()` devuelva filas como dict.
    Se cierra manualmente (`conn.close()` la regresa al pool); NO es un
    context manager. Para filas como tupla usa db_mysql.get_connection();
    para un `with` usa config_mysql.pooled_connection().
    """
    if not MYSQL_AVAILABLE:
        raise RuntimeError("MySQL no disponible: no se puede obtener conexion.")

    conn = get_connection()
    if conn is None:
        raise RuntimeError("MySQL no disponible: el pool no entrego conexion.")

    import MySQLdb

    # Wrapper para que cursor() devuelva filas como diccionario.
    class MySQLConnection:
        def __init__(self, connection):
            self._conn = connection

        def cursor(self):
            return self._conn.cursor(MySQLdb.cursors.DictCursor)

        def __getattr__(self, name):
            return getattr(self._conn, name)

    return MySQLConnection(conn)

def init_db():
    """Inicializar base de datos (solo MySQL)."""
    if not MYSQL_AVAILABLE:
        logger.error("MySQL no disponible: no se puede inicializar la BD.")
        return False

    return mysql_init_db()


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
        logger.error(f"Error probando conexión: {e}")
        return False

if __name__ == "__main__":
    logger.info(" Probando conexión a base de datos...")
    if test_database_connection():
        logger.info(" Conexión exitosa")
        if init_db():
            logger.info(" Base de datos inicializada")
        else:
            logger.error(" Error inicializando base de datos")
    else:
        logger.error(" Error de conexión")
