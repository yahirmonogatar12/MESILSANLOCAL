"""Endpoints HTTP del modulo "Trazabilidad de PCB".

Modulo de SOLO LECTURA / reportes que unifica la trazabilidad material->PCB de
los tres procesos en una sola vista:

  ASSY -> trazabilidad_material_pcb        (alimentada por history_material_assy + input_main)
  IMD  -> trazabilidad_material_pcb_imd    (history_material_imd + output_imd)
  SMT  -> trazabilidad_material_pcb_smt    (historial_cambio_material_smt + input_smt; migracion 019)

Las tres tablas son columna-identicas, asi que se consultan con UNION ALL
agregando una columna 'proceso'. Todo es de solo lectura: estas tablas las
llenan triggers de la base compartida.

Consumido por LISTA_DE_CONTROL_DE_RESULTADOS / Control de inventario.

JS cliente: app/static/js/trazabilidad-pcb.js
Template:   app/templates/Control de resultados/trazabilidad_pcb_ajax.html

Rutas:
  GET /control_resultados/trazabilidad_pcb              -> render template
  GET /api/trazabilidad_pcb/materiales                  -> material por lote prod (JSON)
  GET /api/trazabilidad_pcb/materiales/export           -> idem (.xlsx)
  GET /api/trazabilidad_pcb/por_proveedor               -> trazabilidad inversa por lote prov (JSON)
  GET /api/trazabilidad_pcb/por_proveedor/export        -> idem (.xlsx)
"""

import logging
import traceback

from flask import Blueprint, jsonify, request

from app.api.shared import (
    excel_response,
    execute_query,
    login_requerido,
    obtener_fecha_mexico,
)

logger = logging.getLogger(__name__)


bp = Blueprint("control_resultados_trazabilidad_pcb", __name__)


# Subconsulta union de las 3 tablas de trazabilidad con la columna proceso.
# Se usa como tabla derivada en todas las queries del modulo.
_UNION_TRAZA = """
    (
      SELECT 'ASSY' AS proceso, lot_no, plan_id, linea, part_no, material_code,
             codigo_material_recibido, numero_lote_material, posicion, container_id,
             cantidad_inicial, cantidad_consumida, cantidad_restante, pcb_count,
             material_start_ts, material_end_ts, pcb_first_ts, pcb_last_ts, status
      FROM trazabilidad_material_pcb
      UNION ALL
      SELECT 'IMD' AS proceso, lot_no, plan_id, linea, part_no, material_code,
             codigo_material_recibido, numero_lote_material, posicion, container_id,
             cantidad_inicial, cantidad_consumida, cantidad_restante, pcb_count,
             material_start_ts, material_end_ts, pcb_first_ts, pcb_last_ts, status
      FROM trazabilidad_material_pcb_imd
      UNION ALL
      SELECT 'SMT' AS proceso, lot_no, plan_id, linea, part_no, material_code,
             codigo_material_recibido, numero_lote_material, posicion, container_id,
             cantidad_inicial, cantidad_consumida, cantidad_restante, pcb_count,
             material_start_ts, material_end_ts, pcb_first_ts, pcb_last_ts, status
      FROM trazabilidad_material_pcb_smt
    ) t
"""


# ---------------------------------------------------------------------------
# Render template
# ---------------------------------------------------------------------------


@bp.route("/control_resultados/trazabilidad_pcb")
@login_requerido
def trazabilidad_pcb_ajax():
    """Ruta AJAX canonica para cargar el contenido de Trazabilidad de PCB."""
    try:
        from flask import render_template
        return render_template("Control de resultados/trazabilidad_pcb_ajax.html")
    except Exception as e:
        logger.error("Error al cargar template Trazabilidad de PCB AJAX: %s", e)
        logger.info(traceback.format_exc())
        return f"Error al cargar el contenido: {str(e)}", 500


# ---------------------------------------------------------------------------
# Filtros comunes
# ---------------------------------------------------------------------------


