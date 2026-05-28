"""Modulo Control de salida de lineas.

Migrado desde `app/routes.py` el 2026-05-28 (Fase 3.1). Sin cambios funcionales.

Cubre 3 endpoints y 3 helpers privados:

  Render                /control-salida-lineas-ajax        -> control_salida_lineas_ajax
  Datos (JSON)          /api/control-salida-lineas         -> api_control_salida_lineas
  Exportar Excel        /api/control-salida-lineas/export  -> export_control_salida_lineas

  Helpers privados (solo se usan dentro de este modulo):
    _parse_fecha_control_salida_lineas
    _calcular_estado_control_salida_lineas
    _obtener_control_salida_lineas

Consume `_normalizar_texto_embarques_historial` y `_exportar_historial_embarques_excel`
directo desde su blueprint dueno (`app.api.control_proceso.almacen_embarques`).
Con esta migracion se elimina el ultimo re-export de `routes.py:138-141` que
quedaba abierto desde Fase 2.
"""

import traceback
from datetime import date, datetime, timedelta

from flask import Blueprint, jsonify, render_template, request

from app.api.shared import execute_query, login_requerido
from app.api.control_proceso.almacen_embarques import (
    _exportar_historial_embarques_excel,
    _normalizar_texto_embarques_historial,
)

bp = Blueprint("control_proceso_control_salida_lineas", __name__)


def _parse_fecha_control_salida_lineas(value, fallback):
    """Parsear fechas de filtros del modulo Control de salida de lineas."""
    try:
        return datetime.strptime(str(value or "").strip(), "%Y-%m-%d").date()
    except Exception:
        return fallback


def _calcular_estado_control_salida_lineas(produccion, oqc, almacen):
    if produccion == 0 and oqc == 0 and almacen > 0:
        return "Solo almacen"
    if oqc > produccion or almacen > oqc:
        return "Revisar"
    if produccion > 0 and oqc >= produccion and almacen >= oqc:
        return "Completo"
    if oqc < produccion:
        return "Pendiente OQC"
    if almacen < oqc:
        return "Pendiente almacen"
    return "Sin datos"


