"""Modulo de pendientes QA para Almacen de Embarques.

Rutas:
  GET /almacen-embarques-qa-pendientes-ajax
  GET /almacen-embarques-oqc-pendientes-ajax
  GET /api/almacen-embarques/qa-pendientes
  GET /api/almacen-embarques/qa-pendientes/cajas
"""

import logging
import traceback
from datetime import date, datetime, timedelta

from flask import Blueprint, jsonify, render_template, request

from app.api.shared import execute_query, login_requerido, requiere_permiso_dropdown

logger = logging.getLogger(__name__)

bp = Blueprint("control_proceso_almacen_embarques_oqc_pendientes", __name__)

PERMISO_PAGINA = "LISTA_CONTROL_DE_PROCESO"
PERMISO_SECCION = "Almacén de Embarques"
PERMISO_BOTON = "Pendientes QA Embarques"

_requiere_permiso_pendientes_oqc = requiere_permiso_dropdown(
    PERMISO_PAGINA,
    PERMISO_SECCION,
    PERMISO_BOTON,
)


def _normalizar_texto(value):
    return str(value or "").strip()


def _normalizar_entero(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _serializar_fecha(value):
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return str(value)


def _parsear_fecha(value):
    text = _normalizar_texto(value)
    if not text:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None


def _filtros_pendientes_oqc():
    default_date = date.today()
    fecha_desde = _parsear_fecha(request.args.get("fecha_desde")) or default_date
    fecha_hasta = _parsear_fecha(request.args.get("fecha_hasta")) or default_date
    if fecha_hasta < fecha_desde:
        fecha_desde, fecha_hasta = fecha_hasta, fecha_desde

    search = _normalizar_texto(request.args.get("q") or request.args.get("search"))
    limit = _normalizar_entero(request.args.get("limit")) or 500
    limit = min(max(limit, 1), 5000)

    return {
        "fecha_desde": fecha_desde,
        "fecha_hasta": fecha_hasta,
        "search": search,
        "limit": limit,
    }


def _filtros_payload(filters):
    return {
        "fecha_desde": filters["fecha_desde"].isoformat(),
        "fecha_hasta": filters["fecha_hasta"].isoformat(),
        "search": filters["search"],
    }


def _part_expr():
    return (
        "CAST(COALESCE(NULLIF(o.part_number, ''), pn.part_number, "
        "CONCAT('ID-', o.part_number_id)) AS CHAR CHARACTER SET utf8mb4) "
        "COLLATE utf8mb4_0900_ai_ci"
    )


def _base_where_pendientes_entrada(filters, include_search=True):
    where = [
        "COALESCE(o.qc_passed, 0) = 1",
        "o.status IN ('released', 'received_shipping', 'exception')",
        "COALESCE(er.status, '') <> 'cancelled'",
        "mb.id IS NULL",
    ]
    params = []

    where.append("o.released_at >= %s")
    params.append(filters["fecha_desde"].strftime("%Y-%m-%d"))

    where.append("o.released_at < %s")
    params.append((filters["fecha_hasta"] + timedelta(days=1)).strftime("%Y-%m-%d"))

    search = filters.get("search")
    if include_search and search:
        like_value = f"%{search}%"
        where.append(
            """
            (
                COALESCE(o.part_number, '') LIKE %s
                OR COALESCE(pn.model, '') LIKE %s
                OR COALESCE(o.box_code, '') LIKE %s
                OR COALESCE(o.oqc_folio, '') LIKE %s
            )
            """
        )
        params.extend([like_value, like_value, like_value, like_value])

    return where, params


def _obtener_pendientes_entrada_almacen():
    filters = _filtros_pendientes_oqc()
    where, params = _base_where_pendientes_entrada(filters)
    part_expr = _part_expr()
    from_sql = """
        FROM oqc_release_boxes o
        JOIN exit_records er
          ON er.id = o.exit_record_id
        LEFT JOIN part_numbers pn
          ON pn.id = o.part_number_id
        LEFT JOIN embarques_movimiento_cajas mb
          ON mb.movement_type = 'entry'
         AND mb.oqc_release_box_id = o.id
    """

    summary_sql = f"""
        SELECT
          COUNT(*) AS pending_boxes,
          COALESCE(SUM(o.quantity), 0) AS pending_quantity,
          COUNT(DISTINCT {part_expr}) AS pending_parts
        {from_sql}
        WHERE {" AND ".join(where)}
    """
    summary_row = execute_query(summary_sql, tuple(params), fetch="one") or {}

    rows_sql = f"""
        SELECT
          {part_expr} AS part_number,
          MAX(COALESCE(pn.model, '')) AS product_model,
          COUNT(*) AS pending_boxes,
          COALESCE(SUM(o.quantity), 0) AS pending_quantity,
          COUNT(DISTINCT o.oqc_folio) AS oqc_folios
        {from_sql}
        WHERE {" AND ".join(where)}
        GROUP BY {part_expr}
        ORDER BY pending_quantity DESC, pending_boxes DESC, part_number ASC
        LIMIT %s
    """
    rows = execute_query(rows_sql, tuple(params + [filters["limit"]]), fetch="all") or []

    return {
        "rows": [
            {
                "part_number": _normalizar_texto(row.get("part_number")),
                "product_model": _normalizar_texto(row.get("product_model")),
                "pending_boxes": _normalizar_entero(row.get("pending_boxes")),
                "pending_quantity": _normalizar_entero(row.get("pending_quantity")),
                "oqc_folios": _normalizar_entero(row.get("oqc_folios")),
            }
            for row in rows
        ],
        "summary": {
            "pending_boxes": _normalizar_entero(summary_row.get("pending_boxes")),
            "pending_quantity": _normalizar_entero(summary_row.get("pending_quantity")),
            "pending_parts": _normalizar_entero(summary_row.get("pending_parts")),
        },
        "filters": _filtros_payload(filters),
    }


def _obtener_detalle_entrada_almacen(filters, part_number):
    where, params = _base_where_pendientes_entrada(filters, include_search=True)
    part_expr = _part_expr()
    where.append(f"{part_expr} = %s")
    params.append(part_number)

    detail_sql = f"""
        SELECT
          o.id AS oqc_release_box_id,
          o.oqc_folio,
          o.box_code,
          {part_expr} AS part_number,
          COALESCE(pn.model, '') AS product_model,
          o.quantity,
          o.released_at,
          o.created_at,
          er.folio AS exit_folio,
          er.inspection_date
        FROM oqc_release_boxes o
        JOIN exit_records er
          ON er.id = o.exit_record_id
        LEFT JOIN part_numbers pn
          ON pn.id = o.part_number_id
        LEFT JOIN embarques_movimiento_cajas mb
          ON mb.movement_type = 'entry'
         AND mb.oqc_release_box_id = o.id
        WHERE {" AND ".join(where)}
        ORDER BY o.released_at DESC, o.id DESC
        LIMIT %s
    """
    rows = execute_query(detail_sql, tuple(params + [filters["limit"]]), fetch="all") or []

    return [
        {
            "oqc_release_box_id": _normalizar_entero(row.get("oqc_release_box_id")),
            "oqc_folio": _normalizar_texto(row.get("oqc_folio")),
            "box_code": _normalizar_texto(row.get("box_code")),
            "part_number": _normalizar_texto(row.get("part_number")),
            "product_model": _normalizar_texto(row.get("product_model")),
            "quantity": _normalizar_entero(row.get("quantity")),
            "pending_quantity": _normalizar_entero(row.get("quantity")),
            "released_at": _serializar_fecha(row.get("released_at")),
            "created_at": _serializar_fecha(row.get("created_at")),
            "exit_folio": _normalizar_texto(row.get("exit_folio")),
            "inspection_date": _serializar_fecha(row.get("inspection_date")),
        }
        for row in rows
    ]


def _pendientes_liberacion_oqc_cte():
    return r"""
        WITH latest_serial AS (
          SELECT id, serial, box_code, first_scan, last_scan, lot_no
          FROM (
            SELECT
              b.id,
              b.serial,
              b.box_code,
              b.first_scan,
              b.last_scan,
              b.lot_no,
              ROW_NUMBER() OVER (
                PARTITION BY b.serial
                ORDER BY b.last_scan DESC, b.id DESC
              ) AS rn
            FROM box_scans b FORCE INDEX (idx_box_scans_lastscan_serial11)
            WHERE b.last_scan >= %s
              AND b.last_scan < %s
              AND COALESCE(b.serial, '') <> ''
              AND COALESCE(b.box_code, '') <> ''
          ) ranked
          WHERE rn = 1
        ),
        lqc_source AS (
          SELECT
            UPPER(TRIM(b.box_code)) COLLATE utf8mb4_0900_ai_ci AS box_code,
            CAST(
              COALESCE(
                NULLIF(p.part_no, ''),
                REGEXP_SUBSTR(b.serial, '[A-Z]{3}[0-9]{8}'),
                'SIN PARTE'
              ) AS CHAR CHARACTER SET utf8mb4
            ) COLLATE utf8mb4_0900_ai_ci AS part_number,
            COALESCE(NULLIF(p.model_code, ''), pn.model, '') AS product_model,
            b.serial,
            b.first_scan,
            b.last_scan,
            COALESCE(NULLIF(p.line, ''), 'SIN PLAN') AS linea,
            b.lot_no
          FROM latest_serial b
          LEFT JOIN plan_main p
            ON p.lot_no = b.lot_no
          LEFT JOIN part_numbers pn
            ON CAST(pn.part_number AS CHAR CHARACTER SET utf8mb4) COLLATE utf8mb4_0900_ai_ci =
               CAST(
                 COALESCE(
                   NULLIF(p.part_no, ''),
                   REGEXP_SUBSTR(b.serial, '[A-Z]{3}[0-9]{8}'),
                   ''
                 ) AS CHAR CHARACTER SET utf8mb4
               ) COLLATE utf8mb4_0900_ai_ci
        ),
        lqc_boxes AS (
          SELECT
            box_code,
            part_number,
            MAX(product_model) AS product_model,
            COUNT(DISTINCT serial) AS lqc_quantity,
            MIN(first_scan) AS first_lqc_scan,
            MAX(last_scan) AS last_lqc_scan,
            MAX(linea) AS lineas,
            GROUP_CONCAT(DISTINCT NULLIF(lot_no, '') ORDER BY lot_no SEPARATOR ', ') AS lotes
          FROM lqc_source
          GROUP BY box_code, part_number
        ),
        oqc_source AS (
          SELECT
            UPPER(TRIM(rb.box_code)) COLLATE utf8mb4_0900_ai_ci AS box_code,
            rb.quantity,
            rb.released_at,
            rb.oqc_folio
          FROM oqc_release_boxes rb
          JOIN exit_records er
            ON er.id = rb.exit_record_id
          WHERE rb.status IN ('released', 'received_shipping', 'exception')
            AND COALESCE(rb.qc_passed, 0) = 1
            AND COALESCE(er.status, '') <> 'cancelled'
        ),
        oqc_boxes AS (
          SELECT
            box_code,
            SUM(quantity) AS oqc_quantity,
            COUNT(*) AS oqc_records,
            MAX(released_at) AS last_oqc_release,
            GROUP_CONCAT(DISTINCT oqc_folio ORDER BY oqc_folio SEPARATOR ', ') AS oqc_folios
          FROM oqc_source
          GROUP BY box_code
        ),
        pending_boxes AS (
          SELECT
            lqc.box_code,
            lqc.part_number,
            lqc.product_model,
            lqc.lqc_quantity,
            COALESCE(oqc.oqc_quantity, 0) AS oqc_quantity,
            GREATEST(lqc.lqc_quantity - COALESCE(oqc.oqc_quantity, 0), 0) AS pending_quantity,
            lqc.first_lqc_scan,
            lqc.last_lqc_scan,
            lqc.lineas,
            lqc.lotes,
            oqc.last_oqc_release,
            COALESCE(oqc.oqc_folios, '') AS oqc_folios
          FROM lqc_boxes lqc
          LEFT JOIN oqc_boxes oqc
            ON oqc.box_code = lqc.box_code
          WHERE COALESCE(oqc.oqc_quantity, 0) < lqc.lqc_quantity
        )
    """


def _params_fecha_lqc(filters):
    return [
        filters["fecha_desde"].strftime("%Y-%m-%d"),
        (filters["fecha_hasta"] + timedelta(days=1)).strftime("%Y-%m-%d"),
    ]


def _where_busqueda_liberacion_oqc(filters, extra_conditions=None, extra_params=None):
    conditions = list(extra_conditions or [])
    params = list(extra_params or [])
    search = filters.get("search")
    if search:
        like_value = f"%{search}%"
        conditions.append(
            """
            (
                part_number LIKE %s
                OR product_model LIKE %s
                OR box_code LIKE %s
                OR lineas LIKE %s
                OR lotes LIKE %s
                OR oqc_folios LIKE %s
            )
            """
        )
        params.extend([like_value] * 6)
    if not conditions:
        return "", params
    return "WHERE " + " AND ".join(conditions), params


def _obtener_pendientes_liberacion_oqc():
    filters = _filtros_pendientes_oqc()
    cte_sql = _pendientes_liberacion_oqc_cte()
    where_sql, where_params = _where_busqueda_liberacion_oqc(filters)
    base_params = _params_fecha_lqc(filters)

    summary_sql = f"""
        {cte_sql}
        SELECT
          COUNT(*) AS pending_boxes,
          COALESCE(SUM(pending_quantity), 0) AS pending_quantity,
          COUNT(DISTINCT part_number) AS pending_parts
        FROM pending_boxes
        {where_sql}
    """
    summary_row = execute_query(
        summary_sql,
        tuple(base_params + where_params),
        fetch="one",
    ) or {}

    rows_sql = f"""
        {cte_sql}
        SELECT
          part_number,
          MAX(product_model) AS product_model,
          COUNT(*) AS pending_boxes,
          COALESCE(SUM(lqc_quantity), 0) AS lqc_quantity,
          COALESCE(SUM(oqc_quantity), 0) AS oqc_quantity,
          COALESCE(SUM(pending_quantity), 0) AS pending_quantity
        FROM pending_boxes
        {where_sql}
        GROUP BY part_number
        ORDER BY pending_quantity DESC, pending_boxes DESC, part_number ASC
        LIMIT %s
    """
    rows = execute_query(
        rows_sql,
        tuple(base_params + where_params + [filters["limit"]]),
        fetch="all",
    ) or []

    return {
        "rows": [
            {
                "part_number": _normalizar_texto(row.get("part_number")),
                "product_model": _normalizar_texto(row.get("product_model")),
                "pending_boxes": _normalizar_entero(row.get("pending_boxes")),
                "lqc_quantity": _normalizar_entero(row.get("lqc_quantity")),
                "oqc_quantity": _normalizar_entero(row.get("oqc_quantity")),
                "pending_quantity": _normalizar_entero(row.get("pending_quantity")),
            }
            for row in rows
        ],
        "summary": {
            "pending_boxes": _normalizar_entero(summary_row.get("pending_boxes")),
            "pending_quantity": _normalizar_entero(summary_row.get("pending_quantity")),
            "pending_parts": _normalizar_entero(summary_row.get("pending_parts")),
        },
        "filters": _filtros_payload(filters),
    }


def _obtener_detalle_liberacion_oqc(filters, part_number):
    cte_sql = _pendientes_liberacion_oqc_cte()
    where_sql, where_params = _where_busqueda_liberacion_oqc(
        filters,
        extra_conditions=["part_number = %s"],
        extra_params=[part_number],
    )

    detail_sql = f"""
        {cte_sql}
        SELECT
          box_code,
          part_number,
          product_model,
          lqc_quantity,
          oqc_quantity,
          pending_quantity,
          lineas,
          lotes,
          last_lqc_scan,
          last_oqc_release,
          oqc_folios
        FROM pending_boxes
        {where_sql}
        ORDER BY last_lqc_scan DESC, box_code ASC
        LIMIT %s
    """
    rows = execute_query(
        detail_sql,
        tuple(_params_fecha_lqc(filters) + where_params + [filters["limit"]]),
        fetch="all",
    ) or []

    return [
        {
            "box_code": _normalizar_texto(row.get("box_code")),
            "part_number": _normalizar_texto(row.get("part_number")),
            "product_model": _normalizar_texto(row.get("product_model")),
            "lqc_quantity": _normalizar_entero(row.get("lqc_quantity")),
            "oqc_quantity": _normalizar_entero(row.get("oqc_quantity")),
            "quantity": _normalizar_entero(row.get("pending_quantity")),
            "pending_quantity": _normalizar_entero(row.get("pending_quantity")),
            "lineas": _normalizar_texto(row.get("lineas")),
            "lotes": _normalizar_texto(row.get("lotes")),
            "last_lqc_scan": _serializar_fecha(row.get("last_lqc_scan")),
            "last_oqc_release": _serializar_fecha(row.get("last_oqc_release")),
            "oqc_folios": _normalizar_texto(row.get("oqc_folios")),
        }
        for row in rows
    ]


def _obtener_pendientes_qa_resumen():
    entrada = _obtener_pendientes_entrada_almacen()
    liberacion = _obtener_pendientes_liberacion_oqc()
    return {
        "entry": entrada,
        "release": liberacion,
        "rows": entrada["rows"],
        "summary": entrada["summary"],
        "filters": entrada["filters"],
    }


def _obtener_pendientes_oqc_cajas():
    filters = _filtros_pendientes_oqc()
    part_number = _normalizar_texto(request.args.get("part_number"))
    detail_type = _normalizar_texto(
        request.args.get("tipo") or request.args.get("type") or "entrada"
    ).lower()

    if not part_number:
        return {
            "success": False,
            "error": "Se requiere numero de parte",
            "boxes": [],
        }, 400

    if detail_type in {"liberacion", "release", "oqc"}:
        boxes = _obtener_detalle_liberacion_oqc(filters, part_number)
        normalized_type = "liberacion"
    else:
        boxes = _obtener_detalle_entrada_almacen(filters, part_number)
        normalized_type = "entrada"

    return {
        "success": True,
        "type": normalized_type,
        "part_number": part_number,
        "boxes": boxes,
        "summary": {
            "pending_boxes": len(boxes),
            "pending_quantity": sum(box["pending_quantity"] for box in boxes),
        },
        "filters": _filtros_payload(filters),
    }, 200


@bp.route("/almacen-embarques-qa-pendientes-ajax")
@bp.route("/almacen-embarques-oqc-pendientes-ajax")
@login_requerido
@_requiere_permiso_pendientes_oqc
def almacen_embarques_oqc_pendientes_ajax():
    try:
        return render_template(
            "Control de proceso/almacen_embarques_oqc_pendientes_ajax.html"
        )
    except Exception as e:
        logger.error("Error al cargar pendientes QA embarques: %s", e)
        return f"Error al cargar el contenido: {str(e)}", 500


@bp.route("/api/almacen-embarques/qa-pendientes")
@bp.route("/api/almacen-embarques/oqc-pendientes")
@login_requerido
@_requiere_permiso_pendientes_oqc
def api_almacen_embarques_oqc_pendientes():
    try:
        payload = _obtener_pendientes_qa_resumen()
        payload["success"] = True
        return jsonify(payload)
    except Exception as e:
        logger.error("Error API pendientes QA embarques: %s\n%s", e, traceback.format_exc())
        return jsonify({"success": False, "error": str(e), "rows": []}), 500


@bp.route("/api/almacen-embarques/qa-pendientes/cajas")
@bp.route("/api/almacen-embarques/oqc-pendientes/cajas")
@login_requerido
@_requiere_permiso_pendientes_oqc
def api_almacen_embarques_oqc_pendientes_cajas():
    try:
        payload, status_code = _obtener_pendientes_oqc_cajas()
        return jsonify(payload), status_code
    except Exception as e:
        logger.error("Error API detalle pendientes QA embarques: %s\n%s", e, traceback.format_exc())
        return jsonify({"success": False, "error": str(e), "boxes": []}), 500
