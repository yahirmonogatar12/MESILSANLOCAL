"""Endpoints HTTP del modulo "Historial de cambio de material de SMT".

Consumido por LISTA_CONTROL_DE_CALIDAD / Historial de material.
JS cliente: app/static/js/historial_cambio_material_smt.js
Template:   app/templates/Control de calidad/historial_cambio_material_smt_ajax.html

Rutas:
  GET /historial-cambio-material-smt-ajax  -> render template (canonica)
  GET /historial-cambio-material-smt       -> 301 a la canonica
  GET /smt/historial                       -> 301 a la canonica
  GET /api/smt-historial/data              -> listar con filtros + paginacion
  GET /api/smt-historial/opciones          -> lineas y maquinas disponibles
  GET /api/smt-historial/export            -> exportar filtrado a Excel

Reescrito 2026-09-22 siguiendo WF_002/WF_003/WF_004, con el mismo layout y
estilo que "Historial de maquina ICT". Se eliminaron las APIs legacy
(/api/historial_smt_data, /api/smt_stats, /api/smt/filtros/opciones,
/api/smt/historial/data) junto con el template monolitico anterior y
`smt_historial_simple.py`.

Los endpoints `/api/historial_smt_latest[_v2]` (panel Control de Operacion
SMT) se conservan al final del archivo sin cambios.
"""

import logging
import traceback
from datetime import datetime

from flask import Blueprint, jsonify, redirect, render_template, request

from app.api.shared import excel_response_ict, execute_query, login_requerido
from app.db_mysql import get_connection


logger = logging.getLogger(__name__)


bp = Blueprint('smt_api', __name__)


# ScanDate/ScanTime llegan del equipo en dos formatos ("20260922" / "2026-09-22",
# "135510" / "13:55:10") y a veces con basura ("-", "Update"). Se normalizan a
# digitos para filtrar y se formatean al vuelo para mostrar.
_SCAN_DATE_SQL = "REPLACE(ScanDate,'-','')"
_SCAN_TIME_SQL = "REPLACE(ScanTime,':','')"

# Allowlist de filtros por encabezado (cf_*). Los nombres de columna nunca
# salen del request: solo la clave se busca en este diccionario (WF_003).
_COLUMN_FILTER_SQL = {
    "fecha": f"{_SCAN_DATE_SQL} LIKE %s",
    "hora": f"{_SCAN_TIME_SQL} LIKE %s",
    "linea": "linea LIKE %s",
    "maquina": "maquina LIKE %s",
    "slot": "CAST(SlotNo AS CHAR) LIKE %s",
    "feeder": "FeederBase LIKE %s",
    "resultado": "Result LIKE %s",
    "parte": "PartName LIKE %s",
    "cantidad": "CAST(Quantity AS CHAR) LIKE %s",
    "lote": "LOTNO LIKE %s",
    "barcode": "Barcode LIKE %s",
    "barcode_anterior": "PreviousBarcode LIKE %s",
    "seq": "SEQ LIKE %s",
    "vendor": "Vendor LIKE %s",
    "archivo": "archivo LIKE %s",
}

_SELECT_COLS = (
    "SELECT ScanDate, ScanTime, linea, maquina, SlotNo, FeederBase, Result, "
    "PartName, Quantity, LOTNO, Barcode, PreviousBarcode, SEQ, Vendor, archivo "
    "FROM historial_cambio_material_smt "
)

_EXPORT_HEADERS = [
    "Fecha", "Hora", "Linea", "Maquina", "Slot", "Feeder", "Resultado",
    "Parte", "Cantidad", "Lote", "Barcode", "Barcode Anterior", "SEQ",
    "Vendor", "Archivo",
]
_EXPORT_KEYS = [
    "fecha", "hora", "linea", "maquina", "slot", "feeder", "resultado",
    "parte", "cantidad", "lote", "barcode", "barcode_anterior", "seq",
    "vendor", "archivo",
]


def _solo_digitos(valor):
    return "".join(ch for ch in str(valor or "") if ch.isdigit())


