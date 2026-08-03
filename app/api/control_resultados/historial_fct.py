"""Endpoints HTTP del modulo "Historial de maquina FCT".

Consumido por LISTA_DE_CONTROL_DE_RESULTADOS / Historial de maquinas calidad.
Template: app/templates/Control de resultados/history_fct.html
JS:       app/static/js/fct.js
"""

from __future__ import annotations

import logging

from flask import Blueprint, jsonify, redirect, render_template, request

from app.api.shared import excel_response_ict, execute_query, login_requerido
from app.api.shared.fct_helpers import (
    FCT_TS_EXPR,
    PENDING_TEXT,
    SIN_ESTACION_TEXT,
    SIN_NUMERO_PARTE_TEXT,
    fct_attach_operator,
    fct_line_expr,
    fct_operator_line_expr,
    fct_plan_line_join,
    fmt_date,
    fmt_datetime,
    fmt_time,
    normalize_result,
    parse_steps_json,
    to_int,
)

logger = logging.getLogger(__name__)

bp = Blueprint("historial_fct", __name__)

_FCT_HISTORY_COLUMN_FILTER_SQL = {
    "fecha": "CAST(f.folder_date AS CHAR) LIKE %s",
    "hora": f"CAST(TIME({FCT_TS_EXPR}) AS CHAR) LIKE %s",
    "linea": f"{fct_line_expr()} LIKE %s",
    "estacion": "f.station LIKE %s",
    "resultado": "f.final_result LIKE %s",
    "operador": f"'{PENDING_TEXT}' LIKE %s",
    "no_parte": "f.part_number LIKE %s",
    "serial_number": "f.serial_number LIKE %s",
    "fuente_archivo": "f.source_file LIKE %s",
    "failed_step": "COALESCE(f.failed_step, '') LIKE %s",
    "failed_test_name": "COALESCE(f.failed_test_name, '') LIKE %s",
}


def _append_fct_history_column_filters(sql: str, params: list) -> str:
    for key, clause in _FCT_HISTORY_COLUMN_FILTER_SQL.items():
        value = request.args.get(f"cf_{key}", "").strip()
        if value:
            sql += f" AND {clause}"
            params.append(f"%{value}%")
    return sql


def _fct_base_from() -> str:
    return " FROM fct_test_results f" + fct_plan_line_join(FCT_TS_EXPR)


def _fct_select_cols() -> str:
    line_expr = fct_line_expr()
    operator_line_expr = fct_operator_line_expr()
    return (
        "SELECT f.source_path_hash, f.folder_date AS fecha, "
        f"TIME({FCT_TS_EXPR}) AS hora, "
        f"{line_expr} AS linea, "
        f"{operator_line_expr} AS operator_line, "
        f"COALESCE(NULLIF(TRIM(f.station), ''), '{SIN_ESTACION_TEXT}') AS estacion, "
        "f.final_result AS resultado, "
        f"COALESCE(NULLIF(TRIM(f.part_number), ''), '{SIN_NUMERO_PARTE_TEXT}') AS no_parte, "
        "f.serial_number, "
        f"{FCT_TS_EXPR} AS ts, "
        "f.start_at, f.end_at, f.duration_seconds, f.source_file AS fuente_archivo, "
        "f.failed_step, f.failed_test_name, f.failed_measured_value, f.failed_unit, "
        "f.failed_nominal, f.failed_upper_limit, f.failed_lower_limit, f.failed_row_result, "
        "f.row_count, f.malformed_row_count, "
        f"'{PENDING_TEXT}' AS operador"
    )


