"""Endpoints HTTP del modulo Control de produccion IMT (tabla plan_imd).

Migrado desde `app/routes.py` (2026-05-26). Sin cambios funcionales.

Rutas render:
  GET  /plan-main-imd-ajax                         -> render fragment AJAX

Rutas API (sobre tabla plan_imd):
  GET  /api/plan-imd                               -> listar planes IMD
  POST /api/plan-imd                               -> crear plan IMD
  POST /api/plan-imd/batch-update                  -> update batch (group_no, sequence)
  POST /api/plan-imd/update                        -> editar plan IMD
  POST /api/plan-imd/save-sequences                -> guardar secuencias
  GET  /api/plan-imd/pending                       -> obtener planes pendientes
  GET  /api/plan-imd/pending-reschedule            -> obtener planes para reprogramar
  POST /api/plan-imd/reschedule                    -> reprogramar (crea sublotes)
  POST /api/plan-imd/export-excel                  -> exportar a Excel
  POST /api/plan-imd/import-excel                  -> importar desde Excel

Helpers (_ensure_plan_bom_assignment_columns, _validate_plan_bom_assignment, etc.)
viven en `app.api.control_produccion.plan_assy` para no duplicar codigo.
"""

import io
from datetime import datetime
from functools import wraps

from flask import Blueprint, jsonify, render_template, request, send_file, session

from app.db_mysql import execute_query
from app.api.shared.bom_revisions import (
    _ensure_plan_bom_assignment_columns,
    _validate_plan_bom_assignment,
)
from app.api.shared.plan_lot_no import _fp_safe_date


def login_requerido(f):
    """Proxy del decorador real definido en `app.routes`."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from app import routes as _r
        return _r.login_requerido(f)(*args, **kwargs)

    return decorated_function


def requiere_permiso_dropdown(pagina, seccion, boton):
    """Proxy del decorador real definido en `app.routes`."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from app import routes as _r
            real_decorator = _r.requiere_permiso_dropdown(pagina, seccion, boton)
            return real_decorator(f)(*args, **kwargs)

        return decorated_function

    return decorator


bp = Blueprint("control_produccion_plan_imd", __name__)


# =============================
# CONTROL DE PRODUCCION IMT
# =============================

IMD_PERMISO_PAGINA = "LISTA_CONTROL_DE_PROCESO"
IMD_PERMISO_SECCION = "Control de produccion"
IMD_PERMISO_BOTON = "Control de produccion IMT"


# =============================
# RUTAS RENDER
# =============================

@bp.route("/plan-main-imd-ajax")
@login_requerido
@requiere_permiso_dropdown(IMD_PERMISO_PAGINA, IMD_PERMISO_SECCION, IMD_PERMISO_BOTON)
def plan_main_imd_ajax():
    """Ruta AJAX para cargar dinamicamente el contenido de Plan Main IMT."""
    try:
        return render_template("Control de proceso/Control_produccion_imt.html")
    except Exception as e:
        return f"Error al cargar el contenido: {str(e)}", 500


# =============================
# RUTAS API CORE PLAN IMD
# =============================

