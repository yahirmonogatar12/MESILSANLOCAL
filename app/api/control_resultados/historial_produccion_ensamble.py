"""Historial paginado de produccion de ensamble desde ``input_main``.

Modulo de solo lectura creado conforme a WF_001-WF_004, WF_007 y WF_009.
El timestamp ``ts`` se presenta como columnas independientes de fecha y hora.

Rutas:
  GET /control_resultados/historial_produccion_ensamble
  GET /api/control_resultados/historial_produccion_ensamble
"""

from datetime import datetime
import logging

from flask import Blueprint, jsonify, render_template, request

from app.api.shared import (
    execute_query,
    formatear_fecha,
    formatear_hora,
    login_requerido,
    obtener_fecha_mexico,
    requiere_permiso_dropdown,
    sanitizar_texto,
)


logger = logging.getLogger(__name__)

bp = Blueprint("control_resultados_historial_produccion_ensamble", __name__)

PERMISO_PAGINA = "LISTA_DE_CONTROL_DE_RESULTADOS"
PERMISO_SECCION = "Consultar resultados"
PERMISO_BOTON = "Historial de produccion ensamble"

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
    "barcode": "COALESCE(raw_barcode, '') LIKE %s",
    "lote": "COALESCE(lot_no, '') LIKE %s",
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
            parsed = datetime.strptime(value, fmt)
            return parsed.strftime("%H:%M:%S")
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
    """Construir filtros parametrizados compartidos por COUNT y SELECT."""
    fecha_desde = _parse_date(request.args.get("fecha_desde"), "fecha_desde")
    fecha_hasta = _parse_date(request.args.get("fecha_hasta"), "fecha_hasta")
    hora_desde = _parse_time(request.args.get("hora_desde"), "hora_desde")
    hora_hasta = _parse_time(request.args.get("hora_hasta"), "hora_hasta")
    linea = sanitizar_texto(request.args.get("linea"), 8)
    qr = sanitizar_texto(request.args.get("qr"), 128)
    barcode = sanitizar_texto(request.args.get("barcode"), 128)
    lote = sanitizar_texto(request.args.get("lote"), 32)

    where = ["1 = 1"]
    params = []

    # Rangos sobre ts conservan el uso del indice idx_ts para el filtro de fecha.
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

    for column, value in (
        ("linea", linea),
        ("raw", qr),
        ("raw_barcode", barcode),
        ("lot_no", lote),
    ):
        if value:
            where.append(f"COALESCE({column}, '') LIKE %s")
            params.append(f"%{value}%")

    # Filtros del icono de cada encabezado. Los nombres SQL provienen
    # exclusivamente de este mapa fijo; nunca se interpolan desde el request.
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
        "barcode": row.get("barcode") or "",
        "lote": row.get("lote") or "",
    }


@bp.route("/control_resultados/historial_produccion_ensamble")
@login_requerido
@_requiere_permiso
def historial_produccion_ensamble_ajax():
    """Render AJAX del historial de produccion de ensamble."""
    try:
        return render_template(
            "Control de resultados/historial_produccion_ensamble_ajax.html",
            hoy=obtener_fecha_mexico(),
        )
    except Exception as exc:
        logger.exception("Error cargando Historial de produccion ensamble: %s", exc)
        return "Error al cargar el contenido", 500


@bp.route("/api/control_resultados/historial_produccion_ensamble", methods=["GET"])
@login_requerido
@_requiere_permiso
def api_historial_produccion_ensamble():
    """Listar ``input_main`` con filtros seguros y paginacion de servidor."""
    try:
        page, per_page = _pagination_args()
        where_sql, params = _build_filters()

        count_sql = f"SELECT COUNT(*) AS n FROM input_main WHERE {where_sql}"
        count_row = execute_query(
            count_sql,
            tuple(params) if params else None,
            fetch="one",
        ) or {}
        total = int(count_row.get("n", 0) or 0)
        total_pages = (total + per_page - 1) // per_page if total else 0

        # Si un filtro reduce el numero de paginas, regresar la ultima pagina
        # valida en vez de una tabla vacia fuera de rango.
        if total_pages and page > total_pages:
            page = total_pages
        offset = (page - 1) * per_page

        data_sql = f"""
            SELECT id, DATE(ts) AS fecha, TIME(ts) AS hora,
                   linea, raw AS qr, raw_barcode AS barcode, lot_no AS lote
            FROM input_main
            WHERE {where_sql}
            ORDER BY ts DESC, id DESC
            LIMIT %s OFFSET %s
        """
        data_params = tuple(params) + (per_page, offset)
        rows = execute_query(data_sql, data_params, fetch="all") or []
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
        logger.exception("Error consultando input_main: %s", exc)
        return jsonify(
            {
                "success": False,
                "error": "No fue posible consultar el historial de produccion ensamble",
                "rows": [],
            }
        ), 500
