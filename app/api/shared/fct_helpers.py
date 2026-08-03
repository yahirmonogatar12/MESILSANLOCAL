"""Helpers compartidos para los modulos FCT de Control de resultados."""

from __future__ import annotations

import json
from datetime import date, datetime, time as dt_time, timedelta
from decimal import Decimal

from app.db_mysql import execute_query

PENDING_TEXT = "PENDIENTE"
SIN_PLAN_TEXT = "SIN PLAN"
SIN_TURNO_TEXT = "SIN TURNO"
SIN_ESTACION_TEXT = "SIN ESTACION"
SIN_NUMERO_PARTE_TEXT = "SIN NUMERO DE PARTE"
MULTIPLE_OPERATORS_TEXT = "MULTIPLE"

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


def fct_operator_line_expr() -> str:
    """Linea fisica usada solo para empatar sesiones FCT de operadores.

    La linea visible sigue saliendo del plan. Para resolver operador, la vista
    historial_estaciones_qa maneja M1..M4, mientras que algunos logs FCT traen
    station_line como L01..L04 o la estacion inicia con ese prefijo.
    """
    return (
        "COALESCE("
        "CASE UPPER(TRIM(COALESCE(pm.line, ''))) "
        "WHEN 'M1' THEN 'M1' WHEN 'M2' THEN 'M2' WHEN 'M3' THEN 'M3' WHEN 'M4' THEN 'M4' "
        "END, "
        "CASE UPPER(TRIM(COALESCE(f.station_line, ''))) "
        "WHEN 'L01' THEN 'M1' WHEN 'L02' THEN 'M2' WHEN 'L03' THEN 'M3' WHEN 'L04' THEN 'M4' "
        "WHEN 'M1' THEN 'M1' WHEN 'M2' THEN 'M2' WHEN 'M3' THEN 'M3' WHEN 'M4' THEN 'M4' "
        "END, "
        "CASE "
        "WHEN UPPER(TRIM(COALESCE(f.station, ''))) LIKE 'L01%%' THEN 'M1' "
        "WHEN UPPER(TRIM(COALESCE(f.station, ''))) LIKE 'L02%%' THEN 'M2' "
        "WHEN UPPER(TRIM(COALESCE(f.station, ''))) LIKE 'L03%%' THEN 'M3' "
        "WHEN UPPER(TRIM(COALESCE(f.station, ''))) LIKE 'L04%%' THEN 'M4' "
        "END, "
        "NULLIF(TRIM(pm.line), '')"
        ")"
    )


def _fct_normalize_operator_line(value) -> str:
    text = str(value or "").strip().upper()
    return {
        "L01": "M1",
        "L02": "M2",
        "L03": "M3",
        "L04": "M4",
    }.get(text, text)


def _fct_to_datetime(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, dt_time.min)
    text = str(value).strip()
    if not text:
        return None
    text = text.split(".", 1)[0]
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _fct_load_operator_sessions(min_ts, max_ts, lines: set[str] | None = None) -> dict[str, list[dict]]:
    min_dt = _fct_to_datetime(min_ts)
    max_dt = _fct_to_datetime(max_ts)
    if not min_dt or not max_dt:
        return {}

    normalized_lines = sorted({
        _fct_normalize_operator_line(line)
        for line in (lines or set())
        if _fct_normalize_operator_line(line) and _fct_normalize_operator_line(line) != SIN_PLAN_TEXT
    })

    params: list = [max_dt, min_dt]
    line_filter = ""
    if normalized_lines:
        placeholders = ", ".join(["%s"] * len(normalized_lines))
        line_filter = f" AND linea IN ({placeholders})"
        params.extend(normalized_lines)

    rows = execute_query(
        "SELECT session_id, estacion, linea, usuario, username, estado, inicio_local, fin_local "
        "FROM historial_estaciones_qa "
        "WHERE tipo = 'FCT' "
        "AND usuario IS NOT NULL "
        "AND inicio_local IS NOT NULL "
        "AND inicio_local <= %s "
        "AND COALESCE(fin_local, NOW()) >= %s "
        f"{line_filter} "
        "ORDER BY inicio_local ASC",
        tuple(params),
        fetch="all",
    ) or []

    sessions: dict[str, list[dict]] = {}
    for session in rows:
        line = _fct_normalize_operator_line(session.get("linea"))
        if line:
            sessions.setdefault(line, []).append(session)
    return sessions