@bp.route("/api/plan-imd", methods=["GET"])
@login_requerido
def api_plan_imd_list():
    """Listar planes de la tabla plan_imd"""
    try:
        _ensure_plan_bom_assignment_columns()
        start = request.args.get("start")
        end = request.args.get("end")
        where = []
        params = []
        if start:
            if not end:
                where.append("DATE(working_date) = %s")
                params.append(start)
            else:
                where.append("DATE(working_date) >= %s")
                params.append(start)
        if end:
            where.append("DATE(working_date) <= %s")
            params.append(end)
        sql = (
            "SELECT id, lot_no, wo_code, po_code, working_date, line, shift, model_code, part_no, project, process, "
            "COALESCE(ct,0) AS ct, COALESCE(uph,0) AS uph, COALESCE(plan_count,0) AS plan_count, "
            "COALESCE(produced_count,0) AS produced_count, COALESCE(output,0) AS output, COALESCE(entregadas_main,0) AS entregadas_main, "
            "status, group_no, sequence, routing, assigned_bom_rev, assigned_bom_rev_by, assigned_bom_rev_at FROM plan_imd"
        )
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY COALESCE(group_no,999), COALESCE(sequence,999), working_date, created_at"
        rows = execute_query(sql, tuple(params) if params else None, fetch="all")
        data = []
        for r in rows:
            data.append(
                {
                    "id": r.get("id") if isinstance(r, dict) else r[0],
                    "lot_no": r.get("lot_no") if isinstance(r, dict) else r[1],
                    "wo_code": r.get("wo_code") if isinstance(r, dict) else r[2],
                    "po_code": r.get("po_code") if isinstance(r, dict) else r[3],
                    "working_date": str(
                        (r.get("working_date") if isinstance(r, dict) else r[4]) or ""
                    )[:10],
                    "line": r.get("line") if isinstance(r, dict) else r[5],
                    "shift": r.get("shift") if isinstance(r, dict) else r[6],
                    "model_code": r.get("model_code") if isinstance(r, dict) else r[7],
                    "part_no": r.get("part_no") if isinstance(r, dict) else r[8],
                    "project": r.get("project") if isinstance(r, dict) else r[9],
                    "process": r.get("process") if isinstance(r, dict) else r[10],
                    "ct": r.get("ct") if isinstance(r, dict) else r[11],
                    "uph": r.get("uph") if isinstance(r, dict) else r[12],
                    "plan_count": r.get("plan_count") if isinstance(r, dict) else r[13],
                    "produced_count": r.get("produced_count")
                    if isinstance(r, dict)
                    else r[14],
                    "output": r.get("output") if isinstance(r, dict) else r[15],
                    "entregadas_main": r.get("entregadas_main")
                    if isinstance(r, dict)
                    else r[16],
                    "status": r.get("status") if isinstance(r, dict) else r[17],
                    "group_no": r.get("group_no") if isinstance(r, dict) else r[18],
                    "sequence": r.get("sequence") if isinstance(r, dict) else r[19],
                    "routing": r.get("routing") if isinstance(r, dict) else r[20],
                    "assigned_bom_rev": r.get("assigned_bom_rev") if isinstance(r, dict) else r[21],
                    "assigned_bom_rev_by": r.get("assigned_bom_rev_by") if isinstance(r, dict) else r[22],
                    "assigned_bom_rev_at": str(
                        (r.get("assigned_bom_rev_at") if isinstance(r, dict) else r[23]) or ""
                    ),
                }
            )
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/plan-imd", methods=["POST"])
@login_requerido
def api_plan_imd_create():
    """Crear un nuevo plan en plan_imd"""
    try:
        data = request.get_json() or {}
        working_date = data.get("working_date")
        part_no = data.get("part_no")
        line = data.get("line")
        shift = (data.get("shift") or "DIA").strip().upper()
        plan_count = int(data.get("plan_count") or 0)

        wo_code = data.get("wo_code") or "SIN-WO"
        po_code = data.get("po_code") or "SIN-PO"

        if not (working_date and part_no and line):
            return jsonify(
                {"error": "Parametros requeridos: working_date, part_no, line"}
            ), 400

        fecha = _fp_safe_date(working_date) or datetime.utcnow().date()

        lot_prefix = f"IMD-{fecha.strftime('%y%m%d')}"
        count_query = "SELECT COUNT(*) as cnt FROM plan_imd WHERE lot_no LIKE %s"
        count_result = execute_query(count_query, (f"{lot_prefix}%",), fetch="one")
        count = count_result.get("cnt", 0) if count_result else 0
        lot_no = f"{lot_prefix}-{int(count) + 1:03d}"

        raw_data = execute_query(
            "SELECT part_no, model, ct, uph FROM raw_smd WHERE part_no = %s LIMIT 1",
            (part_no,),
            fetch="one",
        )

        if raw_data:
            model_code = raw_data.get("model") or data.get("model_code") or part_no
            project = data.get("project") or ""
            ct = float(raw_data.get("ct") or data.get("ct") or 0)
            uph = int(float(raw_data.get("uph") or data.get("uph") or 0))
        else:
            model_code = data.get("model_code") or part_no
            project = data.get("project") or ""
            ct = float(data.get("ct") or 0)
            uph = int(data.get("uph") or 0)

        group_no = data.get("group_no", 1)
        sequence = data.get("sequence", 1)
        process = data.get("process") or "IMD"

        sql = (
            "INSERT INTO plan_imd (lot_no, wo_code, po_code, working_date, line, shift, model_code, part_no, project, process, "
            "plan_count, ct, uph, status, group_no, sequence, created_at) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'PLAN',%s,%s,NOW())"
        )
        params = (
            lot_no,
            wo_code,
            po_code,
            fecha,
            line,
            shift,
            model_code,
            part_no,
            project,
            process,
            plan_count,
            ct,
            uph,
            group_no,
            sequence,
        )

        execute_query(sql, params)
        return jsonify({"success": True, "lot_no": lot_no, "id": lot_no})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/plan-imd/batch-update", methods=["POST"])
