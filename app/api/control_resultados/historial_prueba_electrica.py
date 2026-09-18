"""Historial paginado de prueba electrica desde ``history_prueba_electrica``.

Modulo de solo lectura conforme a WF_001-WF_004, WF_007 y WF_009. ``ts`` se
separa en Fecha y Hora; ``raw`` se expone como QR y no existe Barcode.
"""

from datetime import datetime
import logging

from flask import Blueprint, jsonify, render_template, request

from app.api.shared import (
    excel_response_ict,
    execute_query,
    formatear_fecha,
    formatear_hora,
    login_requerido,
    obtener_fecha_hora_mexico,
    obtener_fecha_mexico,
    requiere_permiso_dropdown,
    sanitizar_texto,
)


logger = logging.getLogger(__name__)

bp = Blueprint("control_resultados_historial_prueba_electrica", __name__)

PERMISO_PAGINA = "LISTA_DE_CONTROL_DE_RESULTADOS"
PERMISO_SECCION = "Historial de maquinas calidad"
PERMISO_BOTON = "Historial de prueba electrica"

_requiere_permiso = requiere_permiso_dropdown(
    PERMISO_PAGINA,
    PERMISO_SECCION,
    PERMISO_BOTON,
)

PER_PAGE_DEFAULT = 1000
PER_PAGE_MAX = 1000
PER_PAGE_OPTIONS = {100, 200, 500, 1000}

_COLUMN_FILTER_SQL = {
    "fecha": "CAST(DATE(ts) AS CHAR) LIKE %s",
    "hora": "CAST(TIME(ts) AS CHAR) LIKE %s",
    "linea": "COALESCE(linea, '') LIKE %s",
    "qr": "raw LIKE %s",
    "lote": "COALESCE(lot_no, '') LIKE %s",
    "resultado": "resultado LIKE %s",
}


def _parse_date(value, field):
    value = sanitizar_texto(value, 10)
    if not value:
        return ""
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError(f"{field} debe usar el formato AAAA-MM-DD") from exc
    return value


def _parse_time(value, field):
    value = sanitizar_texto(value, 8)
    if not value:
        return ""
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(value, fmt).strftime("%H:%M:%S")
        except ValueError:
            continue
    raise ValueError(f"{field} debe usar el formato HH:MM o HH:MM:SS")


def _pagination_args():
    try:
        page = max(1, int(request.args.get("page", "1")))
    except (TypeError, ValueError):
        page = 1
    try:
        per_page = int(request.args.get("per_page", str(PER_PAGE_DEFAULT)))
    except (TypeError, ValueError):
        per_page = PER_PAGE_DEFAULT
    if per_page not in PER_PAGE_OPTIONS:
        per_page = min(max(1, per_page), PER_PAGE_MAX)
    return page, per_page


def _build_filters():
    fecha_desde = _parse_date(request.args.get("fecha_desde"), "fecha_desde")
    fecha_hasta = _parse_date(request.args.get("fecha_hasta"), "fecha_hasta")
    hora_desde = _parse_time(request.args.get("hora_desde"), "hora_desde")
    hora_hasta = _parse_time(request.args.get("hora_hasta"), "hora_hasta")
    linea = sanitizar_texto(request.args.get("linea"), 16)
    qr = sanitizar_texto(request.args.get("qr"), 128)
    lote = sanitizar_texto(request.args.get("lote"), 64)

    where = ["1 = 1"]
    params = []
    if fecha_desde:
        where.append("ts >= %s")
        params.append(f"{fecha_desde} 00:00:00")
    if fecha_hasta:
        where.append("ts < DATE_ADD(%s, INTERVAL 1 DAY)")
        params.append(f"{fecha_hasta} 00:00:00")
    if hora_desde:
        where.append("TIME(ts) >= %s")
        params.append(hora_desde)
    if hora_hasta:
        where.append("TIME(ts) <= %s")
        params.append(hora_hasta)

    for column, value in (("linea", linea), ("raw", qr), ("lot_no", lote)):
        if value:
            where.append(f"COALESCE({column}, '') LIKE %s")
            params.append(f"%{value}%")

    for key, clause in _COLUMN_FILTER_SQL.items():
        value = sanitizar_texto(request.args.get(f"cf_{key}"), 128)
        if value:
            where.append(clause)
            params.append(f"%{value}%")

    return " AND ".join(where), params


