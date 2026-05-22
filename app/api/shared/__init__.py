"""Helpers compartidos entre todos los modulos `app.api.*`.

Reexporta los simbolos comunes para que los modulos solo necesiten:

    from app.api.shared import login_requerido, execute_query

en lugar de conocer la estructura interna del paquete legacy.
"""

from app.db_mysql import execute_query
from app.routes import (
    auth_system,
    login_requerido,
    obtener_fecha_hora_mexico,
    _cuchillas_rows_to_json,
)

__all__ = [
    "execute_query",
    "login_requerido",
    "auth_system",
    "obtener_fecha_hora_mexico",
    "_cuchillas_rows_to_json",
]