def _obtener_control_salida_lineas(limit=500):
    """Consultar produccion, liberacion OQC y entradas, acumuladas por parte en el rango."""
    today = date.today()
    default_from = today - timedelta(days=7)
    fecha_desde = _parse_fecha_control_salida_lineas(
        request.args.get("fecha_desde"),
        default_from,
    )
    fecha_hasta = _parse_fecha_control_salida_lineas(
        request.args.get("fecha_hasta"),
        today,
    )
    if fecha_hasta < fecha_desde:
        fecha_desde, fecha_hasta = fecha_hasta, fecha_desde

    fecha_inicio_sql = fecha_desde.strftime("%Y-%m-%d")
    fecha_fin_sql = (fecha_hasta + timedelta(days=1)).strftime("%Y-%m-%d")
    part_number = (request.args.get("part_number", "") or "").strip()
    part_like = f"%{part_number}%"
    output_collation = "utf8mb4_0900_ai_ci"

    production_part_expr = (
        "COALESCE(NULLIF(p.part_no, ''), "
        "NULLIF(LEFT(b.serial, GREATEST(CHAR_LENGTH(b.serial) - 12, 1)), ''), "
        "'SIN PARTE')"
    )
    production_model_expr = "COALESCE(NULLIF(p.model_code, ''), '')"
    oqc_part_expr = "COALESCE(NULLIF(pn.part_number, ''), CONCAT('ID-', er.part_number_id))"
    oqc_model_expr = "COALESCE(NULLIF(pn.model, ''), '')"
    entry_part_expr = "COALESCE(NULLIF(e.part_number, ''), 'SIN PARTE')"
    entry_model_expr = "COALESCE(NULLIF(e.product_model, ''), '')"
    production_part_select = f"({production_part_expr}) COLLATE {output_collation}"
    production_model_select = f"({production_model_expr}) COLLATE {output_collation}"
    oqc_part_select = f"({oqc_part_expr}) COLLATE {output_collation}"
    oqc_model_select = f"({oqc_model_expr}) COLLATE {output_collation}"
    entry_part_select = f"({entry_part_expr}) COLLATE {output_collation}"
    entry_model_select = f"({entry_model_expr}) COLLATE {output_collation}"
    empty_text_select = f"'' COLLATE {output_collation}"

    production_where = ["b.last_scan >= %s", "b.last_scan < %s"]
    production_params = [fecha_inicio_sql, fecha_fin_sql]
    oqc_where = [
        "COALESCE(er.exit_date, er.created_at, CAST(er.inspection_date AS DATETIME)) >= %s",
        "COALESCE(er.exit_date, er.created_at, CAST(er.inspection_date AS DATETIME)) < %s",
        "COALESCE(er.status, '') <> 'cancelled'",
        "COALESCE(er.qc_passed, 1) = 1",
    ]
    oqc_params = [fecha_inicio_sql, fecha_fin_sql]
    entry_where = [
        "COALESCE(e.movement_at, e.created_at) >= %s",
        "COALESCE(e.movement_at, e.created_at) < %s",
        "COALESCE(e.is_fifo_layer_only, 0) = 0",
    ]
    entry_params = [fecha_inicio_sql, fecha_fin_sql]

    if part_number:
        production_where.append(f"{production_part_select} LIKE %s")
        production_params.append(part_like)
        oqc_where.append(f"COALESCE(pn.part_number, '') COLLATE {output_collation} LIKE %s")
        oqc_params.append(part_like)
        entry_where.append(f"e.part_number COLLATE {output_collation} LIKE %s")
        entry_params.append(part_like)

    sql = f"""
        SELECT
            MIN(fuente.fecha) AS fecha_inicio,
            MAX(fuente.fecha) AS fecha_fin,
            fuente.part_number,
            MAX(NULLIF(fuente.product_model, '')) AS product_model,
            SUM(fuente.produced_quantity) AS produced_quantity,
            SUM(fuente.production_boxes) AS production_boxes,
            SUM(fuente.oqc_quantity) AS oqc_quantity,
            SUM(fuente.oqc_records) AS oqc_records,
            SUM(fuente.warehouse_quantity) AS warehouse_quantity,
            SUM(fuente.warehouse_records) AS warehouse_records,
            GROUP_CONCAT(DISTINCT NULLIF(fuente.lineas, '') ORDER BY fuente.lineas SEPARATOR ', ') AS lineas,
            GROUP_CONCAT(DISTINCT NULLIF(fuente.lotes, '') ORDER BY fuente.lotes SEPARATOR ', ') AS lotes,
            GROUP_CONCAT(DISTINCT NULLIF(fuente.oqc_statuses, '') ORDER BY fuente.oqc_statuses SEPARATOR ', ') AS oqc_statuses
        FROM (
            SELECT
                DATE(b.last_scan) AS fecha,
                {production_part_select} AS part_number,
                MAX({production_model_select}) AS product_model,
                COUNT(*) AS produced_quantity,
                COUNT(DISTINCT NULLIF(b.box_code, '')) AS production_boxes,
                0 AS oqc_quantity,
                0 AS oqc_records,
                0 AS warehouse_quantity,
                0 AS warehouse_records,
                (GROUP_CONCAT(DISTINCT NULLIF(p.line, '') ORDER BY p.line SEPARATOR ', ')) COLLATE {output_collation} AS lineas,
                (GROUP_CONCAT(DISTINCT NULLIF(b.lot_no, '') ORDER BY b.lot_no SEPARATOR ', ')) COLLATE {output_collation} AS lotes,
                {empty_text_select} AS oqc_statuses
            FROM box_scans b
            LEFT JOIN plan_main p ON p.lot_no = b.lot_no
            WHERE {" AND ".join(production_where)}
            GROUP BY DATE(b.last_scan), {production_part_select}

            UNION ALL

            SELECT
                DATE(COALESCE(er.exit_date, er.created_at, CAST(er.inspection_date AS DATETIME))) AS fecha,
                {oqc_part_select} AS part_number,
                MAX({oqc_model_select}) AS product_model,
                0 AS produced_quantity,
                0 AS production_boxes,
                SUM(er.quantity) AS oqc_quantity,
                COUNT(*) AS oqc_records,
                0 AS warehouse_quantity,
                0 AS warehouse_records,
                {empty_text_select} AS lineas,
                {empty_text_select} AS lotes,
                (GROUP_CONCAT(DISTINCT COALESCE(er.status, 'pending') ORDER BY er.status SEPARATOR ', ')) COLLATE {output_collation} AS oqc_statuses
            FROM exit_records er
            LEFT JOIN part_numbers pn ON pn.id = er.part_number_id
            WHERE {" AND ".join(oqc_where)}
            GROUP BY DATE(COALESCE(er.exit_date, er.created_at, CAST(er.inspection_date AS DATETIME))), {oqc_part_select}

            UNION ALL

            SELECT
                DATE(COALESCE(e.movement_at, e.created_at)) AS fecha,
                {entry_part_select} AS part_number,
                MAX({entry_model_select}) AS product_model,
                0 AS produced_quantity,
                0 AS production_boxes,
                0 AS oqc_quantity,
                0 AS oqc_records,
                SUM(e.quantity) AS warehouse_quantity,
                COUNT(*) AS warehouse_records,
                {empty_text_select} AS lineas,
                {empty_text_select} AS lotes,
                {empty_text_select} AS oqc_statuses
            FROM embarques_entrada_material e
            WHERE {" AND ".join(entry_where)}
            GROUP BY DATE(COALESCE(e.movement_at, e.created_at)), {entry_part_select}
        ) fuente
        WHERE COALESCE(fuente.part_number, '') <> ''
        GROUP BY fuente.part_number
        ORDER BY fecha_fin DESC, fuente.part_number
        LIMIT %s
    """
    params = production_params + oqc_params + entry_params + [int(limit)]
    rows = execute_query(sql, tuple(params), fetch="all") or []

    result_rows = []
    summary = {
        "produced_quantity": 0,
        "production_boxes": 0,
        "oqc_quantity": 0,
        "oqc_records": 0,
        "warehouse_quantity": 0,
        "warehouse_records": 0,
        "pending_oqc": 0,
        "pending_warehouse": 0,
    }
    for row in rows:
        part = _normalizar_texto_embarques_historial(row.get("part_number"))
        produced = int(row.get("produced_quantity") or 0)
        production_boxes = int(row.get("production_boxes") or 0)
        oqc = int(row.get("oqc_quantity") or 0)
        oqc_records = int(row.get("oqc_records") or 0)
        warehouse = int(row.get("warehouse_quantity") or 0)
        warehouse_records = int(row.get("warehouse_records") or 0)
        pending_oqc = max(produced - oqc, 0)
        pending_warehouse = max(oqc - warehouse, 0)
        if pending_oqc > 0:
            estado = "Pendiente OQC"
        elif pending_warehouse > 0:
            estado = "Pendiente almacen"
        else:
            estado = _calcular_estado_control_salida_lineas(produced, oqc, warehouse)
        fecha_inicio = _normalizar_texto_embarques_historial(row.get("fecha_inicio"))
        fecha_fin = _normalizar_texto_embarques_historial(row.get("fecha_fin"))
        fecha_periodo = (
            fecha_inicio
            if fecha_inicio == fecha_fin or not fecha_fin
            else f"{fecha_inicio} a {fecha_fin}"
        )

        summary["produced_quantity"] += produced
        summary["production_boxes"] += production_boxes
        summary["oqc_quantity"] += oqc
        summary["oqc_records"] += oqc_records
        summary["warehouse_quantity"] += warehouse
        summary["warehouse_records"] += warehouse_records
        summary["pending_oqc"] += pending_oqc
        summary["pending_warehouse"] += pending_warehouse

        result_rows.append(
            {
                "fecha": fecha_periodo,
                "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin,
                "part_number": part,
                "product_model": _normalizar_texto_embarques_historial(row.get("product_model")),
                "lineas": _normalizar_texto_embarques_historial(row.get("lineas")),
                "lotes": _normalizar_texto_embarques_historial(row.get("lotes")),
                "produced_quantity": produced,
                "production_boxes": production_boxes,
                "oqc_quantity": oqc,
                "oqc_records": oqc_records,
                "warehouse_quantity": warehouse,
                "warehouse_records": warehouse_records,
                "pending_oqc": pending_oqc,
                "pending_warehouse": pending_warehouse,
                "produced_cutoff": produced,
                "oqc_cutoff": oqc,
                "warehouse_cutoff": warehouse,
                "oqc_statuses": _normalizar_texto_embarques_historial(row.get("oqc_statuses")),
                "estado": estado,
            }
        )

    return {
        "rows": result_rows,
        "summary": summary,
        "filters": {
            "fecha_desde": fecha_desde.isoformat(),
            "fecha_hasta": fecha_hasta.isoformat(),
            "part_number": part_number,
        },
    }


