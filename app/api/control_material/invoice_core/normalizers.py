"""Normalizacion y serializacion comun para invoices/costing."""

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

def normalizar_pallet_no(value):
    """Normaliza pallet: 1, 01, PALLET 1, Pallet-01 -> 1."""
    if value is None:
        return ""
    if isinstance(value, Decimal):
        value = int(value) if value == value.to_integral_value() else value
    text = str(value).strip()
    if not text:
        return ""
    text = text.replace("\u00a0", " ")
    match = re.search(r"(\d+)", text)
    if match:
        return str(int(match.group(1)))
    text = re.sub(r"(?i)\bpallet\b", "", text)
    text = re.sub(r"[\s\-_]+", "", text).strip().upper()
    return text


def normalizar_numero_parte(value):
    if value is None:
        return ""
    text = str(value).replace("\u00a0", " ").strip()
    text = re.sub(r"\s+", "", text)
    return text.upper()


def parte_base(value):
    """Parte base sin sufijo de version: EAX66946005-1.0 -> EAX66946005.

    El usuario identifica las partes por version (codigo-version), pero en
    `materiales`/almacen/costos la parte se da de alta como la base. Recorta
    todo lo que va despues del ULTIMO guion. Si no hay guion, regresa la parte
    normalizada tal cual.
    """
    base = normalizar_numero_parte(value)
    if "-" in base:
        base = base.rsplit("-", 1)[0]
    return base


def version_parte(value):
    """Version a partir del codigo: EAX66946005-1.0 -> 1.0. Vacio si no hay."""
    normalizado = normalizar_numero_parte(value)
    if "-" in normalizado:
        return normalizado.rsplit("-", 1)[1]
    return ""


def prefijos_por_guion(value):
    """Prefijos del codigo, del mas largo al mas corto, recortando por guion.

    EAX66946005-1.0-202601090001 ->
      [EAX66946005-1.0-202601090001, EAX66946005-1.0, EAX66946005]

    El codigo recibido apila parte + version + lote/secuencia separados por
    guiones (codigo_material_recibido). Para encontrar la parte en `materiales`
    (que casi siempre es la base, sin sufijos) se prueba el codigo completo y se
    van quitando segmentos desde el final hasta dar con uno que exista. Se ordena
    del mas especifico al mas general para preferir el match mas largo.
    """
    normalizado = normalizar_numero_parte(value)
    if not normalizado:
        return []
    partes = normalizado.split("-")
    return ["-".join(partes[: i + 1]) for i in range(len(partes) - 1, -1, -1)]


def raw_text(value):
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, Decimal):
        return format(value, "f")
    return str(value).strip()


def decimal_or_zero(value):
    raw = raw_text(value)
    if not raw:
        return Decimal("0.0000")
    cleaned = raw.upper()
    cleaned = cleaned.replace(",", "")
    cleaned = cleaned.replace("$", "")
    cleaned = cleaned.replace("USD", "").replace("MXN", "").replace("KRW", "")
    cleaned = cleaned.strip()
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = f"-{cleaned[1:-1]}"
    try:
        return Decimal(cleaned).quantize(Decimal("0.0001"))
    except (InvalidOperation, ValueError):
        return Decimal("0.0000")


def decimal_str(value, places="0.0000"):
    if value in (None, ""):
        return None
    try:
        return str(Decimal(str(value)).quantize(Decimal(places)))
    except (InvalidOperation, ValueError):
        return str(value)


def json_value(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")
    return value


def row_to_json(row):
    return {k: json_value(v) for k, v in (row or {}).items()}

# Compatibilidad interna temporal con nombres previos al refactor.
_parte_base = parte_base
_version_parte = version_parte
_prefijos_por_guion = prefijos_por_guion
_raw_text = raw_text
_decimal_or_zero = decimal_or_zero
_decimal_str = decimal_str
_json_value = json_value
_row_to_json = row_to_json
