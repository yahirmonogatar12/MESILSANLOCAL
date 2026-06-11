"""Sanitizacion de valores de request compartida entre modulos `app.api.*`.

Extraidos de stations_qa/historial_operadores_maquina (2026-06-10), donde
vivian duplicados como _text/_bool.
"""


def sanitizar_texto(value, max_len=None):
    """str(value) sin espacios extremos, recortado a max_len si se indica."""
    value = str(value or "").strip()
    if max_len is not None:
        value = value[:max_len]
    return value


def parsear_booleano(value, default=True):
    """Interpreta banderas tipicas de formularios/JSON como booleano."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {
        "1",
        "true",
        "on",
        "si",
        "sí",
        "yes",
        "activo",
        "activa",
    }
