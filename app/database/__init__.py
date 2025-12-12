"""
Módulo Database - Conexión a Base de Datos
SQLite (legacy) y MySQL (principal)
"""

from .db_mysql import (
    execute_query,
    get_mysql_connection,
    get_db_connection,
    MYSQL_AVAILABLE
)
from .config_mysql import test_connection
from .db import init_db, get_db_connection as get_sqlite_connection

__all__ = [
    'execute_query',
    'get_mysql_connection',
    'get_db_connection',
    'MYSQL_AVAILABLE',
    'test_connection',
    'init_db',
    'get_sqlite_connection'
]