def _filtros_comunes():
    """Lee filtros de query params y devuelve (where_sql, params).

    proceso: ASSY/IMD/SMT exacto. lote/parte/material/lote_proveedor: LIKE.
    fecha_inicio/fecha_fin sobre DATE(material_start_ts).
    """
    proceso = request.args.get("proceso", "", type=str).strip().upper()
    lot_no = request.args.get("lot_no", "", type=str).strip()
    part_no = request.args.get("part_no", "", type=str).strip()
    material = request.args.get("material", "", type=str).strip()
    fecha_inicio = request.args.get("fecha_inicio", "", type=str).strip()
    fecha_fin = request.args.get("fecha_fin", "", type=str).strip()

    where = ["1=1"]
    params = []

    if proceso in ("ASSY", "IMD", "SMT"):
        where.append("t.proceso = %s")
        params.append(proceso)
    if lot_no:
        where.append("t.lot_no LIKE %s")
        params.append(f"%{lot_no}%")
    if part_no:
        where.append("t.part_no LIKE %s")
        params.append(f"%{part_no}%")
    if material:
        where.append("(t.material_code LIKE %s OR t.numero_lote_material LIKE %s)")
        params.extend([f"%{material}%", f"%{material}%"])
    if fecha_inicio:
        where.append("DATE(t.material_start_ts) >= %s")
        params.append(fecha_inicio)
    if fecha_fin:
        where.append("DATE(t.material_start_ts) <= %s")
        params.append(fecha_fin)

    return " AND ".join(where), params


# ---------------------------------------------------------------------------
# Vista 1: Materiales por lote de produccion (PCB -> materiales)
# ---------------------------------------------------------------------------


def _query_materiales(limit):
    where_sql, params = _filtros_comunes()
    sql = f"""
        SELECT
          t.proceso, t.lot_no, t.linea, t.part_no, t.material_code,
          t.numero_lote_material, t.codigo_material_recibido, t.posicion,
          t.container_id, t.cantidad_inicial, t.cantidad_consumida,
          t.cantidad_restante, t.pcb_count, t.status,
          t.material_start_ts, t.material_end_ts, t.pcb_last_ts
        FROM {_UNION_TRAZA}
        WHERE {where_sql}
        ORDER BY t.material_start_ts DESC
        LIMIT {int(limit)}
    """
    rows = execute_query(sql, params or None, fetch="all") or []
    result = []
    for r in rows:
        result.append({
            "proceso": r.get("proceso") or "",
            "lot_no": r.get("lot_no") or "",
            "linea": r.get("linea") or "",
            "part_no": r.get("part_no") or "",
            "material_code": r.get("material_code") or "",
            "numero_lote_material": r.get("numero_lote_material") or "",
            "codigo_material_recibido": r.get("codigo_material_recibido") or "",
            "posicion": r.get("posicion") or "",
            "container_id": r.get("container_id") or "",
            "cantidad_inicial": int(r.get("cantidad_inicial") or 0),
            "cantidad_consumida": int(r.get("cantidad_consumida") or 0),
            "cantidad_restante": int(r.get("cantidad_restante") or 0),
            "pcb_count": int(r.get("pcb_count") or 0),
            "status": r.get("status") or "",
            "material_start_ts": str(r.get("material_start_ts") or ""),
            "material_end_ts": str(r.get("material_end_ts") or ""),
            "pcb_last_ts": str(r.get("pcb_last_ts") or ""),
        })
    return result


@bp.route("/api/trazabilidad_pcb/materiales", methods=["GET"])
@login_requerido
def api_traza_materiales():
    """Materiales usados por lote de produccion, a traves de ASSY/IMD/SMT.
    Incluye fecha_hoy (hora planta, helper de shared) para que el front preseleccione
    el filtro Desde en el dia actual."""
    try:
        items = _query_materiales(limit=3000)
        return jsonify({"status": "success", "items": items, "fecha_hoy": obtener_fecha_mexico()})
    except Exception as e:
        logger.error("Error en api_traza_materiales: %s", e)
        return jsonify({"status": "error", "message": str(e), "items": []}), 500