def _append_fct_filters(where_sql: str, params: list) -> str:
    fecha = request.args.get("fecha", "").strip()
    fecha_desde = request.args.get("fecha_desde", "").strip()
    fecha_hasta = request.args.get("fecha_hasta", "").strip()
    no_parte = request.args.get("no_parte", "").strip() or request.args.get("numero_parte", "").strip()
    linea = request.args.get("linea", "").strip()
    estacion = request.args.get("estacion", "").strip()
    resultado = request.args.get("resultado", "").strip().upper()
    serial_like = request.args.get("serial_like", "").strip() or request.args.get("barcode_like", "").strip()

    if fecha_desde or fecha_hasta:
        if fecha_desde:
            where_sql += " AND f.folder_date >= %s"
            params.append(fecha_desde)
        if fecha_hasta:
            where_sql += " AND f.folder_date <= %s"
            params.append(fecha_hasta)
    elif fecha:
        where_sql += " AND f.folder_date = %s"
        params.append(fecha)
    if no_parte:
        where_sql += " AND f.part_number LIKE %s"
        params.append(f"{no_parte}%")
    if linea:
        where_sql += f" AND {fct_line_expr()} = %s"
        params.append(linea)
    if estacion:
        where_sql += " AND f.station LIKE %s"
        params.append(f"%{estacion}%")
    if resultado:
        where_sql += " AND f.final_result = %s"
        params.append(normalize_result(resultado))
    if serial_like:
        if len(serial_like) >= 12:
            where_sql += " AND f.serial_number = %s"
            params.append(serial_like)
        else:
            where_sql += " AND f.serial_number LIKE %s"
            params.append(f"{serial_like}%")

    return _append_fct_history_column_filters(where_sql, params)


def _format_fct_row(row: dict) -> dict:
    return {
        "source_path_hash": row.get("source_path_hash") or "",
        "fecha": fmt_date(row.get("fecha")),
        "hora": fmt_time(row.get("hora")),
        "linea": row.get("linea") or "SIN PLAN",
        "estacion": row.get("estacion") or SIN_ESTACION_TEXT,
        "resultado": normalize_result(row.get("resultado")),
        "operador": row.get("operador") or PENDING_TEXT,
        "no_parte": row.get("no_parte") or SIN_NUMERO_PARTE_TEXT,
        "serial_number": row.get("serial_number") or "",
        "ts": fmt_datetime(row.get("ts")),
        "start_at": fmt_datetime(row.get("start_at")),
        "end_at": fmt_datetime(row.get("end_at")),
        "duration_seconds": to_int(row.get("duration_seconds")),
        "fuente_archivo": row.get("fuente_archivo") or "",
        "failed_step": row.get("failed_step") or "",
        "failed_test_name": row.get("failed_test_name") or "",
        "failed_measured_value": row.get("failed_measured_value") or "",
        "failed_unit": row.get("failed_unit") or "",
        "failed_nominal": row.get("failed_nominal") or "",
        "failed_upper_limit": row.get("failed_upper_limit") or "",
        "failed_lower_limit": row.get("failed_lower_limit") or "",
        "failed_row_result": row.get("failed_row_result") or "",
        "row_count": to_int(row.get("row_count")),
        "malformed_row_count": to_int(row.get("malformed_row_count")),
    }


def _format_step(row: dict, idx: int) -> dict:
    result = normalize_result(row.get("row_result") or row.get("file_result"))
    return {
        "idx": idx,
        "step": row.get("step") or "",
        "serial_number": row.get("serial_number") or "",
        "estacion": row.get("station") or "",
        "tested_at": row.get("tested_at") or "",
        "test_name": row.get("test_name") or "",
        "measured_value": row.get("measured_value") or "",
        "unit": row.get("unit") or "",
        "nominal": row.get("nominal_or_expected") or "",
        "upper_limit": row.get("upper_or_expected") or "",
        "lower_limit": row.get("lower_or_expected") or "",
        "row_result": result,
        "file_result": row.get("file_result") or "",
    }


@bp.route("/historial_fct/ajax")
@login_requerido
def historial_fct_ajax():
    try:
        return render_template("Control de resultados/history_fct.html")
    except Exception as exc:  # pragma: no cover - render error path
        logger.exception("Error al cargar Historial FCT")
        return f"Error al cargar el contenido: {exc}", 500


@bp.route("/historial-fct")
@bp.route("/historial-fct-ajax")
def alias_legacy_historial_fct():
    return redirect("/historial_fct/ajax", code=301)