@login_requerido
def api_plan_imd_batch_update():
    """Actualizar group_no y sequence de multiples planes IMD"""
    try:
        payload = request.get_json() or {}
        updates = payload.get("updates", [])
        updated = 0

        for item in updates:
            plan_id = item.get("id")
            group_no = item.get("group_no")
            sequence = item.get("sequence")

            if not plan_id:
                continue

            sets = []
            vals = []

            if group_no is not None:
                sets.append("group_no = %s")
                vals.append(int(group_no))
            if sequence is not None:
                sets.append("sequence = %s")
                vals.append(int(sequence))

            if not sets:
                continue

            sets.append("updated_at = NOW()")
            vals.append(plan_id)

            sql = f"UPDATE plan_imd SET {', '.join(sets)} WHERE id = %s"
            execute_query(sql, tuple(vals))
            updated += 1

        return jsonify({"success": True, "updated_count": updated})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/plan-imd/update", methods=["POST"])
@login_requerido
def api_plan_imd_update():
    """Actualizar un plan IMD"""
    try:
        _ensure_plan_bom_assignment_columns()
        data = request.get_json() or {}
        lot_no = data.get("lot_no")
        if not lot_no:
            return jsonify({"error": "lot_no requerido"}), 400

        sets = []
        vals = []

        allowed_fields = [
            "status",
            "plan_count",
            "output",
            "line",
            "shift",
            "working_date",
            "model_code",
            "part_no",
            "project",
            "process",
            "ct",
            "uph",
            "group_no",
            "sequence",
        ]

        for field in allowed_fields:
            if field in data:
                sets.append(f"{field} = %s")
                vals.append(data[field])
        if "assigned_bom_rev" in data:
            assigned_bom_rev, assignment_error = _validate_plan_bom_assignment(
                "plan_imd",
                lot_no,
                "IMD",
                data.get("assigned_bom_rev"),
            )
            if assignment_error:
                return jsonify({"error": assignment_error}), 409
            sets.extend(
                [
                    "assigned_bom_rev = %s",
                    "assigned_bom_rev_by = %s",
                    "assigned_bom_rev_at = NOW()",
                ]
            )
            vals.extend([assigned_bom_rev, session.get("usuario", "desconocido")])

        if not sets:
            return jsonify({"error": "No hay campos para actualizar"}), 400

        sets.append("updated_at = NOW()")
        vals.append(lot_no)

        sql = f"UPDATE plan_imd SET {', '.join(sets)} WHERE lot_no = %s"
        execute_query(sql, tuple(vals))

        return jsonify({"success": True, "lot_no": lot_no})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/plan-imd/save-sequences", methods=["POST"])
