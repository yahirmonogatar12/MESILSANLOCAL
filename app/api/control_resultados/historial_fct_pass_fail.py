"""Endpoints HTTP del modulo "Historial de maquina FCT % Pass/Fail"."""

from __future__ import annotations

import logging
import re

from flask import Blueprint, jsonify, redirect, render_template, request

from app.api.shared import excel_response_ict, execute_query, login_requerido
from app.api.shared.fct_helpers import (
    FCT_TS_EXPR,
    PENDING_TEXT,
    SIN_ESTACION_TEXT,
    SIN_NUMERO_PARTE_TEXT,
    fct_attach_operator,
    fct_attach_summary_operators,
    fct_fecha_jornada_expr,
    fct_line_expr,
    fct_operator_line_expr,
    fct_plan_line_join,
    fct_shift_bounds,
    fct_turno_expr,
    fmt_date,
    fmt_datetime,
    normalize_result,
    to_float,
    to_int,
)

logger = logging.getLogger(__name__)

bp = Blueprint("historial_fct_pass_fail", __name__)


def _parse_numeros_parte(raw: str | None, limit: int = 200) -> list[str]:
    if not raw:
        return []
    seen: list[str] = []
    for token in re.split(r"[\s,;]+", raw):
        value = token.strip()
        if value and value not in seen:
            seen.append(value)
        if len(seen) >= limit:
            break
    return seen


def _append_common_filters(sql: str, params: list, *, include_group_filters: bool = False) -> str:
    fecha_desde = request.args.get("fecha_desde", "").strip() or request.args.get("fecha", "").strip()
    fecha_hasta = request.args.get("fecha_hasta", "").strip() or fecha_desde
    numero_parte = request.args.get("numero_parte", "").strip() or request.args.get("no_parte", "").strip()
    numeros_parte = _parse_numeros_parte(request.args.get("numeros_parte", ""))
    turno = request.args.get("turno", "").strip().upper()
    linea = request.args.get("linea", "").strip()
    estacion = request.args.get("estacion", "").strip()
    serial = request.args.get("serial", "").strip() or request.args.get("barcode", "").strip()

    start_dt, end_dt = fct_shift_bounds(fecha_desde, fecha_hasta)
    if start_dt:
        sql += f" AND {FCT_TS_EXPR} >= %s"
        params.append(start_dt)
    if end_dt:
        sql += f" AND {FCT_TS_EXPR} < %s"
        params.append(end_dt)

    if numeros_parte:
        placeholders = " OR ".join(["f.part_number LIKE %s"] * len(numeros_parte))
        sql += f" AND ({placeholders})"
        params.extend(f"{part}%" for part in numeros_parte)
    elif numero_parte:
        sql += " AND f.part_number LIKE %s"
        params.append(f"{numero_parte}%")
    if turno:
        sql += f" AND {fct_turno_expr(FCT_TS_EXPR)} = %s"
        params.append(turno)
    if linea:
        sql += f" AND {fct_line_expr()} = %s"
        params.append(linea)
    if estacion:
        sql += " AND f.station LIKE %s"
        params.append(f"%{estacion}%")
    if serial:
        sql += " AND f.serial_number LIKE %s"
        params.append(f"%{serial}%")

    if include_group_filters:
        fecha_jornada = request.args.get("fecha_jornada", "").strip()
        grupo_linea = request.args.get("grupo_linea", "").strip()
        grupo_estacion = request.args.get("grupo_estacion", "").strip()
        grupo_turno = request.args.get("grupo_turno", "").strip()
        grupo_numero_parte = request.args.get("grupo_numero_parte", "").strip()
        if fecha_jornada:
            sql += f" AND {fct_fecha_jornada_expr(FCT_TS_EXPR)} = %s"
            params.append(fecha_jornada)
        if grupo_linea:
            sql += f" AND {fct_line_expr()} = %s"
            params.append(grupo_linea)
        if grupo_estacion:
            sql += " AND COALESCE(NULLIF(TRIM(f.station), ''), %s) = %s"
            params.extend([SIN_ESTACION_TEXT, grupo_estacion])
        if grupo_turno:
            sql += f" AND {fct_turno_expr(FCT_TS_EXPR)} = %s"
            params.append(grupo_turno)
        if grupo_numero_parte:
            sql += " AND COALESCE(NULLIF(TRIM(f.part_number), ''), %s) = %s"
            params.extend([SIN_NUMERO_PARTE_TEXT, grupo_numero_parte])

    return sql


