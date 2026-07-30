"""Helpers compartidos para los modulos FCT de Control de resultados."""

from __future__ import annotations

import json
from datetime import date, datetime, time as dt_time, timedelta
from decimal import Decimal

PENDING_TEXT = "PENDIENTE"
SIN_PLAN_TEXT = "SIN PLAN"
SIN_TURNO_TEXT = "SIN TURNO"
SIN_ESTACION_TEXT = "SIN ESTACION"
SIN_NUMERO_PARTE_TEXT = "SIN NUMERO DE PARTE"

FCT_TS_EXPR = "COALESCE(f.start_at, f.end_at, f.file_modified_at, TIMESTAMP(f.folder_date))"


def fct_fecha_jornada_expr(ts_column: str = FCT_TS_EXPR) -> str:
    return (
        f"CASE WHEN TIME({ts_column}) >= '07:30:00' "
        f"THEN DATE({ts_column}) ELSE DATE(DATE_SUB({ts_column}, INTERVAL 1 DAY)) END"
    )


def fct_turno_expr(ts_column: str = FCT_TS_EXPR) -> str:
    return (
        "CASE "
        f"WHEN TIME({ts_column}) >= '07:30:00' AND TIME({ts_column}) < '17:30:00' THEN 'DIA' "
        f"WHEN TIME({ts_column}) >= '17:30:00' AND TIME({ts_column}) < '22:30:00' THEN 'TE' "
        f"WHEN TIME({ts_column}) >= '23:00:00' OR TIME({ts_column}) < '07:30:00' THEN 'NOCHE' "
        f"ELSE '{SIN_TURNO_TEXT}' "
        "END"
    )


def fct_plan_line_join(ts_column: str = FCT_TS_EXPR) -> str:
    jornada_expr = fct_fecha_jornada_expr(ts_column)
    return (
        " LEFT JOIN ("
        "  SELECT DATE(working_date) AS plan_date, TRIM(part_no) AS part_no, "
        "  SUBSTRING_INDEX("
        "    GROUP_CONCAT(NULLIF(TRIM(line), '') ORDER BY COALESCE(sequence, 999999), id SEPARATOR ','),"
        "    ',', 1"
        "  ) AS line "
        "  FROM plan_main "
        "  WHERE part_no IS NOT NULL AND TRIM(part_no) <> '' "
        "  GROUP BY DATE(working_date), TRIM(part_no)"
        ") pm ON pm.plan_date = "
        f"{jornada_expr}"
        " AND pm.part_no = TRIM(f.part_number)"
    )


def fct_line_expr() -> str:
    return f"COALESCE(NULLIF(TRIM(pm.line), ''), '{SIN_PLAN_TEXT}')"


def parse_iso_date(value: str | None) -> date | None:
    value = (value or "").strip()
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def fct_shift_bounds(fecha_desde: str | None, fecha_hasta: str | None):
    start_date = parse_iso_date(fecha_desde)
    end_date = parse_iso_date(fecha_hasta) or start_date
    start_dt = datetime.combine(start_date, dt_time(7, 30)) if start_date else None
    end_dt = datetime.combine(end_date + timedelta(days=1), dt_time(7, 30)) if end_date else None
    return start_dt, end_dt


def fmt_date(value) -> str:
    if value is None:
        return ""
    if hasattr(value, "isoformat"):
        return value.isoformat()[:10]
    return str(value)[:10]


def fmt_time(value) -> str:
    if value is None:
        return ""
    text = str(value)
    return text.split(".", 1)[0]


def fmt_datetime(value) -> str:
    if value is None:
        return ""
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return str(value).split(".", 1)[0]


def to_int(value, default=0) -> int:
    try:
        return int(value or default)
    except (TypeError, ValueError):
        return default


def to_float(value, default=0.0) -> float:
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value or default)
    except (TypeError, ValueError):
        return default


def normalize_result(value: str | None) -> str:
    value = (value or "").strip().upper()
    if value in {"PASS", "OK"}:
        return "PASS"
    if value in {"FAIL", "NG"}:
        return "FAIL"
    return value or "UNKNOWN"


def parse_steps_json(raw_value):
    if raw_value is None:
        return []
    if isinstance(raw_value, (list, tuple)):
        return list(raw_value)
    if isinstance(raw_value, (bytes, bytearray)):
        raw_value = raw_value.decode("utf-8", errors="replace")
    try:
        parsed = json.loads(str(raw_value))
    except (TypeError, ValueError):
        return []
    return parsed if isinstance(parsed, list) else []
