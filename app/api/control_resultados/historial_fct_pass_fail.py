"""Endpoints HTTP del modulo "Historial de maquina FCT % Pass/Fail"."""

from __future__ import annotations

import logging
import re
from datetime import timedelta

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


def _request_shift_bounds():
    fecha_desde = request.args.get("fecha_desde", "").strip() or request.args.get("fecha", "").strip()
    fecha_hasta = request.args.get("fecha_hasta", "").strip() or fecha_desde
    return fct_shift_bounds(fecha_desde, fecha_hasta)


def _append_common_filters(
    sql: str,
    params: list,
    *,
    include_group_filters: bool = False,
    bounds: tuple | None = None,
    with_linea: bool = True,
) -> str:
    numero_parte = request.args.get("numero_parte", "").strip() or request.args.get("no_parte", "").strip()
    numeros_parte = _parse_numeros_parte(request.args.get("numeros_parte", ""))
    turno = request.args.get("turno", "").strip().upper()
    linea = request.args.get("linea", "").strip() if with_linea else ""
    estacion = request.args.get("estacion", "").strip()
    serial = request.args.get("serial", "").strip() or request.args.get("barcode", "").strip()

    start_dt, end_dt = bounds or _request_shift_bounds()
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
        # None = no calculado (ver _summary_query piezas=False).
        "piezas_unicas": None if row.get("piezas_unicas") is None else to_int(row.get("piezas_unicas")),
        "piezas_repetidas": None if row.get("piezas_repetidas") is None else to_int(row.get("piezas_repetidas")),
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


