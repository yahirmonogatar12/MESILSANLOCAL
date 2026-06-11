"""Endpoints HTTP del modulo "Inventario reparacion ASSY".

Modulo de SOLO LECTURA / reportes sobre la tabla compartida
`pcb_inventory_scan_prod` (filtrando area='REPARACION'). Esta tabla la llena la
app "Control_produccion" escaneando QR; ambas apps comparten la misma base de
datos MySQL, por lo que aqui solo se consulta.

Es el gemelo de inventario_reparacion_smd.py: mismo patron, misma estructura de
tabla, pero apuntando a pcb_inventory_scan_prod y con la columna extra
`linea_salida_pcb` (linea por la que salio el PCB) en el detalle de movimientos.

Consumido por LISTA_DE_CONTROL_DE_RESULTADOS / Control de inventario, justo
despues de "Inventario reparacion SMD".

JS cliente: app/static/js/inventario-reparacion-assy-module.js
Template:   app/templates/Control de resultados/inventario_reparacion_assy_ajax.html

Rutas:
  GET /control_resultados/inventario_reparacion_assy       -> render template
  GET /api/reparacion_assy/stock                           -> stock actual (JSON)
  GET /api/reparacion_assy/stock/export                    -> stock actual (.xlsx)
  GET /api/reparacion_assy/movimientos                     -> detalle mov. (JSON)
  GET /api/reparacion_assy/movimientos/export             -> detalle mov. (.xlsx)
  GET /api/reparacion_assy/defectos                        -> resumen defecto (JSON)
  GET /api/reparacion_assy/defectos/export                 -> resumen defecto (.xlsx)

Stock = SUM(ENTRADA) - SUM(SALIDA) - SUM(SCRAP). Todas las queries fijan
area='REPARACION'.
"""

import logging
import traceback

from flask import Blueprint, jsonify, render_template, request

from app.api.shared import (
    excel_response,
    execute_query,
    formatear_hora,
    login_requerido,
    requiere_permiso_dropdown,
)

logger = logging.getLogger(__name__)


bp = Blueprint("control_resultados_inventario_reparacion_assy", __name__)


REPA_PERMISO_PAGINA = "LISTA_DE_CONTROL_DE_RESULTADOS"
REPA_PERMISO_SECCION = "Control de inventario"
REPA_PERMISO_BOTON = "Inventario reparacion ASSY"


# Decorador con el permiso fijo del modulo. La fachada accede a auth_system de
# forma lazy en el request, por lo que no hay import circular al cargar.
_requiere_permiso_repa = requiere_permiso_dropdown(
    REPA_PERMISO_PAGINA, REPA_PERMISO_SECCION, REPA_PERMISO_BOTON
)


# ---------------------------------------------------------------------------
# Render template
# ---------------------------------------------------------------------------


@bp.route("/control_resultados/inventario_reparacion_assy")
@login_requerido
@_requiere_permiso_repa
def inventario_reparacion_assy_ajax():
    """Ruta AJAX canonica para cargar el contenido de Inventario reparacion ASSY."""
    try:
        logger.info("Iniciando carga de Inventario reparacion ASSY AJAX...")
        return render_template(
            "Control de resultados/inventario_reparacion_assy_ajax.html"
        )
    except Exception as e:
        logger.error("Error al cargar template Inventario reparacion ASSY AJAX: %s", e)
        logger.info(traceback.format_exc())
        return f"Error al cargar el contenido: {str(e)}", 500


# ---------------------------------------------------------------------------
# Helpers de filtros (comunes a las 3 vistas)
# ---------------------------------------------------------------------------


def _filtros_comunes():
    """Lee filtros comunes desde query params y construye fragmentos SQL.

    Devuelve (where_sql, params). area='REPARACION' siempre fijo.
    """
    numero_parte = request.args.get("numero_parte", "", type=str).strip()
    proceso = request.args.get("proceso", "", type=str).strip().upper()
    fecha_inicio = request.args.get("fecha_inicio", "", type=str).strip()
    fecha_fin = request.args.get("fecha_fin", "", type=str).strip()

    where = ["area = 'REPARACION'"]
    params = []

    if numero_parte:
        where.append("(pcb_part_no LIKE %s OR modelo LIKE %s)")
        params.extend([f"%{numero_parte}%", f"%{numero_parte}%"])

    if proceso in ("SMD", "IMD", "ASSY"):
        where.append("proceso = %s")
        params.append(proceso)

    if fecha_inicio:
        where.append("inventory_date >= %s")
        params.append(fecha_inicio)

    if fecha_fin:
        where.append("inventory_date <= %s")
        params.append(fecha_fin)

    return " AND ".join(where), params


# ---------------------------------------------------------------------------
# Vista 1: Stock actual de reparacion
# ---------------------------------------------------------------------------


