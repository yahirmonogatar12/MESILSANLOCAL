"""CRUD de estaciones/maquinas de calidad en `stations_qa`.

WF_001: opcion en LISTA_CONTROL_DE_CALIDAD / Control de maquinas.
WF_002: template AJAX en Control de calidad/stations_qa_ajax.html.
WF_003: blueprint dueno de render y APIs JSON.
WF_004: CSS persistente en MainTemplate.html y asegurado desde JS.
"""

import logging
from datetime import datetime

from flask import Blueprint, jsonify, render_template, request

from app.api.shared import (
    conexion_o_error,
    dict_cursor,
    excel_response,
    formatear_fecha_hora,
    login_requerido,
    parsear_booleano,
    requiere_permiso_dropdown,
    sanitizar_texto,
)

logger = logging.getLogger(__name__)

bp = Blueprint("stations_qa", __name__)

PERMISO_MODULO = (
    "LISTA_CONTROL_DE_CALIDAD",
    "Control de maquinas",
    "Control de maquinas de calidad",
)
STATION_TYPES = {"ICT", "FCT", "Packing"}


# Aliases locales de los helpers compartidos (app/api/shared/request_helpers.py,
# db_helpers.py y datetime_helpers.py); aqui vivian las copias originales.
_dict_cursor = dict_cursor
_connection_or_response = conexion_o_error
_text = sanitizar_texto
_bool = parsear_booleano
_serialize_datetime = formatear_fecha_hora


def _station_to_json(row):
    return {
        "id": int(row.get("id") or 0),
        "station_code": row.get("station_code") or "",
        "station_name": row.get("station_name") or "",
        "station_type": row.get("station_type") or "",
        "host_name": row.get("host_name") or "",
        "is_active": bool(row.get("is_active")),
        "created_at_utc": _serialize_datetime(row.get("created_at_utc")),
        "updated_at_utc": _serialize_datetime(row.get("updated_at_utc")),
    }


def _payload():
    data = request.get_json(silent=True) or {}
    station_code = _text(data.get("station_code"), 32)
    station_name = _text(data.get("station_name"), 128)
    station_type = _text(data.get("station_type"), 16)
    host_name = _text(data.get("host_name"), 128)
    is_active = _bool(data.get("is_active"), True)

    errors = []
    if not station_code:
        errors.append("El codigo de estacion es requerido.")
    if not station_name:
        errors.append("El nombre de estacion es requerido.")
    if station_type not in STATION_TYPES:
        errors.append("El tipo de estacion debe ser ICT, FCT o Packing.")

    return {
        "station_code": station_code,
        "station_name": station_name,
        "station_type": station_type,
        "host_name": host_name,
        "is_active": 1 if is_active else 0,
    }, errors


def _is_duplicate_error(exc):
    args = getattr(exc, "args", ()) or ()
    code = args[0] if args else None
    message = str(exc)
    return code == 1062 or "Duplicate entry" in message or "uq_stqa_code" in message


def _fetch_station(cursor, station_id):
    cursor.execute(
        """
        SELECT id, station_code, station_name, station_type, host_name,
               is_active, created_at_utc, updated_at_utc
        FROM stations_qa
        WHERE id = %s
        LIMIT 1
        """,
        (station_id,),
    )
    return cursor.fetchone()


def _code_exists(cursor, station_code, host_name, exclude_id=None):
    """Duplicado = mismo codigo EN LA MISMA LINEA (host_name).

    El mismo codigo puede repetirse en lineas distintas; coincide con el
    diseno de QualityLock.Api (StationRepository busca por codigo+linea).
    Requiere el indice compuesto uq_stqa_code_linea (station_code, host_name).
    """
    sql = "SELECT id FROM stations_qa WHERE station_code = %s AND host_name = %s"
    params = [station_code, host_name]
    if exclude_id:
        sql += " AND id <> %s"
        params.append(exclude_id)
    sql += " LIMIT 1"
    cursor.execute(sql, params)
    return cursor.fetchone() is not None


def _duplicate_response(station_code, host_name):
    linea = host_name or "(sin linea)"
    return (
        jsonify(
            {
                "success": False,
                "error": (
                    f"Ya existe una estacion con el codigo '{station_code}' "
                    f"en la linea '{linea}'."
                ),
                "field": "station_code",
            }
        ),
        409,
    )


@bp.route("/control_calidad/stations_qa")
@login_requerido
@requiere_permiso_dropdown(*PERMISO_MODULO)
def stations_qa_ajax():
    """Render AJAX del modulo Control de maquinas de calidad."""
    return render_template("Control de calidad/stations_qa_ajax.html")