@bp.route("/api/trazabilidad_pcb/materiales/export", methods=["GET"])
@login_requerido
def api_traza_materiales_export():
    """Exportar materiales por lote a Excel."""
    try:
        items = _query_materiales(limit=20000)
        headers = [
            "Proceso", "Lote Produccion", "Linea", "No. Parte (PCB)", "Material",
            "Lote Proveedor", "Codigo Recibido", "Posicion", "Contenedor",
            "Cant. Inicial", "Consumido", "Restante", "PCBs", "Estado",
            "Inicio Material", "Fin Material", "Ultimo PCB",
        ]
        keys = [
            "proceso", "lot_no", "linea", "part_no", "material_code",
            "numero_lote_material", "codigo_material_recibido", "posicion", "container_id",
            "cantidad_inicial", "cantidad_consumida", "cantidad_restante", "pcb_count", "status",
            "material_start_ts", "material_end_ts", "pcb_last_ts",
        ]
        widths = [8, 22, 8, 18, 18, 26, 26, 14, 26, 12, 11, 10, 8, 12, 18, 18, 18]
        return excel_response(
            items, headers, keys, widths,
            sheet="Trazabilidad PCB", filename="trazabilidad_pcb_materiales",
        )
    except Exception as e:
        logger.exception("Error exportando materiales trazabilidad: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 500


# ---------------------------------------------------------------------------
# Vista 2: Trazabilidad inversa por lote de proveedor
# (lote proveedor -> que lotes de produccion / PCBs lo usaron)
# ---------------------------------------------------------------------------


# UNION a nivel PCB-material para trazabilidad inversa (recall): cada fila es un
# PCB que uso un material. ASSY/IMD desde el poller; SMT desde el detalle.
_UNION_PCB_MATERIAL = """
    (
      SELECT 'ASSY' AS proceso,
             COALESCE(NULLIF(im.raw_barcode, ''), p.pcb_raw) AS pcb_serial,
             p.pcb_ts AS ts, p.lot_no, p.linea, p.nparte AS part_no,
             p.material AS material_code, p.lote_proveedor AS numero_lote_material,
             p.posicion, p.codigo_material_recibido
      FROM pcb_material_link p
      JOIN input_main im ON im.id = p.input_main_id
      UNION ALL
      SELECT 'IMD',
             COALESCE(NULLIF(o.raw, ''), p.pcb_raw),
             p.pcb_ts, p.lot_no, p.linea, p.nparte,
             p.material, p.lote_proveedor, p.posicion, p.codigo_material_recibido
      FROM pcb_material_link_imd p
      JOIN output_imd o ON o.id = p.input_main_id
      UNION ALL
      SELECT 'SMT', d.pcb_serial, d.ts, t.lot_no, t.linea, t.part_no,
             t.material_code, t.numero_lote_material, t.posicion, t.codigo_material_recibido
      FROM consumo_material_detalle_smt d
      JOIN trazabilidad_material_pcb_smt t ON t.id = d.trazabilidad_id
    ) d
"""


def _query_por_proveedor(limit):
    """Trazabilidad inversa a nivel PCB: cada PCB vinculado a un lote de proveedor.

    El filtro material/lote se EMPUJA dentro de cada rama del UNION (sobre
    pcb_material_link/_imd, que tienen indice por material) en vez de filtrar la
    derivada ya materializada: si no, MySQL escanea 1.9M filas antes de filtrar
    -> timeout. Por eso material es obligatorio en la ruta.
    """
    proceso = request.args.get("proceso", "", type=str).strip().upper()
    material = request.args.get("material", "", type=str).strip()
    fecha_inicio = request.args.get("fecha_inicio", "", type=str).strip()
    fecha_fin = request.args.get("fecha_fin", "", type=str).strip()

    # Filtro por PREFIJO (LIKE 'valor%'). Tolerante (el operador escribe el inicio
    # del lote/material, no necesita el codigo exacto con todos los '!') y AUN usa
    # los indices idx_material / idx_lote_proveedor (type=range), a diferencia de
    # '%valor%' que haria full scan de 1.9M filas y timeout.
    pref = f"{material}%"
    pml = "(p.material LIKE %s OR p.lote_proveedor LIKE %s) AND p.lote_proveedor IS NOT NULL AND p.lote_proveedor <> ''"
    smt = "(t.material_code LIKE %s OR t.numero_lote_material LIKE %s) AND t.numero_lote_material IS NOT NULL AND t.numero_lote_material <> ''"

    ramas = []
    params = []
    if proceso in ("", "ASSY"):
        ramas.append(f"""
          SELECT 'ASSY' AS proceso, COALESCE(NULLIF(im.raw_barcode,''),p.pcb_raw) AS pcb_serial,
                 p.pcb_ts AS ts, p.lot_no, p.linea, p.nparte AS part_no,
                 p.material AS material_code, p.lote_proveedor AS numero_lote_material, p.posicion
          FROM pcb_material_link p JOIN input_main im ON im.id=p.input_main_id
          WHERE {pml}""")
        params += [pref, pref]
    if proceso in ("", "IMD"):
        ramas.append(f"""
          SELECT 'IMD', COALESCE(NULLIF(o.raw,''),p.pcb_raw), p.pcb_ts, p.lot_no, p.linea,
                 p.nparte, p.material, p.lote_proveedor, p.posicion
          FROM pcb_material_link_imd p JOIN output_imd o ON o.id=p.input_main_id
          WHERE {pml}""")
        params += [pref, pref]
    if proceso in ("", "SMT"):
        ramas.append(f"""
          SELECT 'SMT', d.pcb_serial, d.ts, t.lot_no, t.linea, t.part_no,
                 t.material_code, t.numero_lote_material, t.posicion
          FROM consumo_material_detalle_smt d JOIN trazabilidad_material_pcb_smt t ON t.id=d.trazabilidad_id
          WHERE {smt}""")
        params += [pref, pref]

    where_fecha = []
    if fecha_inicio:
        where_fecha.append("DATE(d.ts) >= %s")
        params.append(fecha_inicio)
    if fecha_fin:
        where_fecha.append("DATE(d.ts) <= %s")
        params.append(fecha_fin)
    fecha_sql = (" WHERE " + " AND ".join(where_fecha)) if where_fecha else ""

    sql = f"""
        SELECT d.proceso, d.pcb_serial, d.ts, d.lot_no, d.linea, d.part_no,
               d.material_code, d.numero_lote_material AS lote_proveedor, d.posicion
        FROM ( {" UNION ALL ".join(ramas)} ) d
        {fecha_sql}
        ORDER BY d.ts DESC
        LIMIT {int(limit)}
    """
    rows = execute_query(sql, params or None, fetch="all") or []
    result = []
    for r in rows:
        result.append({
            "lote_proveedor": r.get("lote_proveedor") or "",
            "material_code": r.get("material_code") or "",
            "proceso": r.get("proceso") or "",
            "pcb_serial": r.get("pcb_serial") or "",
            "ts": str(r.get("ts") or ""),
            "lot_no": r.get("lot_no") or "",
            "linea": r.get("linea") or "",
            "part_no": r.get("part_no") or "",
            "posicion": r.get("posicion") or "",
        })
    return result


@bp.route("/api/trazabilidad_pcb/por_proveedor", methods=["GET"])
@login_requerido
def api_traza_por_proveedor():
    """Trazabilidad inversa: cada PCB vinculado a un lote de proveedor (recall).
    Requiere filtro 'material' (lote proveedor o material) para no traer todo."""
    try:
        material = request.args.get("material", "", type=str).strip()
        if not material:
            return jsonify({"status": "success", "items": [],
                            "message": "Ingresa un lote de proveedor o material"})
        items = _query_por_proveedor(limit=5000)
        return jsonify({"status": "success", "items": items})
    except Exception as e:
        logger.error("Error en api_traza_por_proveedor: %s", e)
        return jsonify({"status": "error", "message": str(e), "items": []}), 500


@bp.route("/api/trazabilidad_pcb/por_proveedor/export", methods=["GET"])
@login_requerido
def api_traza_por_proveedor_export():
    """Exportar trazabilidad inversa (PCBs por lote proveedor) a Excel."""
    try:
        items = _query_por_proveedor(limit=50000)
        headers = [
            "Lote Proveedor", "Material", "Proceso", "PCB (QR/Barcode)", "Fecha",
            "Lote Produccion", "Linea", "No. Parte (PCB)", "Posicion",
        ]
        keys = [
            "lote_proveedor", "material_code", "proceso", "pcb_serial", "ts",
            "lot_no", "linea", "part_no", "posicion",
        ]
        widths = [28, 18, 8, 36, 18, 22, 8, 18, 12]
        return excel_response(
            items, headers, keys, widths,
            sheet="PCBs x Lote Proveedor", filename="trazabilidad_pcb_por_proveedor",
        )
    except Exception as e:
        logger.exception("Error exportando trazabilidad por proveedor: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 500


# ---------------------------------------------------------------------------
# Vista 3: Busqueda por PCB (QR / barcode especifico) -> sus materiales
#
# Modelo HIBRIDO (alineado con Verificacion BOM):
#   ASSY/IMD -> pcb_material_link / _imd  (los llena el poller POLLER_LINKS,
#               cobertura completa ~251k PCBs; misma fuente que el buscador de
#               Verificacion BOM). El barcode del PCB se busca contra
#               input_main.raw_barcode / output_imd.raw via input_main_id.
#   SMT      -> consumo_material_detalle_smt (trigger 019; el poller no cubre SMT).
#
# pcb_serial unificado: en ASSY/IMD es input_main.raw_barcode (lo que escanea el
# operador, p.ej. EBR41039152922606220032); en SMT es consumo.pcb_serial.
# ---------------------------------------------------------------------------

# Subconsulta base por proceso. ASSY/IMD desde el poller (con relleno_id e
# input_main_id para enriquecer); SMT desde el detalle de triggers.
_UNION_DETALLE = """
    (
      SELECT 'ASSY' AS proceso, p.input_main_id,
             COALESCE(NULLIF(im.raw_barcode, ''), p.pcb_raw) AS pcb_serial,
             p.pcb_ts AS ts, p.lot_no, p.linea, p.nparte AS part_no,
             p.material AS material_code, p.lote_proveedor AS numero_lote_material,
             p.codigo_material_recibido, p.posicion, p.contenedor AS container_id,
             p.role, p.relleno_id
      FROM pcb_material_link p
      JOIN input_main im ON im.id = p.input_main_id
      UNION ALL
      SELECT 'IMD', p.input_main_id,
             COALESCE(NULLIF(o.raw, ''), p.pcb_raw),
             p.pcb_ts, p.lot_no, p.linea, p.nparte,
             p.material, p.lote_proveedor,
             p.codigo_material_recibido, p.posicion, NULL,
             p.role, p.relleno_id
      FROM pcb_material_link_imd p
      JOIN output_imd o ON o.id = p.input_main_id
      UNION ALL
      SELECT 'SMT', NULL, d.pcb_serial, d.ts, t.lot_no, t.linea, t.part_no,
             t.material_code, t.numero_lote_material, t.codigo_material_recibido,
             t.posicion, t.container_id, 'PRIMARY', NULL
      FROM consumo_material_detalle_smt d
      JOIN trazabilidad_material_pcb_smt t ON t.id = d.trazabilidad_id
    ) d
"""

# Subconsulta de spec del BOM vigente (v_ecos_bom_current). Misma logica que
# Verificacion BOM. COLLATE para evitar choque 0900 vs unicode (item_no es 0900).
_BOM_SPEC = """
    LEFT JOIN (
      SELECT item_no, MAX(spec) AS spec
      FROM v_ecos_bom_current
      WHERE status_name = '사용'
        AND (valid_from IS NULL OR valid_from <= CURDATE())
        AND (valid_to IS NULL OR valid_to >= CURDATE())
      GROUP BY item_no
    ) b ON UPPER(b.item_no) COLLATE utf8mb4_unicode_ci = UPPER(d.material_code)
"""


def _query_por_pcb(limit):
    """Materiales de un PCB (QR/barcode). Hibrido poller (ASSY/IMD) + trigger SMT.
    Enriquece con spec (BOM vigente) y refill/cantidades (relleno_material)."""
    pcb = request.args.get("pcb", "", type=str).strip()
    proceso = request.args.get("proceso", "", type=str).strip().upper()
    if not pcb:
        return []

    where = ["d.pcb_serial LIKE %s"]
    params = [f"%{pcb}%"]
    if proceso in ("ASSY", "IMD", "SMT"):
        where.append("d.proceso = %s")
        params.append(proceso)

    # relleno_material (ASSY) / _imd se eligen por proceso de la fila via UNION
    # de rellenos; un solo LEFT JOIN por id basta porque relleno_id es global.
    sql = f"""
        SELECT
          d.proceso, d.input_main_id, d.pcb_serial, d.ts, d.lot_no, d.linea, d.part_no,
          d.material_code, d.numero_lote_material, d.codigo_material_recibido,
          d.posicion, d.container_id, d.role,
          b.spec,
          r.refill_number, r.cantidad_inicial, r.cantidad_restante, r.qty_per_pcb,
          r.ubicacion
        FROM {_UNION_DETALLE}
        {_BOM_SPEC}
        LEFT JOIN relleno_material r ON r.id = d.relleno_id
        WHERE {" AND ".join(where)}
        ORDER BY d.pcb_serial, d.posicion, d.material_code
        LIMIT {int(limit)}
    """
    rows = execute_query(sql, params, fetch="all") or []
    result = []
    for r in rows:
        result.append({
            "proceso": r.get("proceso") or "",
            "input_main_id": r.get("input_main_id"),
            "pcb_serial": r.get("pcb_serial") or "",
            "ts": str(r.get("ts") or ""),
            "lot_no": r.get("lot_no") or "",
            "linea": r.get("linea") or "",
            "part_no": r.get("part_no") or "",
            "material_code": r.get("material_code") or "",
            "numero_lote_material": r.get("numero_lote_material") or "",
            "codigo_material_recibido": r.get("codigo_material_recibido") or "",
            "posicion": r.get("posicion") or "",
            "container_id": r.get("container_id") or "",
            "role": r.get("role") or "",
            "spec": r.get("spec") or "",
            "refill_number": r.get("refill_number"),
            "cantidad_inicial": r.get("cantidad_inicial"),
            "cantidad_restante": r.get("cantidad_restante"),
            "qty_per_pcb": r.get("qty_per_pcb"),
            "ubicacion": r.get("ubicacion") or "",
        })
    return result


def _query_historial_pcb(input_main_id, proceso):
    """Historial de verificaciones cercanas al PCB (history_material_assy/_imd,
    misma linea+fecha, +-30 min del ts del PCB). Igual que Verificacion BOM."""
    is_imd = (proceso or "").upper() == "IMD"
    tbl_pcb = "output_imd" if is_imd else "input_main"
    col_linea = "line" if is_imd else "linea"
    tbl_hist = "history_material_imd" if is_imd else "history_material_assy"

    pcb = execute_query(
        f"SELECT ts, {col_linea} AS linea FROM {tbl_pcb} WHERE id = %s",
        [input_main_id], fetch="one")
    if not pcb:
        return []

    rows = execute_query(
        f"""SELECT fecha, hora, contenedor, material, posicion, proveedor,
                   spec, qty, result, lote_proveedor, ubicacion
            FROM {tbl_hist}
            WHERE linea = %s AND fecha = DATE(%s)
              AND ABS(TIMESTAMPDIFF(MINUTE, CONCAT(fecha, ' ', hora), %s)) <= 30
            ORDER BY hora DESC LIMIT 200""",
        [pcb.get("linea"), pcb.get("ts"), pcb.get("ts")], fetch="all") or []
    return [{
        "fecha": str(r.get("fecha") or ""),
        "hora": str(r.get("hora") or ""),
        "contenedor": r.get("contenedor") or "",
        "material": r.get("material") or "",
        "posicion": r.get("posicion") or "",
        "proveedor": r.get("proveedor") or "",
        "spec": r.get("spec") or "",
        "qty": r.get("qty") or "",
        "result": r.get("result") or "",
        "lote_proveedor": r.get("lote_proveedor") or "",
        "ubicacion": r.get("ubicacion") or "",
    } for r in rows]


@bp.route("/api/trazabilidad_pcb/por_pcb", methods=["GET"])
@login_requerido
def api_traza_por_pcb():
    """Materiales de un PCB especifico (QR/barcode) con spec y refill/cantidades."""
    try:
        items = _query_por_pcb(limit=3000)
        return jsonify({"status": "success", "items": items})
    except Exception as e:
        logger.error("Error en api_traza_por_pcb: %s", e)
        return jsonify({"status": "error", "message": str(e), "items": []}), 500


@bp.route("/api/trazabilidad_pcb/historial_pcb", methods=["GET"])
@login_requerido
def api_traza_historial_pcb():
    """Historial de verificaciones cercanas a un PCB (history_material_assy/_imd).
    Params: input_main_id, proceso (ASSY/IMD/SMT). SMT no tiene history -> vacio."""
    try:
        input_main_id = request.args.get("input_main_id", type=int)
        proceso = request.args.get("proceso", "", type=str).strip().upper()
        if not input_main_id or proceso == "SMT":
            return jsonify({"status": "success", "items": []})
        items = _query_historial_pcb(input_main_id, proceso)
        return jsonify({"status": "success", "items": items})
    except Exception as e:
        logger.error("Error en api_traza_historial_pcb: %s", e)
        return jsonify({"status": "error", "message": str(e), "items": []}), 500


@bp.route("/api/trazabilidad_pcb/por_pcb/export", methods=["GET"])
@login_requerido
def api_traza_por_pcb_export():
    """Exportar materiales de un PCB a Excel."""
    try:
        items = _query_por_pcb(limit=20000)
        headers = [
            "Proceso", "PCB (QR/Barcode)", "Fecha", "Lote Produccion", "Linea",
            "No. Parte (PCB)", "Material", "Spec", "Lote Proveedor", "Codigo Recibido",
            "Posicion", "Refill", "Cant. Inicial", "Cant. Restante", "Qty/PCB", "Contenedor",
        ]
        keys = [
            "proceso", "pcb_serial", "ts", "lot_no", "linea",
            "part_no", "material_code", "spec", "numero_lote_material", "codigo_material_recibido",
            "posicion", "refill_number", "cantidad_inicial", "cantidad_restante", "qty_per_pcb", "container_id",
        ]
        widths = [8, 36, 18, 22, 8, 18, 18, 24, 26, 26, 14, 8, 12, 12, 9, 26]
        return excel_response(
            items, headers, keys, widths,
            sheet="Trazabilidad x PCB", filename="trazabilidad_pcb_por_pcb",
        )
    except Exception as e:
        logger.exception("Error exportando trazabilidad por PCB: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 500