def _query_stock(limit):
    """Construye y ejecuta la query de stock. Devuelve lista de dicts."""
    where_sql, params = _filtros_comunes()
    include_zero = request.args.get("include_zero", "", type=str).strip().lower()

    having_sql = "" if include_zero in ("1", "true", "si", "yes") else "HAVING stock_actual <> 0"

    sql = f"""
        SELECT
          pcb_part_no,
          modelo,
          proceso,
          SUM(CASE WHEN tipo_movimiento = 'ENTRADA' THEN qty ELSE 0 END) AS total_entrada,
          SUM(CASE WHEN tipo_movimiento = 'SALIDA'  THEN qty ELSE 0 END) AS total_salida,
          SUM(CASE WHEN tipo_movimiento = 'SCRAP'   THEN qty ELSE 0 END) AS total_scrap,
          SUM(CASE WHEN tipo_movimiento = 'ENTRADA' THEN qty ELSE 0 END)
            - SUM(CASE WHEN tipo_movimiento IN ('SALIDA','SCRAP') THEN qty ELSE 0 END) AS stock_actual
        FROM pcb_inventory_scan_prod
        WHERE {where_sql}
        GROUP BY pcb_part_no, modelo, proceso
        {having_sql}
        ORDER BY pcb_part_no, proceso
        LIMIT {int(limit)}
    """
    rows = execute_query(sql, params or None, fetch="all") or []
    result = []
    for r in rows:
        result.append({
            "pcb_part_no": r.get("pcb_part_no") or "",
            "modelo": r.get("modelo") or "",
            "proceso": r.get("proceso") or "",
            "total_entrada": int(r.get("total_entrada") or 0),
            "total_salida": int(r.get("total_salida") or 0),
            "total_scrap": int(r.get("total_scrap") or 0),
            "stock_actual": int(r.get("stock_actual") or 0),
        })
    return result


@bp.route("/api/reparacion_assy/stock", methods=["GET"])
@login_requerido
def api_reparacion_assy_stock():
    """Stock actual de reparacion (prod) agrupado por parte/modelo/proceso."""
    try:
        items = _query_stock(limit=2000)
        return jsonify({"status": "success", "items": items})
    except Exception as e:
        logger.error("Error en api_reparacion_assy_stock: %s", e)
        return jsonify({"status": "error", "message": str(e), "items": []}), 500