def _fmt_fecha(scan_date):
    """20260922 | 2026-09-22 -> 2026-09-22. Basura se devuelve tal cual."""
    d = _solo_digitos(scan_date)
    return f"{d[:4]}-{d[4:6]}-{d[6:8]}" if len(d) == 8 else (scan_date or "")


def _fmt_hora(scan_time):
    """135510 | 13:55:10 -> 13:55:10. Basura se devuelve tal cual."""
    t = _solo_digitos(scan_time)
    if 0 < len(t) <= 6:
        t = t.zfill(6)
        return f"{t[:2]}:{t[2:4]}:{t[4:6]}"
    return scan_time or ""


def _fmt_row(row):
    def _txt(key):
        return row.get(key) or ""

    def _num(key):
        value = row.get(key)
        return value if value is not None else ""

    return {
        "fecha": _fmt_fecha(row.get("ScanDate")),
        "hora": _fmt_hora(row.get("ScanTime")),
        "linea": _txt("linea"),
        "maquina": _txt("maquina"),
        "slot": _num("SlotNo"),
        "feeder": _txt("FeederBase"),
        "resultado": _txt("Result"),
        "parte": _txt("PartName"),
        "cantidad": _num("Quantity"),
        "lote": _txt("LOTNO"),
        "barcode": _txt("Barcode"),
        "barcode_anterior": _txt("PreviousBarcode"),
        "seq": _txt("SEQ"),
        "vendor": _txt("Vendor"),
        "archivo": _txt("archivo"),
    }


def _build_where():
    """WHERE + params a partir de los filtros de la request.

    Devuelve (where_sql, params). Los valores siempre van parametrizados y los
    nombres de columna salen de la allowlist, nunca del request.
    """
    where_sql = "WHERE 1=1"
    params = []

    def _add(clause, *vals):
        nonlocal where_sql
        where_sql += " " + clause
        params.extend(vals)

    fecha_desde = _solo_digitos(request.args.get("fecha_desde", ""))
    fecha_hasta = _solo_digitos(request.args.get("fecha_hasta", ""))
    if fecha_desde or fecha_hasta:
        # Descarta ScanDate corrupto ("-", "Update") antes de comparar texto.
        _add(f"AND CHAR_LENGTH({_SCAN_DATE_SQL})=8")
        if fecha_desde:
            _add(f"AND {_SCAN_DATE_SQL}>=%s", fecha_desde)
        if fecha_hasta:
            _add(f"AND {_SCAN_DATE_SQL}<=%s", fecha_hasta)

    linea = request.args.get("linea", "").strip()
    if linea:
        _add("AND linea=%s", linea)

    maquina = request.args.get("maquina", "").strip()
    if maquina:
        _add("AND maquina=%s", maquina)

    parte = request.args.get("parte", "").strip()
    if parte:
        _add("AND PartName LIKE %s", f"{parte}%")

    resultado = request.args.get("resultado", "").strip()
    if resultado:
        _add("AND Result=%s", resultado)

    barcode_like = request.args.get("barcode_like", "").strip()
    if barcode_like:
        _add("AND Barcode LIKE %s", f"%{barcode_like}%")

    for key, clause in _COLUMN_FILTER_SQL.items():
        value = request.args.get(f"cf_{key}", "").strip()
        if not value:
            continue
        if key in ("fecha", "hora"):
            value = _solo_digitos(value)
            if not value:
                continue
        _add(f"AND {clause}", f"%{value}%")

    return where_sql, params


# ---------------------------------------------------------------------------
# Render template
# ---------------------------------------------------------------------------


@bp.route("/historial-cambio-material-smt-ajax")
@login_requerido
def historial_cambio_material_smt_ajax():
    """Render canonico del fragmento AJAX del historial de cambio de material SMT."""
    try:
        return render_template(
            "Control de calidad/historial_cambio_material_smt_ajax.html"
        )
    except Exception as e:
        logger.error(f"Error al cargar Historial cambio material SMT: {e}")
        return f"Error al cargar el contenido: {e}", 500


