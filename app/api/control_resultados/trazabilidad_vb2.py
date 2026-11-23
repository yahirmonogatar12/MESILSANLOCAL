"""Trazabilidad y costo por PCB desde Verificacion BOM 2.0 (tablas vb2_). Solo lectura.

Plan: MES/Verificacion BOM/Documentacion/PLAN_VERIFICACION_BOM_2.0.md, secciones 5 y 7.
Convive con trazabilidad_pcb.py (fuente actual) durante la transicion; no la reemplaza.

  GET /api/trazabilidad_pcb/v2/lote?lot_no=&etapa=&estimado=1   material y costo de un lote
  GET /api/trazabilidad_pcb/v2/pcb?qr=&estimado=1               estado por etapa, material y costo de una PCB
  GET /api/trazabilidad_pcb/v2/etiqueta?bolsa=                  lotes que consumieron una etiqueta

Costo (D5): por defecto solo el real (invoice o lista de compras, propio o heredado del lote
padre de un sublote). Con estimado=1 se agrega, en campos aparte, el estimado: ultimo costo
real de esa parte -> material_costos -> precio del K-system por el tipo de cambio de vb2_config.
Nunca se suman real y estimado.
"""

import logging
from decimal import Decimal

from flask import Blueprint, jsonify, request

from app.api.shared import execute_query, login_requerido

logger = logging.getLogger(__name__)
bp = Blueprint("control_resultados_trazabilidad_vb2", __name__)

ETAPAS = ("SMT", "IMD", "ASSY")
_FUENTE_PCB = {
    "SMT": ("input_smt", "line"),
    "IMD": ("output_imd", "line"),
    "ASSY": ("input_main", "linea"),
}
_REALES = ("INVOICE", "LISTA_COMPRAS")
_NIVELES_SUBLOTE = 5


def lote_base_smt(lot_no):
    """'SMT-261110-007-01' -> 'SMT-261110-007' (mismo corte que la reprogramacion de plan_smt.py)."""
    partes = str(lot_no or "").split("-")
    return "-".join(partes[:3]) if len(partes) > 3 and partes[0] == "SMT" else str(lot_no or "")


def _en(valores):
    return ", ".join(["%s"] * len(valores))


def _q(sql, params=None):
    return execute_query(sql, params or None, fetch="all") or []


# ---------------------------------------------------------------------------
# Costo por etiqueta
# ---------------------------------------------------------------------------


def _tiene_costo(propio):
    """Un costo de 0 no es un costo: 11,004 de 51,593 etiquetas con fuente INVOICE lo traen en 0
    (medido el 2026-11-13). Se tratan como sin costo para heredar del padre o ir al estimado."""
    return bool(propio) and propio["fuente"] != "SIN_COSTO" and propio["costo"] is not None and Decimal(propio["costo"]) > 0


def resolver_costos(bolsas, propios, padres, ultimo_real, material_costos, ks_precio_krw, krw_usd):
    """Costo unitario de cada (bolsa, material). Funcion pura: todo llega como diccionarios.

    propios:         bolsa -> {"costo", "fuente", "estimado"} de inventario_lote_costos
    padres:          bolsa -> bolsa de la que se dividio (lot_division)
    ultimo_real:     material -> ultimo costo real de esa parte
    material_costos: material -> costo de material_costos
    ks_precio_krw:   material -> pur_price del K-system (KRW)
    Devuelve (bolsa, material) -> {"costo": Decimal|None, "real": bool, "fuente": str}.
    """
    salida = {}
    for bolsa, material in bolsas:
        actual, nivel, propio = bolsa, 0, None
        while actual and nivel <= _NIVELES_SUBLOTE:
            propio = propios.get(actual)
            if _tiene_costo(propio):
                break
            propio = None
            actual, nivel = padres.get(actual), nivel + 1
        if propio:
            real = propio["fuente"] in _REALES and not propio["estimado"]
            fuente = propio["fuente"] + ("" if actual == bolsa else " (lote padre)")
            salida[(bolsa, material)] = {"costo": Decimal(propio["costo"]), "real": real, "fuente": fuente}
        elif material in ultimo_real:
            salida[(bolsa, material)] = {"costo": Decimal(ultimo_real[material]), "real": False, "fuente": "ULTIMO_REAL_PARTE"}
        elif material in material_costos:
            salida[(bolsa, material)] = {"costo": Decimal(material_costos[material]), "real": False, "fuente": "MATERIAL_COSTOS"}
        elif material in ks_precio_krw and krw_usd:
            costo = Decimal(ks_precio_krw[material]) * Decimal(krw_usd)
            salida[(bolsa, material)] = {"costo": costo, "real": False, "fuente": "K_SYSTEM"}
        else:
            salida[(bolsa, material)] = {"costo": None, "real": False, "fuente": "SIN_COSTO"}
    return salida