@bp.route("/api/reparacion_assy/stock/export", methods=["GET"])
@login_requerido
def api_reparacion_assy_stock_export():
    """Exportar stock de reparacion (prod) a Excel."""
    try:
        items = _query_stock(limit=10000)
        headers = [
            "No. Parte", "Modelo", "Proceso",
            "Total Entrada", "Total Salida", "Total Scrap", "Stock Actual",
        ]
        keys = [
            "pcb_part_no", "modelo", "proceso",
            "total_entrada", "total_salida", "total_scrap", "stock_actual",
        ]
        widths = [16, 24, 10, 14, 14, 12, 14]
        return excel_response(
            items, headers, keys, widths,
            sheet="Stock Reparacion ASSY", filename="stock_reparacion_assy",
        )
    except Exception as e:
        logger.exception("Error exportando stock reparacion ASSY: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 500


# ---------------------------------------------------------------------------
# Vista 2: Detalle de movimientos
# ---------------------------------------------------------------------------


def _query_movimientos(limit=None):
    """Detalle de movimientos. limit=None -> sin LIMIT (consulta completa)."""
    where_sql, params = _filtros_comunes()
    tipo = request.args.get("tipo_movimiento", "", type=str).strip().upper()
    if tipo in ("ENTRADA", "SALIDA", "SCRAP"):
        where_sql += " AND tipo_movimiento = %s"
        params.append(tipo)

    limit_sql = "" if limit is None else f"LIMIT {int(limit)}"

    # Nota: no usar DATE_FORMAT con '%...' aqui. execute_query solo interpola
    # '%' cuando hay params; sin filtros la query se ejecuta sin interpolacion
    # y el '%%' quedaria literal. TIME()/created_at no tienen ese problema.
    sql = f"""
        SELECT
          inventory_date,
          created_at         AS fecha_hora,
          TIME(created_at)   AS hora,
          tipo_movimiento,
          scanned_original,
          pcb_part_no,
          modelo,
          proceso,
          defect_type,
          component_location,
          etapa_deteccion,
          linea_salida_pcb,
          qty,
          array_count,
          scanned_by,
          comentarios
        FROM pcb_inventory_scan_prod
        WHERE {where_sql}
        ORDER BY created_at DESC, id DESC
        {limit_sql}
    """
    rows = execute_query(sql, params or None, fetch="all") or []
    result = []
    for r in rows:
        result.append({
            "inventory_date": str(r.get("inventory_date") or ""),
            "fecha_hora": str(r.get("fecha_hora") or ""),
            "hora": formatear_hora(r.get("hora")),
            "tipo_movimiento": r.get("tipo_movimiento") or "",
            "scanned_original": r.get("scanned_original") or "",
            "pcb_part_no": r.get("pcb_part_no") or "",
            "modelo": r.get("modelo") or "",
            "proceso": r.get("proceso") or "",
            "defect_type": r.get("defect_type") or "",
            "component_location": r.get("component_location") or "",
            "etapa_deteccion": r.get("etapa_deteccion") or "",
            "linea_salida_pcb": r.get("linea_salida_pcb") or "",
            "qty": int(r.get("qty") or 0),
            "array_count": int(r.get("array_count") or 0),
            "scanned_by": r.get("scanned_by") or "",
            "comentarios": r.get("comentarios") or "",
        })
    return result


@bp.route("/api/reparacion_assy/movimientos", methods=["GET"])
@login_requerido
def api_reparacion_assy_movimientos():
    """Detalle de transacciones (ENTRADA/SALIDA/SCRAP) de reparacion (prod)."""
    try:
        items = _query_movimientos(limit=None)
        return jsonify({"status": "success", "items": items})
    except Exception as e:
        logger.error("Error en api_reparacion_assy_movimientos: %s", e)
        return jsonify({"status": "error", "message": str(e), "items": []}), 500


@bp.route("/api/reparacion_assy/movimientos/export", methods=["GET"])
@login_requerido
def api_reparacion_assy_movimientos_export():
    """Exportar detalle de movimientos de reparacion (prod) a Excel."""
    try:
        items = _query_movimientos(limit=None)
        headers = [
            "Fecha", "Hora", "Tipo", "QR", "No. Parte", "Modelo", "Proceso",
            "Defecto", "Ubic. Componente", "Etapa Deteccion", "Linea salida",
            "Qty", "Array", "Usuario", "Comentarios",
        ]
        keys = [
            "inventory_date", "hora", "tipo_movimiento", "scanned_original",
            "pcb_part_no", "modelo", "proceso", "defect_type",
            "component_location", "etapa_deteccion", "linea_salida_pcb",
            "qty", "array_count", "scanned_by", "comentarios",
        ]
        widths = [12, 10, 9, 30, 16, 22, 9, 18, 18, 14, 13, 7, 7, 14, 24]
        return excel_response(
            items, headers, keys, widths,
            sheet="Movimientos Reparacion ASSY", filename="movimientos_reparacion_assy",
        )
    except Exception as e:
        logger.exception("Error exportando movimientos reparacion ASSY: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 500


# ---------------------------------------------------------------------------
# Vista 3: Resumen por tipo de defecto
# ---------------------------------------------------------------------------


def _query_defectos(limit):
    where_sql, params = _filtros_comunes()
    # Solo las piezas que ENTRAN a reparacion definen el defecto.
    where_sql += " AND tipo_movimiento = 'ENTRADA'"

    sql = f"""
        SELECT
          COALESCE(NULLIF(defect_type, ''), '(sin defecto)')        AS defect_type,
          COALESCE(NULLIF(etapa_deteccion, ''), '(sin etapa)')      AS etapa_deteccion,
          COUNT(*)   AS registros,
          SUM(qty)   AS qty_total
        FROM pcb_inventory_scan_prod
        WHERE {where_sql}
        GROUP BY defect_type, etapa_deteccion
        ORDER BY qty_total DESC, registros DESC
        LIMIT {int(limit)}
    """
    rows = execute_query(sql, params or None, fetch="all") or []
    result = []
    for r in rows:
        result.append({
            "defect_type": r.get("defect_type") or "",
            "etapa_deteccion": r.get("etapa_deteccion") or "",
            "registros": int(r.get("registros") or 0),
            "qty_total": int(r.get("qty_total") or 0),
        })
    return result


@bp.route("/api/reparacion_assy/defectos", methods=["GET"])
@login_requerido
def api_reparacion_assy_defectos():
    """Resumen de entradas a reparacion (prod) agrupado por defecto y etapa."""
    try:
        items = _query_defectos(limit=2000)
        return jsonify({"status": "success", "items": items})
    except Exception as e:
        logger.error("Error en api_reparacion_assy_defectos: %s", e)
        return jsonify({"status": "error", "message": str(e), "items": []}), 500


@bp.route("/api/reparacion_assy/defectos/export", methods=["GET"])
@login_requerido
def api_reparacion_assy_defectos_export():
    """Exportar resumen por defecto de reparacion (prod) a Excel."""
    try:
        items = _query_defectos(limit=10000)
        headers = ["Defecto", "Etapa Deteccion", "# Registros", "Qty Total"]
        keys = ["defect_type", "etapa_deteccion", "registros", "qty_total"]
        widths = [28, 18, 14, 12]
        return excel_response(
            items, headers, keys, widths,
            sheet="Defectos Reparacion ASSY", filename="defectos_reparacion_assy",
        )
    except Exception as e:
        logger.exception("Error exportando defectos reparacion ASSY: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 500


# La generacion del .xlsx vive en app/api/shared/excel.py (excel_response),
# compartida con inventario_reparacion_smd, stations_qa y
# historial_operadores_maquina.