@login_requerido
def api_plan_imd_save_sequences():
    """Guardar secuencias de planes IMD"""
    try:
        payload = request.get_json() or {}
        sequences = payload.get("sequences", [])
        updated = 0
        for item in sequences:
            lot_no = item.get("lot_no")
            group_no = item.get("group_no")
            sequence = item.get("sequence")
            if not (lot_no and group_no is not None and sequence is not None):
                continue
            vals = []
            sets = []
            sets.append("group_no = %s")
            vals.append(int(group_no))
            sets.append("sequence = %s")
            vals.append(int(sequence))
            if item.get("plan_start_date") and item.get("plan_start_date") != "--":
                sets.append("plan_start_date = %s")
                vals.append(item["plan_start_date"])
            if item.get("planned_start") and item.get("planned_start") != "--":
                sets.append("planned_start = %s")
                vals.append(item["planned_start"])
            if item.get("planned_end") and item.get("planned_end") != "--":
                sets.append("planned_end = %s")
                vals.append(item["planned_end"])
            if "effective_minutes" in item:
                sets.append("effective_minutes = %s")
                vals.append(int(item.get("effective_minutes") or 0))
            if "breaks_minutes" in item:
                sets.append("breaks_minutes = %s")
                vals.append(int(item.get("breaks_minutes") or 0))
            sets.append("updated_at = NOW()")
            vals.append(lot_no)
            sql = f"UPDATE plan_imd SET {', '.join(sets)} WHERE lot_no = %s"
            execute_query(sql, tuple(vals))
            updated += 1
        return jsonify(
            {
                "success": True,
                "updated_count": updated,
                "message": f"{updated} secuencias guardadas correctamente",
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/plan-imd/pending", methods=["GET"])
@login_requerido
def api_plan_imd_pending():
    """Obtener planes IMD pendientes"""
    try:
        start = request.args.get("start")
        end = request.args.get("end")
        where = ["status = 'PLAN'"]
        params = []
        if start:
            where.append("DATE(working_date) >= %s")
            params.append(start)
        if end:
            where.append("DATE(working_date) <= %s")
            params.append(end)

        sql = (
            "SELECT id, lot_no, wo_code, po_code, working_date, line, shift, model_code, part_no, project, process, "
            "COALESCE(ct,0) AS ct, COALESCE(uph,0) AS uph, COALESCE(plan_count,0) AS plan_count, "
            "COALESCE(output,0) AS output, status, group_no, sequence FROM plan_imd"
        )
        sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY working_date, created_at"

        rows = execute_query(sql, tuple(params) if params else None, fetch="all")
        data = []
        for r in rows:
            data.append(
                {
                    "id": r.get("id"),
                    "lot_no": r.get("lot_no"),
                    "wo_code": r.get("wo_code"),
                    "po_code": r.get("po_code"),
                    "working_date": str(r.get("working_date") or "")[:10],
                    "line": r.get("line"),
                    "shift": r.get("shift"),
                    "model_code": r.get("model_code"),
                    "part_no": r.get("part_no"),
                    "project": r.get("project"),
                    "process": r.get("process"),
                    "ct": r.get("ct"),
                    "uph": r.get("uph"),
                    "plan_count": r.get("plan_count"),
                    "output": r.get("output"),
                    "status": r.get("status"),
                    "group_no": r.get("group_no"),
                    "sequence": r.get("sequence"),
                }
            )
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/plan-imd/pending-reschedule", methods=["GET"])
@login_requerido
def api_plan_imd_pending_reschedule():
    """Obtener planes IMD con cantidad pendiente para reprogramar"""
    try:
        start = request.args.get("start")
        end = request.args.get("end")
        where = [
            "COALESCE(status, '') <> 'CANCELADO'",
            "COALESCE(plan_count, 0) > COALESCE(produced_count, 0)",
        ]
        params = []
        if start:
            where.append("DATE(working_date) >= %s")
            params.append(start)
        if end:
            where.append("DATE(working_date) <= %s")
            params.append(end)
        sql = f"""
            SELECT lot_no, working_date, part_no, line, model_code, plan_count,
                   COALESCE(produced_count, 0) as produced_count, status
            FROM plan_imd
            WHERE {" AND ".join(where)}
            ORDER BY working_date, line, sequence
        """
        rows = execute_query(sql, tuple(params), fetch="all") or []
        result = []
        for r in rows:
            wd = r.get("working_date")
            result.append(
                {
                    "lot_no": r["lot_no"],
                    "working_date": wd.strftime("%Y-%m-%d")
                    if hasattr(wd, "strftime")
                    else str(wd)
                    if wd
                    else "",
                    "part_no": r.get("part_no"),
                    "line": r.get("line"),
                    "model_code": r.get("model_code"),
                    "plan_count": r.get("plan_count", 0),
                    "produced_count": r.get("produced_count", 0),
                    "status": r.get("status"),
                }
            )
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/plan-imd/reschedule", methods=["POST"])
@login_requerido
def api_plan_imd_reschedule():
    """Reprogramar planes IMD: crear sublotes con cantidad pendiente y cerrar originales"""
    try:
        data = request.get_json() or {}
        lot_nos = data.get("lot_nos", [])
        new_date = data.get("new_working_date")

        if not (lot_nos and new_date):
            return jsonify({"error": "lot_nos y new_working_date requeridos"}), 400

        placeholders = ",".join(["%s"] * len(lot_nos))
        planes = (
            execute_query(
                f"""
            SELECT lot_no, wo_code, po_code, working_date, line, model_code,
                   part_no, project, process, plan_count, produced_count, ct, uph,
                   routing, status, group_no, sequence, shift
            FROM plan_imd WHERE lot_no IN ({placeholders})
        """,
                tuple(lot_nos),
                fetch="all",
            )
            or []
        )

        if not planes:
            return jsonify({"error": "No se encontraron planes"}), 404

        creados = 0
        for plan in planes:
            lot_original = plan["lot_no"]
            plan_count = plan["plan_count"] or 0
            produced = plan["produced_count"] or 0
            pendiente = plan_count - produced
            if pendiente <= 0:
                continue

            parts = lot_original.split("-")
            if len(parts) > 3:
                lot_base = "-".join(parts[:3])
            else:
                lot_base = lot_original

            result = execute_query(
                "SELECT COUNT(*) as c FROM plan_imd WHERE lot_no LIKE %s AND lot_no <> %s",
                (f"{lot_base}-%", lot_base),
                fetch="one",
            )
            sub_count = execute_query(
                "SELECT COUNT(*) as c FROM plan_imd WHERE lot_no LIKE %s AND lot_no <> %s AND CHAR_LENGTH(lot_no) > CHAR_LENGTH(%s)",
                (f"{lot_base}-%", lot_base, lot_base),
                fetch="one",
            )
            next_seq = (sub_count["c"] if sub_count else 0) + 1
            nuevo_lot = f"{lot_base}-{next_seq:02d}"

            execute_query(
                """
                INSERT INTO plan_imd
                (lot_no, wo_code, po_code, working_date, line, shift, model_code,
                 part_no, project, process, plan_count, ct, uph, routing, status,
                 group_no, sequence, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'PLAN', %s, %s, NOW())
            """,
                (
                    nuevo_lot,
                    plan.get("wo_code"),
                    plan.get("po_code"),
                    new_date,
                    plan.get("line"),
                    plan.get("shift"),
                    plan.get("model_code"),
                    plan.get("part_no"),
                    plan.get("project"),
                    plan.get("process"),
                    pendiente,
                    plan.get("ct"),
                    plan.get("uph"),
                    plan.get("routing"),
                    plan.get("group_no"),
                    plan.get("sequence"),
                ),
            )

            execute_query(
                "UPDATE plan_imd SET plan_count = %s, status = 'TERMINADO', updated_at = NOW() WHERE lot_no = %s",
                (produced, lot_original),
            )
            creados += 1

        return jsonify(
            {
                "success": True,
                "created": creados,
                "message": f"{creados} nuevo(s) plan(es) creado(s) para {new_date}",
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/plan-imd/export-excel", methods=["POST"])
@login_requerido
def api_plan_imd_export_excel():
    """Exportar planes IMD a Excel"""
    try:
        payload = request.get_json() or {}
        plans = payload.get("plans", [])
        if not plans:
            return jsonify({"error": "No hay datos para exportar"}), 400

        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font

        wb = Workbook()
        ws = wb.active
        ws.title = "Plan IMD"
        headers = [
            "Sec",
            "LOT NO",
            "WO",
            "PO",
            "Fecha",
            "Linea",
            "Shift",
            "Modelo",
            "Part No",
            "Proyecto",
            "Proceso",
            "CT",
            "UPH",
            "Plan",
            "Output",
            "Status",
            "Tiempo",
            "Inicio",
            "Fin",
            "Grupo",
        ]
        ws.append(headers)
        for c in ws[1]:
            c.font = Font(bold=True)
            c.alignment = Alignment(horizontal="center")
        for p in plans:
            if p.get("isGroupHeader"):
                ws.append([p.get("groupTitle", f"GRUPO {p.get('groupIndex', 0) + 1}")])
                continue
            ws.append(
                [
                    p.get("secuencia", ""),
                    p.get("lot_no", ""),
                    p.get("wo_code", ""),
                    p.get("po_code", ""),
                    p.get("working_date", ""),
                    p.get("line", ""),
                    p.get("shift", ""),
                    p.get("model_code", ""),
                    p.get("part_no", ""),
                    p.get("project", ""),
                    p.get("process", ""),
                    p.get("ct", ""),
                    p.get("uph", ""),
                    p.get("plan_count", ""),
                    p.get("output", ""),
                    p.get("status", ""),
                    p.get("tiempo_produccion", ""),
                    p.get("inicio", ""),
                    p.get("fin", ""),
                    p.get("grupo", ""),
                ]
            )
        bio = io.BytesIO()
        wb.save(bio)
        bio.seek(0)
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M")
        return send_file(
            bio,
            as_attachment=True,
            download_name=f"Plan_IMD_{ts}.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/plan-imd/import-excel", methods=["POST"])
@login_requerido
def api_plan_imd_import_excel():
    """Importar planes IMD desde archivo Excel"""
    try:
        if "file" not in request.files:
            return jsonify({"error": "No se envio archivo"}), 400

        file = request.files["file"]
        working_date_default = request.form.get(
            "working_date"
        ) or datetime.utcnow().strftime("%Y-%m-%d")

        import pandas as pd

        content = file.read()
        filename = (file.filename or "").lower()

        line_reverse_map = {
            "PANA A": "P1",
            "PANA B": "P2",
            "PANA C": "P3",
            "PANA D": "P4",
        }
        line_reverse_map_upper = {k.upper(): v for k, v in line_reverse_map.items()}

        if filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(content), header=None)
        else:
            df = pd.read_excel(io.BytesIO(content), header=None)

        first_val = str(df.iloc[0, 0]).strip().lower() if len(df) > 0 else ""
        has_headers = first_val in (
            "line",
            "linea",
            "línea",
            "lÃ­nea",
            "part_no",
            "part no",
        )

        if has_headers:
            df.columns = df.iloc[0]
            df = df[1:].reset_index(drop=True)
            df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]

        fecha_default = _fp_safe_date(working_date_default) or datetime.utcnow().date()
        parsed_rows = []

        for _, row in df.iterrows():
            if has_headers:
                line_raw = str(row.get("line", row.get("linea", ""))).strip()
                part_no = str(
                    row.get("part_no", row.get("partno", row.get("part", "")))
                ).strip()
                shift = str(row.get("shift", row.get("turno", "DIA"))).strip().upper()
                try:
                    plan_count = int(
                        float(
                            row.get(
                                "plan_count",
                                row.get("plan", row.get("qty", row.get("cantidad", 0))),
                            )
                            or 0
                        )
                    )
                except Exception:
                    plan_count = 0
            else:
                line_raw = str(row.iloc[0]).strip() if len(row) > 0 else ""
                part_no = str(row.iloc[1]).strip() if len(row) > 1 else ""
                shift = str(row.iloc[2]).strip().upper() if len(row) > 2 else "DIA"
                try:
                    plan_count = int(float(row.iloc[3])) if len(row) > 3 else 0
                except Exception:
                    plan_count = 0

            if (
                not part_no
                or part_no.lower() == "nan"
                or not line_raw
                or line_raw.lower() == "nan"
            ):
                continue

            line = line_reverse_map_upper.get(line_raw.upper(), line_raw)
            if shift == "NAN" or not shift:
                shift = "DIA"

            parsed_rows.append(
                {
                    "line": line,
                    "part_no": part_no,
                    "shift": shift,
                    "plan_count": plan_count,
                }
            )

        if not parsed_rows:
            return jsonify(
                {"success": True, "imported": 0, "message": "0 planes importados"}
            )

        line_priority_imd = {"P1": 0, "P2": 1, "P3": 2, "P4": 3}
        parsed_rows.sort(key=lambda x: line_priority_imd.get(x["line"], 99))

        raw_by_part = {}
        unique_parts = sorted({item["part_no"] for item in parsed_rows})
        lookup_batch_size = 400
        for i in range(0, len(unique_parts), lookup_batch_size):
            batch_parts = unique_parts[i : i + lookup_batch_size]
            placeholders = ",".join(["%s"] * len(batch_parts))
            sql_raw = f"SELECT part_no, model, ct, uph FROM raw_smd WHERE part_no IN ({placeholders})"
            raw_rows = execute_query(sql_raw, tuple(batch_parts), fetch="all") or []
            for raw in raw_rows:
                raw_part_no = str(raw.get("part_no") or "").strip()
                if raw_part_no and raw_part_no not in raw_by_part:
                    raw_by_part[raw_part_no] = raw

        lot_prefix = f"IMD-{fecha_default.strftime('%y%m%d')}"
        count_result = execute_query(
            "SELECT COUNT(*) as cnt FROM plan_imd WHERE lot_no LIKE %s",
            (f"{lot_prefix}%",),
            fetch="one",
        )
        base_count = int((count_result or {}).get("cnt", 0) or 0)

        records = []
        for idx, item in enumerate(parsed_rows, start=1):
            part_no = item["part_no"]
            raw_data = raw_by_part.get(part_no)
            if raw_data:
                model_code = raw_data.get("model") or part_no
                try:
                    ct = float(raw_data.get("ct") or 0)
                except Exception:
                    ct = 0
                try:
                    uph = int(float(raw_data.get("uph") or 0))
                except Exception:
                    uph = 0
            else:
                model_code = part_no
                ct = 0
                uph = 0

            lot_no = f"{lot_prefix}-{base_count + idx:03d}"

            records.append(
                (
                    lot_no,
                    "SIN-WO",
                    "SIN-PO",
                    fecha_default,
                    item["line"],
                    item["shift"],
                    model_code,
                    part_no,
                    "",
                    "IMD",
                    item["plan_count"],
                    ct,
                    uph,
                    "PLAN",
                    1,
                    idx,
                )
            )

        insert_prefix = (
            "INSERT INTO plan_imd (lot_no, wo_code, po_code, working_date, line, shift, model_code, part_no, project, process, "
            "plan_count, ct, uph, status, group_no, sequence, created_at) VALUES "
        )
        row_placeholders = "(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW())"
        insert_batch_size = 200
        imported = 0

        for i in range(0, len(records), insert_batch_size):
            batch = records[i : i + insert_batch_size]
            values_sql = ",".join([row_placeholders] * len(batch))
            params = []
            for rec in batch:
                params.extend(rec)
            execute_query(insert_prefix + values_sql, tuple(params))
            imported += len(batch)

        return jsonify(
            {
                "success": True,
                "imported": imported,
                "message": f"{imported} planes importados",
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500