def _costos(pares):
    """Lee de la base lo que resolver_costos necesita para esos (bolsa, material)."""
    # bolsa puede ser None (carrete de SMT con etiqueta generica, material sin lote).
    pares = sorted({(b, m) for b, m in pares}, key=lambda p: (p[0] or "", p[1]))
    if not pares:
        return {}
    propios, padres = {}, {}
    pendientes = {b for b, _ in pares if b}
    for _ in range(_NIVELES_SUBLOTE + 1):
        if not pendientes:
            break
        lista = sorted(pendientes)
        for r in _q(f"""SELECT codigo_material_recibido c, costo_unitario, fuente_costo, es_estimado
                        FROM inventario_lote_costos WHERE codigo_material_recibido IN ({_en(lista)})""", lista):
            propios[r["c"]] = {"costo": r["costo_unitario"], "fuente": r["fuente_costo"], "estimado": bool(r["es_estimado"])}
        sin_costo = [b for b in lista if not _tiene_costo(propios.get(b))]
        pendientes = set()
        if sin_costo:
            for r in _q(f"SELECT new_code, original_code FROM lot_division WHERE new_code IN ({_en(sin_costo)})", sin_costo):
                padres[r["new_code"]] = r["original_code"]
                pendientes.add(r["original_code"])

    materiales = sorted({m for _, m in pares})
    ultimo_real, mat_costos, ks = {}, {}, {}
    # ponytail: "ultimo" = la fila real mas reciente por parte; un indice por numero_parte_sistema
    # haria falta si esto tarda.
    for r in _q(f"""SELECT c.numero_parte_sistema p, c.costo_unitario FROM inventario_lote_costos c
                    JOIN (SELECT numero_parte_sistema, MAX(id) id FROM inventario_lote_costos
                          WHERE numero_parte_sistema IN ({_en(materiales)}) AND es_estimado = 0
                            AND fuente_costo IN ('INVOICE', 'LISTA_COMPRAS') AND costo_unitario > 0
                          GROUP BY numero_parte_sistema) u ON u.id = c.id""", materiales):
        ultimo_real[r["p"]] = r["costo_unitario"]
    for r in _q(f"""SELECT numero_parte p, costo_unitario_material c FROM material_costos
                    WHERE numero_parte IN ({_en(materiales)}) AND costo_unitario_material > 0 ORDER BY id""", materiales):
        mat_costos[r["p"]] = r["c"]
    for r in _q(f"""SELECT item_no p, MAX(pur_price) c FROM ks_bom_components
                    WHERE item_no IN ({_en(materiales)}) AND currency = 'KRW' AND pur_price > 0
                    GROUP BY item_no""", materiales):
        ks[r["p"]] = r["c"]
    cambio = _q("SELECT valor FROM vb2_config WHERE clave = 'krw_usd'")
    krw_usd = Decimal(cambio[0]["valor"]) if cambio else None
    return resolver_costos(pares, propios, padres, ultimo_real, mat_costos, ks, krw_usd)


# ---------------------------------------------------------------------------
# Filas de vb2_uso_lote con su costo
# ---------------------------------------------------------------------------

_COLS = """u.etapa, u.linea, u.lot_no, u.item_no, u.pcbs, u.cantidad, u.primera_pcb_ts, u.ultima_pcb_ts,
           u.certeza, m.id AS montaje_id, m.material, m.bolsa, m.slot, m.origen"""