def _build_filters():
    """Filtros comunes (q, station_type) para listado y export."""
    q = _text(request.args.get("q"), 80)
    station_type = _text(request.args.get("station_type"), 16)
    where = ["1 = 1"]
    params = []
    if q:
        where.append(
            """
            (
                station_code LIKE %s OR
                station_name LIKE %s OR
                station_type LIKE %s OR
                host_name LIKE %s
            )
            """
        )
        like = f"%{q}%"
        params.extend([like, like, like, like])
    if station_type in STATION_TYPES:
        where.append("station_type = %s")
        params.append(station_type)
    return " AND ".join(where), params


def _query_stations(cursor):
    """Ejecuta el listado filtrado y devuelve filas serializadas."""
    where_sql, params = _build_filters()
    cursor.execute(
        f"""
        SELECT id, station_code, station_name, station_type, host_name,
               is_active, created_at_utc, updated_at_utc
        FROM stations_qa
        WHERE {where_sql}
        ORDER BY station_type ASC, station_code ASC
        LIMIT 1000
        """,
        params,
    )
    return [_station_to_json(row) for row in (cursor.fetchall() or [])]


@bp.route("/api/control_calidad/stations_qa", methods=["GET"])
@login_requerido
@requiere_permiso_dropdown(*PERMISO_MODULO)
def list_stations_qa():
    """Listar estaciones QA con filtros simples."""
    conn, error_response = _connection_or_response()
    if error_response:
        return error_response
    cursor = _dict_cursor(conn)
    try:
        rows = _query_stations(cursor)
        return jsonify({"success": True, "records": rows, "total": len(rows)})
    except Exception as exc:
        logger.exception("Error listando stations_qa: %s", exc)
        return jsonify({"success": False, "error": str(exc), "records": []}), 500
    finally:
        cursor.close()
        conn.close()


@bp.route("/api/control_calidad/stations_qa/export", methods=["GET"])
@login_requerido
@requiere_permiso_dropdown(*PERMISO_MODULO)
def export_stations_qa():
    """Exportar el listado filtrado de estaciones QA a Excel (helper shared)."""
    conn, error_response = _connection_or_response()
    if error_response:
        return error_response
    cursor = _dict_cursor(conn)
    try:
        rows = _query_stations(cursor)
        items = [
            {
                "linea": r["host_name"],
                "station_code": r["station_code"],
                "station_name": r["station_name"],
                "station_type": r["station_type"],
                "estado": "Activa" if r["is_active"] else "Inactiva",
                "created_at_utc": r["created_at_utc"],
                "updated_at_utc": r["updated_at_utc"],
            }
            for r in rows
        ]
        headers = [
            "Línea", "Código", "Nombre", "Tipo",
            "Estado", "Creado UTC", "Actualizado UTC",
        ]
        keys = [
            "linea", "station_code", "station_name", "station_type",
            "estado", "created_at_utc", "updated_at_utc",
        ]
        widths = [12, 14, 28, 10, 10, 20, 20]
        filename = f"estaciones_calidad_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        return excel_response(
            items, headers, keys, widths,
            sheet="Estaciones QA", filename=filename,
        )
    except Exception as exc:
        logger.exception("Error exportando stations_qa: %s", exc)
        return jsonify({"success": False, "error": str(exc)}), 500
    finally:
        cursor.close()
        conn.close()


@bp.route("/api/control_calidad/stations_qa/<int:station_id>", methods=["GET"])
@login_requerido
@requiere_permiso_dropdown(*PERMISO_MODULO)
def get_station_qa(station_id):
    """Obtener una estacion QA por id."""
    conn, error_response = _connection_or_response()
    if error_response:
        return error_response
    cursor = _dict_cursor(conn)
    try:
        row = _fetch_station(cursor, station_id)
        if not row:
            return jsonify({"success": False, "error": "Estacion no encontrada"}), 404
        return jsonify({"success": True, "record": _station_to_json(row)})
    except Exception as exc:
        logger.exception("Error obteniendo station_qa %s: %s", station_id, exc)
        return jsonify({"success": False, "error": str(exc)}), 500
    finally:
        cursor.close()
        conn.close()