def _fct_session_covers(session: dict, timestamp: datetime) -> bool:
    start = _fct_to_datetime(session.get("inicio_local"))
    end = _fct_to_datetime(session.get("fin_local"))
    if not start or timestamp < start:
        return False
    return end is None or timestamp <= end


def _fct_session_overlaps(session: dict, start_ts: datetime, end_ts: datetime) -> bool:
    start = _fct_to_datetime(session.get("inicio_local"))
    end = _fct_to_datetime(session.get("fin_local"))
    if not start:
        return False
    return start <= end_ts and (end is None or end >= start_ts)


def _fct_unique_operator_text(sessions: list[dict]) -> str:
    operators: dict[str, str] = {}
    for session in sessions:
        key = str(session.get("username") or session.get("usuario") or "").strip()
        display = str(session.get("usuario") or session.get("username") or "").strip()
        if key and display and key not in operators:
            operators[key] = display
    if not operators:
        return PENDING_TEXT
    if len(operators) == 1:
        return next(iter(operators.values()))
    return MULTIPLE_OPERATORS_TEXT


def _fct_operator_list_text(sessions: list[dict]) -> str:
    operators: dict[str, str] = {}
    for session in sessions:
        key = str(session.get("username") or session.get("usuario") or "").strip()
        display = str(session.get("usuario") or session.get("username") or "").strip()
        if key and display and key not in operators:
            operators[key] = display
    return ", ".join(operators.values()) if operators else PENDING_TEXT


def fct_attach_operator(rows: list[dict]) -> list[dict]:
    """Anota operador por timestamp del test dentro de una sesion FCT."""
    timestamps = [_fct_to_datetime(row.get("ts")) for row in rows if row.get("ts")]
    timestamps = [timestamp for timestamp in timestamps if timestamp]
    if not timestamps:
        for row in rows:
            row["operador"] = PENDING_TEXT
        return rows

    lines = {
        _fct_normalize_operator_line(row.get("operator_line") or row.get("linea"))
        for row in rows
        if row.get("operator_line") or row.get("linea")
    }
    sessions_by_line = _fct_load_operator_sessions(min(timestamps), max(timestamps), lines)

    for row in rows:
        timestamp = _fct_to_datetime(row.get("ts"))
        line = _fct_normalize_operator_line(row.get("operator_line") or row.get("linea"))
        candidates = [
            session
            for session in sessions_by_line.get(line, [])
            if timestamp and _fct_session_covers(session, timestamp)
        ]
        row["operador"] = _fct_unique_operator_text(candidates)
    return rows


def fct_attach_summary_operators(rows: list[dict]) -> list[dict]:
    """Anota operadores que solaparon el rango [primer_test, ultimo_test]."""
    timestamps = []
    for row in rows:
        for key in ("primer_test", "ultimo_test"):
            timestamp = _fct_to_datetime(row.get(key))
            if timestamp:
                timestamps.append(timestamp)
    if not timestamps:
        for row in rows:
            row["operador"] = PENDING_TEXT
        return rows

    lines = {
        _fct_normalize_operator_line(row.get("operator_line") or row.get("linea"))
        for row in rows
        if row.get("operator_line") or row.get("linea")
    }
    sessions_by_line = _fct_load_operator_sessions(min(timestamps), max(timestamps), lines)

    for row in rows:
        start_ts = _fct_to_datetime(row.get("primer_test"))
        end_ts = _fct_to_datetime(row.get("ultimo_test"))
        line = _fct_normalize_operator_line(row.get("operator_line") or row.get("linea"))
        candidates = [
            session
            for session in sessions_by_line.get(line, [])
            if start_ts and end_ts and _fct_session_overlaps(session, start_ts, end_ts)
        ]
        row["operador"] = _fct_operator_list_text(candidates)
    return rows


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
