"""Helpers de conexion MySQL (pool de config_mysql) para CRUDs transaccionales.

Para consultas simples de lectura usa `execute_query` (re-exportado en
app.api.shared). Estos helpers son para modulos que necesitan manejar su
propia conexion/cursor/commit, p.ej. el CRUD de stations_qa.

Extraidos de control_calidad/stations_qa.py (2026-06-10).
"""

from flask import jsonify

from app.config_mysql import get_pooled_connection

try:
    import MySQLdb
    import MySQLdb.cursors
except Exception:  # pragma: no cover - entorno sin driver MySQL
    MySQLdb = None


def dict_cursor(conn):
    """Cursor de dicts si el driver lo soporta; cursor normal si no."""
    if MySQLdb is not None and getattr(MySQLdb, "cursors", None):
        return conn.cursor(MySQLdb.cursors.DictCursor)
    return conn.cursor()


def conexion_o_error():
    """(conexion, None) del pool, o (None, respuesta 503) si no hay BD."""
    conn = get_pooled_connection()
    if conn is None:
        return None, (
            jsonify({"success": False, "error": "Base de datos no disponible"}),
            503,
        )
    return conn, None
