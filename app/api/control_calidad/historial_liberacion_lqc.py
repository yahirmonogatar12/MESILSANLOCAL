"""Endpoints HTTP del modulo "Historial de liberacion LQC".

Consumido por LISTA_CONTROL_DE_CALIDAD / Inspeccion de calidad.
JS cliente: app/static/js/historial_liberacion_lqc.js
Template:   app/templates/Control de calidad/historial_liberacion_lqc_ajax.html
CSS:        app/static/css/historial_liberacion_lqc.css (persistente en MainTemplate.html)

Rutas canonicas:
  GET /historial_liberacion_lqc/ajax  -> render template
  GET /api/lqc/lineas                 -> resumen por linea + UPH del dia operativo
  GET /api/lqc/datos                  -> registros LQC filtrados por linea/rango

Alias 2026-05-28 (compat):
  GET /historial-liberacion-lqc-ajax  -> 301 a la canonica
  GET /api/smt-scanner/lineas         -> 301 a /api/lqc/lineas
  GET /api/smt-scanner/datos          -> 301 a /api/lqc/datos

Migrado desde app/routes.py el 2026-05-28. Los 3 helpers _lqc_* eran
privados del modulo (solo consumidos por estas 2 APIs); se quedan locales
al blueprint.
"""

from datetime import date as _date
from datetime import datetime, time, timedelta

from flask import Blueprint, jsonify, redirect, render_template, request

from app.api.shared import login_requerido
from app.config_mysql import get_pooled_connection
from app.api.pda.shipping_material import get_dict_cursor


bp = Blueprint("historial_liberacion_lqc", __name__)


# ---------------------------------------------------------------------------
# Helpers privados (fecha operativa con corte 07:30)
# ---------------------------------------------------------------------------


def _lqc_fecha_operativa(now=None):
    now = now or datetime.now()
    corte = now.replace(hour=7, minute=30, second=0, microsecond=0)
    if now >= corte:
        return now.date()
    return (now - timedelta(days=1)).date()


def _lqc_parse_fecha(value, fallback):
    try:
        return datetime.strptime(str(value or ""), "%Y-%m-%d").date()
    except Exception:
        return fallback


def _lqc_ventana_operativa(fecha_inicio, fecha_fin):
    inicio = datetime.combine(fecha_inicio, time(7, 30))
    fin = datetime.combine(fecha_fin + timedelta(days=1), time(7, 30))
    return inicio, fin


# ---------------------------------------------------------------------------
# Render template + aliases
# ---------------------------------------------------------------------------


@bp.route("/historial_liberacion_lqc/ajax")
@login_requerido
def historial_liberacion_lqc_ajax():
    """Render canonico del template Historial de liberacion LQC."""
    return render_template("Control de calidad/historial_liberacion_lqc_ajax.html")


@bp.route("/historial-liberacion-lqc-ajax")
def alias_legacy_lqc_render():
    """Alias 301 -> /historial_liberacion_lqc/ajax."""
    return redirect("/historial_liberacion_lqc/ajax", code=301)


@bp.route("/api/smt-scanner/lineas")
def alias_legacy_lqc_lineas():
    """Alias 301 -> /api/lqc/lineas."""
    return redirect("/api/lqc/lineas", code=301)


@bp.route("/api/smt-scanner/datos")
def alias_legacy_lqc_datos():
    """Alias 301 -> /api/lqc/datos (preserva query string)."""
    qs = request.query_string.decode("utf-8")
    target = "/api/lqc/datos"
    if qs:
        target = f"{target}?{qs}"
    return redirect(target, code=301)


# ---------------------------------------------------------------------------
# APIs canonicas
# ---------------------------------------------------------------------------