@bp.route("/control-salida-lineas-ajax")
@login_requerido
def control_salida_lineas_ajax():
    """Ruta AJAX para consultar salida de lineas contra OQC y almacen de embarques."""
    try:
        return render_template("Control de proceso/control_salida_lineas_ajax.html")
    except Exception as e:
        print(f"Error al cargar template Control de salida de lineas AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@bp.route("/api/control-salida-lineas")
@login_requerido
def api_control_salida_lineas():
    """Obtener produccion, liberacion OQC y entradas de almacen por parte/fecha."""
    try:
        payload = _obtener_control_salida_lineas()
        payload["success"] = True
        return jsonify(payload)
    except Exception as e:
        print(f"Error API Control de salida de lineas: {e}\n{traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e), "rows": []}), 500


@bp.route("/api/control-salida-lineas/export")
@login_requerido
def export_control_salida_lineas():
    """Exportar Control de salida de lineas a Excel."""
    try:
        payload = _obtener_control_salida_lineas(limit=5000)
        return _exportar_historial_embarques_excel(
            "Salida Lineas",
            "control_salida_lineas.xlsx",
            {
                "Periodo": "fecha",
                "No. Parte": "part_number",
                "Produccion": "produced_quantity",
                "Liberacion OQC": "oqc_quantity",
                "Pendiente OQC": "pending_oqc",
                "Entradas Almacen": "warehouse_quantity",
                "Pendientes Almacen": "pending_warehouse",
            },
            payload["rows"],
        )
    except Exception as e:
        print(f"Error exportando Control de salida de lineas: {e}\n{traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500
