"""Endpoints HTTP del modulo "Historial de maquina ICT % Pass/Fail".

Consumido por LISTA_DE_CONTROL_DE_RESULTADOS / Historial de maquinas calidad.
JS cliente: app/static/js/ict-Pass-Fail.js
Template:   app/templates/Control de resultados/history_ict_Pass_Fail.html

Rutas:
  GET /historial_ict_pass_fail/ajax  -> render template (canonica)
  GET /api/ict/pass-fail             -> resumen Pass/Fail por jornada/turno
  GET /api/ict/pass-fail/detail      -> detalle de barcodes por fila del resumen
  GET /api/ict/pass-fail/export      -> exportar resumen a Excel

Alias 2026-05-27:
  GET /historial-maquina-ict-pass-fail      -> 301 a /historial_ict_pass_fail/ajax
  GET /historial-maquina-ict-pass-fail-ajax -> 301 a /historial_ict_pass_fail/ajax

Migrado desde app/routes.py el 2026-05-27. Las 3 APIs ya tenian
@login_requerido en el original; se conservan.

Helpers compartidos con los otros 2 modulos ICT viven en
app/api/shared/ict_helpers.py.
"""

from datetime import datetime, timedelta
from datetime import time as dt_time

from flask import Blueprint, jsonify, redirect, render_template, request

from app.api.shared import execute_query, login_requerido
from app.api.shared.ict_helpers import _ict_format_row


bp = Blueprint("historial_ict_pass_fail", __name__)


# ---------------------------------------------------------------------------
# Helpers privados del modulo
# ---------------------------------------------------------------------------


def _ict_pass_fail_fecha_jornada_expr(ts_column="ts"):
    return (
        f"CASE WHEN TIME({ts_column}) >= '07:30:00' "
        f"THEN DATE({ts_column}) ELSE DATE(DATE_SUB({ts_column}, INTERVAL 1 DAY)) END"
    )


def _ict_pass_fail_turno_expr(ts_column="ts"):
    return (
        "CASE "
        f"WHEN TIME({ts_column}) >= '07:30:00' AND TIME({ts_column}) < '17:30:00' THEN 'DIA' "
        f"WHEN TIME({ts_column}) >= '17:30:00' AND TIME({ts_column}) < '22:00:00' THEN 'TIEMPO EXTRA' "
        "ELSE 'NOCHE' "
        "END"
    )


def _build_history_ict_pass_fail_summary_query():
    """Construir query para resumen Pass/Fail de ICT por jornada, turno, linea y numero de parte."""
    fecha_desde = (
        request.args.get("fecha_desde", "").strip()
        or request.args.get("fecha", "").strip()
    )
    fecha_hasta = request.args.get("fecha_hasta", "").strip() or fecha_desde
    numero_parte = (
        request.args.get("numero_parte", "").strip()
        or request.args.get("no_parte", "").strip()
    )
    turno = request.args.get("turno", "").strip().upper()
    barcode = (
        request.args.get("barcode", "").strip()
        or request.args.get("barcode_like", "").strip()
    )

    fecha_jornada_expr = _ict_pass_fail_fecha_jornada_expr("ts")
    turno_expr = _ict_pass_fail_turno_expr("ts")

    sql = (
        "SELECT "
        f"{fecha_jornada_expr} AS fecha, "
        "COALESCE(NULLIF(TRIM(linea), ''), 'SIN LINEA') AS linea, "
        "COALESCE(ict, 0) AS ict, "
        f"{turno_expr} AS turno, "
        "COALESCE(NULLIF(TRIM(no_parte), ''), 'SIN NUMERO DE PARTE') AS numero_parte, "
        "COUNT(*) AS total, "
        "SUM(CASE WHEN UPPER(COALESCE(resultado, '')) = 'OK' THEN 1 ELSE 0 END) AS ok_count, "
        "SUM(CASE WHEN UPPER(COALESCE(resultado, '')) = 'NG' THEN 1 ELSE 0 END) AS ng_count "
        "FROM history_ict WHERE 1=1"
    )
    params = []

    if fecha_desde:
        start_date = datetime.strptime(fecha_desde, "%Y-%m-%d").date()
        params.append(datetime.combine(start_date, dt_time(7, 30)))
        sql += " AND ts >= %s"
    if fecha_hasta:
        end_date = datetime.strptime(fecha_hasta, "%Y-%m-%d").date()
        params.append(datetime.combine(end_date + timedelta(days=1), dt_time(7, 30)))
        sql += " AND ts < %s"
    if numero_parte:
        sql += " AND no_parte LIKE %s"
        params.append(f"{numero_parte}%")
    if barcode:
        sql += " AND barcode LIKE %s"
        params.append(f"{barcode}%")
    if turno in {"DIA", "TIEMPO EXTRA", "NOCHE"}:
        sql += f" AND {turno_expr}=%s"
        params.append(turno)

    sql += (
        f" GROUP BY {fecha_jornada_expr},"
        " COALESCE(NULLIF(TRIM(linea), ''), 'SIN LINEA'),"
        " COALESCE(ict, 0),"
        f" {turno_expr},"
        " COALESCE(NULLIF(TRIM(no_parte), ''), 'SIN NUMERO DE PARTE')"
        " ORDER BY fecha ASC, linea ASC, ict ASC, FIELD(turno, 'DIA', 'TIEMPO EXTRA', 'NOCHE'), total DESC, numero_parte ASC"
    )

    return sql, tuple(params) if params else None


