"""
Módulo de Utilidades de Zona Horaria
Manejo centralizado de fecha/hora en zona horaria de México (GMT-6)
"""

from datetime import datetime, timedelta, timezone


# Zona horaria de México Central (GMT-6)
MEXICO_TZ = timezone(timedelta(hours=-6))


def get_mexico_time() -> datetime:
    """
    Obtener fecha y hora actual en zona horaria de México (GMT-6)
    
    Returns:
        datetime: Fecha y hora actual en México
    """
    try:
        utc_now = datetime.utcnow()
        mexico_time = utc_now - timedelta(hours=6)
        return mexico_time
    except Exception:
        # Fallback a hora local
        return datetime.now()


def get_mexico_time_str(formato: str = '%Y-%m-%d %H:%M:%S') -> str:
    """
    Obtener fecha y hora actual de México en formato string
    
    Args:
        formato: Formato de salida (default: '%Y-%m-%d %H:%M:%S')
    
    Returns:
        str: Fecha formateada
    """
    return get_mexico_time().strftime(formato)


def get_mexico_time_mysql() -> str:
    """
    Obtener hora de México en formato compatible con MySQL DATETIME
    
    Returns:
        str: Formato 'YYYY-MM-DD HH:MM:SS'
    """
    return get_mexico_time().strftime('%Y-%m-%d %H:%M:%S')


def get_mexico_time_iso() -> str:
    """
    Obtener hora de México en formato ISO sin zona horaria
    
    Returns:
        str: Formato ISO 8601
    """
    return get_mexico_time().isoformat()


def get_mexico_date() -> str:
    """
    Obtener solo la fecha actual de México
    
    Returns:
        str: Formato 'YYYY-MM-DD'
    """
    return get_mexico_time().strftime('%Y-%m-%d')


def get_mexico_time_for_code() -> str:
    """
    Obtener fecha en formato para códigos (YYMMDD)
    
    Returns:
        str: Formato 'YYMMDD'
    """
    return get_mexico_time().strftime('%y%m%d')


def parse_date(date_str: str, formato: str = '%Y-%m-%d') -> datetime:
    """
    Parsear string de fecha a datetime
    
    Args:
        date_str: String de fecha
        formato: Formato esperado
    
    Returns:
        datetime: Objeto datetime
    
    Raises:
        ValueError: Si el formato no coincide
    """
    return datetime.strptime(date_str, formato)


def safe_parse_date(date_str: str) -> datetime:
    """
    Intentar parsear fecha con múltiples formatos
    
    Args:
        date_str: String de fecha
    
    Returns:
        datetime o None si no se puede parsear
    """
    if not date_str:
        return None
        
    formatos = [
        '%Y-%m-%d',
        '%Y/%m/%d',
        '%d-%m-%Y',
        '%d/%m/%Y',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%dT%H:%M:%S',
    ]
    
    for fmt in formatos:
        try:
            return datetime.strptime(str(date_str)[:19], fmt)
        except ValueError:
            continue
    
    return None


def format_datetime_for_display(dt: datetime) -> str:
    """
    Formatear datetime para mostrar en UI
    
    Args:
        dt: Objeto datetime
    
    Returns:
        str: Formato legible 'DD/MM/YYYY HH:MM'
    """
    if not dt:
        return ''
    return dt.strftime('%d/%m/%Y %H:%M')


def classify_shift(dt: datetime = None) -> str:
    """
    Clasificar turno según hora
    
    Args:
        dt: Datetime a clasificar (default: hora actual de México)
    
    Returns:
        str: 'DIA', 'TIEMPO_EXTRA' o 'NOCHE'
    
    Turnos:
        - DÍA: 7:30 - 17:30
        - TIEMPO_EXTRA: 17:30 - 22:00
        - NOCHE: 22:30 - 7:00 (del día siguiente)
    """
    if dt is None:
        dt = get_mexico_time()
    
    mins = dt.hour * 60 + dt.minute
    
    # DÍA: 7:30 (450 mins) hasta 17:30 (1050 mins)
    if 7*60+30 <= mins < 17*60+30:
        return "DIA"
    
    # TIEMPO_EXTRA: 17:30 (1050 mins) hasta 22:00 (1320 mins)
    if 17*60+30 <= mins < 22*60+0:
        return "TIEMPO_EXTRA"
    
    # NOCHE: 22:30 (1350 mins) hasta 7:00 (420 mins del día siguiente)
    if mins >= 22*60+30 or mins < 7*60+0:
        return "NOCHE"
    
    # Gaps de transición
    if 22*60+0 <= mins < 22*60+30:
        return "TIEMPO_EXTRA"  # Gap 22:00-22:30 -> fin de tiempo extra
    if 7*60+0 <= mins < 7*60+30:
        return "NOCHE"  # Gap 7:00-7:30 -> fin de noche
    
    return "DIA"  # Fallback


def get_shift_routing(shift: str) -> int:
    """
    Obtener número de routing según turno
    
    Args:
        shift: Nombre del turno
    
    Returns:
        int: 1=DIA, 2=TIEMPO_EXTRA, 3=NOCHE
    """
    return {
        'DIA': 1,
        'TIEMPO EXTRA': 2,
        'TIEMPO_EXTRA': 2,
        'NOCHE': 3
    }.get(shift.upper(), 1)