def _format_summary(row: dict) -> dict:
    total = to_int(row.get("total"))
    pass_count = to_int(row.get("pass_count"))
    fail_count = to_int(row.get("fail_count"))
    unknown_count = to_int(row.get("unknown_count"))
    return {
        "fecha": fmt_date(row.get("fecha")),
        "linea": row.get("linea") or "SIN PLAN",
        "estacion": row.get("estacion") or SIN_ESTACION_TEXT,
        "turno": row.get("turno") or "",
        "numero_parte": row.get("numero_parte") or SIN_NUMERO_PARTE_TEXT,
        "primer_test": fmt_datetime(row.get("primer_test")),
        "ultimo_test": fmt_datetime(row.get("ultimo_test")),
        "total": total,
        "pass_count": pass_count,
        "fail_count": fail_count,
        "unknown_count": unknown_count,
        "pass_pct": round(to_float(row.get("pass_pct")), 2) if total else 0,
        "fail_pct": round(to_float(row.get("fail_pct")), 2) if total else 0,
        "unknown_pct": round(to_float(row.get("unknown_pct")), 2) if total else 0,
        "piezas_unicas": to_int(row.get("piezas_unicas")),
        "piezas_repetidas": to_int(row.get("piezas_repetidas")),
        "fallas_con_paso": to_int(row.get("fallas_con_paso")),
        "fallas_sin_paso": to_int(row.get("fallas_sin_paso")),
        "operador": row.get("operador") or PENDING_TEXT,
    }


def _format_detail(row: dict) -> dict:
    return {
        "fecha": fmt_date(row.get("fecha")),
        "linea": row.get("linea") or "SIN PLAN",
        "estacion": row.get("estacion") or SIN_ESTACION_TEXT,
        "turno": row.get("turno") or "",
        "numero_parte": row.get("numero_parte") or SIN_NUMERO_PARTE_TEXT,
        "serial_number": row.get("serial_number") or "",
        "resultado": normalize_result(row.get("resultado")),
        "start_at": fmt_datetime(row.get("start_at")),
        "end_at": fmt_datetime(row.get("end_at")),
        "source_path_hash": row.get("source_path_hash") or "",
        "fuente_archivo": row.get("fuente_archivo") or "",
        "failed_step": row.get("failed_step") or "",
        "failed_test_name": row.get("failed_test_name") or "",
        "failed_measured_value": row.get("failed_measured_value") or "",
        "failed_unit": row.get("failed_unit") or "",
        "operador": row.get("operador") or PENDING_TEXT,
    }


def _summary_query() -> tuple[str, tuple]:
    params: list = []
    fecha_expr = fct_fecha_jornada_expr(FCT_TS_EXPR)
    turno_expr = fct_turno_expr(FCT_TS_EXPR)
    line_expr = fct_line_expr()
    operator_line_expr = fct_operator_line_expr()
    estacion_expr = f"COALESCE(NULLIF(TRIM(f.station), ''), '{SIN_ESTACION_TEXT}')"
    numero_parte_expr = f"COALESCE(NULLIF(TRIM(f.part_number), ''), '{SIN_NUMERO_PARTE_TEXT}')"
    where_sql = _append_common_filters(" WHERE 1=1", params)

    sql = (
        "SELECT "
        f"{fecha_expr} AS fecha, {line_expr} AS linea, {estacion_expr} AS estacion, "
        f"{operator_line_expr} AS operator_line, "
        f"{turno_expr} AS turno, {numero_parte_expr} AS numero_parte, "
        f"MIN({FCT_TS_EXPR}) AS primer_test, MAX({FCT_TS_EXPR}) AS ultimo_test, "
        "COUNT(*) AS total, "
        "SUM(CASE WHEN UPPER(COALESCE(f.final_result, '')) = 'PASS' THEN 1 ELSE 0 END) AS pass_count, "
        "SUM(CASE WHEN UPPER(COALESCE(f.final_result, '')) = 'FAIL' THEN 1 ELSE 0 END) AS fail_count, "
        "SUM(CASE WHEN UPPER(COALESCE(f.final_result, '')) NOT IN ('PASS', 'FAIL') THEN 1 ELSE 0 END) AS unknown_count, "
        "ROUND(100 * SUM(CASE WHEN UPPER(COALESCE(f.final_result, '')) = 'PASS' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2) AS pass_pct, "
        "ROUND(100 * SUM(CASE WHEN UPPER(COALESCE(f.final_result, '')) = 'FAIL' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2) AS fail_pct, "
        "ROUND(100 * SUM(CASE WHEN UPPER(COALESCE(f.final_result, '')) NOT IN ('PASS', 'FAIL') THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2) AS unknown_pct, "
        "COUNT(DISTINCT f.serial_number) AS piezas_unicas, "
        "GREATEST(COUNT(*) - COUNT(DISTINCT f.serial_number), 0) AS piezas_repetidas, "
        "SUM(CASE WHEN UPPER(COALESCE(f.final_result, '')) = 'FAIL' AND COALESCE(f.failed_step, '') <> '' THEN 1 ELSE 0 END) AS fallas_con_paso, "
        "SUM(CASE WHEN UPPER(COALESCE(f.final_result, '')) = 'FAIL' AND COALESCE(f.failed_step, '') = '' THEN 1 ELSE 0 END) AS fallas_sin_paso "
        "FROM fct_test_results f"
        f"{fct_plan_line_join(FCT_TS_EXPR)}"
        f"{where_sql} "
        f"GROUP BY {fecha_expr}, {line_expr}, {operator_line_expr}, {estacion_expr}, {turno_expr}, {numero_parte_expr} "
        "ORDER BY fecha DESC, linea ASC, estacion ASC, turno ASC, numero_parte ASC "
        "LIMIT 5000"
    )
    return sql, tuple(params)