# ---------------------------------------------------------------------------
# Render template
# ---------------------------------------------------------------------------


@bp.route("/historial_ict_pass_fail/ajax")
@login_requerido
def historial_ict_pass_fail_ajax():
    """Render canonico del template Historial ICT Pass/Fail."""
    try:
        return render_template("Control de resultados/history_ict_Pass_Fail.html")
    except Exception as e:
        print(f"Error al cargar Historial maquina ICT % Pass/Fail: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@bp.route("/historial-maquina-ict-pass-fail")
@bp.route("/historial-maquina-ict-pass-fail-ajax")
def alias_legacy_pass_fail():
    """Aliases 301 -> /historial_ict_pass_fail/ajax."""
    return redirect("/historial_ict_pass_fail/ajax", code=301)


# ---------------------------------------------------------------------------
# APIs
# ---------------------------------------------------------------------------


@bp.route("/api/ict/pass-fail")
@login_requerido
def ict_pass_fail_api():
    """Obtener resumen Pass/Fail de ICT con el mismo formato que Vision."""
    try:
        sql, params = _build_history_ict_pass_fail_summary_query()
        rows = execute_query(sql, params, fetch="all") or []

        result = []
        for row in rows:
            total = int(row.get("total") or 0)
            ok_count = int(row.get("ok_count") or 0)
            ng_count = int(row.get("ng_count") or 0)
            porcentaje_ok = round((ok_count / total) * 100, 2) if total else 0
            porcentaje_ng = round((ng_count / total) * 100, 2) if total else 0

            result.append({
                "fecha": _ict_format_row({"fecha": row.get("fecha")}).get("fecha", ""),
                "linea": row.get("linea", "") or "",
                "ict": row.get("ict", "") or "",
                "turno": row.get("turno", "") or "",
                "numero_parte": row.get("numero_parte", "") or "",
                "total": total,
                "ok_count": ok_count,
                "ng_count": ng_count,
                "porcentaje_ok": porcentaje_ok,
                "porcentaje_ng": porcentaje_ng,
            })

        return jsonify(result)
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


@bp.route("/api/ict/pass-fail/detail")
@login_requerido
def ict_pass_fail_detail_api():
    """Obtener detalle de barcodes para una fila del resumen ICT Pass/Fail."""
    try:
        fecha = request.args.get("fecha", "").strip()
        linea = request.args.get("linea", "").strip()
        ict = request.args.get("ict", "").strip()
        turno = request.args.get("turno", "").strip().upper()
        numero_parte = request.args.get("numero_parte", "").strip()
        barcode = request.args.get("barcode", "").strip()

        try:
            min_intentos = max(1, int(request.args.get("min_intentos", "").strip() or 1))
        except ValueError:
            min_intentos = 1

        if not all([fecha, linea, ict, turno, numero_parte]):
            return jsonify({"error": "Faltan filtros para consultar el detalle."}), 400

        if turno not in {"DIA", "TIEMPO EXTRA", "NOCHE"}:
            return jsonify({"error": "Turno invalido para consultar detalle."}), 400

        fecha_jornada = datetime.strptime(fecha, "%Y-%m-%d").date()
        fecha_inicio = datetime.combine(fecha_jornada, dt_time(7, 30))
        fecha_fin = datetime.combine(fecha_jornada + timedelta(days=1), dt_time(7, 30))

        linea_expr = "COALESCE(NULLIF(TRIM(h.linea), ''), 'SIN LINEA')"
        ict_expr = "COALESCE(h.ict, 0)"
        numero_parte_expr = "COALESCE(NULLIF(TRIM(h.no_parte), ''), 'SIN NUMERO DE PARTE')"
        turno_expr = _ict_pass_fail_turno_expr("h.ts")

        sql = (
            "SELECT detalle.barcode, detalle.numero_parte, detalle.linea, "
            "detalle.ict, detalle.turno, detalle.primer_test, detalle.ultimo_test, "
            "detalle.intentos, detalle.ok_count, detalle.ng_count, "
            "detalle.resultado_primer, detalle.resultado_final, "
            "COALESCE(reparacion.defect_count, 0) AS defect_count, "
            "CASE WHEN reparacion.defect_count IS NULL THEN 0 ELSE 1 END AS fue_reparacion, "
            "reparacion.primera_reparacion, "
            "COALESCE(reparacion.defectos, '') AS defectos "
            "FROM ("
            " SELECT h.barcode AS barcode, "
            f" MIN({numero_parte_expr}) AS numero_parte, "
            f" MIN({linea_expr}) AS linea, "
            f" MIN({ict_expr}) AS ict, "
            f" MIN({turno_expr}) AS turno, "
            " MIN(h.ts) AS primer_test, "
            " MAX(h.ts) AS ultimo_test, "
            " COUNT(*) AS intentos, "
            " SUM(CASE WHEN UPPER(COALESCE(h.resultado, '')) = 'OK' THEN 1 ELSE 0 END) AS ok_count, "
            " SUM(CASE WHEN UPPER(COALESCE(h.resultado, '')) = 'NG' THEN 1 ELSE 0 END) AS ng_count, "
            " SUBSTRING_INDEX(GROUP_CONCAT(UPPER(COALESCE(h.resultado, '')) ORDER BY h.ts ASC, h.id ASC SEPARATOR ','), ',', 1) AS resultado_primer, "
            " SUBSTRING_INDEX(GROUP_CONCAT(UPPER(COALESCE(h.resultado, '')) ORDER BY h.ts DESC, h.id DESC SEPARATOR ','), ',', 1) AS resultado_final "
            " FROM history_ict h "
            " WHERE h.ts >= %s AND h.ts < %s "
            f" AND {linea_expr}=%s "
            f" AND {ict_expr}=%s "
            f" AND {turno_expr}=%s "
            f" AND {numero_parte_expr}=%s "
        )
        params = [fecha_inicio, fecha_fin, linea, ict, turno, numero_parte]

        if barcode:
            sql += " AND h.barcode LIKE %s "
            params.append(f"{barcode}%")

        sql += (
            " GROUP BY h.barcode "
            " HAVING COUNT(*) >= %s "
            ") detalle "
            "LEFT JOIN ("
            " SELECT codigo, COUNT(*) AS defect_count, MIN(fecha) AS primera_reparacion, "
            " GROUP_CONCAT(DISTINCT NULLIF(TRIM(defecto), '') ORDER BY defecto SEPARATOR ', ') AS defectos "
            " FROM defect_data GROUP BY codigo"
            ") reparacion ON reparacion.codigo = detalle.barcode "
            "ORDER BY detalle.intentos DESC, detalle.ultimo_test DESC, detalle.barcode ASC"
        )
        params.append(min_intentos)

        rows = execute_query(sql, tuple(params), fetch="all") or []
        formatted_rows = []
        for row in rows:
            formatted = _ict_format_row(row)
            intentos = int(formatted.get("intentos") or 0)
            ok_count = int(formatted.get("ok_count") or 0)
            ng_count = int(formatted.get("ng_count") or 0)
            defect_count = int(formatted.get("defect_count") or 0)
            fue_reparacion = bool(int(formatted.get("fue_reparacion") or 0))
            resultado_primer = (formatted.get("resultado_primer") or "").upper()
            resultado_final = (formatted.get("resultado_final") or "").upper()

            formatted["intentos"] = intentos
            formatted["ok_count"] = ok_count
            formatted["ng_count"] = ng_count
            formatted["defect_count"] = defect_count
            formatted["fue_reparacion"] = fue_reparacion
            formatted["resultado_primer"] = resultado_primer
            formatted["resultado_final"] = resultado_final
            formatted["pass_real"] = resultado_primer == "OK" or (
                fue_reparacion and ok_count > 0
            )
            formatted_rows.append(formatted)

        total_intentos = sum(row["intentos"] for row in formatted_rows)
        ok_total = sum(row["ok_count"] for row in formatted_rows)
        ng_total = sum(row["ng_count"] for row in formatted_rows)
        piezas_unicas = len(formatted_rows)
        piezas_repetidas = sum(1 for row in formatted_rows if row["intentos"] > 1)
        piezas_reparacion = sum(1 for row in formatted_rows if row["fue_reparacion"])
        pass_real = sum(1 for row in formatted_rows if row["pass_real"])
        porcentaje_pass_real = (
            round((pass_real / piezas_unicas) * 100, 2) if piezas_unicas else 0
        )

        return jsonify({
            "summary": {
                "fecha": fecha,
                "linea": linea,
                "ict": ict,
                "turno": turno,
                "numero_parte": numero_parte,
                "total_intentos": total_intentos,
                "ok_total": ok_total,
                "ng_total": ng_total,
                "piezas_unicas": piezas_unicas,
                "piezas_repetidas": piezas_repetidas,
                "piezas_reparacion": piezas_reparacion,
                "pass_real": pass_real,
                "porcentaje_pass_real": porcentaje_pass_real,
            },
            "rows": formatted_rows,
        })
    except ValueError:
        return jsonify({"error": "Fecha invalida para consultar detalle."}), 400
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


@bp.route("/api/ict/pass-fail/export")
@login_requerido
def ict_pass_fail_export():
    """Exportar resumen Pass/Fail de ICT a un archivo de Excel."""
    from app.api.shared.excel_helpers import (
        _create_vision_pass_fail_excel_image,
        _send_excel_download,
    )

    try:
        sql, params = _build_history_ict_pass_fail_summary_query()
        rows = execute_query(sql, params, fetch="all") or []

        from io import BytesIO

        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

        wb = Workbook()
        ws = wb.active
        ws.title = "ICT Pass Fail"

        header_fill = PatternFill(start_color="3f6b6e", end_color="3f6b6e", fill_type="solid")
        cell_fill = PatternFill(start_color="a1a09c", end_color="a1a09c", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF", size=10)
        border = Border(
            left=Side(style="thin", color="000000"),
            right=Side(style="thin", color="000000"),
            top=Side(style="thin", color="000000"),
            bottom=Side(style="thin", color="000000"),
        )

        headers = [
            "Fecha", "Linea", "ICT", "Turno", "Numero de parte",
            "Total", "OK", "NG", "% Pass", "% Fail", "PORCENTAJE",
        ]

        for col_num, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_num, value=header)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = border

        for row_idx, row in enumerate(rows, start=2):
            total = int(row.get("total") or 0)
            ok_count = int(row.get("ok_count") or 0)
            ng_count = int(row.get("ng_count") or 0)
            porcentaje_ok = round((ok_count / total) * 100, 2) if total else 0
            porcentaje_ng = round((ng_count / total) * 100, 2) if total else 0

            values = [
                _ict_format_row({"fecha": row.get("fecha")}).get("fecha", ""),
                row.get("linea", "") or "",
                row.get("ict", "") or "",
                row.get("turno", "") or "",
                row.get("numero_parte", "") or "",
                total,
                ok_count,
                ng_count,
                porcentaje_ok,
                porcentaje_ng,
            ]

            for col_num, value in enumerate(values, start=1):
                cell = ws.cell(row=row_idx, column=col_num, value=value)
                cell.fill = cell_fill
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.border = border

            image_cell = ws.cell(row=row_idx, column=11, value="")
            image_cell.fill = cell_fill
            image_cell.alignment = Alignment(horizontal="center", vertical="center")
            image_cell.border = border

            excel_image = _create_vision_pass_fail_excel_image(porcentaje_ok, porcentaje_ng)
            ws.add_image(excel_image, f"K{row_idx}")
            ws.row_dimensions[row_idx].height = 24

        column_widths = [14, 20, 10, 18, 28, 14, 12, 12, 14, 14, 58]
        for col_num, width in enumerate(column_widths, start=1):
            column_letter = ws.cell(row=1, column=col_num).column_letter
            ws.column_dimensions[column_letter].width = width

        ws.freeze_panes = "A2"

        output = BytesIO()
        wb.save(output)
        output.seek(0)

        filename = f"historial_ict_pass_fail_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return _send_excel_download(output, filename)
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500
