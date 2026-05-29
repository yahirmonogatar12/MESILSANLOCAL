"""Configuracion central de logging para el MES.

Reemplaza el uso de `print(...)` como mecanismo de log. Cada modulo debe
obtener su logger con:

    import logging
    logger = logging.getLogger(__name__)

y usar `logger.info/warning/error(...)`. La configuracion del root logger
(handler + formato + nivel) se hace UNA sola vez al arranque llamando a
`configure_logging()` desde el entry point (`run.py`) y desde
`app_factory.create_app()`.

Nivel configurable por entorno con `MES_LOG_LEVEL` (default INFO).
"""

import logging
import os
import sys

_CONFIGURED = False

_DEFAULT_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def configure_logging(force=False):
    """Configura el root logger una sola vez (idempotente).

    - Nivel desde `MES_LOG_LEVEL` (INFO por defecto).
    - Handler a stdout con timestamp + nivel + nombre del logger.
    - Fuerza UTF-8 en el stream para no romper con emojis/acentos en
      consolas Windows (el CI ya tuvo que setear PYTHONIOENCODING).
    """
    global _CONFIGURED
    if _CONFIGURED and not force:
        return

    level_name = os.getenv("MES_LOG_LEVEL", "INFO").strip().upper()
    level = getattr(logging, level_name, logging.INFO)

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(logging.Formatter(_DEFAULT_FORMAT, datefmt=_DATE_FORMAT))

    root = logging.getLogger()
    # Evitar handlers duplicados si algo ya configuro el root.
    for existing in list(root.handlers):
        root.removeHandler(existing)
    root.addHandler(handler)
    root.setLevel(level)

    # Reconfigurar el stream a UTF-8 cuando la plataforma lo permita.
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass

    _CONFIGURED = True