@bp.route("/api/lqc/lineas")
@login_requerido
def lqc_lineas_api():
    """Resumen de escaneos LQC por linea real usando box_scans + plan_main."""
    try:
        ahora_dt = datetime.now()
        fecha_operativa = _lqc_fecha_operativa(ahora_dt)
        ventana_inicio, ventana_fin = _lqc_ventana_operativa(
            fecha_operativa, fecha_operativa
        )
        ventana_fin_consulta = min(ahora_dt, ventana_fin)
        hoy = fecha_operativa.isoformat()
        ahora = ahora_dt.strftime("%Y-%m-%d %H:%M:%S")
        inicio_sql = ventana_inicio.strftime("%Y-%m-%d %H:%M:%S")
        fin_sql = ventana_fin_consulta.strftime("%Y-%m-%d %H:%M:%S")
        lineas_config = ["M1", "M2", "M3", "M4", "DP1", "DP2", "DP3", "H1"]
        line_expr = "COALESCE(NULLIF(p.line, ''), 'SIN PLAN')"
        slot_expr = """
                    DATE_ADD(
                        STR_TO_DATE(
                            DATE_FORMAT(DATE_SUB(b.last_scan, INTERVAL 30 MINUTE), '%%Y-%%m-%%d %%H:00:00'),
                            '%%Y-%%m-%%d %%H:%%i:%%s'
                        ),
                        INTERVAL 30 MINUTE
                    )
        """

        conn = get_pooled_connection()
        if conn is None:
            return jsonify({"success": True, "lineas": [], "uph_hoy": {}})

        cursor = get_dict_cursor(conn)
        try:
            cursor.execute(
                f"""
                SELECT
                    {line_expr} AS linea,
                    COUNT(*) AS total_hoy
                FROM box_scans b
                LEFT JOIN plan_main p ON p.lot_no = b.lot_no
                WHERE b.last_scan >= %s
                  AND b.last_scan < %s
                GROUP BY linea
                """,
                (inicio_sql, fin_sql),
            )
            rows = cursor.fetchall()
            counts = {r["linea"]: int(r["total_hoy"] or 0) for r in rows}

            cursor.execute(
                f"""
                SELECT
                    {line_expr} AS linea,
                    DATE_FORMAT({slot_expr}, '%%Y-%%m-%%d %%H:%%i:%%s') AS slot_key,
                    HOUR({slot_expr}) AS hora,
                    COUNT(*) AS total
                FROM box_scans b
                LEFT JOIN plan_main p ON p.lot_no = b.lot_no
                WHERE b.last_scan >= %s
                  AND b.last_scan < %s
                GROUP BY linea, slot_key, hora
                ORDER BY slot_key
                """,
                (inicio_sql, fin_sql),
            )
            uph_rows = cursor.fetchall()
            uph_hoy = {}
            uph_slots_map = {}
            for r in uph_rows:
                l = r["linea"]
                slot_key = r["slot_key"]
                if l not in uph_hoy:
                    uph_hoy[l] = {}
                uph_hoy[l][slot_key] = int(r["total"] or 0)
                if slot_key not in uph_slots_map:
                    uph_slots_map[slot_key] = {
                        "key": slot_key,
                        "label": "",
                        "hour": int(r["hora"] or 0),
                    }
            uph_slots = []
            if ventana_fin_consulta >= ventana_inicio:
                start_slot = ventana_inicio
                end_slot = ventana_fin
                current_slot = start_slot
                while current_slot < end_slot:
                    key = current_slot.strftime("%Y-%m-%d %H:%M:%S")
                    slot = uph_slots_map.get(
                        key, {"key": key, "hour": current_slot.hour}
                    )
                    slot["label"] = current_slot.strftime("%H:%M")
                    uph_slots.append(slot)
                    current_slot += timedelta(hours=1)

            ordered_lines = lineas_config[:]
            ordered_lines.extend(
                sorted([line for line in counts.keys() if line not in ordered_lines])
            )
            lineas = [{"linea": l, "total_hoy": counts.get(l, 0)} for l in ordered_lines]
            return jsonify(
                {
                    "success": True,
                    "fecha_consulta": hoy,
                    "actualizado": ahora,
                    "ventana_inicio": inicio_sql,
                    "ventana_fin": fin_sql,
                    "lineas": lineas,
                    "uph_hoy": uph_hoy,
                    "uph_slots": uph_slots,
                }
            )
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        return (
            jsonify({"success": False, "error": str(e), "lineas": [], "uph_hoy": {}}),
            500,
        )


