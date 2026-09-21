"""API de Historial de operacion por proceso (Control de proceso).

Une los planes de SMT (plan_smt), IMT (plan_imd) y ASSY (plan_main) por
working_date: plan, WO, lote, input y output.
  - Input  = produced_count (piezas escaneadas en la linea).
  - Output = output solo en ASSY; SMT e IMT son puro input -> "N/A".

Rutas:
  GET /api/historial-operacion-proceso          -> listar (start, end, proceso, cf_<columna>)
  GET /api/historial-operacion-proceso/export   -> Excel con los mismos filtros
"""

import logging
from datetime import datetime

from flask import Blueprint, jsonify, request

from app.api.shared import (
    excel_response,
    execute_query,
    login_requerido,
    obtener_fecha_hora_mexico,
    requiere_permiso_dropdown,
    sanitizar_texto,
)

logger = logging.getLogger(__name__)

bp = Blueprint("control_proceso_historial_operacion_proceso", __name__)

_requiere_permiso = requiere_permiso_dropdown(
    "LISTA_CONTROL_DE_PROCESO", "Control de produccion", "Historial de operacion por proceso"
)

# Mismos nombres de linea que muestran Plan SMT / Plan IMT.
_LINEA_SMT = (
    "CASE line WHEN 'SA' THEN 'SMT A' WHEN 'SB' THEN 'SMT B' WHEN 'SC' THEN 'SMT C' "
    "WHEN 'SD' THEN 'SMT D' WHEN 'SE' THEN 'SMT E' ELSE line END"
)
_LINEA_IMT = (
    "CASE line WHEN 'P1' THEN 'PANA A' WHEN 'P2' THEN 'PANA B' "
    "WHEN 'P3' THEN 'PANA C' WHEN 'P4' THEN 'PANA D' ELSE line END"
)

# proceso -> (tabla, expresion de linea, expresion de output)
_PROCESOS = {
    "SMT": ("plan_smt", _LINEA_SMT, "NULL"),
    "IMT": ("plan_imd", _LINEA_IMT, "NULL"),
    "ASSY": ("plan_main", "line", "COALESCE(output, 0)"),
}

# Filtros por encabezado (cf_<campo>) sobre las columnas ya unidas.
_COLUMN_FILTER_SQL = {
    "fecha": "fecha LIKE %s",
    "linea": "COALESCE(linea, '') LIKE %s",
    "wo": "COALESCE(wo, '') LIKE %s",
    "lote": "COALESCE(lote, '') LIKE %s",
    "part_no": "COALESCE(part_no, '') LIKE %s",
    "modelo": "COALESCE(modelo, '') LIKE %s",
    "plan": "CAST(plan_count AS CHAR) LIKE %s",
    "input": "CAST(input_count AS CHAR) LIKE %s",
    "output": "CAST(output_count AS CHAR) LIKE %s",
    "status": "COALESCE(status, '') LIKE %s",
}


def _consulta():
    """SQL + params desde start/end (YYYY-MM-DD), proceso y cf_*. Default: hoy."""
    hoy = obtener_fecha_hora_mexico().strftime("%Y-%m-%d")
    start = request.args.get("start") or hoy
    end = request.args.get("end") or start
    for valor in (start, end):
        datetime.strptime(valor, "%Y-%m-%d")  # ValueError -> 400
    proceso = (request.args.get("proceso") or "").strip().upper()
    procesos = [proceso] if proceso in _PROCESOS else list(_PROCESOS)

    ramas, params = [], []
    for nombre in procesos:
        tabla, linea, output = _PROCESOS[nombre]
        # El filtro de fecha va dentro de cada rama para usar idx_working_date.
        ramas.append(
            f"SELECT '{nombre}' AS proceso, DATE_FORMAT(working_date, '%%Y-%%m-%%d') AS fecha, "
            f"{linea} AS linea, wo_code AS wo, lot_no AS lote, part_no, model_code AS modelo, "
            "COALESCE(plan_count, 0) AS plan_count, COALESCE(produced_count, 0) AS input_count, "
            f"{output} AS output_count, status "
            f"FROM {tabla} WHERE working_date BETWEEN %s AND %s"
        )
        params += [start, end]

    where = []
    for campo, clausula in _COLUMN_FILTER_SQL.items():
        valor = sanitizar_texto(request.args.get(f"cf_{campo}"), 128)
        if valor:
            where.append(clausula)
            params.append(f"%{valor}%")

    sql = "SELECT * FROM (" + " UNION ALL ".join(ramas) + ") p"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY fecha DESC, FIELD(proceso, 'SMT', 'IMT', 'ASSY'), linea, lote LIMIT 5000"
    return sql, params


def _registros():
    sql, params = _consulta()
    rows = execute_query(sql, tuple(params), fetch="all") or []
    for r in rows:
        if r["output_count"] is None:
            r["output_count"] = "N/A"  # SMT / IMT: puro input
    return rows


@bp.route("/api/historial-operacion-proceso", methods=["GET"])
@login_requerido
@_requiere_permiso
def api_historial_operacion_proceso():
    try:
        return jsonify({"success": True, "data": _registros()})
    except ValueError:
        return jsonify({"success": False, "error": "Fecha invalida (YYYY-MM-DD)"}), 400
    except Exception as e:
        logger.error(f"Error en historial de operacion por proceso: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/api/historial-operacion-proceso/export", methods=["GET"])
@login_requerido
@_requiere_permiso
def api_historial_operacion_proceso_export():
    try:
        rows = _registros()
    except ValueError:
        return jsonify({"success": False, "error": "Fecha invalida (YYYY-MM-DD)"}), 400
    columnas = [
        ("Proceso", "proceso", 10), ("Fecha", "fecha", 12), ("Linea", "linea", 12),
        ("WO", "wo", 18), ("Lote", "lote", 24), ("Part No", "part_no", 16),
        ("Modelo", "modelo", 16), ("Plan", "plan_count", 10), ("Input", "input_count", 10),
        ("Output", "output_count", 10), ("Status", "status", 14),
    ]
    headers, keys, widths = zip(*columnas)
    return excel_response(
        rows, headers, keys, widths, "Operacion por proceso",
        f"Historial_Operacion_Proceso_{obtener_fecha_hora_mexico():%Y%m%d_%H%M}", freeze="A2",
    )