@bp.route("/historial-cambio-material-smt")
@bp.route("/smt/historial")
def alias_legacy_historial_cambio_material_smt():
    """Aliases 301 -> /historial-cambio-material-smt-ajax."""
    return redirect("/historial-cambio-material-smt-ajax", code=301)


# ---------------------------------------------------------------------------
# APIs
# ---------------------------------------------------------------------------


@bp.route("/api/smt-historial/data")
@login_requerido
def smt_historial_data():
    """Registros del historial con filtros y paginacion.

    Paginacion: `page` (1-based) y `per_page` (default 1000, max 1000).
    Respuesta: { rows, total, page, per_page, total_pages }.
    """
    try:
        where_sql, params = _build_where()

        try:
            page = max(1, int(request.args.get("page", "1")))
        except ValueError:
            page = 1
        try:
            per_page = int(request.args.get("per_page", "1000"))
        except ValueError:
            per_page = 1000
        per_page = max(1, min(per_page, 1000))

        count_row = execute_query(
            "SELECT COUNT(*) AS n FROM historial_cambio_material_smt " + where_sql,
            tuple(params),
            fetch="one",
        ) or {}
        total = int(count_row.get("n", 0))

        offset = (page - 1) * per_page
        rows = execute_query(
            _SELECT_COLS + where_sql + " ORDER BY id DESC LIMIT %s OFFSET %s",
            tuple(params) + (per_page, offset),
            fetch="all",
        ) or []

        return jsonify({
            "rows": [_fmt_row(row) for row in rows],
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page,
        })
    except Exception as e:
        logger.exception("Error en /api/smt-historial/data")
        return jsonify({"error": str(e)}), 500


@bp.route("/api/smt-historial/opciones")
@login_requerido
def smt_historial_opciones():
    """Valores distintos de linea y maquina para poblar los selects."""
    try:
        lineas = execute_query(
            "SELECT DISTINCT linea FROM historial_cambio_material_smt "
            "WHERE linea IS NOT NULL AND linea<>'' ORDER BY linea",
            fetch="all",
        ) or []
        maquinas = execute_query(
            "SELECT DISTINCT maquina FROM historial_cambio_material_smt "
            "WHERE maquina IS NOT NULL AND maquina<>'' ORDER BY maquina",
            fetch="all",
        ) or []
        return jsonify({
            "lineas": [r["linea"] for r in lineas],
            "maquinas": [r["maquina"] for r in maquinas],
        })
    except Exception as e:
        logger.exception("Error en /api/smt-historial/opciones")
        return jsonify({"error": str(e), "lineas": [], "maquinas": []}), 500


@bp.route("/api/smt-historial/export")
@login_requerido
def smt_historial_export():
    """Exportar el historial filtrado a Excel (mismos filtros que /data)."""
    try:
        where_sql, params = _build_where()
        rows = execute_query(
            _SELECT_COLS + where_sql + " ORDER BY id DESC LIMIT 10000",
            tuple(params),
            fetch="all",
        ) or []
        return excel_response_ict(
            [_fmt_row(row) for row in rows],
            _EXPORT_HEADERS,
            _EXPORT_KEYS,
            widths=[16] * len(_EXPORT_HEADERS),
            sheet="Historial SMT",
            filename=(
                "historial_cambio_material_smt_"
                + datetime.now().strftime("%Y%m%d_%H%M%S")
            ),
        )
    except Exception as e:
        logger.exception("Error en /api/smt-historial/export")
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# Fase 4 (2026-05-28): 2 endpoints "latest" migrados desde routes.py.
# Consumidos por el panel "Control de Operacion SMT" para hacer match contra
# BOM con el ultimo material escaneado por (linea, maquina, SlotNo).
# `convertir_linea_smt` se trae junto porque solo lo usa la variante v2.
# ---------------------------------------------------------------------------


def convertir_linea_smt(linea_nombre):
    """Convierte nombres de linea SMT a formato de BD (SMT A -> 1line, etc.)"""
    conversion = {
        "SMT A": "1line",
        "SMT B": "2line",
        "SMT C": "3line",
        "SMT D": "4line",
    }
    return conversion.get(linea_nombre, linea_nombre)


