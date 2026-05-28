"""Endpoints HTTP del modulo Plan SMT (tabla plan_smt).

Migrado desde `app/routes.py` (2026-05-25). Sin cambios funcionales.

Rutas:
  GET    /api/plan-smt                     -> listar planes (con filtros de fecha)
  POST   /api/plan-smt                     -> crear plan
  POST   /api/plan-smt/batch-update        -> update batch
  POST   /api/plan-smt/update              -> update single
  POST   /api/plan-smt/save-sequences      -> guardar secuencias
  GET    /api/plan-smt/pending             -> pendientes
  POST   /api/plan-smt/reschedule          -> reschedule
  POST   /api/plan-smt/export-excel        -> export
  POST   /api/plan-smt/import-excel        -> import

Bootstrap `crear_tabla_plan_smt_v2` se reexporta desde `app/routes.py`
para preservar consumidores legacy (`startup_init.py`).
"""

import io
from datetime import date, datetime
from functools import wraps

import pandas as pd
from flask import Blueprint, jsonify, render_template, request, send_file

from app.db_mysql import execute_query
from app.api.shared.plan_lot_no import _fp_safe_date


def login_requerido(f):
    """Proxy del decorador real definido en `app.routes`."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from app import routes as _r
        return _r.login_requerido(f)(*args, **kwargs)

    return decorated_function


bp = Blueprint("control_produccion_plan_smt", __name__)


# ====== RUTAS API PARA PLAN SMT (tabla plan_smt) ======
def crear_tabla_plan_smt_v2():
    """Crear tabla plan_smt si no existe (misma estructura que plan_imd)"""
    try:
        query = """
        CREATE TABLE IF NOT EXISTS plan_smt (
            id INT AUTO_INCREMENT PRIMARY KEY,
            lot_no VARCHAR(50),
            wo_code VARCHAR(100),
            po_code VARCHAR(100),
            working_date DATE,
            line VARCHAR(20),
            shift VARCHAR(20) DEFAULT 'DIA',
            model_code VARCHAR(100),
            part_no VARCHAR(100),
            project VARCHAR(100),
            process VARCHAR(50) DEFAULT 'SMT',
            ct DECIMAL(10,2) DEFAULT 0,
            uph INT DEFAULT 0,
            plan_count INT DEFAULT 0,
            produced_count INT DEFAULT 0,
            output INT DEFAULT 0,
            entregadas_main INT DEFAULT 0,
            status VARCHAR(30) DEFAULT 'PLAN',
            group_no INT DEFAULT 1,
            sequence INT DEFAULT 1,
            routing VARCHAR(100),
            plan_start_date DATE,
            planned_start VARCHAR(10),
            planned_end VARCHAR(10),
            effective_minutes INT DEFAULT 0,
            breaks_minutes INT DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_lot_no (lot_no),
            INDEX idx_working_date (working_date),
            INDEX idx_line (line),
            INDEX idx_part_no (part_no)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
        execute_query(query)
        print("Tabla plan_smt creada/verificada")
    except Exception as e:
        print(f"Error creando tabla plan_smt: {e}")


# crear_tabla_plan_smt_v2 movido a app/startup_init.py


@bp.route("/api/plan-smt", methods=["GET"])
@login_requerido
def api_plan_smt_list():
    """Listar planes de la tabla plan_smt"""
    try:
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
            "status, group_no, sequence, routing FROM plan_smt"
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
                }
            )
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/plan-smt", methods=["POST"])
@login_requerido
def api_plan_smt_create():
    """Crear un nuevo plan en plan_smt"""
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

        lot_prefix = f"SMT-{fecha.strftime('%y%m%d')}"
        count_query = "SELECT COUNT(*) as cnt FROM plan_smt WHERE lot_no LIKE %s"
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
        process = data.get("process") or "SMT"

        sql = (
            "INSERT INTO plan_smt (lot_no, wo_code, po_code, working_date, line, shift, model_code, part_no, project, process, "
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


@bp.route("/api/plan-smt/batch-update", methods=["POST"])
@login_requerido
def api_plan_smt_batch_update():
    """Actualizar group_no y sequence de multiples planes SMT"""
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
            sql = f"UPDATE plan_smt SET {', '.join(sets)} WHERE id = %s"
            execute_query(sql, tuple(vals))
            updated += 1
        return jsonify({"success": True, "updated_count": updated})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/plan-smt/update", methods=["POST"])
@login_requerido
def api_plan_smt_update():
    """Actualizar un plan SMT"""
    try:
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
        if not sets:
            return jsonify({"error": "No hay campos para actualizar"}), 400
        sets.append("updated_at = NOW()")
        vals.append(lot_no)
        sql = f"UPDATE plan_smt SET {', '.join(sets)} WHERE lot_no = %s"
        execute_query(sql, tuple(vals))
        return jsonify({"success": True, "lot_no": lot_no})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/plan-smt/save-sequences", methods=["POST"])
@login_requerido
def api_plan_smt_save_sequences():
    """Guardar secuencias de planes SMT"""
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
            sql = f"UPDATE plan_smt SET {', '.join(sets)} WHERE lot_no = %s"
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


@bp.route("/api/plan-smt/pending", methods=["GET"])
@login_requerido
def api_plan_smt_pending():
    """Obtener planes SMT con cantidad pendiente para reprogramar"""
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
            FROM plan_smt
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


@bp.route("/api/plan-smt/reschedule", methods=["POST"])
@login_requerido
def api_plan_smt_reschedule():
    """Reprogramar planes SMT: crear sublotes con cantidad pendiente y cerrar originales"""
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
            FROM plan_smt WHERE lot_no IN ({placeholders})
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

            # Determinar lote base
            parts = lot_original.split("-")
            # SMT-YYMMDD-NNN formato base tiene 3 partes separadas por -
            if len(parts) > 3:
                lot_base = "-".join(parts[:3])
            else:
                lot_base = lot_original

            # Buscar siguiente secuencia de sublotes
            sub_count = execute_query(
                "SELECT COUNT(*) as c FROM plan_smt WHERE lot_no LIKE %s AND lot_no <> %s AND CHAR_LENGTH(lot_no) > CHAR_LENGTH(%s)",
                (f"{lot_base}-%", lot_base, lot_base),
                fetch="one",
            )
            next_seq = (sub_count["c"] if sub_count else 0) + 1
            nuevo_lot = f"{lot_base}-{next_seq:02d}"

            execute_query(
                """
                INSERT INTO plan_smt
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

            # Cerrar plan original
            execute_query(
                "UPDATE plan_smt SET plan_count = %s, status = 'TERMINADO', updated_at = NOW() WHERE lot_no = %s",
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


@bp.route("/api/plan-smt/export-excel", methods=["POST"])
@login_requerido
def api_plan_smt_export_excel():
    """Exportar planes SMT a Excel"""
    try:
        payload = request.get_json() or {}
        plans = payload.get("plans", [])
        if not plans:
            return jsonify({"error": "No hay datos para exportar"}), 400
        import io

        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font

        wb = Workbook()
        ws = wb.active
        ws.title = "Plan SMT"
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
                ]
            )
        bio = io.BytesIO()
        wb.save(bio)
        bio.seek(0)
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M")
        return send_file(
            bio,
            as_attachment=True,
            download_name=f"Plan_SMT_{ts}.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/plan-smt/import-excel", methods=["POST"])
@login_requerido
def api_plan_smt_import_excel():
    """Importar planes SMT desde archivo Excel"""
    try:
        if "file" not in request.files:
            return jsonify({"error": "No se envio archivo"}), 400

        file = request.files["file"]
        working_date_default = request.form.get(
            "working_date"
        ) or datetime.utcnow().strftime("%Y-%m-%d")
        import io

        import pandas as pd

        content = file.read()
        filename = (file.filename or "").lower()

        line_reverse_map = {
            "SMT A": "SA",
            "SMT B": "SB",
            "SMT C": "SC",
            "SMT D": "SD",
            "SMT E": "SE",
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

        # Ordenar por linea para que lotes sean consecutivos por linea
        line_priority_smt = {"SA": 0, "SB": 1, "SC": 2, "SD": 3, "SE": 4}
        parsed_rows.sort(key=lambda x: line_priority_smt.get(x["line"], 99))

        # Resolver datos de raw_smd en lotes para evitar consultas por fila
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

        # Obtener base de lotes una sola vez
        lot_prefix = f"SMT-{fecha_default.strftime('%y%m%d')}"
        count_result = execute_query(
            "SELECT COUNT(*) as cnt FROM plan_smt WHERE lot_no LIKE %s",
            (f"{lot_prefix}%",),
            fetch="one",
        )
        base_count = int((count_result or {}).get("cnt", 0) or 0)

        # Preparar filas para insercion masiva
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
                    lot_no,  # lot_no
                    "SIN-WO",  # wo_code
                    "SIN-PO",  # po_code
                    fecha_default,  # working_date
                    item["line"],  # line
                    item["shift"],  # shift
                    model_code,  # model_code
                    part_no,  # part_no
                    "",  # project
                    "SMT",  # process
                    item["plan_count"],  # plan_count
                    ct,  # ct
                    uph,  # uph
                    "PLAN",  # status
                    1,  # group_no
                    idx,  # sequence
                )
            )

        insert_prefix = (
            "INSERT INTO plan_smt (lot_no, wo_code, po_code, working_date, line, shift, model_code, part_no, project, process, "
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


# ---------------------------------------------------------------------------
# Fase 3.2 (2026-05-28): render template del modulo migrado desde routes.py.
# ---------------------------------------------------------------------------


@bp.route("/plan-main-smt-ajax")
@login_requerido
def plan_main_smt_ajax():
    try:
        return render_template("Control de proceso/Control_produccion_smt_plan.html")
    except Exception as e:
        return f"Error al cargar el contenido: {str(e)}", 500