@bp.route("/historial_fct_pass_fail/ajax")
@login_requerido
def historial_fct_pass_fail_ajax():
    try:
        return render_template("Control de resultados/history_fct_Pass_Fail.html")
    except Exception as exc:  # pragma: no cover - render error path
        logger.exception("Error al cargar Historial FCT Pass/Fail")
        return f"Error al cargar el contenido: {exc}", 500


@bp.route("/historial-maquina-fct-pass-fail")
@bp.route("/historial-maquina-fct-pass-fail-ajax")
def alias_legacy_historial_fct_pass_fail():
    return redirect("/historial_fct_pass_fail/ajax", code=301)


@bp.route("/api/fct/pass-fail")
@login_requerido
def fct_pass_fail_api():
    try:
        sql, params = _summary_query()
        rows = execute_query(sql, params, fetch="all") or []
        fct_attach_summary_operators(rows)
        return jsonify([_format_summary(row) for row in rows])
    except Exception as exc:
        logger.exception("Error en endpoint FCT Pass/Fail")
        return jsonify({"error": str(exc)}), 500


@bp.route("/api/fct/pass-fail/detail")
@login_requerido
def fct_pass_fail_detail_api():
    try:
        params: list = []
        where_sql = _append_common_filters(" WHERE 1=1", params, include_group_filters=True)
        rows = execute_query(
            "SELECT "
            f"{fct_fecha_jornada_expr(FCT_TS_EXPR)} AS fecha, "
            f"{fct_line_expr()} AS linea, "
            f"{fct_operator_line_expr()} AS operator_line, "
            f"COALESCE(NULLIF(TRIM(f.station), ''), '{SIN_ESTACION_TEXT}') AS estacion, "
            f"{fct_turno_expr(FCT_TS_EXPR)} AS turno, "
            f"COALESCE(NULLIF(TRIM(f.part_number), ''), '{SIN_NUMERO_PARTE_TEXT}') AS numero_parte, "
            "f.serial_number, f.final_result AS resultado, f.start_at, f.end_at, "
            f"{FCT_TS_EXPR} AS ts, "
            "f.source_path_hash, f.source_file AS fuente_archivo, f.failed_step, f.failed_test_name, "
            "f.failed_measured_value, f.failed_unit "
            "FROM fct_test_results f"
            f"{fct_plan_line_join(FCT_TS_EXPR)}"
            f"{where_sql} "
            f"ORDER BY {FCT_TS_EXPR} DESC LIMIT 2000",
            tuple(params),
            fetch="all",
        ) or []
        fct_attach_operator(rows)
        return jsonify([_format_detail(row) for row in rows])
    except Exception as exc:
        logger.exception("Error en detalle FCT Pass/Fail")
        return jsonify({"error": str(exc)}), 500


@bp.route("/api/fct/pass-fail/export")
@login_requerido
def export_fct_pass_fail_excel():
    try:
        sql, params = _summary_query()
        rows = execute_query(sql, params, fetch="all") or []
        fct_attach_summary_operators(rows)
        data = [_format_summary(row) for row in rows]
        return excel_response_ict(
            data,
            [
                "Fecha", "Linea", "Estacion", "Turno", "No Parte", "Primer test", "Ultimo test",
                "Total", "PASS", "FAIL", "UNKNOWN", "% PASS", "% FAIL", "% UNKNOWN",
                "Piezas unicas", "Piezas repetidas", "Fallas con paso", "Fallas sin paso",
                "Operador",
            ],
            [
                "fecha", "linea", "estacion", "turno", "numero_parte", "primer_test", "ultimo_test",
                "total", "pass_count", "fail_count", "unknown_count", "pass_pct", "fail_pct", "unknown_pct",
                "piezas_unicas", "piezas_repetidas", "fallas_con_paso", "fallas_sin_paso",
                "operador",
            ],
            [12, 14, 18, 12, 18, 20, 20, 10, 10, 10, 10, 10, 10, 12, 14, 16, 14, 14, 18],
            "FCT PassFail",
            "historial_fct_pass_fail",
            freeze="A2",
        )
    except Exception as exc:
        logger.exception("Error exportando FCT Pass/Fail")
        return jsonify({"error": str(exc)}), 500
