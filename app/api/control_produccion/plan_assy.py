"""Endpoints HTTP del modulo Control de produccion ASSY (tabla plan_main).

Migrado desde `app/routes.py` (2026-05-26). Sin cambios funcionales.

Rutas render:
  GET  /plan-main                                  -> render legacy standalone
  GET  /plan-main-assy-ajax                        -> render fragment AJAX

Rutas API (sobre tabla plan_main):
  GET  /api/plan                                   -> listar planes (filtros fecha)
  POST /api/plan                                   -> crear plan
  POST /api/plan/update                            -> editar plan
  POST /api/plan/status                            -> cambiar status (con validaciones)
  GET  /api/plan/bom-revisions                     -> revisiones BOM por part_no
  POST /api/plan/save-sequences                    -> guardar orden/secuencia/tiempos
  GET  /api/plan/pending                           -> planes con cantidad pendiente
  POST /api/plan/reschedule                        -> reprogramar planes (crea sublotes)
  POST /api/plan/export-excel                      -> exportar a Excel
  GET  /api/plan/input-main/scan-lots              -> listar lotes SCAN sin asignar
  POST /api/plan/input-main/assign-lot             -> asignar lote SCAN a plan existente
  POST /api/plan/input-main/create-plan            -> crear plan desde lote SCAN
  GET  /api/plan-main/list                         -> listar planes (formato modulo Crear Plan)

NO movido aqui:
  - /api/work-orders, /api/work-orders/import, /api/wo/exportar:
    consumidos tambien por `crear-plan-produccion.js` (modulo Crear Plan), siguen en routes.py.
  - /api/plan-run/*: consumidos por "Control de operacion de linea Main", siguen en routes.py.
  - /api/raw/search: ortogonal al modulo plan_assy, sigue en routes.py.
"""

import io
import os
from datetime import date, datetime, timedelta
from functools import wraps

import pandas as pd
from flask import Blueprint, jsonify, render_template, request, send_file, session
from werkzeug.utils import secure_filename

# Importar directo desde modulos fuente (NO desde app.api.shared) para
# evitar import circular: shared -> routes -> plan_assy -> shared.
from app.db import get_db_connection
from app.db_mysql import execute_query
from app.config_mysql import get_pooled_connection
from app.api.pda.shipping_material import get_dict_cursor
from app.api.shared.bom_revisions import (
    _ensure_plan_bom_assignment_columns,
    _plan_bom_revision_catalog,
    _plan_has_ks_snapshot,  # noqa: F401  - reexportado por compatibilidad
    _validate_plan_bom_assignment,
)
from app.api.shared.plan_lot_no import _fp_generate_lot_no, _fp_safe_date


# `login_requerido` y `requiere_permiso_dropdown` viven en `app.routes`.
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


bp = Blueprint("control_produccion_plan_assy", __name__)


# =============================
# CONTROL DE PRODUCCION ASSY
# =============================

ASSY_PERMISO_PAGINA = "LISTA_CONTROL_DE_PROCESO"
ASSY_PERMISO_SECCION = "Control de produccion"
ASSY_PERMISO_BOTON = "Control de produccion ASSY"


# =============================
# Helpers locales (privados al blueprint)
# =============================
# Migracion 2026-05-26: _fp_safe_date, _fp_generate_lot_no movidos a
# app/api/shared/plan_lot_no.py (importados arriba).
# _ensure_plan_bom_assignment_columns, _validate_plan_bom_assignment,
# _plan_has_ks_snapshot movidos a app/api/shared/bom_revisions.py.

def _obtener_fecha_hora_mexico():
    """Reexport de obtener_fecha_hora_mexico desde routes (anti-circular)."""
    from app import routes as _r
    return _r.obtener_fecha_hora_mexico()


# =============================
# RUTAS RENDER
# =============================

@bp.route("/plan-main")
@login_requerido
def view_plan_main():
    """Pagina de planeacion (plantilla en Control de proceso)."""
    return render_template("Control de proceso/Control_produccion_assy.html")


@bp.route("/plan-main-assy-ajax")
@login_requerido
@requiere_permiso_dropdown(ASSY_PERMISO_PAGINA, ASSY_PERMISO_SECCION, ASSY_PERMISO_BOTON)
def plan_main_assy_ajax():
    """Ruta AJAX para cargar dinamicamente el contenido de Plan Main ASSY."""
    try:
        return render_template("Control de proceso/Control_produccion_assy.html")
    except Exception as e:
        return f"Error al cargar el contenido: {str(e)}", 500


# =============================
# RUTAS API CORE PLAN ASSY
# =============================

