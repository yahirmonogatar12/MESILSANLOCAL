"""Renders y APIs para modulos PPM's de Control de calidad.

WF_001: opciones en LISTA_CONTROL_DE_CALIDAD / PPM's.
WF_002: cada modulo carga en su propio *-unique-container.
WF_003: blueprint dueno de renders AJAX y APIs JSON.
WF_004: CSS persistente en MainTemplate.html y JS idempotente por template.
"""

from collections import defaultdict
from datetime import date, datetime, timedelta
import re

from flask import Blueprint, jsonify, render_template, request, session

from app.api.shared import login_requerido
from app.api.pda.shipping_material import get_dict_cursor, normalize_integer
from app.config_mysql import get_pooled_connection

bp = Blueprint("control_calidad_ppms", __name__)

PPM_SCALE = 1_000_000
DEFAULT_LQC_TARGET = 20_000
TARGET_TABLE = "control_calidad_ppm_targets"


def _today():
    return datetime.now().date()


def _parse_date(value, fallback):
    try:
        return datetime.strptime(str(value or ""), "%Y-%m-%d").date()
    except Exception:
        return fallback


def _date_window(start_date, end_date):
    if end_date < start_date:
        start_date, end_date = end_date, start_date
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date + timedelta(days=1), datetime.min.time())
    return start_date, end_date, start_dt, end_dt


def _period_key(value, group_by):
    if isinstance(value, datetime):
        day = value.date()
    else:
        day = value
    if group_by == "week":
        iso = day.isocalendar()
        return f"{iso.year}-W{iso.week:02d}"
    if group_by == "month":
        return day.strftime("%Y-%m")
    return day.strftime("%Y-%m-%d")


def _period_label(key, group_by):
    if group_by == "week":
        return f"W{int(key.split('W')[-1])}"
    if group_by == "month":
        month_names = [
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        ]
        return month_names[int(key.split("-")[1]) - 1]
    return key[5:]


def _period_keys_between(start_date, end_date, group_by):
    keys = []
    seen = set()
    cursor = start_date
    while cursor <= end_date:
        key = _period_key(cursor, group_by)
        if key not in seen:
            keys.append({"key": key, "label": _period_label(key, group_by)})
            seen.add(key)
        cursor += timedelta(days=1)
    return keys


def _week_start(day):
    return day - timedelta(days=day.isoweekday() - 1)


def _last_week_periods(end_date, count=12):
    last_week = _week_start(end_date)
    if end_date.isoweekday() < 7:
        last_week -= timedelta(weeks=1)
    first_week = last_week - timedelta(weeks=count - 1)
    return [
        {
            "key": _period_key(first_week + timedelta(weeks=index), "week"),
            "label": _period_label(
                _period_key(first_week + timedelta(weeks=index), "week"),
                "week",
            ),
        }
        for index in range(count)
    ], first_week, last_week + timedelta(days=6)


def _ppm(defects, inspected):
    inspected = int(inspected or 0)
    if inspected <= 0:
        return 0
    return round((int(defects or 0) / inspected) * PPM_SCALE)


def _empty_metric():
    return {"inspected": 0, "defects": 0, "ppm": 0}


def _normalize_text(value):
    return str(value or "").strip()


def _normalize_part(value):
    return _normalize_text(value).upper()


def _base_part_number(value):
    text = _normalize_part(value)
    match = re.search(r"[A-Z]{3}\d{8}", text)
    return match.group(0) if match else text


def _normalize_line(value):
    line = _normalize_text(value).upper()
    if not line:
        return ""
    compact = line.replace(" ", "").replace("-", "")
    if compact.startswith("DP") and compact[2:].isdigit():
        return f"D{int(compact[2:])}"
    if compact.startswith("D") and compact[1:].isdigit():
        return f"D{int(compact[1:])}"
    return line


def _project_part_number(part_number):
    part = _base_part_number(part_number)
    if len(part) > 2 and part[-2:].isdigit():
        return part[:-2]
    return part or "SIN PARTE"


def _forced_line_for_part(part_number):
    part = _base_part_number(part_number)
    if part == "EBR32881301":
        return "M2"
    return ""


