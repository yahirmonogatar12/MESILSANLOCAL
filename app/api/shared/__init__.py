"""Helpers compartidos entre todos los modulos `app.api.*`.

Reexporta los simbolos comunes para que los modulos solo necesiten:

    from app.api.shared import (
        execute_query,
        login_requerido,
        obtener_fecha_hora_mexico,
    )

en lugar de conocer la estructura interna del paquete legacy.

Los re-exports se resuelven de forma LAZY via PEP 562 `__getattr__`.
Esto evita el import circular cuando `routes.py` importa submódulos de
`app.api.shared.*` durante su propia carga, y evita arrastrar `db_mysql`
cuando solo se necesita un helper liviano de shared.

Fase 2 (2026-05-28): `_cuchillas_rows_to_json` removido del proxy lazy;
`material_admin.py` lo importa directo desde su blueprint dueno.
"""

__all__ = [
    "execute_query",
    "login_requerido",
    "requiere_permiso_dropdown",
    "auth_system",
    "obtener_fecha_hora_mexico",
]

_LAZY_FROM_ROUTES = {
    "auth_system",
    "login_requerido",
}

_LAZY_FROM_DB_MYSQL = {
    "execute_query",
}

_LAZY_FROM_DATETIME_HELPERS = {
    "obtener_fecha_hora_mexico",
}

# Fachada de permisos por boton (app/api/shared/permisos.py).
_LAZY_FROM_PERMISOS = {
    "requiere_permiso_dropdown",
}


def __getattr__(name):
    if name in _LAZY_FROM_DB_MYSQL:
        from app.db_mysql import execute_query
        return execute_query
    if name in _LAZY_FROM_DATETIME_HELPERS:
        from app.api.shared.datetime_helpers import obtener_fecha_hora_mexico
        return obtener_fecha_hora_mexico
    if name in _LAZY_FROM_PERMISOS:
        from app.api.shared.permisos import requiere_permiso_dropdown
        return requiere_permiso_dropdown
    if name in _LAZY_FROM_ROUTES:
        from app import routes as _r
        return getattr(_r, name)
    raise AttributeError(f"module 'app.api.shared' has no attribute {name!r}")
