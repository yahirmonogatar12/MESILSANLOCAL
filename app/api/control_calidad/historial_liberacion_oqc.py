"""Endpoints HTTP del modulo "Historial de liberacion OQC".

Consumido por LISTA_CONTROL_DE_CALIDAD / Inspeccion de calidad.
Template: app/templates/Control de calidad/historial_liberacion_oqc_ajax.html
JS:       app/static/js/historial_liberacion_oqc.js
CSS:      app/static/css/historial_liberacion_oqc.css
"""

import logging
import traceback
from datetime import date as _date
from datetime import datetime, timedelta

from flask import Blueprint, jsonify, redirect, render_template, request

from app.api.shared import (
    excel_response,
    execute_query,
    login_requerido,
    obtener_fecha_hora_mexico,
    requiere_permiso_dropdown,
)

logger = logging.getLogger(__name__)

bp = Blueprint("historial_liberacion_oqc", __name__)

PERMISO_MODULO = (
    "LISTA_CONTROL_DE_CALIDAD",
    "Inspeccion de calidad",
    "Historial de liberacion OQC",
)

_requiere_permiso_oqc = requiere_permiso_dropdown(*PERMISO_MODULO)

OQC_LIMIT_INICIAL = 300
OQC_LIMIT_FILTRADO = 5000
OQC_LIMIT_EXPORT = 10000

OQC_STATUS_LABELS = {
    "released": "Liberada",
    "received_shipping": "Recibida embarques",
    "cancelled": "Cancelada",
    "rejected": "Rechazada",
    "exception": "Excepcion",
}

OQC_SOURCE_LABELS = {
    "batch": "Lote",
    "migration": "Migracion",
    "manual": "Manual",
}


def _normalizar_texto(value):
    return str(value or "").strip()


def _normalizar_entero(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _serializar_fecha_hora(value):
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, _date):
        return value.strftime("%Y-%m-%d")
    return str(value).replace("T", " ")


def _fecha_hora(value):
    serialized = _serializar_fecha_hora(value)
    if " " not in serialized:
        return serialized, ""
    fecha, hora = serialized.split(" ", 1)
    return fecha, hora[:8]


def _parsear_fecha(value):
    text = _normalizar_texto(value)
    if not text:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None


def _filtros_historial_oqc():
    fecha_desde = _parsear_fecha(request.args.get("fecha_desde"))
    fecha_hasta = _parsear_fecha(request.args.get("fecha_hasta"))
    if fecha_desde and fecha_hasta and fecha_hasta < fecha_desde:
        fecha_desde, fecha_hasta = fecha_hasta, fecha_desde

    status = _normalizar_texto(request.args.get("status")).lower()
    if status and status not in OQC_STATUS_LABELS:
        status = ""

    source = _normalizar_texto(request.args.get("source")).lower()
    if source and source not in OQC_SOURCE_LABELS:
        source = ""

    qc = _normalizar_texto(request.args.get("qc")).lower()
    if qc not in {"passed", "failed", "unknown"}:
        qc = ""

    return {
        "search": _normalizar_texto(
            request.args.get("search") or request.args.get("q")
        )[:160],
        "fecha_desde": fecha_desde,
        "fecha_hasta": fecha_hasta,
        "status": status,
        "source": source,
        "qc": qc,
    }


def _filtros_payload(filters):
    return {
        "search": filters["search"],
        "fecha_desde": (
            filters["fecha_desde"].isoformat() if filters["fecha_desde"] else ""
        ),
        "fecha_hasta": (
            filters["fecha_hasta"].isoformat() if filters["fecha_hasta"] else ""
        ),
        "status": filters["status"],
        "source": filters["source"],
        "qc": filters["qc"],
    }


def _tiene_filtros(filters):
    return any(
        [
            filters.get("search"),
            filters.get("fecha_desde"),
            filters.get("fecha_hasta"),
            filters.get("status"),
            filters.get("source"),
            filters.get("qc"),
        ]
    )


def _obtener_limite_historial_oqc(filters=None):
    filters = filters or _filtros_historial_oqc()
    requested_limit = _normalizar_entero(request.args.get("limit"))
    default_limit = OQC_LIMIT_FILTRADO if _tiene_filtros(filters) else OQC_LIMIT_INICIAL
    limit = requested_limit or default_limit
    return min(max(limit, 1), OQC_LIMIT_FILTRADO)