def _init_ppm_target_table(cursor):
    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS `{TARGET_TABLE}` (
          id INT NOT NULL AUTO_INCREMENT,
          module_key VARCHAR(50) NOT NULL,
          scope_key VARCHAR(100) NOT NULL DEFAULT 'global',
          target_ppm INT NOT NULL DEFAULT {DEFAULT_LQC_TARGET},
          updated_by VARCHAR(120) NULL,
          created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
          PRIMARY KEY (id),
          UNIQUE KEY uq_ppm_target_scope (module_key, scope_key)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )


def _get_target(cursor, module_key="lqc", scope_key="global"):
    _init_ppm_target_table(cursor)
    cursor.execute(
        f"""
        SELECT target_ppm
        FROM `{TARGET_TABLE}`
        WHERE module_key = %s
          AND scope_key = %s
        LIMIT 1
        """,
        (module_key, scope_key),
    )
    row = cursor.fetchone()
    if not row:
        return DEFAULT_LQC_TARGET
    return int(row.get("target_ppm") or DEFAULT_LQC_TARGET)


def _set_target(cursor, target_ppm, module_key="lqc", scope_key="global"):
    _init_ppm_target_table(cursor)
    updated_by = (
        session.get("nombre_completo")
        or session.get("usuario")
        or session.get("username")
        or "Sistema"
    )
    cursor.execute(
        f"""
        INSERT INTO `{TARGET_TABLE}` (module_key, scope_key, target_ppm, updated_by)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
          target_ppm = VALUES(target_ppm),
          updated_by = VALUES(updated_by),
          updated_at = CURRENT_TIMESTAMP
        """,
        (module_key, scope_key, int(target_ppm), updated_by),
    )


def _load_part_catalog(cursor):
    cursor.execute(
        """
        SELECT part_number, model
        FROM part_numbers
        WHERE COALESCE(active, 1) = 1
          AND COALESCE(part_number, '') <> ''
        """
    )
    rows = cursor.fetchall()
    catalog = []
    model_by_part = {}
    for row in rows:
        part = _normalize_part(row.get("part_number"))
        if not part:
            continue
        model = _normalize_text(row.get("model"))
        catalog.append(part)
        if model and part not in model_by_part:
            model_by_part[part] = model
    catalog.sort(key=len, reverse=True)
    return catalog, model_by_part


def _resolve_part(raw_value, catalog):
    value = _normalize_part(raw_value)
    if not value:
        return ""
    for part in catalog:
        if value.startswith(part):
            return part
    for part in catalog:
        if len(part) >= 6 and part in value:
            return part
    return _base_part_number(value)