def _serialize_row(row, numero):
    return {
        "numero": numero,
        "linea": row.get("linea") or "",
        "fecha": formatear_fecha(row.get("fecha")),
        "hora": formatear_hora(row.get("hora")),
        "qr": row.get("qr") or "",
        "lote": row.get("lote") or "",
        "resultado": row.get("resultado") or "",
    }


@bp.route("/control_resultados/historial_prueba_electrica")
@login_requerido
@_requiere_permiso
def historial_prueba_electrica_ajax():
    try:
        return render_template(
            "Control de resultados/historial_prueba_electrica_ajax.html",
            hoy=obtener_fecha_mexico(),
        )
    except Exception as exc:
        logger.exception("Error cargando Historial de prueba electrica: %s", exc)
        return "Error al cargar el contenido", 500


@bp.route("/api/control_resultados/historial_prueba_electrica", methods=["GET"])
@login_requerido
@_requiere_permiso
def api_historial_prueba_electrica():
    try:
        page, per_page = _pagination_args()
        where_sql, params = _build_filters()

        count_sql = f"SELECT COUNT(*) AS n FROM history_prueba_electrica WHERE {where_sql}"
        count_row = execute_query(
            count_sql,
            tuple(params) if params else None,
            fetch="one",
        ) or {}
        total = int(count_row.get("n", 0) or 0)
        total_pages = (total + per_page - 1) // per_page if total else 0
        if total_pages and page > total_pages:
            page = total_pages
        offset = (page - 1) * per_page

        data_sql = f"""
            SELECT id, DATE(ts) AS fecha, TIME(ts) AS hora,
                   linea, raw AS qr, lot_no AS lote, resultado
            FROM history_prueba_electrica
            WHERE {where_sql}
            ORDER BY ts DESC, id DESC
            LIMIT %s OFFSET %s
        """
        rows = execute_query(
            data_sql,
            tuple(params) + (per_page, offset),
            fetch="all",
        ) or []
        items = [
            _serialize_row(row, offset + index)
            for index, row in enumerate(rows, start=1)
        ]
        return jsonify(
            {
                "success": True,
                "rows": items,
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": total_pages,
            }
        )
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc), "rows": []}), 400
    except Exception as exc:
        logger.exception("Error consultando history_prueba_electrica: %s", exc)
        return jsonify(
            {
                "success": False,
                "error": "No fue posible consultar el historial de prueba electrica",
                "rows": [],
            }
        ), 500


@bp.route(
    "/api/control_resultados/historial_prueba_electrica/export",
    methods=["GET"],
)
@login_requerido
@_requiere_permiso
def export_historial_prueba_electrica():
    """Exportar a Excel la pagina visible de history_prueba_electrica, sin Barcode."""
    try:
        page, per_page = _pagination_args()
        where_sql, params = _build_filters()
        offset = (page - 1) * per_page
        data_sql = f"""
            SELECT id, DATE(ts) AS fecha, TIME(ts) AS hora,
                   linea, raw AS qr, lot_no AS lote, resultado
            FROM history_prueba_electrica
            WHERE {where_sql}
            ORDER BY ts DESC, id DESC
            LIMIT %s OFFSET %s
        """
        rows = execute_query(
            data_sql,
            tuple(params) + (per_page, offset),
            fetch="all",
        ) or []
        items = [
            _serialize_row(row, offset + index)
            for index, row in enumerate(rows, start=1)
        ]
        filename = (
            "historial_prueba_electrica_"
            f"{obtener_fecha_hora_mexico().strftime('%Y%m%d_%H%M%S')}"
        )
        return excel_response_ict(
            items,
            ["#", "Línea", "Fecha", "Hora", "QR", "Lote", "Resultado"],
            ["numero", "linea", "fecha", "hora", "qr", "lote", "resultado"],
            [10, 14, 13, 12, 38, 18, 12],
            sheet="Prueba electrica",
            filename=filename,
            freeze="A2",
        )
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception as exc:
        logger.exception("Error exportando history_prueba_electrica a Excel: %s", exc)
        return jsonify(
            {
                "success": False,
                "error": "No fue posible exportar el historial de prueba electrica",
            }
        ), 500