def _part_number_expr():
    return "COALESCE(NULLIF(o.part_number, ''), pn.part_number, CONCAT('ID-', o.part_number_id))"


def _release_datetime_expr():
    return "COALESCE(o.released_at, o.created_at)"


def _movimientos_embarques_subquery():
    return """
        SELECT
          oqc_release_box_id,
          MAX(CASE WHEN movement_type = 'entry' THEN movement_folio END) AS entry_folio,
          MAX(CASE WHEN movement_type = 'entry' THEN movement_at END) AS entry_at,
          MAX(CASE WHEN movement_type = 'exit' THEN movement_folio END) AS exit_folio,
          MAX(CASE WHEN movement_type = 'exit' THEN movement_at END) AS exit_at
        FROM embarques_movimiento_cajas
        WHERE oqc_release_box_id IS NOT NULL
        GROUP BY oqc_release_box_id
    """


def _base_from_sql():
    return f"""
        FROM oqc_release_boxes o
        LEFT JOIN exit_records er
          ON er.id = o.exit_record_id
        LEFT JOIN part_numbers pn
          ON pn.id = o.part_number_id
        LEFT JOIN operators op
          ON op.id = o.released_by
        LEFT JOIN (
          {_movimientos_embarques_subquery()}
        ) mb
          ON mb.oqc_release_box_id = o.id
    """


def _where_historial_oqc(filters):
    where = ["1 = 1"]
    params = []
    release_dt = _release_datetime_expr()

    if filters.get("fecha_desde"):
        where.append(f"{release_dt} >= %s")
        params.append(filters["fecha_desde"].strftime("%Y-%m-%d 00:00:00"))

    if filters.get("fecha_hasta"):
        fecha_fin = filters["fecha_hasta"] + timedelta(days=1)
        where.append(f"{release_dt} < %s")
        params.append(fecha_fin.strftime("%Y-%m-%d 00:00:00"))

    if filters.get("status"):
        where.append("o.status = %s")
        params.append(filters["status"])

    if filters.get("source"):
        where.append("o.source = %s")
        params.append(filters["source"])

    qc = filters.get("qc")
    if qc == "passed":
        where.append("COALESCE(o.qc_passed, 0) = 1")
    elif qc == "failed":
        where.append("COALESCE(o.qc_passed, 0) = 0")
    elif qc == "unknown":
        where.append("o.qc_passed IS NULL")

    if filters.get("search"):
        like_value = f"%{filters['search']}%"
        where.append(
            f"""
            (
                COALESCE(o.oqc_folio, '') LIKE %s
                OR COALESCE(o.box_code, '') LIKE %s
                OR COALESCE(o.part_number, '') LIKE %s
                OR COALESCE(pn.part_number, '') LIKE %s
                OR COALESCE(pn.model, '') LIKE %s
                OR COALESCE(pn.customer, '') LIKE %s
                OR COALESCE(o.destination, '') LIKE %s
                OR COALESCE(o.employee_id, '') LIKE %s
                OR COALESCE(op.name, '') LIKE %s
                OR COALESCE(er.folio, '') LIKE %s
                OR COALESCE(mb.entry_folio, '') LIKE %s
                OR COALESCE(mb.exit_folio, '') LIKE %s
                OR {_part_number_expr()} LIKE %s
            )
            """
        )
        params.extend([like_value] * 13)

    return " AND ".join(where), params


def _estado_calidad_label(value):
    if value is None:
        return "Sin dato"
    return "OK" if _normalizar_entero(value) == 1 else "NG"


def _estado_embarques(row):
    if row.get("exit_folio"):
        return "Salida embarques"
    if row.get("entry_folio"):
        return "Entrada embarques"
    if _normalizar_texto(row.get("status")).lower() == "received_shipping":
        return "Recibida embarques"
    return "Pendiente entrada"


