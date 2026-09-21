"""API del modulo Control de Scrap (tabla scrap_records).

Los registros los capturan las apps de escaneo (Control_produccion, ControlIMD,
Control_inventario_SMD). Aqui solo se consultan y se exportan (sin edicion).

Rutas:
  GET  /api/control-scrap                -> listar (start, end, area, cf_<columna>)
  GET  /api/control-scrap/export         -> Excel con los mismos filtros
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

bp = Blueprint("control_proceso_control_scrap", __name__)

_requiere_permiso_scrap = requiere_permiso_dropdown(
    "LISTA_CONTROL_DE_PROCESO", "Control de material Scrap", "Control de Scrap"
)

_COLUMNAS = (
    "id, scanned_original, cliente, assy_type, part_no, raw_barcode, modelo, area, "
    "proceso, ubicacion, motivo_scrap_id, motivo_scrap_texto, comentarios, "
    "usuario_registro, cantidad, "
    "DATE_FORMAT(fecha_registro, '%%Y-%%m-%%d') AS fecha, "
    "DATE_FORMAT(fecha_registro, '%%H:%%i:%%s') AS hora"
)


# Filtros por encabezado de tabla (cf_<campo>), mismo patron que Historial de input.
_COLUMN_FILTER_SQL = {
    "cliente": "COALESCE(cliente, '') LIKE %s",
    "fecha": "CAST(DATE(fecha_registro) AS CHAR) LIKE %s",
    "hora": "CAST(TIME(fecha_registro) AS CHAR) LIKE %s",
    "codigo": "scanned_original LIKE %s",
    "part_no": "COALESCE(part_no, '') LIKE %s",
    "modelo": "COALESCE(modelo, '') LIKE %s",
    "area": "COALESCE(area, '') LIKE %s",
    "proceso": "COALESCE(proceso, '') LIKE %s",
    "motivo": "COALESCE(motivo_scrap_texto, '') LIKE %s",
    "cantidad": "CAST(cantidad AS CHAR) LIKE %s",
    "comentarios": "COALESCE(comentarios, '') LIKE %s",
    "usuario": "COALESCE(usuario_registro, '') LIKE %s",
}


def _filtros():
    """WHERE + params desde start/end (YYYY-MM-DD), area y cf_*. Default: hoy."""
    hoy = obtener_fecha_hora_mexico().strftime("%Y-%m-%d")
    start = request.args.get("start") or hoy
    end = request.args.get("end") or start
    for valor in (start, end):
        datetime.strptime(valor, "%Y-%m-%d")  # ValueError -> 400
    # Rango semiabierto para usar idx_fecha (DATE(col) no usa indice).
    where = ["fecha_registro >= %s", "fecha_registro < DATE_ADD(%s, INTERVAL 1 DAY)"]
    params = [start, end]
    area = (request.args.get("area") or "").strip()
    if area:
        where.append("area = %s")
        params.append(area)
    for campo, clausula in _COLUMN_FILTER_SQL.items():
        valor = sanitizar_texto(request.args.get(f"cf_{campo}"), 128)
        if valor:
            where.append(clausula)
            params.append(f"%{valor}%")
    return " WHERE " + " AND ".join(where), params


def _registros():
    where, params = _filtros()
    sql = f"SELECT {_COLUMNAS} FROM scrap_records{where} ORDER BY fecha_registro DESC, id DESC LIMIT 5000"
    return execute_query(sql, tuple(params), fetch="all") or []


@bp.route("/api/control-scrap", methods=["GET"])
@login_requerido
@_requiere_permiso_scrap
def api_control_scrap_list():
    try:
        return jsonify({"success": True, "data": _registros()})
    except ValueError:
        return jsonify({"success": False, "error": "Fecha invalida (YYYY-MM-DD)"}), 400
    except Exception as e:
        logger.error(f"Error listando scrap: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/api/control-scrap/export", methods=["GET"])
@login_requerido
@_requiere_permiso_scrap
def api_control_scrap_export():
    try:
        rows = _registros()
    except ValueError:
        return jsonify({"success": False, "error": "Fecha invalida (YYYY-MM-DD)"}), 400
    columnas = [
        ("Cliente", "cliente", 14), ("Fecha", "fecha", 12), ("Hora", "hora", 10),
        ("Codigo", "scanned_original", 34),
        ("Part No", "part_no", 16), ("Modelo", "modelo", 16), ("Area", "area", 14),
        ("Proceso", "proceso", 12),
        ("Motivo", "motivo_scrap_texto", 28), ("Cantidad", "cantidad", 10),
        ("Comentarios", "comentarios", 40), ("Usuario", "usuario_registro", 24),
    ]
    headers, keys, widths = zip(*columnas)
    return excel_response(
        rows, headers, keys, widths, "Scrap",
        f"Control_Scrap_{obtener_fecha_hora_mexico():%Y%m%d_%H%M}", freeze="A2",
    )