@bp.route("/api/control_calidad/stations_qa", methods=["POST"])
@login_requerido
@requiere_permiso_dropdown(*PERMISO_MODULO)
def create_station_qa():
    """Crear una estacion QA."""
    payload, errors = _payload()
    if errors:
        return jsonify({"success": False, "error": " ".join(errors)}), 400

    conn, error_response = _connection_or_response()
    if error_response:
        return error_response
    cursor = _dict_cursor(conn)
    try:
        if _code_exists(cursor, payload["station_code"], payload["host_name"]):
            return _duplicate_response(payload["station_code"], payload["host_name"])
        cursor.execute(
            """
            INSERT INTO stations_qa
                (station_code, station_name, station_type, host_name, is_active)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                payload["station_code"],
                payload["station_name"],
                payload["station_type"],
                payload["host_name"],
                payload["is_active"],
            ),
        )
        station_id = cursor.lastrowid
        conn.commit()
        row = _fetch_station(cursor, station_id)
        return jsonify({"success": True, "record": _station_to_json(row)}), 201
    except Exception as exc:
        conn.rollback()
        if _is_duplicate_error(exc):
            return _duplicate_response(payload["station_code"], payload["host_name"])
        logger.exception("Error creando station_qa: %s", exc)
        return jsonify({"success": False, "error": str(exc)}), 500
    finally:
        cursor.close()
        conn.close()


@bp.route("/api/control_calidad/stations_qa/<int:station_id>", methods=["PUT"])
@login_requerido
@requiere_permiso_dropdown(*PERMISO_MODULO)
def update_station_qa(station_id):
    """Actualizar una estacion QA."""
    payload, errors = _payload()
    if errors:
        return jsonify({"success": False, "error": " ".join(errors)}), 400

    conn, error_response = _connection_or_response()
    if error_response:
        return error_response
    cursor = _dict_cursor(conn)
    try:
        if not _fetch_station(cursor, station_id):
            return jsonify({"success": False, "error": "Estacion no encontrada"}), 404
        if _code_exists(
            cursor, payload["station_code"], payload["host_name"], exclude_id=station_id
        ):
            return _duplicate_response(payload["station_code"], payload["host_name"])
        cursor.execute(
            """
            UPDATE stations_qa
            SET station_code = %s,
                station_name = %s,
                station_type = %s,
                host_name = %s,
                is_active = %s
            WHERE id = %s
            """,
            (
                payload["station_code"],
                payload["station_name"],
                payload["station_type"],
                payload["host_name"],
                payload["is_active"],
                station_id,
            ),
        )
        conn.commit()
        row = _fetch_station(cursor, station_id)
        return jsonify({"success": True, "record": _station_to_json(row)})
    except Exception as exc:
        conn.rollback()
        if _is_duplicate_error(exc):
            return _duplicate_response(payload["station_code"], payload["host_name"])
        logger.exception("Error actualizando station_qa %s: %s", station_id, exc)
        return jsonify({"success": False, "error": str(exc)}), 500
    finally:
        cursor.close()
        conn.close()


@bp.route("/api/control_calidad/stations_qa/<int:station_id>/active", methods=["PATCH"])
@login_requerido
@requiere_permiso_dropdown(*PERMISO_MODULO)
def toggle_station_qa(station_id):
    """Activar o desactivar una estacion QA."""
    data = request.get_json(silent=True) or {}
    conn, error_response = _connection_or_response()
    if error_response:
        return error_response
    cursor = _dict_cursor(conn)
    try:
        current = _fetch_station(cursor, station_id)
        if not current:
            return jsonify({"success": False, "error": "Estacion no encontrada"}), 404
        next_active = (
            _bool(data.get("is_active"), True)
            if "is_active" in data
            else not bool(current.get("is_active"))
        )
        cursor.execute(
            "UPDATE stations_qa SET is_active = %s WHERE id = %s",
            (1 if next_active else 0, station_id),
        )
        conn.commit()
        row = _fetch_station(cursor, station_id)
        return jsonify({"success": True, "record": _station_to_json(row)})
    except Exception as exc:
        conn.rollback()
        logger.exception("Error cambiando estado station_qa %s: %s", station_id, exc)
        return jsonify({"success": False, "error": str(exc)}), 500
    finally:
        cursor.close()
        conn.close()


@bp.route("/api/control_calidad/stations_qa/<int:station_id>", methods=["DELETE"])
@login_requerido
@requiere_permiso_dropdown(*PERMISO_MODULO)
def delete_station_qa(station_id):
    """Eliminar una estacion QA."""
    conn, error_response = _connection_or_response()
    if error_response:
        return error_response
    cursor = _dict_cursor(conn)
    try:
        if not _fetch_station(cursor, station_id):
            return jsonify({"success": False, "error": "Estacion no encontrada"}), 404
        cursor.execute("DELETE FROM stations_qa WHERE id = %s", (station_id,))
        conn.commit()
        return jsonify({"success": True})
    except Exception as exc:
        conn.rollback()
        logger.exception("Error eliminando station_qa %s: %s", station_id, exc)
        return jsonify({"success": False, "error": str(exc)}), 500
    finally:
        cursor.close()
        conn.close()