def _serializar_liberacion_oqc(row):
    release_dt = row.get("release_dt") or row.get("released_at") or row.get("created_at")
    fecha, hora = _fecha_hora(release_dt)
    status = _normalizar_texto(row.get("status")).lower()
    source = _normalizar_texto(row.get("source")).lower()
    return {
        "id": _normalizar_entero(row.get("id")),
        "fecha": fecha,
        "hora": hora,
        "release_dt": _serializar_fecha_hora(release_dt),
        "oqc_folio": _normalizar_texto(row.get("oqc_folio")),
        "box_code": _normalizar_texto(row.get("box_code")),
        "part_number": _normalizar_texto(row.get("part_number")),
        "quantity": _normalizar_entero(row.get("quantity")),
        "product_model": _normalizar_texto(row.get("product_model")),
        "customer": _normalizar_texto(row.get("customer")),
        "destination": _normalizar_texto(row.get("destination")),
        "qc_passed": row.get("qc_passed"),
        "qc_result": _estado_calidad_label(row.get("qc_passed")),
        "status": status,
        "status_label": OQC_STATUS_LABELS.get(status, status or "Sin estado"),
        "source": source,
        "source_label": OQC_SOURCE_LABELS.get(source, source or "Sin fuente"),
        "released_by": _normalizar_entero(row.get("released_by")),
        "employee_id": _normalizar_texto(row.get("employee_id")),
        "released_by_name": _normalizar_texto(row.get("released_by_name")),
        "exit_record_folio": _normalizar_texto(row.get("exit_record_folio")),
        "inspection_date": _serializar_fecha_hora(row.get("inspection_date")),
        "entry_folio": _normalizar_texto(row.get("entry_folio")),
        "entry_at": _serializar_fecha_hora(row.get("entry_at")),
        "exit_folio": _normalizar_texto(row.get("exit_folio")),
        "exit_at": _serializar_fecha_hora(row.get("exit_at")),
        "shipping_status": _estado_embarques(row),
        "created_at": _serializar_fecha_hora(row.get("created_at")),
        "updated_at": _serializar_fecha_hora(row.get("updated_at")),
    }


def _resumen_historial_oqc(filters):
    part_expr = _part_number_expr()
    where_sql, params = _where_historial_oqc(filters)
    summary_sql = f"""
        SELECT
          COUNT(*) AS total_boxes,
          COALESCE(SUM(o.quantity), 0) AS total_quantity,
          COUNT(DISTINCT o.oqc_folio) AS total_folios,
          COUNT(DISTINCT {part_expr}) AS total_parts,
          COALESCE(SUM(CASE WHEN COALESCE(o.qc_passed, 0) = 1 THEN 1 ELSE 0 END), 0) AS qc_passed_boxes,
          COALESCE(SUM(CASE WHEN o.status = 'released' THEN 1 ELSE 0 END), 0) AS released_boxes,
          COALESCE(SUM(CASE WHEN o.status = 'received_shipping' THEN 1 ELSE 0 END), 0) AS received_shipping_boxes,
          COALESCE(SUM(CASE WHEN o.status = 'exception' THEN 1 ELSE 0 END), 0) AS exception_boxes,
          COALESCE(SUM(CASE WHEN o.status IN ('cancelled', 'rejected') THEN 1 ELSE 0 END), 0) AS inactive_boxes,
          COALESCE(SUM(CASE WHEN mb.entry_folio IS NOT NULL THEN 1 ELSE 0 END), 0) AS entry_boxes,
          COALESCE(SUM(CASE WHEN mb.exit_folio IS NOT NULL THEN 1 ELSE 0 END), 0) AS exit_boxes
        {_base_from_sql()}
        WHERE {where_sql}
    """
    row = execute_query(summary_sql, tuple(params), fetch="one") or {}
    return {
        "total_boxes": _normalizar_entero(row.get("total_boxes")),
        "total_quantity": _normalizar_entero(row.get("total_quantity")),
        "total_folios": _normalizar_entero(row.get("total_folios")),
        "total_parts": _normalizar_entero(row.get("total_parts")),
        "qc_passed_boxes": _normalizar_entero(row.get("qc_passed_boxes")),
        "released_boxes": _normalizar_entero(row.get("released_boxes")),
        "received_shipping_boxes": _normalizar_entero(row.get("received_shipping_boxes")),
        "exception_boxes": _normalizar_entero(row.get("exception_boxes")),
        "inactive_boxes": _normalizar_entero(row.get("inactive_boxes")),
        "entry_boxes": _normalizar_entero(row.get("entry_boxes")),
        "exit_boxes": _normalizar_entero(row.get("exit_boxes")),
    }


