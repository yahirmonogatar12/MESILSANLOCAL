"""Helpers compartidos entre los 3 modulos ICT (Control de resultados).

Consumido por:
  - app/api/control_resultados/historial_ict.py             (defects + 5 APIs)
  - app/api/control_resultados/historial_ict_pass_fail.py   (3 APIs Pass/Fail)
  - app/api/control_resultados/historial_cambios_parametros_ict.py  (4 APIs)

Migrado desde app/routes.py el 2026-05-27. routes.py reexporta los 4
helpers para no romper cualquier consumidor legacy que aun no se haya
identificado (patron usado tambien en el refactor de Almacen de Embarques).
"""

from datetime import date, datetime, timedelta
from datetime import time as dt_time

# Import directo de db_mysql (no de app.api.shared) para evitar ciclo:
# routes.py reexporta estos helpers, y app.api.shared.__init__ importa de
# routes. Importar app.api.shared aqui haria circular.
from app.db_mysql import execute_query
from app.services.ict_lgd_parser import (
    IctLgdNotFoundError,
    IctLgdPathError,
    get_lgd_parameters_for_barcode,
    resolve_lgd_path,
)


def _append_indexable_text_filter(sql, params, column_name, raw_value, exact_min_length=12):
    """Agregar filtro exacto o por prefijo para evitar LIKE con comodin inicial."""
    value = (raw_value or "").strip()
    if not value:
        return sql

    if len(value) >= exact_min_length:
        sql += f" AND {column_name}=%s"
        params.append(value)
    else:
        sql += f" AND {column_name} LIKE %s"
        params.append(f"{value}%")
    return sql


def _ict_format_row(row):
    """Convertir campos fecha/hora a cadenas serializables."""
    if not row:
        return {}

    formatted = {}
    for key, value in row.items():
        if isinstance(value, datetime):
            formatted[key] = value.isoformat(sep=" ")
        elif isinstance(value, date):
            formatted[key] = value.isoformat()
        elif isinstance(value, dt_time):
            formatted[key] = value.strftime("%H:%M:%S")
        elif isinstance(value, timedelta):
            formatted[key] = str(value)
        else:
            formatted[key] = value
    return formatted


def _ict_find_history_record(barcode, ts=None):
    """Buscar el registro resumen que apunta al archivo LGD local."""
    sql = (
        "SELECT barcode, ts, fuente_archivo, linea, ict "
        "FROM history_ict WHERE barcode=%s"
    )
    params = [barcode]
    if ts:
        sql += " AND ts=%s"
        params.append(ts)
    sql += " ORDER BY ts DESC LIMIT 1"
    return execute_query(sql, tuple(params), fetch="one")


def _ict_load_local_parameters(barcode, ts=None):
    """Cargar parametros ICT desde el LGD local (usado por defects y export)."""
    history_row = _ict_find_history_record(barcode, ts)
    if not history_row:
        raise IctLgdNotFoundError("No se encontro el registro ICT solicitado.")

    source_file = (history_row.get("fuente_archivo") or "").strip()
    if not source_file:
        raise IctLgdPathError("El registro no tiene fuente_archivo.")

    lgd_path = resolve_lgd_path(source_file)
    cached_rows = get_lgd_parameters_for_barcode(str(lgd_path), barcode)
    # Copia local porque seteamos linea/ict/fuente_archivo. El resultado de
    # get_lgd_parameters_for_barcode comparte memoria con el cache global.
    rows = [dict(row) for row in cached_rows]
    for row in rows:
        row.setdefault("linea", history_row.get("linea"))
        row.setdefault("ict", history_row.get("ict"))
        row.setdefault("fuente_archivo", source_file)
    return rows, source_file