@bp.route("/api/plan", methods=["GET"])
@login_requerido
def api_plan_list():
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
            "SELECT id, lot_no, wo_code, po_code, working_date, line, routing, model_code, part_no, project, process, "
            "COALESCE(ct,0) AS ct, COALESCE(uph,0) AS uph, COALESCE(plan_count,0) AS plan_count, "
            "COALESCE(produced_count,0) AS input, COALESCE(output,0) AS output, COALESCE(entregadas_main,0) AS entregadas_main, "
            "COALESCE(produced_count,0) AS produced, status, group_no, sequence, "
            "assigned_bom_rev, assigned_bom_rev_by, assigned_bom_rev_at FROM plan_main"
        )
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY COALESCE(group_no,999), COALESCE(sequence,999), working_date, created_at"
        rows = execute_query(sql, tuple(params) if params else None, fetch="all")
        data = []
        for r in rows:
            data.append(
                {
                    "lot_no": r.get("lot_no") if isinstance(r, dict) else r[1],
                    "wo_code": r.get("wo_code") if isinstance(r, dict) else r[2],
                    "po_code": r.get("po_code") if isinstance(r, dict) else r[3],
                    "working_date": str(
                        (r.get("working_date") if isinstance(r, dict) else r[4]) or ""
                    )[:10],
                    "line": r.get("line") if isinstance(r, dict) else r[5],
                    "routing": r.get("routing") if isinstance(r, dict) else r[6],
                    "model_code": r.get("model_code") if isinstance(r, dict) else r[7],
                    "part_no": r.get("part_no") if isinstance(r, dict) else r[8],
                    "project": r.get("project") if isinstance(r, dict) else r[9],
                    "process": r.get("process") if isinstance(r, dict) else r[10],
                    "ct": r.get("ct") if isinstance(r, dict) else r[11],
                    "uph": r.get("uph") if isinstance(r, dict) else r[12],
                    "plan_count": r.get("plan_count") if isinstance(r, dict) else r[13],
                    "input": r.get("input") if isinstance(r, dict) else r[14],
                    "output": r.get("output") if isinstance(r, dict) else r[15],
                    "entregadas_main": r.get("entregadas_main")
                    if isinstance(r, dict)
                    else r[16],
                    "produced": r.get("produced") if isinstance(r, dict) else r[17],
                    "status": r.get("status") if isinstance(r, dict) else r[18],
                    "group_no": r.get("group_no") if isinstance(r, dict) else r[19],
                    "sequence": r.get("sequence") if isinstance(r, dict) else r[20],
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


@bp.route("/api/plan/bom-revisions", methods=["GET"])
@login_requerido
def api_plan_bom_revisions():
    try:
        _ensure_plan_bom_assignment_columns()
        part_no = (request.args.get("part_no") or "").strip()
        if not part_no:
            return jsonify({"error": "part_no requerido"}), 400
        return jsonify({"success": True, "data": _plan_bom_revision_catalog(part_no)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/plan/input-main/scan-lots", methods=["GET"])
@login_requerido
def api_plan_input_main_scan_lots():
    """Listar lotes provisionales SCAN de input_main pendientes de asignar."""
    try:
        today = _obtener_fecha_hora_mexico().date()
        default_from = today - timedelta(days=7)
        date_from = request.args.get("date_from") or str(default_from)
        date_to = request.args.get("date_to") or str(today)
        line = (request.args.get("line") or "").strip()
        part_no = (request.args.get("part_no") or "").strip()
        try:
            limit = int(request.args.get("limit") or 200)
        except Exception:
            limit = 200
        limit = max(1, min(limit, 500))

        where = [
            "i.lot_no LIKE 'SCAN-%%'",
            "COALESCE(i.result, 'OK') = 'OK'",
        ]
        params = []
        if date_from:
            where.append("DATE(i.ts) >= %s")
            params.append(date_from)
        if date_to:
            where.append("DATE(i.ts) <= %s")
            params.append(date_to)
        if line:
            where.append("i.linea = %s")
            params.append(line)
        if part_no:
            where.append("(i.nparte LIKE %s OR i.modelo LIKE %s)")
            params.extend([f"%{part_no}%", f"%{part_no}%"])

        scan_sql = f"""
            SELECT
                i.linea,
                i.nparte,
                GROUP_CONCAT(DISTINCT NULLIF(i.modelo, '') ORDER BY i.modelo SEPARATOR ', ') AS modelos,
                COUNT(DISTINCT i.lot_no) AS lotes_scan,
                COUNT(*) AS registros,
                SUM(COALESCE(i.cantidad, 1)) AS cantidad_total,
                MIN(i.ts) AS primero,
                MAX(i.ts) AS ultimo
            FROM input_main i
            WHERE {' AND '.join(where)}
            GROUP BY i.linea, i.nparte
            ORDER BY ultimo DESC
            LIMIT %s
        """
        rows = execute_query(scan_sql, tuple(params + [limit]), fetch="all") or []

        scan_items = []
        lines = set()
        parts = set()
        for r in rows:
            item = {
                "linea": r.get("linea") or "",
                "nparte": r.get("nparte") or "",
                "modelo": r.get("modelos") or "",
                "lotes_scan": int(r.get("lotes_scan") or 0),
                "registros": int(r.get("registros") or 0),
                "cantidad_total": int(r.get("cantidad_total") or r.get("registros") or 0),
                "primero": str(r.get("primero") or ""),
                "ultimo": str(r.get("ultimo") or ""),
            }
            scan_items.append(item)
            if item["linea"]:
                lines.add(item["linea"])
            if item["nparte"]:
                parts.add(item["nparte"])

        plan_options = []
        if lines and parts:
            plan_where = [
                "COALESCE(p.status, '') <> 'CANCELADO'",
                "p.line IN (" + ",".join(["%s"] * len(lines)) + ")",
                "p.part_no IN (" + ",".join(["%s"] * len(parts)) + ")",
            ]
            plan_params = list(lines) + list(parts)
            if date_from:
                plan_where.append("DATE(p.working_date) >= DATE_SUB(%s, INTERVAL 1 DAY)")
                plan_params.append(date_from)
            if date_to:
                plan_where.append("DATE(p.working_date) <= DATE_ADD(%s, INTERVAL 1 DAY)")
                plan_params.append(date_to)

            plan_sql = f"""
                SELECT
                    p.lot_no,
                    p.working_date,
                    p.line,
                    p.part_no,
                    p.model_code,
                    p.status,
                    COALESCE(p.plan_count, 0) AS plan_count,
                    COALESCE(p.produced_count, 0) AS produced_count
                FROM plan_main p
                WHERE {' AND '.join(plan_where)}
                ORDER BY p.working_date DESC, p.line, p.sequence, p.lot_no
            """
            plan_rows = execute_query(plan_sql, tuple(plan_params), fetch="all") or []
            for p in plan_rows:
                plan_options.append(
                    {
                        "lot_no": p.get("lot_no") or "",
                        "working_date": str(p.get("working_date") or "")[:10],
                        "line": p.get("line") or "",
                        "part_no": p.get("part_no") or "",
                        "model_code": p.get("model_code") or "",
                        "status": p.get("status") or "",
                        "plan_count": int(p.get("plan_count") or 0),
                        "produced_count": int(p.get("produced_count") or 0),
                    }
                )

        return jsonify(
            {
                "success": True,
                "scan_lots": scan_items,
                "plan_options": plan_options,
                "filters": {
                    "date_from": date_from,
                    "date_to": date_to,
                    "line": line,
                    "part_no": part_no,
                    "limit": limit,
                },
            }
        )
    except Exception as e:
        print(f"Error en api_plan_input_main_scan_lots: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/api/plan/input-main/assign-lot", methods=["POST"])
@login_requerido
def api_plan_input_main_assign_lot():
    """Asignar un lote provisional SCAN a un lote real de plan_main."""
    conn = None
    cursor = None
    try:
        data = request.get_json(silent=True) or {}
        scan_lot_no = (data.get("scan_lot_no") or "").strip()
        target_lot_no = (data.get("target_lot_no") or "").strip()
        group_line = (data.get("linea") or data.get("line") or "").strip()
        group_part_no = (data.get("nparte") or data.get("part_no") or "").strip()
        date_from = (data.get("date_from") or "").strip()
        date_to = (data.get("date_to") or "").strip()

        if scan_lot_no and not scan_lot_no.startswith("SCAN-"):
            return jsonify({"success": False, "error": "scan_lot_no invalido"}), 400
        if not scan_lot_no and not (group_line and group_part_no and date_from and date_to):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Para asignar por grupo se requieren linea, nparte, date_from y date_to",
                    }
                ),
                400,
            )
        if not target_lot_no:
            return jsonify({"success": False, "error": "target_lot_no requerido"}), 400

        conn = get_pooled_connection()
        if conn is None:
            raise RuntimeError("No fue posible obtener conexion MySQL.")
        cursor = get_dict_cursor(conn)
        conn.autocommit(False)

        cursor.execute(
            """
            SELECT lot_no, line, part_no, status,
                   COALESCE(plan_count, 0) AS plan_count,
                   COALESCE(produced_count, 0) AS produced_count
            FROM plan_main
            WHERE lot_no = %s
            FOR UPDATE
            """,
            (target_lot_no,),
        )
        plan = cursor.fetchone()
        if not plan:
            conn.rollback()
            return jsonify({"success": False, "error": "El Lot No destino no existe en plan_main"}), 404
        if (plan.get("status") or "").upper() == "CANCELADO":
            conn.rollback()
            return jsonify({"success": False, "error": "No se puede asignar a un plan CANCELADO"}), 400
        allow_extend = bool(data.get("allow_extend"))

        scan_where = [
            "lot_no LIKE 'SCAN-%%'",
            "COALESCE(result, 'OK') = 'OK'",
        ]
        scan_params = []
        if scan_lot_no:
            scan_where.append("lot_no = %s")
            scan_params.append(scan_lot_no)
        else:
            scan_where.extend(["linea = %s", "nparte = %s", "DATE(ts) >= %s", "DATE(ts) <= %s"])
            scan_params.extend([group_line, group_part_no, date_from, date_to])
        scan_where_sql = " AND ".join(scan_where)

        cursor.execute(
            f"""
            SELECT
                COUNT(*) AS registros,
                SUM(COALESCE(cantidad, 1)) AS cantidad_total,
                COUNT(DISTINCT lot_no) AS lotes_scan,
                MIN(linea) AS linea,
                MAX(linea) AS linea_max,
                MIN(nparte) AS nparte,
                MAX(nparte) AS nparte_max
            FROM input_main
            WHERE {scan_where_sql}
            """,
            tuple(scan_params),
        )
        scan = cursor.fetchone() or {}
        registros = int(scan.get("registros") or 0)
        cantidad_total = int(scan.get("cantidad_total") or registros)
        if registros <= 0:
            conn.rollback()
            return jsonify({"success": False, "error": "No hay registros OK para este lote SCAN"}), 404

        scan_line = (scan.get("linea") or "").strip()
        scan_line_max = (scan.get("linea_max") or "").strip()
        scan_part = (scan.get("nparte") or "").strip()
        scan_part_max = (scan.get("nparte_max") or "").strip()
        target_line = (plan.get("line") or "").strip()
        target_part = (plan.get("part_no") or "").strip()

        if scan_line != scan_line_max or scan_part != scan_part_max:
            conn.rollback()
            return jsonify({"success": False, "error": "El lote SCAN contiene mas de una linea o numero de parte"}), 400
        if scan_line != target_line or scan_part != target_part:
            conn.rollback()
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "El lote SCAN no coincide con la linea y numero de parte del plan destino",
                        "scan": {"linea": scan_line, "nparte": scan_part},
                        "target": {"linea": target_line, "nparte": target_part},
                    }
                ),
                400,
            )

        plan_count = int(plan.get("plan_count") or 0)
        produced_count = int(plan.get("produced_count") or 0)
        pending_count = plan_count - produced_count
        if pending_count <= 0:
            conn.rollback()
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "El plan destino ya esta completo. Cree un plan nuevo para estos escaneos.",
                        "plan_count": plan_count,
                        "produced_count": produced_count,
                    }
                ),
                400,
            )
        if cantidad_total > pending_count and not allow_extend:
            conn.rollback()
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "La cantidad SCAN excede el pendiente del plan. Use Extender + asignar.",
                        "can_extend": True,
                        "cantidad_total": cantidad_total,
                        "pending_count": pending_count,
                    }
                ),
                409,
            )

        cursor.execute(
            f"""
            UPDATE input_main
            SET lot_no = %s
            WHERE {scan_where_sql}
            """,
            tuple([target_lot_no] + scan_params),
        )
        updated_rows = cursor.rowcount
        if updated_rows <= 0:
            conn.rollback()
            return jsonify({"success": False, "error": "No se actualizo ningun registro"}), 409

        if cantidad_total > pending_count and allow_extend:
            cursor.execute(
                """
                UPDATE plan_main
                SET plan_count = %s,
                    produced_count = COALESCE(produced_count, 0) + %s,
                    updated_at = NOW()
                WHERE lot_no = %s
                """,
                (produced_count + cantidad_total, cantidad_total, target_lot_no),
            )
        else:
            cursor.execute(
                """
                UPDATE plan_main
                SET produced_count = COALESCE(produced_count, 0) + %s,
                    updated_at = NOW()
                WHERE lot_no = %s
                """,
                (cantidad_total, target_lot_no),
            )

        conn.commit()
        assigned_scan_lots = int(scan.get("lotes_scan") or 0)
        return jsonify(
            {
                "success": True,
                "scan_lot_no": scan_lot_no,
                "target_lot_no": target_lot_no,
                "updated_rows": updated_rows,
                "lotes_scan": assigned_scan_lots,
                "cantidad_total": cantidad_total,
                "extended": cantidad_total > pending_count and allow_extend,
                "message": f"{assigned_scan_lots} lote(s) SCAN / {updated_rows} registro(s) asignado(s) a {target_lot_no}",
            }
        )
    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        print(f"Error en api_plan_input_main_assign_lot: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if cursor:
            try:
                cursor.close()
            except Exception:
                pass
        if conn:
            try:
                conn.autocommit(True)
            except Exception:
                pass
            conn.close()


@bp.route("/api/plan/input-main/create-plan", methods=["POST"])
@login_requerido
def api_plan_input_main_create_plan():
    """Crear un plan ASSY para un grupo SCAN y asignar sus escaneos al nuevo lote."""
    conn = None
    cursor = None
    try:
        data = request.get_json(silent=True) or {}
        group_line = (data.get("linea") or data.get("line") or "").strip()
        group_part_no = (data.get("nparte") or data.get("part_no") or "").strip()
        date_from = (data.get("date_from") or "").strip()
        date_to = (data.get("date_to") or "").strip()
        working_date_raw = (data.get("working_date") or date_to or date_from).strip()

        if not (group_line and group_part_no and date_from and date_to):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Se requieren linea, nparte, date_from y date_to",
                    }
                ),
                400,
            )

        working_date = _fp_safe_date(working_date_raw) or _obtener_fecha_hora_mexico().date()
        lot_no = _fp_generate_lot_no(datetime.combine(working_date, datetime.min.time()))

        conn = get_pooled_connection()
        if conn is None:
            raise RuntimeError("No fue posible obtener conexion MySQL.")
        cursor = get_dict_cursor(conn)
        conn.autocommit(False)

        scan_where_sql = (
            "lot_no LIKE 'SCAN-%%' "
            "AND COALESCE(result, 'OK') = 'OK' "
            "AND linea = %s "
            "AND nparte = %s "
            "AND DATE(ts) >= %s "
            "AND DATE(ts) <= %s"
        )
        scan_params = (group_line, group_part_no, date_from, date_to)
        cursor.execute(
            f"""
            SELECT
                COUNT(*) AS registros,
                SUM(COALESCE(cantidad, 1)) AS cantidad_total,
                COUNT(DISTINCT lot_no) AS lotes_scan,
                MIN(ts) AS primero,
                MAX(ts) AS ultimo
            FROM input_main
            WHERE {scan_where_sql}
            """,
            scan_params,
        )
        scan = cursor.fetchone() or {}
        registros = int(scan.get("registros") or 0)
        cantidad_total = int(scan.get("cantidad_total") or registros)
        if registros <= 0:
            conn.rollback()
            return jsonify({"success": False, "error": "No hay registros SCAN OK para crear plan"}), 404

        cursor.execute(
            """
            SELECT part_no, model, project, c_t as ct, uph
            FROM raw
            WHERE TRIM(part_no) = %s OR TRIM(model) = %s OR TRIM(part_no) LIKE %s
            ORDER BY id DESC
            LIMIT 1
            """,
            (group_part_no, group_part_no, f"%{group_part_no}%"),
        )
        raw_data = cursor.fetchone() or {}
        model_code = raw_data.get("model") or group_part_no
        project = raw_data.get("project") or ""
        try:
            ct = int(float(raw_data.get("ct") or 0))
        except Exception:
            ct = 0
        try:
            uph = int(float(raw_data.get("uph") or 0))
        except Exception:
            uph = 0

        cursor.execute(
            """
            INSERT INTO plan_main
              (lot_no, wo_code, po_code, working_date, line, model_code, part_no,
               project, process, plan_count, produced_count, ct, uph, routing, status, created_at)
            VALUES
              (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """,
            (
                lot_no,
                "SIN-WO",
                "SIN-PO",
                working_date,
                group_line,
                model_code,
                group_part_no,
                project,
                "MAIN",
                cantidad_total,
                cantidad_total,
                ct,
                uph,
                1,
                "TERMINADO",
            ),
        )
        cursor.execute(
            f"""
            UPDATE input_main
            SET lot_no = %s
            WHERE {scan_where_sql}
            """,
            tuple([lot_no] + list(scan_params)),
        )
        updated_rows = cursor.rowcount
        if updated_rows <= 0:
            conn.rollback()
            return jsonify({"success": False, "error": "No se actualizo ningun registro SCAN"}), 409

        conn.commit()
        return jsonify(
            {
                "success": True,
                "lot_no": lot_no,
                "updated_rows": updated_rows,
                "cantidad_total": cantidad_total,
                "message": f"Plan {lot_no} creado con {cantidad_total} pieza(s) y {updated_rows} escaneo(s) asignado(s)",
            }
        )
    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        print(f"Error en api_plan_input_main_create_plan: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if cursor:
            try:
                cursor.close()
            except Exception:
                pass
        if conn:
            try:
                conn.autocommit(True)
            except Exception:
                pass
            conn.close()


@bp.route("/api/plan", methods=["POST"])
@login_requerido
def api_plan_create():
    try:
        data = request.get_json() or {}
        working_date = data.get("working_date")
        part_no = data.get("part_no")
        line = data.get("line")
        turno = (data.get("turno") or "DIA").strip().upper()
        plan_count = int(data.get("plan_count") or 0)

        wo_code = data.get("wo_code") or ""
        po_code = data.get("po_code") or ""

        if not wo_code or wo_code.strip() == "":
            wo_code = "SIN-WO"
        if not po_code or po_code.strip() == "":
            po_code = "SIN-PO"

        if not (working_date and part_no and line):
            return jsonify({"error": "Parametros requeridos"}), 400
        fecha = _fp_safe_date(working_date) or datetime.utcnow().date()
        routing = {"DIA": 1, "TIEMPO EXTRA": 2, "NOCHE": 3}.get(turno, 1)
        lot_no = _fp_generate_lot_no(datetime.combine(fecha, datetime.min.time()))

        raw_data_query = """
            SELECT part_no, model, project, c_t as ct, uph
            FROM raw
            WHERE part_no = %s OR part_no LIKE %s OR model = %s OR model LIKE %s
            ORDER BY id DESC
            LIMIT 1
        """
        raw_params = (part_no, f"%{part_no}%", part_no, f"%{part_no}%")

        raw_data = execute_query(raw_data_query, raw_params, fetch="one")

        if raw_data:
            model_code = raw_data.get("model") or part_no
            project = raw_data.get("project") or ""

            try:
                ct = float(raw_data.get("ct") or 0)
            except Exception:
                ct = 0.0
            try:
                uph_raw = raw_data.get("uph")
                if uph_raw and str(uph_raw).strip().replace(".", "").isdigit():
                    uph = int(float(str(uph_raw).strip()))
                else:
                    uph = 0
            except Exception:
                uph = 0
        else:
            model_code = part_no
            project = ""
            ct = 0.0
            uph = 0

        group_no = data.get("group_no")
        sequence = None

        if group_no is not None:
            seq_query = (
                "SELECT MAX(sequence) as max_seq FROM plan_main WHERE group_no = %s"
            )
            seq_result = execute_query(seq_query, (int(group_no),), fetch="one")
            max_seq = seq_result.get("max_seq") if seq_result else None
            sequence = (max_seq + 1) if max_seq is not None else 1

        if group_no is not None and sequence is not None:
            sql = (
                "INSERT INTO plan_main (lot_no, wo_code, po_code, working_date, line, model_code, part_no, project, process, plan_count, ct, uph, routing, status, group_no, sequence, created_at) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'PLAN',%s,%s,NOW())"
            )
            params = (
                lot_no,
                wo_code,
                po_code,
                fecha,
                line,
                model_code,
                part_no,
                project,
                "MAIN",
                plan_count,
                ct,
                uph,
                routing,
                int(group_no),
                sequence,
            )
        else:
            sql = (
                "INSERT INTO plan_main (lot_no, wo_code, po_code, working_date, line, model_code, part_no, project, process, plan_count, ct, uph, routing, status, created_at) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'PLAN',NOW())"
            )
            params = (
                lot_no,
                wo_code,
                po_code,
                fecha,
                line,
                model_code,
                part_no,
                project,
                "MAIN",
                plan_count,
                ct,
                uph,
                routing,
            )

        execute_query(sql, params)
        return jsonify(
            {
                "success": True,
                "lot_no": lot_no,
                "model_code": model_code,
                "ct": ct,
                "uph": uph,
                "project": project,
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/plan/update", methods=["POST"])
@login_requerido
def api_plan_update():
    try:
        _ensure_plan_bom_assignment_columns()
        data = request.get_json() or {}
        lot_no = data.get("lot_no")
        if not lot_no:
            return jsonify({"error": "lot_no requerido"}), 400
        fields = []
        vals = []
        if "plan_count" in data:
            fields.append("plan_count = %s")
            vals.append(int(data.get("plan_count") or 0))
        if "status" in data:
            fields.append("status = %s")
            vals.append(str(data.get("status")))
        if "line" in data:
            fields.append("line = %s")
            vals.append(str(data.get("line")))
        if "wo_code" in data:
            fields.append("wo_code = %s")
            vals.append(str(data.get("wo_code")))
        if "po_code" in data:
            fields.append("po_code = %s")
            vals.append(str(data.get("po_code")))
        if "turno" in data:
            routing = {"DIA": 1, "TIEMPO EXTRA": 2, "NOCHE": 3}.get(
                str(data.get("turno")).strip().upper(), 1
            )
            fields.append("routing = %s")
            vals.append(routing)
        if "uph" in data:
            fields.append("uph = %s")
            vals.append(str(data.get("uph")))
        if "ct" in data:
            fields.append("ct = %s")
            vals.append(str(data.get("ct")))
        if "project" in data:
            fields.append("project = %s")
            vals.append(str(data.get("project")))
        if "model_code" in data:
            fields.append("model_code = %s")
            vals.append(str(data.get("model_code")))
        if "assigned_bom_rev" in data:
            assigned_bom_rev, assignment_error = _validate_plan_bom_assignment(
                "plan_main",
                lot_no,
                "MAIN",
                data.get("assigned_bom_rev"),
            )
            if assignment_error:
                return jsonify({"error": assignment_error}), 409
            fields.extend(
                [
                    "assigned_bom_rev = %s",
                    "assigned_bom_rev_by = %s",
                    "assigned_bom_rev_at = NOW()",
                ]
            )
            vals.extend([assigned_bom_rev, session.get("usuario", "desconocido")])
        if not fields:
            return jsonify({"error": "Sin cambios"}), 400
        fields.append("updated_at = NOW()")
        sql = f"UPDATE plan_main SET {', '.join(fields)} WHERE lot_no = %s"
        vals.append(lot_no)
        execute_query(sql, tuple(vals))
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/plan/status", methods=["POST"])
@login_requerido
def api_plan_status():
    """Actualizar el status de un plan con validaciones y motivos"""
    try:
        data = request.get_json() or {}
        lot_no = data.get("lot_no", "").strip()
        new_status = data.get("status", "").strip().upper()

        if not lot_no:
            return jsonify(
                {"error": "lot_no requerido", "error_code": "MISSING_LOT_NO"}
            ), 400

        if not new_status:
            return jsonify(
                {"error": "status requerido", "error_code": "MISSING_STATUS"}
            ), 400

        valid_statuses = [
            "PENDIENTE",
            "EN PROGRESO",
            "PAUSADO",
            "TERMINADO",
            "CANCELADO",
        ]
        if new_status not in valid_statuses:
            return jsonify(
                {
                    "error": f"Status invalido: {new_status}",
                    "error_code": "INVALID_STATUS",
                }
            ), 400

        check_sql = "SELECT line, status, plan_count, produced_count, started_at, pause_started_at, paused_at FROM plan_main WHERE lot_no = %s"
        plan_result = execute_query(check_sql, (lot_no,), fetch="one")

        if not plan_result:
            return jsonify(
                {"error": "Plan no encontrado", "error_code": "NOT_FOUND"}
            ), 404

        current_line = plan_result.get("line") or plan_result.get("linea")
        current_status = (plan_result.get("status") or "").strip().upper()
        plan_count = int(plan_result.get("plan_count") or plan_result.get("qty") or 0)
        produced_count = int(
            plan_result.get("produced_count") or plan_result.get("producido") or 0
        )
        started_at = plan_result.get("started_at")
        pause_started_at = plan_result.get("pause_started_at")
        paused_at = int(plan_result.get("paused_at") or 0)

        if new_status == "EN PROGRESO" and current_status != "EN PROGRESO":
            conflict_sql = """
                SELECT lot_no FROM plan_main
                WHERE line = %s AND status = 'EN PROGRESO' AND lot_no != %s
                LIMIT 1
            """
            conflict_result = execute_query(
                conflict_sql, (current_line, lot_no), fetch="one"
            )

            if conflict_result:
                conflicting_lot = conflict_result.get("lot_no") or conflict_result.get(
                    "lote"
                )
                return jsonify(
                    {
                        "error": "Ya existe un plan EN PROGRESO en esta linea",
                        "error_code": "LINE_CONFLICT",
                        "line": current_line,
                        "lot_no_en_progreso": conflicting_lot,
                    }
                ), 409

        update_fields = ["status = %s", "updated_at = NOW()"]
        update_values = [new_status]

        if new_status == "EN PROGRESO":
            if current_status == "PAUSADO" and pause_started_at:
                update_fields.append(
                    "paused_at = paused_at + TIMESTAMPDIFF(SECOND, pause_started_at, NOW())"
                )
            elif current_status != "EN PROGRESO" and not started_at:
                update_fields.append("started_at = NOW()")

        if new_status == "PAUSADO" and current_status == "EN PROGRESO":
            if "pause_reason" in data:
                update_fields.append("pause_reason = %s")
                update_values.append(str(data.get("pause_reason", "")))
            update_fields.append("pause_started_at = NOW()")

        if new_status == "TERMINADO":
            if current_status == "PAUSADO" and pause_started_at:
                update_fields.append(
                    "paused_at = paused_at + TIMESTAMPDIFF(SECOND, pause_started_at, NOW())"
                )
            update_fields.append("ended_at = NOW()")
            if produced_count < plan_count and "end_reason" in data:
                update_fields.append("end_reason = %s")
                update_values.append(str(data.get("end_reason", "")))

        update_sql = (
            f"UPDATE plan_main SET {', '.join(update_fields)} WHERE lot_no = %s"
        )
        update_values.append(lot_no)

        rows_affected = execute_query(update_sql, tuple(update_values))

        if isinstance(rows_affected, int) and rows_affected == 0:
            return jsonify(
                {
                    "error": "No se actualizo ninguna fila",
                    "error_code": "NO_ROWS_UPDATED",
                }
            ), 400

        return jsonify(
            {
                "success": True,
                "lot_no": lot_no,
                "new_status": new_status,
                "line": current_line,
            }
        )

    except Exception as e:
        print(f"Error en api_plan_status: {e}")
        import traceback

        traceback.print_exc()
        return jsonify({"error": str(e), "error_code": "UNHANDLED_EXCEPTION"}), 500


@bp.route("/api/plan/save-sequences", methods=["POST"])
@login_requerido
def api_plan_save_sequences():
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
            sql = f"UPDATE plan_main SET {', '.join(sets)} WHERE lot_no = %s"
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


@bp.route("/api/plan/pending", methods=["GET"])
@login_requerido
def api_plan_pending():
    """Obtener planes con cantidad pendiente. Filtra por rango de fechas si se proporcionan start y end."""
    try:
        start = request.args.get("start")
        end = request.args.get("end")

        where = ["status <> 'CANCELADO'"]
        params = []

        if start:
            where.append("DATE(working_date) >= %s")
            params.append(start)
            print(f" Filtro START aplicado: {start}")

        if end:
            where.append("DATE(working_date) <= %s")
            params.append(end)
            print(f" Filtro END aplicado: {end}")

        where.append("COALESCE(plan_count, 0) > COALESCE(produced_count, 0)")

        sql = (
            "SELECT lot_no, working_date, part_no, line, "
            "COALESCE(plan_count,0) AS plan_count, "
            "COALESCE(produced_count,0) AS input, "
            "status "
            "FROM plan_main "
            "WHERE " + " AND ".join(where) + " "
            "ORDER BY working_date, lot_no"
        )

        print(f" SQL Query: {sql}")
        print(f" Parametros: {tuple(params) if params else 'Sin parametros'}")

        rows = execute_query(sql, tuple(params) if params else None, fetch="all")

        data = []
        for r in rows:
            data.append(
                {
                    "lot_no": r["lot_no"] if isinstance(r, dict) else r[0],
                    "working_date": str(
                        (r["working_date"] if isinstance(r, dict) else r[1]) or ""
                    )[:10],
                    "part_no": r["part_no"] if isinstance(r, dict) else r[2],
                    "line": r["line"] if isinstance(r, dict) else r[3],
                    "plan_count": r["plan_count"] if isinstance(r, dict) else r[4],
                    "input": r["input"] if isinstance(r, dict) else r[5],
                    "status": r["status"] if isinstance(r, dict) else r[6],
                }
            )

        print(f" Planes pendientes encontrados: {len(data)}")
        return jsonify(data)

    except Exception as e:
        print(f" Error en api_plan_pending: {str(e)}")
        return jsonify({"error": str(e)}), 500


@bp.route("/api/plan/reschedule", methods=["POST"])
@login_requerido
def api_plan_reschedule():
    """Reprogramar planes pendientes creando NUEVOS planes con la cantidad restante.

    NO modifica el plan original, sino que crea un nuevo registro con:
    - Mismo lot_no, part_no
    - Nueva working_date
    - plan_count = plan_count_original - produced_count (cantidad pendiente)
    """
    try:
        data = request.get_json() or {}
        lot_nos = data.get("lot_nos", [])
        new_date = data.get("new_working_date")

        if not (lot_nos and new_date):
            return jsonify({"error": "Parametros requeridos"}), 400

        placeholders = ",".join(["%s"] * len(lot_nos))
        sql_select = f"""
            SELECT lot_no, wo_id, wo_code, po_code, working_date, line, model_code,
                   part_no, project, process, plan_count, produced_count, ct, uph, routing,
                   status, group_no, sequence
            FROM plan_main
            WHERE lot_no IN ({placeholders})
        """
        print(f" Buscando {len(lot_nos)} planes para reprogramar")
        planes_originales = execute_query(sql_select, tuple(lot_nos), fetch="all")

        if not planes_originales:
            print(f" No se encontraron planes para los lot_nos: {lot_nos}")
            return jsonify({"error": "No se encontraron planes para reprogramar"}), 404

        print(f" Se encontraron {len(planes_originales)} planes")
        nuevos_planes_creados = 0

        for plan in planes_originales:
            lot_no_original = plan["lot_no"]
            plan_count_original = plan["plan_count"] or 0
            produced_count = plan["produced_count"] or 0

            cantidad_pendiente = plan_count_original - produced_count

            print(
                f"Plan {lot_no_original}: plan_count={plan_count_original}, produced={produced_count}, pendiente={cantidad_pendiente}"
            )

            if cantidad_pendiente <= 0:
                print(f"Saltando {lot_no_original} - no hay cantidad pendiente")
                continue

            # Generar NUEVO LOT_NO manteniendo trazabilidad del lote original
            if lot_no_original.count("-") >= 3:
                parts = lot_no_original.rsplit("-", 1)
                lot_no_base = parts[0]
            else:
                lot_no_base = lot_no_original

            sql_count = """
                SELECT COUNT(*) as count
                FROM plan_main
                WHERE lot_no LIKE %s AND lot_no <> %s
            """
            pattern = f"{lot_no_base}-%"
            result = execute_query(sql_count, (pattern, lot_no_base), fetch="one")
            count = result["count"] if result else 0
            next_seq = count + 1

            nuevo_lot_no = f"{lot_no_base}-{next_seq:02d}"
            print(
                f"Nuevo lot_no generado: {nuevo_lot_no} (reprogramacion #{next_seq} de {lot_no_base})"
            )

            sql_insert = """
                INSERT INTO plan_main
                (lot_no, wo_id, wo_code, po_code, working_date, line, model_code,
                 part_no, project, process, plan_count, ct, uph, routing, status,
                 group_no, sequence, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """

            print(
                f"Creando nuevo plan {nuevo_lot_no} con {cantidad_pendiente} unidades para {new_date}"
            )

            execute_query(
                sql_insert,
                (
                    nuevo_lot_no,
                    plan.get("wo_id"),
                    plan.get("wo_code"),
                    plan.get("po_code"),
                    new_date,
                    plan.get("line"),
                    plan.get("model_code"),
                    plan.get("part_no"),
                    plan.get("project"),
                    plan.get("process"),
                    cantidad_pendiente,
                    plan.get("ct"),
                    plan.get("uph"),
                    plan.get("routing"),
                    "PLAN",
                    plan.get("group_no"),
                    plan.get("sequence"),
                ),
            )

            print(
                f"Nuevo plan creado: {nuevo_lot_no} (trazabilidad: {lot_no_original} -> {nuevo_lot_no})"
            )

            execute_query(
                "UPDATE plan_main SET plan_count = %s, status = 'TERMINADO', updated_at = NOW() WHERE lot_no = %s",
                (produced_count, lot_no_original),
            )
            print(
                f"Plan original {lot_no_original} actualizado: plan_count={produced_count}, status=TERMINADO"
            )

            nuevos_planes_creados += 1

        print(f"Total de planes creados: {nuevos_planes_creados}")
        return jsonify(
            {
                "success": True,
                "created": nuevos_planes_creados,
                "message": f"{nuevos_planes_creados} nuevo(s) plan(es) creado(s) para {new_date}",
            }
        )

    except Exception as e:
        print(f" Error en api_plan_reschedule: {str(e)}")
        import traceback

        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@bp.route("/api/plan/export-excel", methods=["POST"])
@login_requerido
def api_plan_export_excel():
    try:
        payload = request.get_json() or {}
        plans = payload.get("plans", [])
        if not plans:
            return jsonify({"error": "No hay datos para exportar"}), 400

        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font

        wb = Workbook()
        ws = wb.active
        ws.title = "Plan Produccion"
        headers = [
            "Sec",
            "LOT NO",
            "WO",
            "PO",
            "Fecha",
            "Linea",
            "Turno",
            "Modelo",
            "Part No",
            "Proyecto",
            "Proceso",
            "CT",
            "UPH",
            "Plan",
            "Producido",
            "Status",
            "Tiempo",
            "Inicio",
            "Fin",
            "Grupo",
            "Extra",
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
                    p.get("turno", ""),
                    p.get("model_code", ""),
                    p.get("part_no", ""),
                    p.get("project", ""),
                    p.get("process", ""),
                    p.get("ct", ""),
                    p.get("uph", ""),
                    p.get("plan_count", ""),
                    p.get("produced", ""),
                    p.get("status", ""),
                    p.get("tiempo_produccion", ""),
                    p.get("inicio", ""),
                    p.get("fin", ""),
                    p.get("grupo", ""),
                    p.get("extra", ""),
                ]
            )
        bio = io.BytesIO()
        wb.save(bio)
        bio.seek(0)
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M")
        return send_file(
            bio,
            as_attachment=True,
            download_name=f"Plan_Produccion_{ts}.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/plan-main/list", methods=["GET"])
@login_requerido
def api_plan_main_list():
    try:
        _ensure_plan_bom_assignment_columns()
        q = request.args.get("q", "").strip()
        linea = request.args.get("linea")
        desde = request.args.get("desde")
        hasta = request.args.get("hasta")
        solo_pendientes = request.args.get("solo_pendientes") == "true"
        where = []
        params = []
        if q:
            where.append("(lot_no LIKE %s OR part_no LIKE %s OR model_code LIKE %s)")
            qv = f"%{q}%"
            params.extend([qv, qv, qv])
        if linea and linea not in ("Todos", "ALL"):
            where.append("line = %s")
            params.append(linea)
        if desde:
            where.append("DATE(working_date) >= %s")
            params.append(desde)
        if hasta:
            where.append("DATE(working_date) <= %s")
            params.append(hasta)
        if solo_pendientes:
            where.append("status = 'PLAN'")
        sql = (
            "SELECT id, lot_no, part_no, model_code, line, working_date, COALESCE(plan_count,0) AS qty, COALESCE(produced_count,0) AS producido, "
            "GREATEST(COALESCE(plan_count,0)-COALESCE(produced_count,0),0) AS falta, COALESCE(ct,0) AS ct, COALESCE(uph,0) AS uph, status, process, "
            "assigned_bom_rev, assigned_bom_rev_by, assigned_bom_rev_at "
            "FROM plan_main"
        )
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY working_date DESC, created_at DESC"
        rows = execute_query(sql, tuple(params) if params else None, fetch="all")
        out = []
        for r in rows:
            qty = r["qty"] if isinstance(r, dict) else r[6]
            producido = (
                r["produced_count"]
                if isinstance(r, dict) and "produced_count" in r
                else (r["producido"] if isinstance(r, dict) else r[7])
            )
            pct = int(round((producido / qty) * 100, 0)) if qty else 0
            out.append(
                {
                    "id": r["id"] if isinstance(r, dict) else r[0],
                    "lote": r["lot_no"] if isinstance(r, dict) else r[1],
                    "nparte": r["part_no"] if isinstance(r, dict) else r[2],
                    "modelo": r["model_code"] if isinstance(r, dict) else r[3],
                    "linea": r["line"] if isinstance(r, dict) else r[4],
                    "fecha_inicio": str(
                        (r["working_date"] if isinstance(r, dict) else r[5]) or ""
                    )[:10],
                    "qty": qty,
                    "producido": producido,
                    "falta": max(0, qty - producido),
                    "ct": r["ct"] if isinstance(r, dict) else r[9],
                    "uph": r["uph"] if isinstance(r, dict) else r[10],
                    "estatus": r["status"] if isinstance(r, dict) else r[11],
                    "process": r["process"] if isinstance(r, dict) else r[12],
                    "assigned_bom_rev": r["assigned_bom_rev"] if isinstance(r, dict) else r[13],
                    "assigned_bom_rev_by": r["assigned_bom_rev_by"] if isinstance(r, dict) else r[14],
                    "assigned_bom_rev_at": str(
                        (r["assigned_bom_rev_at"] if isinstance(r, dict) else r[15]) or ""
                    ),
                }
            )
        return jsonify(out)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# Fase 4 (2026-05-28): /importar_excel_plan_produccion migrado desde routes.py.
# Importa work orders desde un Excel con columnas (linea, modelo, numero_parte,
# cantidad, fecha_operacion, codigo_po). Crea registros en work_orders con
# codigo_wo auto-generado por dia (WO-YYMMDD-NNNN).
# ---------------------------------------------------------------------------


@bp.route("/importar_excel_plan_produccion", methods=["POST"])
@login_requerido
def importar_excel_plan_produccion():
    """Importar plan de produccion desde Excel"""
    conn = None
    cursor = None
    temp_path = None

    try:
        if "file" not in request.files:
            return jsonify(
                {"success": False, "error": "No se proporciono archivo"}
            ), 400

        file = request.files["file"]
        if file.filename == "":
            return jsonify({"success": False, "error": "No se selecciono archivo"}), 400

        if (
            not file
            or not file.filename
            or not file.filename.lower().endswith((".xlsx", ".xls"))
        ):
            return jsonify(
                {
                    "success": False,
                    "error": "Formato de archivo no valido. Use .xlsx o .xls",
                }
            ), 400

        # Guardar el archivo temporalmente (junto al modulo, como en el legacy)
        filename = secure_filename(file.filename)
        temp_path = os.path.join(os.path.dirname(__file__), "temp_" + filename)
        file.save(temp_path)

        # Leer el archivo Excel
        try:
            df = pd.read_excel(
                temp_path, engine="openpyxl" if filename.endswith(".xlsx") else "xlrd"
            )

            # Si las primeras filas contienen datos directamente (sin encabezados claros)
            # y las columnas tienen nombres genericos como 0, 1, 2, etc.
            if all(isinstance(col, int) for col in df.columns):
                df = pd.read_excel(
                    temp_path,
                    header=None,
                    engine="openpyxl" if filename.endswith(".xlsx") else "xlrd",
                )
                if len(df.columns) >= 3:
                    df.columns = ["Modelo", "Numero_Parte", "Cantidad"] + [
                        f"Col_{i}" for i in range(3, len(df.columns))
                    ]
                elif len(df.columns) == 2:
                    df.columns = ["Modelo", "Cantidad"]
                else:
                    df.columns = ["Modelo"]
        except Exception as e:
            try:
                df = pd.read_excel(temp_path, header=None)
                if len(df.columns) >= 3:
                    df.columns = ["Modelo", "Numero_Parte", "Cantidad"] + [
                        f"Col_{i}" for i in range(3, len(df.columns))
                    ]
                elif len(df.columns) == 2:
                    df.columns = ["Modelo", "Cantidad"]
                else:
                    df.columns = ["Modelo"]
            except Exception as e2:
                return jsonify(
                    {
                        "success": False,
                        "error": f"Error al leer el archivo Excel: {str(e2)}",
                    }
                ), 500

        if df.empty:
            return jsonify(
                {"success": False, "error": "El archivo Excel esta vacio"}
            ), 400

        usuario_actual = session.get("usuario", "USUARIO_EXCEL")

        fecha_operacion_usuario = request.form.get("fecha_operacion", "").strip()
        if fecha_operacion_usuario:
            print(
                f" Fecha de operacion personalizada seleccionada: {fecha_operacion_usuario}"
            )
        else:
            print(" Usando fechas del Excel o fecha actual como respaldo")

        def obtener_nombre_modelo(codigo_modelo):
            """Obtener nombre (project) desde raw por part_no"""
            try:
                if not codigo_modelo:
                    return ""
                cursor.execute(
                    "SELECT project FROM raw WHERE TRIM(part_no)=TRIM(%s) ORDER BY id DESC LIMIT 1",
                    (codigo_modelo,),
                )
                row = cursor.fetchone()
                return (row.get("project") if row else "") or ""
            except Exception as e:
                print(f"Error obteniendo nombre modelo para {codigo_modelo}: {e}")
                return ""

        conn = get_db_connection()
        cursor = conn.cursor()

        # Asegurar que la tabla work_orders tenga la columna linea
        try:
            cursor.execute("SHOW COLUMNS FROM work_orders LIKE 'linea'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE work_orders ADD COLUMN linea VARCHAR(32)")
                print(" Columna 'linea' agregada a work_orders")
        except Exception as e:
            print(f"Error agregando columna linea: {e}")

        registros_insertados = 0
        registros_actualizados = 0
        errores = []

        # Mapeo de columnas (flexible para diferentes nombres)
        mapeo_columnas = {
            "linea": ["Linea", "linea", "Line", "LINEA", "Linea"],
            "modelo": ["Modelo", "modelo", "Model", "MODELO"],
            "numero_parte": [
                "Numero de parte",
                "Numero de parte",
                "numero_parte",
                "Part Number",
                "NUMERO_PARTE",
                "Numero_Parte",
            ],
            "cantidad": ["Cantidad", "cantidad", "Quantity", "CANTIDAD"],
            "fecha_operacion": [
                "Fecha",
                "fecha_operacion",
                "Fecha de operacion",
                "Date",
                "FECHA",
            ],
            "codigo_po": [
                "PO",
                "codigo_po",
                "Codigo PO",
                "Purchase Order",
                "CODIGO_PO",
            ],
        }

        print(f"Columnas en el DataFrame: {list(df.columns)}")
        print(f"Primeras 3 filas del DataFrame:")
        print(df.head(3))

        columnas_detectadas = {}
        for campo, posibles_nombres in mapeo_columnas.items():
            for nombre in posibles_nombres:
                if nombre in df.columns:
                    columnas_detectadas[campo] = nombre
                    break

        print(f"Columnas detectadas: {columnas_detectadas}")

        if "modelo" not in columnas_detectadas or "cantidad" not in columnas_detectadas:
            error_msg = (
                f"El archivo debe contener al menos las columnas: Modelo y Cantidad. "
            )
            error_msg += f"Columnas encontradas: {list(df.columns)}. "
            error_msg += f"Mapeo detectado: {columnas_detectadas}"

            return jsonify({"success": False, "error": error_msg}), 400

        for index, row in df.iterrows():
            try:
                modelo = str(row.get(columnas_detectadas["modelo"], "")).strip()
                cantidad = row.get(columnas_detectadas["cantidad"], 0)

                if not modelo or modelo == "nan":
                    errores.append(f"Fila {index + 2}: Modelo vacio")
                    continue

                try:
                    cantidad = (
                        int(float(cantidad))
                        if cantidad and str(cantidad) != "nan"
                        else 0
                    )
                except (ValueError, TypeError):
                    cantidad = 0

                if cantidad <= 0:
                    errores.append(f"Fila {index + 2}: Cantidad invalida ({cantidad})")
                    continue

                linea = str(row.get(columnas_detectadas.get("linea", ""), "")).strip()
                if linea == "nan":
                    linea = ""

                numero_parte = str(
                    row.get(columnas_detectadas.get("numero_parte", ""), "")
                ).strip()
                if numero_parte == "nan":
                    numero_parte = ""

                codigo_po = str(
                    row.get(columnas_detectadas.get("codigo_po", ""), "SIN-PO")
                ).strip()
                if codigo_po == "nan" or not codigo_po:
                    codigo_po = "SIN-PO"

                fecha_operacion_usuario = request.form.get(
                    "fecha_operacion", ""
                ).strip()

                if fecha_operacion_usuario:
                    fecha_operacion = fecha_operacion_usuario
                else:
                    fecha_operacion = row.get(
                        columnas_detectadas.get("fecha_operacion", ""), ""
                    )
                    if pd.isna(fecha_operacion) or fecha_operacion == "nan":
                        fecha_operacion = datetime.now().strftime("%Y-%m-%d")
                    else:
                        try:
                            if isinstance(fecha_operacion, str):
                                from dateutil import parser

                                fecha_operacion = parser.parse(
                                    fecha_operacion
                                ).strftime("%Y-%m-%d")
                            else:
                                fecha_operacion = fecha_operacion.strftime("%Y-%m-%d")
                        except:
                            fecha_operacion = datetime.now().strftime("%Y-%m-%d")

                fecha_codigo = datetime.now().strftime("%y%m%d")

                cursor.execute(
                    """
                    SELECT codigo_wo FROM work_orders
                    WHERE codigo_wo LIKE %s
                    ORDER BY codigo_wo DESC LIMIT 1
                """,
                    (f"WO-{fecha_codigo}-%",),
                )

                ultimo_wo = cursor.fetchone()
                if ultimo_wo:
                    try:
                        ultimo_numero = int(ultimo_wo["codigo_wo"].split("-")[-1])
                        nuevo_numero = ultimo_numero + 1
                    except:
                        nuevo_numero = 1
                else:
                    nuevo_numero = 1

                codigo_wo = f"WO-{fecha_codigo}-{nuevo_numero:04d}"

                codigo_modelo = modelo
                nombre_modelo = obtener_nombre_modelo(codigo_modelo)

                cursor.execute(
                    """
                    INSERT INTO work_orders
                    (codigo_wo, codigo_po, modelo, codigo_modelo, nombre_modelo, linea,
                     cantidad_planeada, fecha_operacion, usuario_creacion, modificador, estado)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'CREADA')
                """,
                    (
                        codigo_wo,
                        codigo_po,
                        modelo
                        if modelo
                        else numero_parte,
                        codigo_modelo,
                        nombre_modelo,
                        linea,
                        cantidad,
                        fecha_operacion,
                        usuario_actual,
                        usuario_actual,
                    ),
                )

                registros_insertados += 1

            except Exception as e:
                errores.append(f"Fila {index + 2}: {str(e)}")
                continue

        conn.commit()

        mensaje = f"Importacion completada. {registros_insertados} WOs creadas."
        if fecha_operacion_usuario:
            mensaje += f" Fecha de operacion aplicada: {fecha_operacion_usuario}."
        if errores:
            mensaje += f" {len(errores)} errores encontrados."

        return jsonify(
            {
                "success": True,
                "message": mensaje,
                "registros_procesados": registros_insertados,
                "errores": len(errores),
                "fecha_aplicada": fecha_operacion_usuario or "Fechas del Excel/Actual",
                "detalles": {
                    "insertados": registros_insertados,
                    "errores": errores[:10]
                    if errores
                    else [],
                },
            }
        )

    except Exception as e:
        print(f"Error general en importar_excel_plan_produccion: {str(e)}")
        return jsonify({"success": False, "error": f"Error interno: {str(e)}"}), 500

    finally:
        try:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception as e:
            print(f"Error en cleanup: {str(e)}")