@bp.route("/api/fct/data")
@login_requerido
def fct_data_api():
    try:
        page_raw = request.args.get("page", "").strip()
        per_page_raw = request.args.get("per_page", "").strip()
        paginated = bool(page_raw)
        serial_like = request.args.get("serial_like", "").strip() or request.args.get("barcode_like", "").strip()
        if serial_like and len(serial_like) < 6:
            empty = {"rows": [], "total": 0, "page": 1, "per_page": 0, "total_pages": 0}
            return jsonify(empty if paginated else [])

        params: list = []
        where_sql = _append_fct_filters(" WHERE 1=1", params)
        from_sql = _fct_base_from()

        if paginated:
            try:
                page = max(1, int(page_raw))
            except ValueError:
                page = 1
            try:
                per_page = int(per_page_raw) if per_page_raw else 1000
            except ValueError:
                per_page = 1000
            per_page = max(1, min(per_page, 1000))

            count_row = execute_query(
                "SELECT COUNT(*) AS n" + from_sql + where_sql,
                tuple(params),
                fetch="one",
            ) or {}
            total = to_int(count_row.get("n"))
            offset = (page - 1) * per_page
            rows = execute_query(
                _fct_select_cols() + from_sql + where_sql + f" ORDER BY {FCT_TS_EXPR} DESC LIMIT %s OFFSET %s",
                tuple(params) + (per_page, offset),
                fetch="all",
            ) or []
            fct_attach_operator(rows)
            total_pages = (total + per_page - 1) // per_page if per_page else 0
            return jsonify({
                "rows": [_format_fct_row(row) for row in rows],
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": total_pages,
            })

        rows = execute_query(
            _fct_select_cols() + from_sql + where_sql + f" ORDER BY {FCT_TS_EXPR} DESC LIMIT 500",
            tuple(params),
            fetch="all",
        ) or []
        fct_attach_operator(rows)
        return jsonify([_format_fct_row(row) for row in rows])
    except Exception as exc:
        logger.exception("Error en endpoint FCT")
        return jsonify({"error": str(exc)}), 500


@bp.route("/api/fct/steps")
@login_requerido
def fct_steps_api():
    source_path_hash = request.args.get("source_path_hash", "").strip()
    only_fail = request.args.get("only_fail", "").strip() in {"1", "true", "TRUE"}
    if not source_path_hash:
        return jsonify([])
    try:
        row = execute_query(
            "SELECT test_steps_json FROM fct_test_results WHERE source_path_hash = %s LIMIT 1",
            (source_path_hash,),
            fetch="one",
        ) or {}
        steps = [_format_step(item, idx + 1) for idx, item in enumerate(parse_steps_json(row.get("test_steps_json")))]
        if only_fail:
            steps = [item for item in steps if item.get("row_result") == "FAIL"]
        return jsonify(steps)
    except Exception as exc:
        logger.exception("Error en endpoint FCT steps")
        return jsonify({"error": str(exc)}), 500


@bp.route("/api/fct/export")
@login_requerido
def export_fct_excel():
    try:
        params: list = []
        where_sql = _append_fct_filters(" WHERE 1=1", params)
        rows = execute_query(
            _fct_select_cols() + _fct_base_from() + where_sql + f" ORDER BY {FCT_TS_EXPR} DESC LIMIT 50000",
            tuple(params),
            fetch="all",
        ) or []
        fct_attach_operator(rows)
        data = [_format_fct_row(row) for row in rows]
        return excel_response_ict(
            data,
            [
                "Fecha", "Hora", "Linea", "Estacion", "Resultado", "Operador",
                "No Parte", "Serial", "Inicio", "Fin", "Duracion seg", "Fuente",
                "Paso fallo", "Prueba fallo", "Valor", "Unidad", "Nominal", "Limite sup", "Limite inf",
                "Filas", "Filas malformadas",
            ],
            [
                "fecha", "hora", "linea", "estacion", "resultado", "operador",
                "no_parte", "serial_number", "start_at", "end_at", "duration_seconds", "fuente_archivo",
                "failed_step", "failed_test_name", "failed_measured_value", "failed_unit", "failed_nominal",
                "failed_upper_limit", "failed_lower_limit", "row_count", "malformed_row_count",
            ],
            [12, 10, 14, 18, 12, 18, 18, 26, 20, 20, 12, 32, 12, 28, 16, 10, 14, 14, 14, 10, 14],
            "Historial FCT",
            "historial_fct",
            freeze="A2",
        )
    except Exception as exc:
        logger.exception("Error exportando Historial FCT")
        return jsonify({"error": str(exc)}), 500