def _con_costo(filas, ver_estimado):
    costos = _costos((f["bolsa"], f["material"]) for f in filas)
    total_real, total_est, sin_real = Decimal(0), Decimal(0), 0
    salida = []
    for f in filas:
        c = costos.get((f["bolsa"], f["material"]), {"costo": None, "real": False, "fuente": "SIN_COSTO"})
        cantidad = Decimal(f["cantidad"])
        fila = {
            "etapa": f["etapa"], "linea": f["linea"], "lot_no": f["lot_no"], "item_no": f["item_no"],
            "material": f["material"], "bolsa": f["bolsa"] or "", "slot": f.get("slot") or "",
            "pcbs": int(f["pcbs"]), "cantidad": float(cantidad), "certeza": f["certeza"],
            "primera_pcb_ts": str(f["primera_pcb_ts"]), "ultima_pcb_ts": str(f["ultima_pcb_ts"]),
            "costo_unitario": None, "costo": None, "fuente_costo": c["fuente"] if c["real"] else "",
        }
        if c["real"]:
            fila["costo_unitario"] = float(c["costo"])
            fila["costo"] = float(cantidad * c["costo"])
            total_real += cantidad * c["costo"]
        else:
            sin_real += 1
            if ver_estimado and c["costo"] is not None:
                fila["costo_estimado_unitario"] = float(c["costo"])
                fila["costo_estimado"] = float(cantidad * c["costo"])
                fila["fuente_estimado"] = c["fuente"]
                total_est += cantidad * c["costo"]
        salida.append(fila)
    totales = {"costo_real": float(total_real), "filas_sin_costo_real": sin_real}
    if ver_estimado:
        totales["costo_estimado"] = float(total_est)  # aparte: nunca se suma al real (D5)
    return salida, totales


def _ver_estimado():
    return request.args.get("estimado", "") in ("1", "true", "si")


@bp.route("/api/trazabilidad_pcb/v2/lote", methods=["GET"])
@login_requerido
def api_v2_lote():
    lot_no = request.args.get("lot_no", "", type=str).strip()
    etapa = request.args.get("etapa", "", type=str).strip().upper()
    if not lot_no:
        return jsonify({"status": "error", "message": "lot_no es obligatorio"}), 400
    try:
        etapas = [etapa] if etapa in ETAPAS else list(ETAPAS)
        filas = _q(f"""SELECT {_COLS} FROM vb2_uso_lote u JOIN vb2_montaje m ON m.id = u.montaje_id
                       WHERE u.lot_no = %s AND u.etapa IN ({_en(etapas)})
                       ORDER BY u.etapa, u.item_no, u.primera_pcb_ts""", [lot_no, *etapas])
        # D10: el paso de SMT sin QR es un sublote; su material cuenta para el lote original.
        hijos = _q("""SELECT u.*, m.material, m.bolsa, m.slot, m.origen FROM plan_smt p
                      JOIN vb2_uso_lote u ON u.etapa = 'SMT' AND u.lot_no = p.lot_no
                      JOIN vb2_montaje m ON m.id = u.montaje_id
                      WHERE p.lote_padre = %s""", [lot_no]) if "SMT" in etapas else []
        items, totales = _con_costo(filas + hijos, _ver_estimado())
        pcbs = {e: max([f["pcbs"] for f in items if f["etapa"] == e and f["lot_no"] == lot_no] or [0]) for e in etapas}
        return jsonify({"status": "success", "lot_no": lot_no, "items": items, "totales": totales, "pcbs_por_etapa": pcbs})
    except Exception as e:
        logger.exception("api_v2_lote")
        return jsonify({"status": "error", "message": str(e)}), 500


def _estado_pcb(etapa, pcb, avance, ajuste_seg):
    """VINCULADA / PENDIENTE / POR_CALCULAR para una PCB en una etapa (7.2)."""
    if not pcb:
        return "PENDIENTE", []  # D4: sin registro en la etapa; puede aparecer despues
    if not avance or pcb["id"] > avance["ultimo_id"]:
        return "POR_CALCULAR", []
    filas = _q(f"""SELECT {_COLS} FROM vb2_uso_lote u JOIN vb2_montaje m ON m.id = u.montaje_id
                   WHERE u.etapa = %s AND u.linea = %s AND u.lot_no = %s
                     AND u.primera_pcb_ts <= %s + INTERVAL %s SECOND AND u.ultima_pcb_ts >= %s + INTERVAL %s SECOND""",
               [etapa, pcb["linea"], pcb["lot_no"], pcb["ts"], ajuste_seg, pcb["ts"], ajuste_seg])
    return ("VINCULADA" if filas else "PENDIENTE"), filas