@bp.route("/api/historial_smt_latest", methods=["GET"])
@login_requerido
def api_historial_smt_latest():
    """Devuelve el ultimo escaneo por (linea, maquina, SlotNo) desde la tabla
    historial_cambio_material_smt. Pensado para el panel de Control de Operacion SMT
    que requiere el ultimo material escaneado para hacer match con el BOM.

    Parametros:
      - linea: opcional. Ej: 'SMT B'. Si se omite, devuelve para todas las lineas.
    """
    try:
        linea = request.args.get("linea", "").strip()

        conn = get_connection()
        cursor = conn.cursor()

        where_sub = ""
        params = []
        if linea:
            where_sub = "WHERE linea = %s"
            params.append(linea)

        # Seleccionar el ultimo registro por grupo usando fecha_subida
        query = f"""
            SELECT h.id, h.linea, h.maquina, h.archivo, h.ScanDate, h.ScanTime,
                   h.SlotNo, h.Result, h.PreviousBarcode, h.Productdate,
                   h.PartName, h.Quantity, h.SEQ, h.Vendor, h.LOTNO,
                   h.Barcode, h.FeederBase, h.fecha_subida,
                   CASE WHEN UPPER(h.FeederBase) LIKE '%%F%%' THEN 'FRONT'
                        WHEN UPPER(h.FeederBase) LIKE '%%R%%' THEN 'REAR'
                        ELSE 'UNKNOWN' END AS side_norm
            FROM historial_cambio_material_smt h
            INNER JOIN (
                SELECT linea, maquina, SlotNo,
                       CASE WHEN UPPER(FeederBase) LIKE '%%F%%' THEN 'FRONT'
                            WHEN UPPER(FeederBase) LIKE '%%R%%' THEN 'REAR'
                            ELSE 'UNKNOWN' END AS side_norm,
                       MAX(fecha_subida) AS max_fecha
                FROM historial_cambio_material_smt
                {where_sub}
                GROUP BY linea, maquina, SlotNo, side_norm
            ) m
            ON h.linea = m.linea AND h.maquina = m.maquina
               AND h.SlotNo = m.SlotNo AND h.fecha_subida = m.max_fecha
               AND (
                    (CASE WHEN UPPER(h.FeederBase) LIKE '%%F%%' THEN 'FRONT'
                          WHEN UPPER(h.FeederBase) LIKE '%%R%%' THEN 'REAR'
                          ELSE 'UNKNOWN' END) = m.side_norm
               )
            {("WHERE h.linea = %s" if linea else "")}
            ORDER BY h.linea, h.maquina, h.SlotNo, side_norm
        """

        if linea:
            cursor.execute(query, params + params)
        else:
            cursor.execute(query)

        rows = cursor.fetchall()

        data = []
        for r in rows:
            linea_v = r[1] if len(r) > 1 else ""
            maquina_v = r[2] if len(r) > 2 else ""
            scan_date = r[4] if len(r) > 4 else ""
            scan_time = r[5] if len(r) > 5 else ""
            slot_no = r[6] if len(r) > 6 else ""
            part_name = r[10] if len(r) > 10 else ""
            quantity = r[11] if len(r) > 11 else 0
            vendor = r[13] if len(r) > 13 else ""
            feeder_base = r[16] if len(r) > 16 else ""

            formatted = {
                "linea": linea_v,
                "maquina": maquina_v,
                "Equipment": maquina_v,
                "SlotNo": slot_no,
                "FeederBase": feeder_base,
                "RegistDate": scan_date,
                "fecha_formateada": scan_date,
                "PartName": part_name,
                "Quantity": quantity,
                "Vendor": vendor,
                "ScanDate": scan_date,
                "ScanTime": scan_time,
            }
            data.append(formatted)

        cursor.close()
        conn.close()

        return jsonify({"success": True, "data": data, "total": len(data)})
    except Exception as e:
        logger.error(f"Error en api_historial_smt_latest: {e}")
        logger.info(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500


# Variante robusta con lado FRONT/REAR agrupado explicitamente
@bp.route("/api/historial_smt_latest_v2", methods=["GET"])
@login_requerido
def api_historial_smt_latest_v2():
    try:
        linea_input = request.args.get("linea", "").strip()
        linea = convertir_linea_smt(linea_input)

        conn = get_connection()
        cursor = conn.cursor()

        where_sub = ""
        params = []
        if linea:
            where_sub = "WHERE linea = %s"
            params.append(linea)

        query = f"""
            SELECT h.id, h.linea, h.maquina, h.archivo, h.ScanDate, h.ScanTime,
                   h.SlotNo, h.Result, h.PreviousBarcode, h.Productdate,
                   h.PartName, h.Quantity, h.SEQ, h.Vendor, h.LOTNO,
                   h.Barcode, h.FeederBase, h.fecha_subida,
                   CASE WHEN UPPER(h.FeederBase) LIKE '%%F%%' THEN 'FRONT'
                        WHEN UPPER(h.FeederBase) LIKE '%%R%%' THEN 'REAR'
                        ELSE 'UNKNOWN' END AS side_norm
            FROM historial_cambio_material_smt h
            INNER JOIN (
                SELECT linea, maquina, SlotNo,
                       (CASE WHEN UPPER(FeederBase) LIKE '%%F%%' THEN 'FRONT'
                             WHEN UPPER(FeederBase) LIKE '%%R%%' THEN 'REAR'
                             ELSE 'UNKNOWN' END) AS side_norm,
                       MAX(fecha_subida) AS max_fecha
                FROM historial_cambio_material_smt
                {where_sub}
                GROUP BY linea, maquina, SlotNo,
                         (CASE WHEN UPPER(FeederBase) LIKE '%%F%%' THEN 'FRONT'
                               WHEN UPPER(FeederBase) LIKE '%%R%%' THEN 'REAR'
                               ELSE 'UNKNOWN' END)
            ) m
              ON h.linea = m.linea AND h.maquina = m.maquina
             AND h.SlotNo = m.SlotNo AND h.fecha_subida = m.max_fecha
             AND (
                 (CASE WHEN UPPER(h.FeederBase) LIKE '%%F%%' THEN 'FRONT'
                       WHEN UPPER(h.FeederBase) LIKE '%%R%%' THEN 'REAR'
                       ELSE 'UNKNOWN' END) = m.side_norm
             )
            {("WHERE h.linea = %s" if linea else "")}
            ORDER BY h.linea, h.maquina, h.SlotNo, m.side_norm
        """

        if linea:
            cursor.execute(query, params + params)
        else:
            cursor.execute(query)

        rows = cursor.fetchall()
        data = []
        for r in rows:
            linea_v = r[1] if len(r) > 1 else ""
            maquina_v = r[2] if len(r) > 2 else ""
            scan_date = r[4] if len(r) > 4 else ""
            scan_time = r[5] if len(r) > 5 else ""
            slot_no = r[6] if len(r) > 6 else ""
            part_name = r[10] if len(r) > 10 else ""
            quantity = r[11] if len(r) > 11 else 0
            vendor = r[13] if len(r) > 13 else ""
            feeder_base = r[16] if len(r) > 16 else ""

            formatted = {
                "linea": linea_v,
                "maquina": maquina_v,
                "Equipment": maquina_v,
                "SlotNo": slot_no,
                "FeederBase": feeder_base,
                "RegistDate": scan_date,
                "fecha_formateada": scan_date,
                "PartName": part_name,
                "Quantity": quantity,
                "Vendor": vendor,
                "ScanDate": scan_date,
                "ScanTime": scan_time,
            }
            data.append(formatted)

        cursor.close()
        conn.close()

        return jsonify({"success": True, "data": data, "total": len(data)})
    except Exception as e:
        logger.error("Error en api_historial_smt_latest_v2: %s", e)
        logger.info(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500