def _obtener_historial_liberacion_oqc(limit=None):
    filters = _filtros_historial_oqc()
    if limit is None:
        limit = _obtener_limite_historial_oqc(filters)
    else:
        limit = min(max(_normalizar_entero(limit), 1), OQC_LIMIT_EXPORT)

    part_expr = _part_number_expr()
    release_dt = _release_datetime_expr()
    where_sql, params = _where_historial_oqc(filters)
    rows_sql = f"""
        SELECT
          o.id,
          o.oqc_folio,
          o.box_code,
          {part_expr} AS part_number,
          o.quantity,
          o.destination,
          o.qc_passed,
          o.status,
          o.source,
          o.released_by,
          o.employee_id,
          o.released_at,
          {release_dt} AS release_dt,
          o.created_at,
          o.updated_at,
          COALESCE(pn.model, '') AS product_model,
          COALESCE(pn.customer, '') AS customer,
          COALESCE(op.name, '') AS released_by_name,
          er.folio AS exit_record_folio,
          er.inspection_date,
          mb.entry_folio,
          mb.entry_at,
          mb.exit_folio,
          mb.exit_at
        {_base_from_sql()}
        WHERE {where_sql}
        ORDER BY release_dt DESC, o.id DESC
        LIMIT %s
    """
    rows = execute_query(rows_sql, tuple(params + [limit]), fetch="all") or []
    records = [_serializar_liberacion_oqc(row) for row in rows]
    summary = _resumen_historial_oqc(filters)
    return {
        "success": True,
        "records": records,
        "rows": records,
        "summary": summary,
        "filters": _filtros_payload(filters),
        "limit": limit,
        "total": len(records),
        "truncated": summary["total_boxes"] > len(records),
    }


@bp.route("/historial_liberacion_oqc/ajax")
@login_requerido
@_requiere_permiso_oqc
def historial_liberacion_oqc_ajax():
    """Render AJAX del modulo Historial de liberacion OQC."""
    return render_template("Control de calidad/historial_liberacion_oqc_ajax.html")


@bp.route("/historial-liberacion-oqc-ajax")
def alias_historial_liberacion_oqc_ajax():
    """Alias 301 hacia la ruta canonica."""
    return redirect("/historial_liberacion_oqc/ajax", code=301)


@bp.route("/api/oqc/liberaciones")
@login_requerido
@_requiere_permiso_oqc
def api_historial_liberacion_oqc():
    """Listado y resumen de liberaciones OQC desde oqc_release_boxes."""
    try:
        return jsonify(_obtener_historial_liberacion_oqc())
    except Exception as exc:
        logger.error(
            "Error API historial liberacion OQC: %s\n%s",
            exc,
            traceback.format_exc(),
        )
        return jsonify({"success": False, "error": str(exc), "records": []}), 500


@bp.route("/api/oqc/liberaciones/export")
@login_requerido
@_requiere_permiso_oqc
def export_historial_liberacion_oqc():
    """Exportar historial de liberaciones OQC a Excel."""
    try:
        payload = _obtener_historial_liberacion_oqc(limit=OQC_LIMIT_EXPORT)
        rows = payload["records"]
        timestamp = obtener_fecha_hora_mexico().strftime("%Y%m%d_%H%M%S")
        return excel_response(
            rows,
            [
                "Fecha",
                "Hora",
                "Folio OQC",
                "Box ID",
                "No. Parte",
                "Cantidad",
                "Modelo",
                "Cliente",
                "Liberado por",
            ],
            [
                "fecha",
                "hora",
                "oqc_folio",
                "box_code",
                "part_number",
                "quantity",
                "product_model",
                "customer",
                "released_by_name",
            ],
            [12, 10, 18, 22, 18, 12, 26, 16, 32],
            "Liberacion OQC",
            f"historial_liberacion_oqc_{timestamp}",
            freeze="A2",
        )
    except Exception as exc:
        logger.error(
            "Error exportando historial liberacion OQC: %s\n%s",
            exc,
            traceback.format_exc(),
        )
        return jsonify({"success": False, "error": str(exc)}), 500