@bp.route("/api/lqc/datos")
@login_requerido
def lqc_datos_api():
    """Registros LQC desde box_scans filtrados por linea real y rango de fechas."""
    try:
        fecha_default = _lqc_fecha_operativa()
        lineas = [l.strip() for l in request.args.getlist("lineas") if l.strip()]
        fecha_inicio = _lqc_parse_fecha(request.args.get("fecha_inicio"), fecha_default)
        fecha_fin = _lqc_parse_fecha(request.args.get("fecha_fin"), fecha_default)
        if fecha_fin < fecha_inicio:
            fecha_inicio, fecha_fin = fecha_fin, fecha_inicio
        ventana_inicio, ventana_fin = _lqc_ventana_operativa(fecha_inicio, fecha_fin)
        inicio_sql = ventana_inicio.strftime("%Y-%m-%d %H:%M:%S")
        fin_sql = ventana_fin.strftime("%Y-%m-%d %H:%M:%S")
        turno_filtro = request.args.get("turno", "Todos")
        line_expr = "COALESCE(NULLIF(p.line, ''), 'SIN PLAN')"
        fecha_operativa_expr = """
                    CASE
                        WHEN TIME(b.last_scan) >= '07:30:00' THEN DATE(b.last_scan)
                        ELSE DATE_SUB(DATE(b.last_scan), INTERVAL 1 DAY)
                    END
        """
        turno_expr = """
                    CASE
                        WHEN TIME(b.last_scan) >= '07:30:00' AND TIME(b.last_scan) < '17:30:00' THEN 'DIA'
                        WHEN TIME(b.last_scan) >= '17:30:00' AND TIME(b.last_scan) < '22:00:00' THEN 'TIEMPO EXTRA'
                        ELSE 'NOCHE'
                    END
        """

        conn = get_pooled_connection()
        if conn is None:
            return jsonify({"success": True, "records": []})

        cursor = get_dict_cursor(conn)
        try:
            where_conditions = ["b.last_scan >= %s", "b.last_scan < %s"]
            params = [inicio_sql, fin_sql]

            if lineas:
                placeholders = ",".join(["%s"] * len(lineas))
                where_conditions.append(f"{line_expr} IN ({placeholders})")
                params.extend(lineas)

            if turno_filtro != "Todos":
                where_conditions.append(f"{turno_expr} = %s")
                params.append(turno_filtro)

            where_clause = " AND ".join(where_conditions)
            query = f"""
                SELECT
                    {line_expr} AS linea,
                    {fecha_operativa_expr} AS fecha,
                    COALESCE(NULLIF(p.part_no, ''), LEFT(b.serial, GREATEST(CHAR_LENGTH(b.serial) - 12, 1))) AS part,
                    COALESCE(NULLIF(p.model_code, ''), '') AS model_code,
                    COALESCE(b.lot_no, '') AS lot_no,
                    b.box_code,
                    b.id AS scan_id,
                    b.serial,
                    b.status AS box_status,
                    b.first_scan,
                    b.last_scan,
                    {turno_expr} AS turno
                FROM box_scans b
                LEFT JOIN plan_main p ON p.lot_no = b.lot_no
                WHERE {where_clause}
                ORDER BY b.last_scan DESC, b.id DESC
            """
            cursor.execute(query, params)
            rows = cursor.fetchall()

            historico_por_serial = {}
            seriales = sorted(
                {
                    str(r.get("serial") or "").strip()
                    for r in rows
                    if str(r.get("serial") or "").strip()
                }
            )
            for i in range(0, len(seriales), 1000):
                serial_chunk = seriales[i : i + 1000]
                placeholders = ",".join(["%s"] * len(serial_chunk))
                cursor.execute(
                    f"""
                    SELECT serial
                    FROM box_scans
                    WHERE serial IN ({placeholders})
                    GROUP BY serial
                    HAVING COUNT(*) > 1
                    """,
                    serial_chunk,
                )
                for h in cursor.fetchall():
                    serial = str(h.get("serial") or "").strip()
                    if serial:
                        historico_por_serial[serial] = []

            seriales_repetidos = sorted(historico_por_serial.keys())
            for i in range(0, len(seriales_repetidos), 1000):
                serial_chunk = seriales_repetidos[i : i + 1000]
                placeholders = ",".join(["%s"] * len(serial_chunk))
                cursor.execute(
                    f"""
                    SELECT
                        id,
                        serial,
                        CASE
                            WHEN TIME(last_scan) >= '07:30:00' THEN DATE(last_scan)
                            ELSE DATE_SUB(DATE(last_scan), INTERVAL 1 DAY)
                        END AS fecha_operativa,
                        last_scan
                    FROM box_scans
                    WHERE serial IN ({placeholders})
                    ORDER BY serial, last_scan, id
                    """,
                    serial_chunk,
                )
                for h in cursor.fetchall():
                    serial = str(h.get("serial") or "").strip()
                    if not serial:
                        continue
                    historico_por_serial[serial].append(
                        {
                            "id": h.get("id"),
                            "fecha": str(h.get("fecha_operativa"))
                            if h.get("fecha_operativa")
                            else "",
                            "last_scan": str(h.get("last_scan")).replace("T", " ")
                            if h.get("last_scan")
                            else "",
                        }
                    )

            records = []
            for r in rows:
                serial = r["serial"] or ""
                historico = historico_por_serial.get(serial, [])
                scan_id = r.get("scan_id")
                otros_escaneos = [
                    h
                    for h in historico
                    if scan_id is None or h.get("id") != scan_id
                ]
                fechas_repetidas = []
                scans_repetidos = []
                for h in otros_escaneos:
                    fecha_hist = h.get("fecha") or ""
                    scan_hist = h.get("last_scan") or ""
                    if fecha_hist and fecha_hist not in fechas_repetidas:
                        fechas_repetidas.append(fecha_hist)
                    if scan_hist and scan_hist not in scans_repetidos:
                        scans_repetidos.append(scan_hist)
                es_duplicado_historico = len(otros_escaneos) > 0
                es_original = False
                if historico:
                    primer_id = min(
                        (h.get("id") for h in historico if h.get("id") is not None),
                        default=None,
                    )
                    es_original = primer_id is not None and scan_id == primer_id
                status = r.get("box_status") or ""
                if es_duplicado_historico and not es_original:
                    status = "Duplicado"
                records.append(
                    {
                        "linea": r["linea"],
                        "fecha": str(r["fecha"]) if r["fecha"] else "",
                        "part": r["part"] or "",
                        "model_code": r.get("model_code") or "",
                        "lot_no": r.get("lot_no") or "",
                        "box_code": r.get("box_code") or "",
                        "serial": serial,
                        "status": status,
                        "duplicado_historico": es_duplicado_historico and not es_original,
                        "es_original": es_original,
                        "total_repeticiones": len(historico),
                        "fechas_repetidas": ", ".join(fechas_repetidas),
                        "escaneos_repetidos": " | ".join(scans_repetidos[:5]),
                        "first_scan": str(r.get("first_scan")).replace("T", " ")
                        if r.get("first_scan")
                        else "",
                        "last_scan": str(r["last_scan"]).replace("T", " ")
                        if r["last_scan"]
                        else "",
                        "turno": r["turno"],
                    }
                )
            return jsonify({"success": True, "records": records, "total": len(records)})
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "records": []}), 500
