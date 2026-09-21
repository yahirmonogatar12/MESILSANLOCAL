"""API del modulo Control de Scrap (tabla scrap_records).

Los registros los capturan las apps de escaneo (Control_produccion, ControlIMD,
Control_inventario_SMD). Aqui se consultan, se corrige cantidad/motivo/
ubicacion/comentarios y se exportan. Cada edicion queda en scrap_record_edits,
igual que en Control_produccion.

Rutas:
  GET  /api/control-scrap                -> listar (start, end, area, cf_<columna>)
  GET  /api/control-scrap/motivos        -> motivos activos
  POST /api/control-scrap/update         -> editar un registro (con auditoria)
  GET  /api/control-scrap/export         -> Excel con los mismos filtros
"""

import logging
from datetime import datetime

from flask import Blueprint, jsonify, request, session

from app.api.shared import (
    conexion_o_error,
    dict_cursor,
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


@bp.route("/api/control-scrap/motivos", methods=["GET"])
@login_requerido
@_requiere_permiso_scrap
def api_control_scrap_motivos():
    try:
        rows = execute_query(
            "SELECT id, motivo FROM scrap_motivos WHERE activo = 1 ORDER BY motivo",
            fetch="all",
        ) or []
        return jsonify({"success": True, "data": rows})
    except Exception as e:
        logger.error(f"Error listando motivos de scrap: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/api/control-scrap/update", methods=["POST"])
@login_requerido
@_requiere_permiso_scrap
def api_control_scrap_update():
    data = request.get_json(silent=True) or {}
    try:
        record_id = int(data.get("id"))
        cantidad = int(data.get("cantidad"))
        motivo_id = int(data.get("motivo_scrap_id"))
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "id, cantidad y motivo son requeridos"}), 400
    if cantidad < 0:
        return jsonify({"success": False, "error": "La cantidad no puede ser negativa"}), 400
    edit_reason = (data.get("edit_reason") or "").strip()
    if not edit_reason:
        return jsonify({"success": False, "error": "El motivo de la edicion es requerido"}), 400
    ubicacion = (data.get("ubicacion") or "").strip()[:100] or None
    comentarios = (data.get("comentarios") or "").strip() or None
    editor = session.get("nombre_completo") or session.get("usuario") or "desconocido"

    conn, err = conexion_o_error()
    if err:
        return err
    cur = dict_cursor(conn)
    try:
        conn.begin()  # el pool usa autocommit; UPDATE + auditoria van juntos
        cur.execute("SELECT * FROM scrap_records WHERE id = %s FOR UPDATE", (record_id,))
        actual = cur.fetchone()
        if not actual:
            conn.rollback()
            return jsonify({"success": False, "error": "Registro no encontrado"}), 404

        # Se acepta el motivo actual aunque ya este inactivo (registros de sistema).
        cur.execute("SELECT motivo, activo FROM scrap_motivos WHERE id = %s", (motivo_id,))
        motivo = cur.fetchone()
        if not motivo or (not motivo["activo"] and motivo_id != actual["motivo_scrap_id"]):
            conn.rollback()
            return jsonify({"success": False, "error": "Motivo no encontrado o inactivo"}), 400

        cur.execute(
            "UPDATE scrap_records SET cantidad = %s, motivo_scrap_id = %s, "
            "motivo_scrap_texto = %s, ubicacion = %s, comentarios = %s WHERE id = %s",
            (cantidad, motivo_id, motivo["motivo"], ubicacion, comentarios, record_id),
        )
        # Mismo formato de auditoria que Control_produccion (campos no editables: old = new).
        cur.execute(
            "INSERT INTO scrap_record_edits (scrap_record_id, "
            "old_scanned_original, new_scanned_original, "
            "old_scanned_original_norm, new_scanned_original_norm, "
            "old_assy_type, new_assy_type, old_part_no, new_part_no, "
            "old_raw_barcode, new_raw_barcode, old_modelo, new_modelo, "
            "old_area, new_area, old_proceso, new_proceso, "
            "old_motivo_scrap_id, new_motivo_scrap_id, "
            "old_motivo_scrap_texto, new_motivo_scrap_texto, "
            "old_comentarios, new_comentarios, old_cantidad, new_cantidad, "
            "edit_reason, edited_by_user_id, edited_by_name, edited_at) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                record_id,
                actual["scanned_original"], actual["scanned_original"],
                actual["scanned_original_norm"], actual["scanned_original_norm"],
                actual["assy_type"], actual["assy_type"],
                actual["part_no"], actual["part_no"],
                actual["raw_barcode"], actual["raw_barcode"],
                actual["modelo"], actual["modelo"],
                actual["area"], actual["area"],
                actual["proceso"], actual["proceso"],
                actual["motivo_scrap_id"], motivo_id,
                actual["motivo_scrap_texto"], motivo["motivo"],
                actual["comentarios"], comentarios,
                actual["cantidad"], cantidad,
                edit_reason, None, editor[:100], obtener_fecha_hora_mexico(),
            ),
        )
        conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        conn.rollback()
        logger.error(f"Error editando scrap {record_id}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cur.close()
        conn.close()


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
