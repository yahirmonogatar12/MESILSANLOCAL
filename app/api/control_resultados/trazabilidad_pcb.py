"""Endpoints HTTP del modulo "Trazabilidad de PCB".

Modulo de SOLO LECTURA / reportes que unifica la trazabilidad material->PCB de
los tres procesos en una sola vista:

  ASSY -> pcb_scan_snapshot/pcb_scan_material modo MAIN (trg_pcb_snapshot_main, desde
          2026-09-09); antes: por PCB, consumos de relleno_historial; por lote,
          trazabilidad_material_pcb
  IMD  -> idem modo IMD (trg_pcb_snapshot_imd); antes: relleno_historial_imd /
          trazabilidad_material_pcb_imd
  SMT  -> trazabilidad_material_pcb_smt    (historial_cambio_material_smt + input_smt; migracion 019)

Las ramas se juntan con UNION ALL agregando una columna 'proceso'. Todo es de
solo lectura: estas tablas las llenan triggers de la base compartida.

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
from datetime import date, timedelta

from flask import Blueprint, jsonify, request

from app.api.shared import (
    excel_response,
    execute_query,
    login_requerido,
    obtener_fecha_mexico,
)

logger = logging.getLogger(__name__)


bp = Blueprint("control_resultados_trazabilidad_pcb", __name__)


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
# Vista 1: Materiales por lote de produccion (PCB -> materiales)
# ---------------------------------------------------------------------------

# Columnas de las tablas de trazabilidad (las tres son columna-identicas).
_COLS_TRAZA = """lot_no, plan_id, linea, part_no, material_code,
             codigo_material_recibido, numero_lote_material, posicion, container_id,
             cantidad_inicial, cantidad_consumida, cantidad_restante, pcb_count,
             material_start_ts, material_end_ts, pcb_first_ts, pcb_last_ts, status"""

# proceso -> (tabla de trazabilidad, modo del snapshot). SMT no tiene snapshot.
_TABLAS_TRAZA = {
    "ASSY": ("trazabilidad_material_pcb", "MAIN"),
    "IMD": ("trazabilidad_material_pcb_imd", "IMD"),
    "SMT": ("trazabilidad_material_pcb_smt", None),
}

# ASSY/IMD salen del snapshot por PCB. Ahi trazabilidad_material_pcb/_imd llevan la
# cuenta por posicion y la posicion es siempre la misma ('0'): cada carga
# "reemplaza" a la anterior y cada PCB queda con un solo material (medido
# 2026-10-02: 1-2 por PCB contra 155-260 en el snapshot), asi que su pcb_count,
# fin y estado no sirven. Esas tablas solo cubren lotes sin snapshot (anteriores
# al 2026-09-09). Del snapshot salen las PCBs y la primera/ultima PCB con cada
# contenedor; no hay cantidades ni estado (status = 'EN_LINEA').
# COUNT(*) y GROUP BY por contenedor: la PK de pcb_scan_material es
# (modo, pcb_id, container_id), asi que cada PCB cuenta una vez por contenedor.
# Con COUNT(DISTINCT) y GROUP BY por todas las columnas un dia tardaba 20 s.
_SNAP_TRAZA = """
      SELECT '{proceso}' AS proceso, s.lot_no, NULL AS plan_id, s.linea,
             ANY_VALUE(s.nparte) AS part_no, ANY_VALUE(m.material) AS material_code,
             ANY_VALUE(m.codigo_material_recibido) AS codigo_material_recibido,
             ANY_VALUE(m.lote_proveedor) AS numero_lote_material,
             ANY_VALUE(m.posicion) AS posicion, m.container_id,
             NULL AS cantidad_inicial, NULL AS cantidad_consumida, NULL AS cantidad_restante,
             COUNT(*) AS pcb_count, MIN(s.pcb_ts) AS material_start_ts,
             MAX(s.pcb_ts) AS material_end_ts, MIN(s.pcb_ts) AS pcb_first_ts,
             MAX(s.pcb_ts) AS pcb_last_ts, 'EN_LINEA' AS status
      FROM pcb_scan_snapshot s
      STRAIGHT_JOIN pcb_scan_material m ON m.modo = s.modo AND m.pcb_id = s.pcb_id
      WHERE s.modo = '{modo}' AND {where}
      GROUP BY s.lot_no, s.linea, m.container_id"""

# ponytail: sin filtro de lote el snapshot se acota a 3 dias (1 dia de MAIN agrega
# ~570k filas en 1.3 s; 7 dias tardan 19 s). Si hace falta mas, tabla resumen por
# lote/contenedor llenada por un EVENT.
_SNAP_DIAS_MAX = 3


def _query_materiales(limit):
    """Materiales por lote. Devuelve (items, aviso).

    proceso: ASSY/IMD/SMT exacto. lote/parte/material/lote_proveedor: LIKE.
    Fechas: sobre material_start_ts en las tablas de trazabilidad y sobre la hora
    de la PCB en el snapshot. Los filtros van dentro de cada rama del UNION.
    """
    proceso = request.args.get("proceso", "", type=str).strip().upper()
    lot_no = request.args.get("lot_no", "", type=str).strip()
    part_no = request.args.get("part_no", "", type=str).strip()
    material = request.args.get("material", "", type=str).strip()
    fecha_inicio = request.args.get("fecha_inicio", "", type=str).strip()
    fecha_fin = request.args.get("fecha_fin", "", type=str).strip()

    # wt/pt: tablas de trazabilidad (t). ws/ps: snapshot (s, m).
    wt, pt, ws, ps = ["1=1"], [], ["1=1"], []
    if lot_no:
        wt.append("t.lot_no LIKE %s")
        ws.append("s.lot_no LIKE %s")
        pt.append(f"%{lot_no}%")
        ps.append(f"%{lot_no}%")
    if part_no:
        wt.append("t.part_no LIKE %s")
        ws.append("s.nparte LIKE %s")
        pt.append(f"%{part_no}%")
        ps.append(f"%{part_no}%")
    if material:
        wt.append("(t.material_code LIKE %s OR t.numero_lote_material LIKE %s)")
        ws.append("(m.material LIKE %s OR m.lote_proveedor LIKE %s)")
        pt += [f"%{material}%", f"%{material}%"]
        ps += [f"%{material}%", f"%{material}%"]
    if fecha_inicio:
        wt.append("DATE(t.material_start_ts) >= %s")
        pt.append(fecha_inicio)
    if fecha_fin:
        wt.append("DATE(t.material_start_ts) <= %s")
        pt.append(fecha_fin)

    aviso = ""
    desde, hasta = fecha_inicio, fecha_fin
    if not lot_no:
        hasta = hasta or obtener_fecha_mexico()
        minimo = (date.fromisoformat(hasta) - timedelta(days=_SNAP_DIAS_MAX - 1)).isoformat()
        if not desde or desde < minimo:
            desde = minimo
            aviso = (f"ASSY/IMD sin filtro de lote se limita a {_SNAP_DIAS_MAX} dias "
                     f"(desde {desde}). Filtra por lote para ver mas.")
    if desde:
        ws.append("s.pcb_ts >= %s")
        ps.append(desde)
    if hasta:
        ws.append("s.pcb_ts < %s + INTERVAL 1 DAY")
        ps.append(hasta)

    ramas, params = [], []
    for proc, (tabla, modo) in _TABLAS_TRAZA.items():
        if proceso not in ("", proc):
            continue
        sin_snapshot = ""
        if modo:
            ramas.append(_SNAP_TRAZA.format(proceso=proc, modo=modo, where=" AND ".join(ws)))
            params += ps
            sin_snapshot = (" AND NOT EXISTS (SELECT 1 FROM pcb_scan_snapshot x"
                            f" WHERE x.modo = '{modo}' AND x.lot_no = t.lot_no AND x.linea = t.linea)")
        ramas.append(f"""
      SELECT '{proc}' AS proceso, {_COLS_TRAZA}
      FROM {tabla} t
      WHERE {" AND ".join(wt)}{sin_snapshot}""")
        params += pt

    sql = f"""
        SELECT
          t.proceso, t.lot_no, t.linea, t.part_no, t.material_code,
          t.numero_lote_material, t.codigo_material_recibido, t.posicion,
          t.container_id, t.cantidad_inicial, t.cantidad_consumida,
          t.cantidad_restante, t.pcb_count, t.status,
          t.material_start_ts, t.material_end_ts, t.pcb_last_ts
        FROM ( {" UNION ALL ".join(ramas)} ) t
        ORDER BY t.material_start_ts DESC
        LIMIT {int(limit)}
    """
    rows = execute_query(sql, params or None, fetch="all") or []

    def cantidad(v):
        return "" if v is None else int(v)

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
            "cantidad_inicial": cantidad(r.get("cantidad_inicial")),
            "cantidad_consumida": cantidad(r.get("cantidad_consumida")),
            "cantidad_restante": cantidad(r.get("cantidad_restante")),
            "pcb_count": int(r.get("pcb_count") or 0),
            "status": r.get("status") or "",
            "material_start_ts": str(r.get("material_start_ts") or ""),
            "material_end_ts": str(r.get("material_end_ts") or ""),
            "pcb_last_ts": str(r.get("pcb_last_ts") or ""),
        })
    return result, aviso


@bp.route("/api/trazabilidad_pcb/materiales", methods=["GET"])
@login_requerido
def api_traza_materiales():
    """Materiales usados por lote de produccion, a traves de ASSY/IMD/SMT.
    Incluye fecha_hoy (hora planta, helper de shared) para que el front preseleccione
    el filtro Desde en el dia actual."""
    try:
        items, aviso = _query_materiales(limit=3000)
        return jsonify({"status": "success", "items": items, "message": aviso,
                        "fecha_hoy": obtener_fecha_mexico()})
    except Exception as e:
        logger.error("Error en api_traza_materiales: %s", e)
        return jsonify({"status": "error", "message": str(e), "items": []}), 500


@bp.route("/api/trazabilidad_pcb/materiales/export", methods=["GET"])
@login_requerido
def api_traza_materiales_export():
    """Exportar materiales por lote a Excel."""
    try:
        items, _ = _query_materiales(limit=20000)
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


# ASSY/IMD: el material de cada PCB sale de pcb_scan_snapshot/pcb_scan_material
# (triggers trg_pcb_snapshot_main/_imd desde 2026-09-09: lo que habia EN_LINEA al
# escanear la PCB; misma fuente que Verificacion BOM).
#
# PCBs SIN snapshot (anteriores): de los consumos que trg_relleno_consumo(_imd)
# registra al insertar la PCB (relleno_historial(_imd), evento CONSUMO, mismo
# input_id). pcb_material_link/_imd (poller de Verificacion BOM, apagado el
# 2026-09-11) ya NO se usan: ligaba un material por PCB comparando contra la hora
# de la estacion (relojes adelantados hasta 1 h); en M3 el 22-jun el 85% de sus
# enlaces era un material que la PCB no consumio. El consumo da el material con
# certeza pero no la bolsa: un relleno acumula bolsas ("Acumulado bolsa"), asi que
# el lote es el de las bolsas que tuvo el relleno ANTES del consumo; con mas de un
# lote se listan todos (para un recall, de mas es lo seguro).
_CONSUMO = {
    "ASSY": {"pcb": "input_main", "serial": "COALESCE(NULLIF(p.raw_barcode, ''), p.raw)",
             "linea": "p.linea", "hist": "relleno_historial", "idx": "idx_hist",
             "relleno": "relleno_material", "modo": "MAIN"},
    "IMD": {"pcb": "output_imd", "serial": "p.raw",
            "linea": "p.line", "hist": "relleno_historial_imd", "idx": "idx_rh_imd",
            "relleno": "relleno_material_imd", "modo": "IMD"},
}
# Bolsa de un evento RELLENO: 'Acumulado bolsa: X (+50) | Cont: ...', 'Registro
# inicial: X (50) ...', 'Relleno parcial[ inicial]: X (...' o, en IMD, X a secas.
_BOLSA = "TRIM(SUBSTRING_INDEX(SUBSTRING_INDEX({ref}, ' (', 1), ': ', -1))"
_SIN_SNAPSHOT = (
    "NOT EXISTS (SELECT 1 FROM pcb_scan_snapshot s"
    " WHERE s.modo = '{modo}' AND s.pcb_id = p.id)"
)


def _recall_sin_snapshot(proceso):
    """Rama de Vista 2 para PCBs sin snapshot: cada PCB que consumio de un relleno
    mientras una bolsa del lote/material buscado seguia en el (2 params: material
    y lote por prefijo).

    Misma regla que _bolsas_presentes: la bolsa X sigue presente en el consumo C si
    lo que entro despues de X no cubre el saldo de C (cantidad_antes). acum = lo
    acumulado en rellenos hasta cada evento. Sin este tope salian todos los
    consumos posteriores del relleno (miles de PCBs que la bolsa ya no alcanzo).
    """
    c = _CONSUMO[proceso]
    bolsa = _BOLSA.format(ref="b.referencia")
    if proceso == "IMD":  # IMD tambien usa placas IPM (ipm_records), como el snapshot
        origen = (f"LEFT JOIN control_material_almacen a ON a.codigo_material_recibido = {bolsa}"
                  f" LEFT JOIN ipm_records ip ON ip.ipm_part_lot = {bolsa}")
        lote, parte = "COALESCE(a.numero_lote_material, ip.part_lot)", "COALESCE(a.numero_parte, ip.part_no)"
    else:
        origen = f"JOIN control_material_almacen a ON a.codigo_material_recibido = {bolsa}"
        lote, parte = "a.numero_lote_material", "a.numero_parte"
    return f"""
          SELECT * FROM (
            WITH bolsas AS (
              SELECT b.relleno_id, b.id AS entrada, {lote} AS lote
              FROM {c['hist']} b FORCE INDEX ({c['idx']}_evento) {origen}
              WHERE b.evento = 'RELLENO' AND ({parte} LIKE %s OR {lote} LIKE %s) AND {lote} <> ''
            ),
            eventos AS (
              SELECT h.relleno_id, h.id, h.evento, h.input_id, h.cantidad_antes,
                     SUM(IF(h.evento = 'RELLENO', h.cantidad_delta, 0))
                       OVER (PARTITION BY h.relleno_id ORDER BY h.id) AS acum
              FROM {c['hist']} h FORCE INDEX ({c['idx']}_relleno)
              WHERE h.relleno_id IN (SELECT relleno_id FROM bolsas)
                AND h.evento IN ('RELLENO', 'CONSUMO')
            )
            SELECT '{proceso}' AS proceso, {c['serial']} AS pcb_serial, p.created_at AS ts,
                   p.lot_no, {c['linea']} AS linea, p.nparte AS part_no, r.material_code,
                   x.lote AS numero_lote_material, r.posicion
            FROM bolsas x
            JOIN eventos ex ON ex.id = x.entrada
            JOIN eventos ec ON ec.relleno_id = x.relleno_id AND ec.evento = 'CONSUMO'
             AND ec.id > x.entrada
             AND (ec.acum - ex.acum < ec.cantidad_antes OR ec.acum = ex.acum)
            JOIN {c['relleno']} r ON r.id = x.relleno_id
            JOIN {c['pcb']} p ON p.id = ec.input_id
            WHERE {_SIN_SNAPSHOT.format(modo=c['modo'])}
          ) z"""


def _query_por_proveedor(limit):
    """Trazabilidad inversa a nivel PCB: cada PCB vinculado a un lote de proveedor.

    El filtro material/lote se EMPUJA dentro de cada rama del UNION en vez de
    filtrar la derivada ya materializada: si no, MySQL escanea millones de filas
    antes de filtrar -> timeout. Por eso material es obligatorio en la ruta.
    """
    proceso = request.args.get("proceso", "", type=str).strip().upper()
    material = request.args.get("material", "", type=str).strip()
    fecha_inicio = request.args.get("fecha_inicio", "", type=str).strip()
    fecha_fin = request.args.get("fecha_fin", "", type=str).strip()

    # Filtro por PREFIJO (LIKE 'valor%'). Tolerante (el operador escribe el inicio
    # del lote/material, no necesita el codigo exacto con todos los '!') y AUN usa
    # los indices por material (type=range), a diferencia de '%valor%' que haria
    # full scan y timeout.
    # ponytail: el OR material/lote impide usar idx_scan_lote_prov (Verificacion BOM
    # sql/022) y recorre las ~7M filas de MAIN (5.2 s el 2026-10-02). Si molesta,
    # partir cada rama de snapshot en dos (una por material, otra por lote).
    pref = f"{material}%"
    snap = "(m.material LIKE %s OR m.lote_proveedor LIKE %s) AND m.lote_proveedor IS NOT NULL AND m.lote_proveedor <> ''"
    smt = "(t.material_code LIKE %s OR t.numero_lote_material LIKE %s) AND t.numero_lote_material IS NOT NULL AND t.numero_lote_material <> ''"

    # Los nombres de columna del UNION salen de la PRIMERA rama, y con filtro de
    # proceso cualquiera de ASSY/IMD/SMT puede quedar primera: todas llevan alias.
    # ts = hora del SERVIDOR (captured_at / created_at): la de la estacion se adelanta.
    ramas = []
    params = []
    if proceso in ("", "ASSY"):
        ramas.append(f"""
          SELECT 'ASSY' AS proceso, COALESCE(NULLIF(im.raw_barcode,''),im.raw) AS pcb_serial,
                 CAST(s.captured_at AS DATETIME) AS ts, s.lot_no, s.linea, s.nparte AS part_no,
                 m.material AS material_code, m.lote_proveedor AS numero_lote_material, m.posicion
          FROM pcb_scan_material m
          JOIN pcb_scan_snapshot s ON s.modo=m.modo AND s.pcb_id=m.pcb_id
          JOIN input_main im ON im.id=m.pcb_id
          WHERE m.modo='MAIN' AND {snap}""")
        ramas.append(_recall_sin_snapshot("ASSY"))
        params += [pref, pref, pref, pref]
    if proceso in ("", "IMD"):
        ramas.append(f"""
          SELECT 'IMD' AS proceso, o.raw AS pcb_serial, CAST(s.captured_at AS DATETIME) AS ts,
                 s.lot_no, s.linea, s.nparte AS part_no, m.material AS material_code,
                 m.lote_proveedor AS numero_lote_material, m.posicion
          FROM pcb_scan_material m
          JOIN pcb_scan_snapshot s ON s.modo=m.modo AND s.pcb_id=m.pcb_id
          JOIN output_imd o ON o.id=m.pcb_id
          WHERE m.modo='IMD' AND {snap}""")
        ramas.append(_recall_sin_snapshot("IMD"))
        params += [pref, pref, pref, pref]
    if proceso in ("", "SMT"):
        ramas.append(f"""
          SELECT 'SMT' AS proceso, d.pcb_serial, d.ts, t.lot_no, t.linea, t.part_no,
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

    # DISTINCT: el snapshot guarda cada bolsa EN_LINEA, y dos bolsas del mismo
    # lote en la misma posicion repetirian la PCB.
    sql = f"""
        SELECT DISTINCT d.proceso, d.pcb_serial, d.ts, d.lot_no, d.linea, d.part_no,
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
#   ASSY/IMD -> pcb_scan_snapshot/pcb_scan_material; PCBs anteriores al 2026-09-09
#               (sin snapshot) -> sus consumos (ver _CONSUMO y _consumos_sin_snapshot).
#               El barcode del PCB se busca contra input_main.raw_barcode /
#               output_imd.raw via el id de la PCB.
#   SMT      -> consumo_material_detalle_smt (trigger 019).
#
# pcb_serial unificado: en ASSY/IMD es input_main.raw_barcode (lo que escanea el
# operador, p.ej. EBR41039152922606220032); en SMT es consumo.pcb_serial.
# ts: hora del SERVIDOR (captured_at / created_at); la de la estacion se adelanta.
# ---------------------------------------------------------------------------

# Snapshot + SMT. El snapshot no guarda relleno (refill y cantidades salen vacios
# en esas filas); role = 'PRESENT' como en Verificacion BOM: material presente en
# la linea. pcb_serial = barcode mostrado; pcb_raw_alt = la otra forma del codigo
# del PCB (raw 'I...;MAIN;...' vs raw_barcode 'EBR...'). Se busca contra AMBOS
# porque el operador puede pegar cualquiera de los dos.
_UNION_DETALLE = """
    (
      SELECT 'ASSY' AS proceso, s.pcb_id AS input_main_id,
             COALESCE(NULLIF(im.raw_barcode, ''), im.raw) AS pcb_serial,
             im.raw AS pcb_raw_alt,
             CAST(s.captured_at AS DATETIME) AS ts, s.lot_no, s.linea, s.nparte AS part_no,
             m.material AS material_code, m.lote_proveedor AS numero_lote_material,
             m.codigo_material_recibido, m.posicion, m.container_id, 'PRESENT' AS role
      FROM pcb_scan_snapshot s
      JOIN pcb_scan_material m ON m.modo = s.modo AND m.pcb_id = s.pcb_id
      JOIN input_main im ON im.id = s.pcb_id
      WHERE s.modo = 'MAIN'
      UNION ALL
      SELECT 'IMD', s.pcb_id, o.raw, o.raw,
             CAST(s.captured_at AS DATETIME), s.lot_no, s.linea, s.nparte,
             m.material, m.lote_proveedor,
             m.codigo_material_recibido, m.posicion, m.container_id, 'PRESENT'
      FROM pcb_scan_snapshot s
      JOIN pcb_scan_material m ON m.modo = s.modo AND m.pcb_id = s.pcb_id
      JOIN output_imd o ON o.id = s.pcb_id
      WHERE s.modo = 'IMD'
      UNION ALL
      SELECT 'SMT', NULL, d.pcb_serial, d.pcb_serial, d.ts, t.lot_no, t.linea, t.part_no,
             t.material_code, t.numero_lote_material, t.codigo_material_recibido,
             t.posicion, t.container_id, 'PRIMARY'
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


def _bolsas_presentes(entradas, consumo_id, saldo):
    """Bolsas que seguian en el relleno al consumir: las mas recientes antes del
    consumo cuyas cantidades cubren el saldo que quedaba (cantidad_antes). Las
    anteriores ya se habian gastado. Sin saldo (<= 0), solo la ultima."""
    presentes, cubierto = set(), 0.0
    for e in sorted((e for e in entradas if e["id"] < consumo_id), key=lambda e: e["id"], reverse=True):
        presentes.add(e["bolsa"])
        cubierto += float(e["cantidad_delta"] or 0)
        if cubierto >= float(saldo or 0):
            break
    return sorted(presentes)


def _consumos_sin_snapshot(pcb, proceso, limit):
    """Materiales de PCBs sin snapshot, desde sus consumos (ver _CONSUMO).

    Lote: el de las bolsas presentes en el relleno al consumir (_bolsas_presentes).
    Una bolsa -> se muestra; varias -> "N bolsas posibles" y sus lotes distintos
    con " / ".
    """
    filas = []
    for proc, c in _CONSUMO.items():
        if proceso not in ("", proc):
            continue
        # STRAIGHT_JOIN: primero la PCB (LIKE) y luego su consumo por fecha indexada;
        # al reves recorreria los millones de consumos. El consumo se graba en el
        # mismo INSERT de la PCB: misma created_at.
        rows = execute_query(f"""
            SELECT d.*, b.spec FROM (
              SELECT '{proc}' AS proceso, p.id AS input_main_id, {c['serial']} AS pcb_serial,
                     p.created_at AS ts, p.lot_no, {c['linea']} AS linea, p.nparte AS part_no,
                     r.material_code, r.posicion, h.id AS consumo_id, h.relleno_id,
                     h.cantidad_antes AS saldo,
                     r.refill_number, r.cantidad_inicial, r.cantidad_restante,
                     r.qty_per_pcb, r.ubicacion
              FROM {c['pcb']} p
              STRAIGHT_JOIN {c['hist']} h FORCE INDEX ({c['idx']}_fecha)
                ON h.created_at BETWEEN p.created_at - INTERVAL 2 MINUTE
                                    AND p.created_at + INTERVAL 2 MINUTE
               AND h.input_id = p.id AND h.evento = 'CONSUMO'
              JOIN {c['relleno']} r ON r.id = h.relleno_id
              WHERE ({c['serial']} LIKE %s OR p.raw LIKE %s)
                AND {_SIN_SNAPSHOT.format(modo=c['modo'])}
              LIMIT {int(limit)}
            ) d
            {_BOM_SPEC}""", [f"%{pcb}%", f"%{pcb}%"], fetch="all") or []
        if not rows:
            continue

        rellenos = sorted({r["relleno_id"] for r in rows})
        entradas = execute_query(f"""
            SELECT relleno_id, id, cantidad_delta, {_BOLSA.format(ref='referencia')} AS bolsa
            FROM {c['hist']}
            WHERE relleno_id IN ({", ".join(["%s"] * len(rellenos))})
              AND evento = 'RELLENO' AND referencia NOT LIKE 'Re-relleno%%'""",
            rellenos, fetch="all") or []
        entradas = [e for e in entradas if e["bolsa"] and " " not in e["bolsa"]]
        bolsas = sorted({e["bolsa"] for e in entradas})
        lote_de = {}
        if bolsas:
            marcas = ", ".join(["%s"] * len(bolsas))
            for f in execute_query(f"""
                SELECT codigo_material_recibido AS bolsa, numero_lote_material AS lote
                FROM control_material_almacen WHERE codigo_material_recibido IN ({marcas})
                UNION ALL
                SELECT ipm_part_lot, part_lot FROM ipm_records WHERE ipm_part_lot IN ({marcas})""",
                    bolsas + bolsas, fetch="all") or []:
                if f["lote"]:
                    lote_de.setdefault(f["bolsa"], f["lote"])

        for r in rows:
            previas = _bolsas_presentes([e for e in entradas if e["relleno_id"] == r["relleno_id"]],
                                        r["consumo_id"], r["saldo"])
            lotes = sorted({lote_de[b] for b in previas if b in lote_de})
            r["codigo_material_recibido"] = (previas[0] if len(previas) == 1
                                             else f"{len(previas)} bolsas posibles" if previas else "")
            r["numero_lote_material"] = " / ".join(lotes)
            r["container_id"] = ""
            r["role"] = "CONSUMO"
            filas.append(r)
    return filas


def _query_por_pcb(limit):
    """Materiales de un PCB (QR/barcode): snapshot o consumos (ASSY/IMD) + trigger
    SMT. Enriquece con spec (BOM vigente) y, en consumos, refill/cantidades."""
    pcb = request.args.get("pcb", "", type=str).strip()
    proceso = request.args.get("proceso", "", type=str).strip().upper()
    if not pcb:
        return []

    where = ["(d.pcb_serial LIKE %s OR d.pcb_raw_alt LIKE %s)"]
    params = [f"%{pcb}%", f"%{pcb}%"]
    if proceso in ("ASSY", "IMD", "SMT"):
        where.append("d.proceso = %s")
        params.append(proceso)

    sql = f"""
        SELECT
          d.proceso, d.input_main_id, d.pcb_serial, d.ts, d.lot_no, d.linea, d.part_no,
          d.material_code, d.numero_lote_material, d.codigo_material_recibido,
          d.posicion, d.container_id, d.role, b.spec
        FROM {_UNION_DETALLE}
        {_BOM_SPEC}
        WHERE {" AND ".join(where)}
        LIMIT {int(limit)}
    """
    rows = execute_query(sql, params, fetch="all") or []
    rows += _consumos_sin_snapshot(pcb, proceso, limit)
    rows.sort(key=lambda r: (r.get("pcb_serial") or "", str(r.get("posicion") or ""),
                             r.get("material_code") or ""))
    result = []
    for r in rows[:limit]:
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
    misma linea+fecha, +-30 min de la PCB).

    Hora de la PCB: created_at (servidor). El historial guarda fecha/hora del
    servidor y input_main.ts trae el reloj de la estacion, adelantado hasta 1 h:
    con ts la ventana caia en escaneos de una hora despues.
    """
    is_imd = (proceso or "").upper() == "IMD"
    tbl_pcb = "output_imd" if is_imd else "input_main"
    col_linea = "line" if is_imd else "linea"
    tbl_hist = "history_material_imd" if is_imd else "history_material_assy"

    pcb = execute_query(
        f"SELECT created_at AS ts, {col_linea} AS linea FROM {tbl_pcb} WHERE id = %s",
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
