"""Helpers compartidos entre todos los modulos `app.api.*`.

Reexporta los simbolos comunes para que los modulos solo necesiten:

    from app.api.shared import login_requerido, execute_query

en lugar de conocer la estructura interna del paquete legacy.

Los re-exports de `app.routes` (auth_system, login_requerido,
obtener_fecha_hora_mexico) se resuelven de forma LAZY via PEP 562
`__getattr__`. Esto evita el import circular cuando `routes.py` importa
submódulos de `app.api.shared.*` durante su propia carga (los submódulos
son seguros porque no dependen de `routes`; solo los re-exports lo hacen,
y al ser lazy se evaluan cuando `routes` ya terminó de definir esos
símbolos).

Fase 2 (2026-05-28): `_cuchillas_rows_to_json` removido del proxy lazy;
`material_admin.py` lo importa directo desde su blueprint dueno.
"""

from app.db_mysql import execute_query

__all__ = [
    "execute_query",
    "login_requerido",
    "auth_system",
    "obtener_fecha_hora_mexico",
]

_LAZY_FROM_ROUTES = {
    "auth_system",
    "login_requerido",
    "obtener_fecha_hora_mexico",
}


def __getattr__(name):
    if name in _LAZY_FROM_ROUTES:
        from app import routes as _r
        return getattr(_r, name)
    raise AttributeError(f"module 'app.api.shared' has no attribute {name!r}")
