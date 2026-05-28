"""Helpers compartidos de fecha/hora para modulos del portal."""

from datetime import datetime, timedelta


def obtener_fecha_hora_mexico():
    """Obtener fecha y hora actual en zona horaria de Mexico (GMT-6)."""
    try:
        return datetime.utcnow() - timedelta(hours=6)
    except Exception:
        return datetime.now()