def _summary_query(bounds: tuple, piezas: bool) -> tuple[str, tuple]:
    """Resumen de una ventana de fechas en 2 niveles.

    Nivel interno: agrupa por llaves baratas (sin el join al plan, que por
    fila costaba ~5s/año). Nivel externo: une el plan ya agrupado y reagrupa
    por linea/operator_line. Las columnas internas se llaman station /
    part_number / station_line para reusar tal cual los helpers de fct_helpers.
    ponytail: si dos grupos internos caen en la misma fila externa (misma
    estacion con station_line distinta el mismo turno) piezas_unicas se suma
    y contaria doble un serial presente en ambos; no pasa en los datos.
    piezas=False omite COUNT(DISTINCT serial) (~2/3 del costo): la pantalla
    no muestra piezas unicas/repetidas, solo el Excel.
    """
    params: list = []
    where_sql = _append_common_filters(" WHERE 1=1", params, bounds=bounds, with_linea=False)
    inner = (
        "SELECT "
        f"{fct_fecha_jornada_expr(FCT_TS_EXPR)} AS fecha, {fct_turno_expr(FCT_TS_EXPR)} AS turno, "
        f"COALESCE(NULLIF(TRIM(f.station), ''), '{SIN_ESTACION_TEXT}') AS station, "
        f"COALESCE(NULLIF(TRIM(f.part_number), ''), '{SIN_NUMERO_PARTE_TEXT}') AS numero_parte, "
        "NULLIF(TRIM(f.part_number), '') AS part_number, "
        "CASE UPPER(TRIM(COALESCE(f.station_line, ''))) "
        "WHEN 'L01' THEN 'M1' WHEN 'L02' THEN 'M2' WHEN 'L03' THEN 'M3' WHEN 'L04' THEN 'M4' "
        "WHEN 'M1' THEN 'M1' WHEN 'M2' THEN 'M2' WHEN 'M3' THEN 'M3' WHEN 'M4' THEN 'M4' "
        "END AS station_line, "
        f"MIN({FCT_TS_EXPR}) AS primer_test, MAX({FCT_TS_EXPR}) AS ultimo_test, "
        "COUNT(*) AS total, "
        "SUM(CASE WHEN UPPER(COALESCE(f.final_result, '')) = 'PASS' THEN 1 ELSE 0 END) AS pass_count, "
        "SUM(CASE WHEN UPPER(COALESCE(f.final_result, '')) = 'FAIL' THEN 1 ELSE 0 END) AS fail_count, "
        "SUM(CASE WHEN UPPER(COALESCE(f.final_result, '')) NOT IN ('PASS', 'FAIL') THEN 1 ELSE 0 END) AS unknown_count, "
        f"{'COUNT(DISTINCT f.serial_number)' if piezas else 'NULL'} AS piezas_unicas, "
        "SUM(CASE WHEN UPPER(COALESCE(f.final_result, '')) = 'FAIL' AND COALESCE(f.failed_step, '') <> '' THEN 1 ELSE 0 END) AS fallas_con_paso, "
        "SUM(CASE WHEN UPPER(COALESCE(f.final_result, '')) = 'FAIL' AND COALESCE(f.failed_step, '') = '' THEN 1 ELSE 0 END) AS fallas_sin_paso "
        f"FROM fct_test_results f{where_sql} "
        # Posicional: station/part_number/station_line chocan con columnas reales.
        "GROUP BY 1, 2, 3, 4, 5, 6"
    )

    outer_where = " WHERE 1=1"
    linea = request.args.get("linea", "").strip()
    if linea:
        outer_where += f" AND {fct_line_expr()} = %s"
        params.append(linea)

    sql = (
        "SELECT f.fecha, "
        f"{fct_line_expr()} AS linea, f.station AS estacion, "
        f"{fct_operator_line_expr()} AS operator_line, "
        "f.turno, f.numero_parte, "
        "MIN(f.primer_test) AS primer_test, MAX(f.ultimo_test) AS ultimo_test, "
        "SUM(f.total) AS total, SUM(f.pass_count) AS pass_count, "
        "SUM(f.fail_count) AS fail_count, SUM(f.unknown_count) AS unknown_count, "
        "ROUND(100 * SUM(f.pass_count) / NULLIF(SUM(f.total), 0), 2) AS pass_pct, "
        "ROUND(100 * SUM(f.fail_count) / NULLIF(SUM(f.total), 0), 2) AS fail_pct, "
        "ROUND(100 * SUM(f.unknown_count) / NULLIF(SUM(f.total), 0), 2) AS unknown_pct, "
        "SUM(f.piezas_unicas) AS piezas_unicas, "
        "GREATEST(SUM(f.total) - SUM(f.piezas_unicas), 0) AS piezas_repetidas, "
        "SUM(f.fallas_con_paso) AS fallas_con_paso, SUM(f.fallas_sin_paso) AS fallas_sin_paso "
        # primer_test cae en la misma jornada que fecha -> mismo join del plan.
        f"FROM ({inner}) f{fct_plan_line_join('f.primer_test')}{outer_where} "
        "GROUP BY 1, 2, 3, 4, 5, 6 "
        "ORDER BY fecha DESC, linea ASC, estacion ASC, turno ASC, numero_parte ASC "
        "LIMIT 5000"
    )
    return sql, tuple(params)


def _fetch_summary_rows(piezas: bool = False) -> list[dict]:
    """Resumen del rango en ventanas de 31 jornadas, de la mas nueva a la mas vieja.

    Un año en un solo query tardaba ~40s y el pool corta a los 10s
    (read_timeout); por ventana queda en ~1-2s. Las ventanas cortan a las
    07:30 (frontera de jornada) asi que ninguna fila se parte, y como el
    orden es fecha DESC, concatenarlas da el mismo orden. El LIMIT 5000 queda
    por ventana (antes truncaba el rango completo).
    """
    start_dt, end_dt = _request_shift_bounds()
    windows = [(start_dt, end_dt)]
    if start_dt and end_dt:
        windows = []
        while start_dt < end_dt:
            nxt = min(start_dt + timedelta(days=31), end_dt)
            windows.append((start_dt, nxt))
            start_dt = nxt
    rows: list[dict] = []
    for bounds in reversed(windows):
        sql, params = _summary_query(bounds, piezas)
        rows += execute_query(sql, params, fetch="all") or []
    return rows


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
        rows = _fetch_summary_rows()
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
        rows = _fetch_summary_rows(piezas=True)
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
