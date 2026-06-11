"""Helpers compartidos de fecha/hora para modulos del portal."""

from datetime import datetime, timedelta


def obtener_fecha_hora_mexico():
    """Obtener fecha y hora actual en zona horaria de Mexico (GMT-6)."""
    try:
        return datetime.utcnow() - timedelta(hours=6)
    except Exception:
        return datetime.now()


def obtener_fecha_mexico():
    """Fecha actual de Mexico (GMT-6) como string 'YYYY-MM-DD'."""
    return obtener_fecha_hora_mexico().strftime("%Y-%m-%d")


def formatear_hora(valor):
    """Normaliza una hora a 'HH:MM:SS'.

    TIME()/sec_to_time() de MySQL llegan como timedelta en los drivers
    (pymysql/MySQLdb); str() no rellena el cero a la izquierda (p.ej.
    '9:05:00'). Aqui se rellena y se descartan microsegundos.
    """
    if valor is None:
        return ""
    if isinstance(valor, timedelta):
        total = int(valor.total_seconds()) % (24 * 3600)
        h, resto = divmod(total, 3600)
        m, s = divmod(resto, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"
    s = str(valor)
    return s.split(".")[0][-8:] if len(s) >= 8 else s


def formatear_fecha(valor):
    """Serializa un date/datetime a 'YYYY-MM-DD' (string vacio si es None)."""
    if valor is None:
        return ""
    if hasattr(valor, "strftime"):
        return valor.strftime("%Y-%m-%d")
    return str(valor)


def formatear_fecha_hora(valor):
    """Serializa un datetime a 'YYYY-MM-DD HH:MM:SS' (vacio si es None)."""
    if valor is None:
        return ""
    if hasattr(valor, "strftime"):
        return valor.strftime("%Y-%m-%d %H:%M:%S")
    return str(valor).replace("T", " ")