def _coerce_datetime(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    try:
        return datetime.fromisoformat(str(value))
    except Exception:
        return datetime.min


def _load_latest_lines(cursor, part_numbers, part_catalog=None):
    parts = sorted({_normalize_part(part) for part in part_numbers if _normalize_part(part)})
    if not parts:
        return {}, {}

    part_set = set(parts)
    latest_line_candidate = {}
    latest_family_line_candidate = {}
    latest_model_by_part = {}
    parts_by_project = defaultdict(list)
    for part in parts:
        project = _project_part_number(part)
        if project and project != part:
            parts_by_project[project].append(part)

    def remember_line_candidate(store, part, line, sort_date, source_priority=0, record_id=""):
        part = _normalize_part(part)
        line = _normalize_line(line)
        if not part or part not in part_set or not line:
            return
        sort_key = (_coerce_datetime(sort_date), int(source_priority), str(record_id or ""))
        current = store.get(part)
        if not current or sort_key > current["sort_key"]:
            store[part] = {"line": line, "sort_key": sort_key}

    def remember_line(part, line, sort_date, source_priority=0, record_id=""):
        remember_line_candidate(
            latest_line_candidate, part, line, sort_date, source_priority, record_id
        )

    def remember_family_line(project, line, sort_date, source_priority=0, record_id=""):
        for part in parts_by_project.get(project, []):
            remember_line_candidate(
                latest_family_line_candidate,
                part,
                line,
                sort_date,
                source_priority,
                record_id,
            )

    def remember_model(part, model):
        model = _normalize_text(model)
        if model and part in part_set and part not in latest_model_by_part:
            latest_model_by_part[part] = model

    def remember_family_model(project, model):
        for part in parts_by_project.get(project, []):
            remember_model(part, model)

    for start in range(0, len(parts), 500):
        chunk = parts[start : start + 500]
        placeholders = ",".join(["%s"] * len(chunk))
        cursor.execute(
            f"""
            SELECT part_no, line, model_code, working_date, updated_at, id
            FROM plan_main
            WHERE part_no IN ({placeholders})
              AND COALESCE(part_no, '') <> ''
            ORDER BY part_no ASC,
                     working_date DESC,
                     updated_at DESC,
                     id DESC
            """,
            chunk,
        )
        for row in cursor.fetchall():
            part = _normalize_part(row.get("part_no"))
            if not part:
                continue
            line = _normalize_line(row.get("line"))
            model = _normalize_text(row.get("model_code"))
            remember_line(
                part,
                line,
                row.get("working_date") or row.get("updated_at"),
                1,
                row.get("id"),
            )
            remember_model(part, model)

    projects = sorted(parts_by_project)
    for start in range(0, len(projects), 80):
        chunk = [project for project in projects[start : start + 80] if len(project) >= 6]
        if not chunk:
            continue
        conditions = " OR ".join(["part_no LIKE %s"] * len(chunk))
        cursor.execute(
            f"""
            SELECT part_no, line, model_code, working_date, updated_at, id
            FROM plan_main
            WHERE COALESCE(part_no, '') <> ''
              AND ({conditions})
            ORDER BY working_date DESC,
                     updated_at DESC,
                     id DESC
            """,
            [f"{project}%" for project in chunk],
        )
        for row in cursor.fetchall():
            row_part = _normalize_part(row.get("part_no"))
            project = _project_part_number(row_part)
            line = _normalize_line(row.get("line"))
            model = _normalize_text(row.get("model_code"))
            remember_family_line(
                project,
                line,
                row.get("working_date") or row.get("updated_at"),
                1,
                row.get("id"),
            )
            remember_family_model(project, model)

    catalog = part_catalog or parts
    defect_lookups = sorted(set(parts) | set(projects))
    for start in range(0, len(defect_lookups), 80):
        chunk = [part for part in defect_lookups[start : start + 80] if len(part) >= 6]
        if not chunk:
            continue
        conditions = " OR ".join(["codigo LIKE %s"] * len(chunk))
        cursor.execute(
            f"""
            SELECT id, fecha, linea, codigo, modelo
            FROM defect_data
            WHERE COALESCE(codigo, '') <> ''
              AND COALESCE(linea, '') <> ''
              AND ({conditions})
            ORDER BY fecha DESC, id DESC
            """,
            [f"%{part}%" for part in chunk],
        )
        for row in cursor.fetchall():
            part = _resolve_part(row.get("codigo"), catalog)
            if part in part_set:
                remember_line(part, row.get("linea"), row.get("fecha"), 0, row.get("id"))
                remember_model(part, row.get("modelo"))
                continue
            project = _project_part_number(part)
            remember_family_line(project, row.get("linea"), row.get("fecha"), 0, row.get("id"))
            remember_family_model(project, row.get("modelo"))

    latest_line_by_part = {
        part: candidate["line"] for part, candidate in latest_line_candidate.items()
    }
    for part, candidate in latest_family_line_candidate.items():
        latest_line_by_part.setdefault(part, candidate["line"])
    for part in parts:
        forced_line = _forced_line_for_part(part)
        if forced_line:
            latest_line_by_part[part] = forced_line
    return latest_line_by_part, latest_model_by_part


def _fetch_lqc_inspections(cursor, start_dt, end_dt):
    cursor.execute(
        """
        SELECT
          b.id,
          b.serial,
          b.lot_no,
          b.last_scan,
          b.status,
          1 AS quantity,
          p.line AS plan_line,
          p.part_no AS plan_part,
          p.model_code AS plan_model
        FROM box_scans b
        LEFT JOIN (
          SELECT pm.*
          FROM plan_main pm
          INNER JOIN (
            SELECT lot_no, MAX(id) AS id
            FROM plan_main
            WHERE COALESCE(lot_no, '') <> ''
            GROUP BY lot_no
          ) latest
            ON latest.id = pm.id
        ) p
          ON p.lot_no = b.lot_no
        WHERE b.last_scan >= %s
          AND b.last_scan < %s
        """,
        (start_dt.strftime("%Y-%m-%d %H:%M:%S"), end_dt.strftime("%Y-%m-%d %H:%M:%S")),
    )
    return cursor.fetchall()


def _fetch_oqc_inspections(cursor, start_dt, end_dt):
    cursor.execute(
        """
        SELECT
          er.id,
          COALESCE(er.exit_date, er.created_at, CAST(er.inspection_date AS DATETIME)) AS last_scan,
          er.quantity,
          er.status,
          er.qc_passed,
          pn.part_number AS plan_part,
          pn.model AS plan_model,
          '' AS plan_line
        FROM exit_records er
        LEFT JOIN part_numbers pn
          ON pn.id = er.part_number_id
        WHERE COALESCE(er.exit_date, er.created_at, CAST(er.inspection_date AS DATETIME)) >= %s
          AND COALESCE(er.exit_date, er.created_at, CAST(er.inspection_date AS DATETIME)) < %s
          AND COALESCE(er.status, '') <> 'cancelled'
          AND COALESCE(er.qc_passed, 1) = 1
        """,
        (start_dt.strftime("%Y-%m-%d %H:%M:%S"), end_dt.strftime("%Y-%m-%d %H:%M:%S")),
    )
    return cursor.fetchall()


def _fetch_defects(cursor, start_dt, end_dt, stage):
    cursor.execute(
        """
        SELECT
          id,
          fecha,
          linea,
          codigo,
          modelo,
          defecto,
          status
        FROM defect_data
        WHERE fecha >= %s
          AND fecha < %s
          AND etapa_deteccion = %s
        """,
        (
            start_dt.strftime("%Y-%m-%d %H:%M:%S"),
            end_dt.strftime("%Y-%m-%d %H:%M:%S"),
            stage,
        ),
    )
    return cursor.fetchall()


def _prepare_ppm_records(cursor, start_dt, end_dt, part_catalog, model_by_part, stage):
    if stage == "OQC":
        inspection_rows = _fetch_oqc_inspections(cursor, start_dt, end_dt)
    else:
        inspection_rows = _fetch_lqc_inspections(cursor, start_dt, end_dt)
    defect_rows = _fetch_defects(cursor, start_dt, end_dt, stage)

    parts_seen = set()
    inspection_records = []
    defect_records = []

    for row in inspection_rows:
        part = _resolve_part(row.get("plan_part"), part_catalog) or _resolve_part(
            row.get("serial"), part_catalog
        )
        if part:
            parts_seen.add(part)
        inspection_records.append(
            {
                "date": row.get("last_scan"),
                "part_number": part,
                "model": model_by_part.get(part)
                or _normalize_text(row.get("plan_model")),
                "line": _normalize_line(row.get("plan_line")),
                "quantity": int(row.get("quantity") or 0) or 1,
            }
        )

    for row in defect_rows:
        part = _resolve_part(row.get("codigo"), part_catalog)
        if part:
            parts_seen.add(part)
        defect_records.append(
            {
                "date": row.get("fecha"),
                "part_number": part,
                "model": model_by_part.get(part)
                or _normalize_text(row.get("modelo")),
                "line": "",
                "fallback_line": _normalize_line(row.get("linea")),
            }
        )

    latest_line_by_part, latest_model_by_part = _load_latest_lines(
        cursor, parts_seen, part_catalog
    )

    for record in inspection_records:
        part = record.get("part_number") or ""
        if not record["line"]:
            record["line"] = _normalize_line(
                latest_line_by_part.get(part, "") or "SIN PLAN"
            )
        if not record["model"]:
            record["model"] = latest_model_by_part.get(part, "")

    for record in defect_records:
        part = record.get("part_number") or ""
        record["line"] = _normalize_line(
            latest_line_by_part.get(part, "")
            or record.get("fallback_line", "")
            or "SIN PLAN"
        )
        if not record["model"]:
            record["model"] = latest_model_by_part.get(part, "")

    return inspection_records, defect_records


def _matches_filters(record, selected_lines, search_text):
    if selected_lines and _normalize_line(record["line"]) not in selected_lines:
        return False
    if search_text:
        haystack = " ".join(
            [
                record.get("part_number") or "",
                record.get("model") or "",
                record.get("line") or "",
            ]
        ).upper()
        if search_text.upper() not in haystack:
            return False
    return True


def _finalize_metric(metric):
    metric["ppm"] = _ppm(metric["defects"], metric["inspected"])
    return metric


def _metric_payload(metric, target):
    return {
        "inspected": int(metric.get("inspected") or 0),
        "defects": int(metric.get("defects") or 0),
        "ppm": int(metric.get("ppm") or 0),
        "target": int(target or DEFAULT_LQC_TARGET),
    }


def _build_period_payload(
    inspection_records,
    defect_records,
    periods,
    group_by,
    selected_lines,
    search_text,
    target,
):
    by_period = {period["key"]: _empty_metric() for period in periods}
    for record in inspection_records:
        if not _matches_filters(record, selected_lines, search_text):
            continue
        key = _period_key(record["date"], group_by)
        by_period.setdefault(key, _empty_metric())["inspected"] += int(
            record.get("quantity") or 1
        )
    for record in defect_records:
        if not _matches_filters(record, selected_lines, search_text):
            continue
        key = _period_key(record["date"], group_by)
        by_period.setdefault(key, _empty_metric())["defects"] += 1

    for metric in by_period.values():
        _finalize_metric(metric)

    period_labels = {period["key"]: period["label"] for period in periods}
    return [
        {
            "key": key,
            "label": period_labels.get(key, _period_label(key, group_by)),
            **_metric_payload(by_period.get(key, _empty_metric()), target),
        }
        for key in [period["key"] for period in periods]
    ]


def _build_line_weekly_payload(
    inspection_records,
    defect_records,
    periods,
    selected_lines,
    search_text,
    target,
):
    period_keys = {period["key"] for period in periods}
    by_line_week = {}

    def ensure_line(line):
        if line not in by_line_week:
            by_line_week[line] = {period["key"]: _empty_metric() for period in periods}
        return by_line_week[line]

    for record in inspection_records:
        if not _matches_filters(record, selected_lines, search_text):
            continue
        key = _period_key(record["date"], "week")
        if key not in period_keys:
            continue
        line = record.get("line") or "SIN PLAN"
        ensure_line(line)[key]["inspected"] += int(record.get("quantity") or 1)

    for record in defect_records:
        if not _matches_filters(record, selected_lines, search_text):
            continue
        key = _period_key(record["date"], "week")
        if key not in period_keys:
            continue
        line = record.get("line") or "SIN PLAN"
        ensure_line(line)[key]["defects"] += 1

    rows = []
    for line, week_metrics in sorted(by_line_week.items()):
        weeks = []
        for period in periods:
            metric = week_metrics.get(period["key"], _empty_metric())
            _finalize_metric(metric)
            weeks.append(
                {
                    "key": period["key"],
                    "label": period["label"],
                    **_metric_payload(metric, target),
                }
            )
        rows.append({"line": line, "weeks": weeks})

    return {"periods": periods, "rows": rows}


def _build_ppms_payload(cursor, args, stage="LQC", module_key="lqc"):
    today = _today()
    default_start = date(today.year, today.month, 1)
    start_date = _parse_date(args.get("fecha_inicio"), default_start)
    end_date = _parse_date(args.get("fecha_fin"), today)
    start_date, end_date, start_dt, end_dt = _date_window(start_date, end_date)
    group_by = args.get("group_by") or "month"
    if group_by not in {"day", "week", "month"}:
        group_by = "month"

    selected_lines = {
        _normalize_line(line)
        for line in args.getlist("lineas")
        if _normalize_line(line)
    }
    search_text = _normalize_text(args.get("q"))
    target = _get_target(cursor, module_key)
    part_catalog, model_by_part = _load_part_catalog(cursor)

    trend_year = end_date.year
    trend_start = date(trend_year, 1, 1)
    trend_end = date(trend_year, 12, 31)
    _, _, trend_start_dt, trend_end_dt = _date_window(trend_start, trend_end)
    weekly_periods, weekly_start, weekly_end = _last_week_periods(end_date, 12)
    _, _, weekly_start_dt, weekly_end_dt = _date_window(weekly_start, weekly_end)
    trend_inspection_records, trend_defect_records = _prepare_ppm_records(
        cursor, trend_start_dt, trend_end_dt, part_catalog, model_by_part, stage
    )
    if trend_start_dt <= start_dt and end_dt <= trend_end_dt:
        inspection_records = [
            record
            for record in trend_inspection_records
            if start_dt <= record["date"] < end_dt
        ]
        defect_records = [
            record
            for record in trend_defect_records
            if start_dt <= record["date"] < end_dt
        ]
    else:
        inspection_records, defect_records = _prepare_ppm_records(
            cursor, start_dt, end_dt, part_catalog, model_by_part, stage
        )
    if trend_start_dt <= weekly_start_dt and weekly_end_dt <= trend_end_dt:
        weekly_inspection_records = [
            record
            for record in trend_inspection_records
            if weekly_start_dt <= record["date"] < weekly_end_dt
        ]
        weekly_defect_records = [
            record
            for record in trend_defect_records
            if weekly_start_dt <= record["date"] < weekly_end_dt
        ]
    else:
        weekly_inspection_records, weekly_defect_records = _prepare_ppm_records(
            cursor, weekly_start_dt, weekly_end_dt, part_catalog, model_by_part, stage
        )

    periods = _period_keys_between(start_date, end_date, group_by)
    period_payload = _build_period_payload(
        inspection_records,
        defect_records,
        periods,
        group_by,
        selected_lines,
        search_text,
        target,
    )
    trend_periods = _period_keys_between(trend_start, trend_end, "month")
    trend_payload = _build_period_payload(
        trend_inspection_records,
        trend_defect_records,
        trend_periods,
        "month",
        selected_lines,
        search_text,
        target,
    )
    line_weekly_payload = _build_line_weekly_payload(
        weekly_inspection_records,
        weekly_defect_records,
        weekly_periods,
        selected_lines,
        search_text,
        target,
    )
    by_line = defaultdict(_empty_metric)
    by_top_part = defaultdict(_empty_metric)
    by_part = defaultdict(_empty_metric)
    total = _empty_metric()
    lines_seen = set()

    for record in inspection_records:
        if not _matches_filters(record, selected_lines, search_text):
            continue
        inspected_quantity = int(record.get("quantity") or 1)
        by_line[record["line"]]["inspected"] += inspected_quantity
        part_number = record.get("part_number") or "SIN PARTE"
        project_number = _project_part_number(part_number)
        by_top_part[project_number]["inspected"] += inspected_quantity
        by_top_part[project_number]["part_number"] = project_number
        by_top_part[project_number]["model"] = record.get("model") or ""
        line = record.get("line") or "SIN PLAN"
        part_key = f"{line}||{part_number}"
        by_part[part_key]["inspected"] += inspected_quantity
        by_part[part_key]["part_number"] = part_number
        by_part[part_key]["model"] = record.get("model") or ""
        by_part[part_key]["line"] = line
        total["inspected"] += inspected_quantity
        lines_seen.add(record["line"])

    for record in defect_records:
        if not _matches_filters(record, selected_lines, search_text):
            continue
        by_line[record["line"]]["defects"] += 1
        part_number = record.get("part_number") or "SIN PARTE"
        project_number = _project_part_number(part_number)
        by_top_part[project_number]["defects"] += 1
        by_top_part[project_number]["part_number"] = project_number
        by_top_part[project_number]["model"] = record.get("model") or ""
        line = record.get("line") or "SIN PLAN"
        part_key = f"{line}||{part_number}"
        by_part[part_key]["defects"] += 1
        by_part[part_key]["part_number"] = part_number
        by_part[part_key]["model"] = record.get("model") or ""
        by_part[part_key]["line"] = line
        total["defects"] += 1
        lines_seen.add(record["line"])

    for metric in by_line.values():
        _finalize_metric(metric)
    for metric in by_top_part.values():
        _finalize_metric(metric)
    for metric in by_part.values():
        _finalize_metric(metric)
    _finalize_metric(total)

    line_payload = [
        {"line": line, **_metric_payload(metric, target)}
        for line, metric in sorted(by_line.items())
    ]
    top_part_payload = sorted(
        [
            {
                "part_number": metric.get("part_number") or part_number,
                "model": metric.get("model") or "",
                **_metric_payload(metric, target),
            }
            for part_number, metric in by_top_part.items()
        ],
        key=lambda item: (
            item["ppm"],
            item["defects"],
            item["inspected"],
        ),
        reverse=True,
    )
    part_payload = sorted(
        [
            {
                "part_number": metric.get("part_number") or part,
                "model": metric.get("model") or "",
                "line": metric.get("line") or "",
                **_metric_payload(metric, target),
            }
            for part, metric in by_part.items()
        ],
        key=lambda item: item["ppm"],
        reverse=True,
    )

    return {
        "success": True,
        "stage": stage,
        "target": target,
        "groupBy": group_by,
        "dateFrom": start_date.isoformat(),
        "dateTo": end_date.isoformat(),
        "summary": _metric_payload(total, target),
        "periods": period_payload,
        "trendYear": trend_year,
        "trendPeriods": trend_payload,
        "lines": sorted(lines_seen),
        "byLine": line_payload,
        "topParts": top_part_payload[:5],
        "topPartDetails": top_part_payload[:5],
        "lineWeeklyDetails": line_weekly_payload,
        "byPart": part_payload[:200],
    }


def _build_ppms_lqc_payload(cursor, args):
    return _build_ppms_payload(cursor, args, stage="LQC", module_key="lqc")


def _build_ppms_oqc_payload(cursor, args):
    return _build_ppms_payload(cursor, args, stage="OQC", module_key="oqc")


@bp.route("/control_calidad/ppms/iqc")
@login_requerido
def ppms_iqc_ajax():
    """Render inicial para PPM's IQC."""
    return render_template("Control de calidad/ppms_iqc_ajax.html")


@bp.route("/control_calidad/ppms/lqc")
@login_requerido
def ppms_lqc_ajax():
    """Render inicial para PPM's LQC."""
    return render_template("Control de calidad/ppms_lqc_ajax.html")


@bp.route("/control_calidad/ppms/oqc")
@login_requerido
def ppms_oqc_ajax():
    """Render inicial para PPM's OQC."""
    return render_template("Control de calidad/ppms_oqc_ajax.html")


@bp.route("/api/control_calidad/ppms/lqc", methods=["GET"])
@login_requerido
def ppms_lqc_data_api():
    conn = get_pooled_connection()
    if conn is None:
        return jsonify({"success": False, "error": "Base de datos no disponible"}), 503
    cursor = get_dict_cursor(conn)
    try:
        return jsonify(_build_ppms_lqc_payload(cursor, request.args))
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500
    finally:
        cursor.close()
        conn.close()


@bp.route("/api/control_calidad/ppms/oqc", methods=["GET"])
@login_requerido
def ppms_oqc_data_api():
    conn = get_pooled_connection()
    if conn is None:
        return jsonify({"success": False, "error": "Base de datos no disponible"}), 503
    cursor = get_dict_cursor(conn)
    try:
        return jsonify(_build_ppms_oqc_payload(cursor, request.args))
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500
    finally:
        cursor.close()
        conn.close()


@bp.route("/api/control_calidad/ppms/lqc/target", methods=["GET", "POST"])
@login_requerido
def ppms_lqc_target_api():
    conn = get_pooled_connection()
    if conn is None:
        return jsonify({"success": False, "error": "Base de datos no disponible"}), 503
    cursor = get_dict_cursor(conn)
    try:
        if request.method == "POST":
            data = request.get_json(silent=True) or {}
            target = normalize_integer(data.get("target"))
            if target is None or target < 0:
                return jsonify({"success": False, "error": "Target invalido"}), 400
            _set_target(cursor, target, "lqc")
            conn.commit()
        target = _get_target(cursor, "lqc")
        return jsonify({"success": True, "target": target})
    except Exception as exc:
        conn.rollback()
        return jsonify({"success": False, "error": str(exc)}), 500
    finally:
        cursor.close()
        conn.close()


@bp.route("/api/control_calidad/ppms/oqc/target", methods=["GET", "POST"])
@login_requerido
def ppms_oqc_target_api():
    conn = get_pooled_connection()
    if conn is None:
        return jsonify({"success": False, "error": "Base de datos no disponible"}), 503
    cursor = get_dict_cursor(conn)
    try:
        if request.method == "POST":
            data = request.get_json(silent=True) or {}
            target = normalize_integer(data.get("target"))
            if target is None or target < 0:
                return jsonify({"success": False, "error": "Target invalido"}), 400
            _set_target(cursor, target, "oqc")
            conn.commit()
        target = _get_target(cursor, "oqc")
        return jsonify({"success": True, "target": target})
    except Exception as exc:
        conn.rollback()
        return jsonify({"success": False, "error": str(exc)}), 500
    finally:
        cursor.close()
        conn.close()