@bp.route("/api/trazabilidad_pcb/v2/pcb", methods=["GET"])
@login_requerido
def api_v2_pcb():
    qr = request.args.get("qr", "", type=str).strip()
    if not qr:
        return jsonify({"status": "error", "message": "qr es obligatorio"}), 400
    try:
        config = {r["clave"]: r["valor"] for r in _q("SELECT clave, valor FROM vb2_config WHERE clave LIKE 'smt.ajuste_seg.%'")}
        etapas = []
        for etapa in ETAPAS:
            tabla, col = _FUENTE_PCB[etapa]
            ok = " AND result = 'OK'" if etapa == "ASSY" else ""
            pcb = (_q(f"SELECT id, ts, {col} AS linea, lot_no FROM {tabla} WHERE raw = %s{ok} ORDER BY id LIMIT 1", [qr]) or [None])[0]
            avance = None
            if pcb:
                avance = (_q("SELECT ultimo_id FROM vb2_avance WHERE etapa = %s AND linea = %s", [etapa, pcb["linea"]]) or [None])[0]
            ajuste = int(float(config.get(f"smt.ajuste_seg.{pcb['linea']}", 0))) if pcb and etapa == "SMT" else 0
            estado, filas = _estado_pcb(etapa, pcb, avance, ajuste)
            if pcb and etapa == "SMT":
                # D10 / 7.7: material del TOP (sin QR) de este BOTTOM, a nivel de lote. El TOP apunta
                # al lote base SMT-YYMMDD-NNN; la PCB puede venir de un reprogramado SMT-YYMMDD-NNN-01.
                filas += _q(f"""SELECT {_COLS} FROM plan_smt p
                                JOIN vb2_uso_lote u ON u.etapa = 'SMT' AND u.lot_no = p.lot_no
                                JOIN vb2_montaje m ON m.id = u.montaje_id WHERE p.lote_padre = %s""",
                            [lote_base_smt(pcb["lot_no"])])
            # Lo que le toca a esta PCB de cada fila: el promedio por PCB de esa fila.
            por_pcb = [dict(f, cantidad=Decimal(f["cantidad"]) / int(f["pcbs"]), pcbs=1) for f in filas]
            items, totales = _con_costo(por_pcb, _ver_estimado())
            etapas.append({
                "etapa": etapa, "estado": estado, "linea": pcb["linea"] if pcb else "",
                "lot_no": pcb["lot_no"] if pcb else "", "ts": str(pcb["ts"]) if pcb else "",
                "items": items, "totales": totales,
            })
        total = {"costo_real": sum(e["totales"]["costo_real"] for e in etapas)}
        if _ver_estimado():
            total["costo_estimado"] = sum(e["totales"].get("costo_estimado", 0) for e in etapas)
        return jsonify({"status": "success", "qr": qr, "etapas": etapas, "totales": total})
    except Exception as e:
        logger.exception("api_v2_pcb")
        return jsonify({"status": "error", "message": str(e)}), 500


@bp.route("/api/trazabilidad_pcb/v2/etiqueta", methods=["GET"])
@login_requerido
def api_v2_etiqueta():
    bolsa = request.args.get("bolsa", "", type=str).strip()
    if not bolsa:
        return jsonify({"status": "error", "message": "bolsa es obligatoria"}), 400
    try:
        filas = _q(f"""SELECT {_COLS}, m.montado_at, m.retirado_at FROM vb2_montaje m
                       JOIN vb2_uso_lote u ON u.montaje_id = m.id
                       WHERE m.bolsa = %s ORDER BY u.primera_pcb_ts""", [bolsa])
        items, totales = _con_costo(filas, _ver_estimado())
        return jsonify({"status": "success", "bolsa": bolsa, "items": items, "totales": totales})
    except Exception as e:
        logger.exception("api_v2_etiqueta")
        return jsonify({"status": "error", "message": str(e)}), 500
