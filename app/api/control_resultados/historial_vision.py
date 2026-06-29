"""Endpoints HTTP del modulo "Historial de maquina vision".

Consumido por LISTA_DE_CONTROL_DE_RESULTADOS / Historial de maquinas calidad.
JS cliente: app/static/js/history_vision.js
Template:   app/templates/Control de resultados/history_vision.html

Rutas:
  GET /historial_vision/ajax    -> render template (canonica)
  GET /api/vision/data          -> listar registros con filtros
  GET /api/vision/image-info    -> metadata de la imagen asociada a un registro
  GET /api/vision/image-file    -> servir imagen resuelta (Result share UNC)
  GET /api/vision/export        -> exportar listado filtrado a Excel
  GET /api/vision/stops/export  -> exportar paros filtrados a Excel

Alias 2026-05-27:
  GET /historial-vision         -> 301 a /historial_vision/ajax
  GET /historial-vision-ajax    -> 301 a /historial_vision/ajax

Migrado desde app/routes.py el 2026-05-27. Las 4 APIs ya tenian
@login_requerido en el original.

Helpers compartidos con historial_vision_pass_fail.py viven en
app/api/shared/vision_helpers.py.
"""

import re
from datetime import datetime
from pathlib import Path

from flask import (
    Blueprint, jsonify, redirect, render_template, request, send_file, url_for,
)

from app.api.shared import excel_response_ict, execute_query, login_requerido
from app.api.shared.vision_helpers import (
    _build_history_vision_count_query,
    _build_history_vision_query,
    _build_vision_stops_count_query,
    _build_vision_stops_query,
    _fetch_ajustes_for_stops,
    _get_history_vision_record,
    _resolve_history_vision_image,
    _vision_format_value,
    _vision_is_safe_path,
)

import logging
logger = logging.getLogger(__name__)


bp = Blueprint("historial_vision", __name__)


# ---------------------------------------------------------------------------
# Render template
# ---------------------------------------------------------------------------


@bp.route("/historial_vision/ajax")
@login_requerido
def historial_vision_ajax():
    """Render canonico del template Historial Vision."""
    try:
        return render_template("Control de resultados/history_vision.html")
    except Exception as e:
        logger.error(f"Error al cargar Historial Vision: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@bp.route("/historial-vision")
@bp.route("/historial-vision-ajax")
def alias_legacy_historial_vision():
    """Aliases 301 -> /historial_vision/ajax."""
    return redirect("/historial_vision/ajax", code=301)


# ---------------------------------------------------------------------------
# APIs
# ---------------------------------------------------------------------------


@bp.route("/api/vision/data")
@login_requerido
def vision_data_api():
    """Registros Vision con filtros y paginacion opcional retro-compatible."""
    import traceback
    try:
        page_raw = request.args.get("page", "").strip()
        if not page_raw:
            sql, params = _build_history_vision_query()
            rows = execute_query(sql, params, fetch="all") or []
            return jsonify(_serialize_history_vision(rows))

        try:
            page = max(1, int(page_raw))
        except ValueError:
            page = 1
        try:
            per_page = int(request.args.get("per_page", 1000))
        except (TypeError, ValueError):
            per_page = 1000
        per_page = max(1, min(per_page, 1000))

        count_sql, count_params = _build_history_vision_count_query()
        count_row = execute_query(count_sql, count_params, fetch="one") or {}
        total = int(count_row.get("n", 0))
        total_pages = (total + per_page - 1) // per_page if total else 0
        if total_pages:
            page = min(page, total_pages)

        offset = (page - 1) * per_page
        sql, params = _build_history_vision_query(per_page, offset)
        rows = execute_query(sql, params, fetch="all") or []
        return jsonify({
            "rows": _serialize_history_vision(rows),
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
        })
    except Exception as e:
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


def _serialize_history_vision(rows):
    """Normalizar fechas y valores de registros para listado paginado y legacy."""
    return [
        {
            "id": row.get("id"),
            "linea": _vision_format_value(row.get("linea", "")) or "",
            "fecha": _vision_format_value(row.get("fecha", "")) or "",
            "hora": _vision_format_value(row.get("hora", "")) or "",
            "numero_parte": _vision_format_value(row.get("numero_parte", "")) or "",
            "qr": _vision_format_value(row.get("qr", "")) or "",
            "barcode": _vision_format_value(row.get("barcode", "")) or "",
            "resultado": _vision_format_value(row.get("resultado", "")) or "",
        }
        for row in rows
    ]


@bp.route("/api/vision/stops")
@login_requerido
def vision_stops_api():
    """Paros reales de Vision (STOP -> RUN estable) con el ajuste de tecnico relacionado.

    Con ``page`` devuelve filas y metadata de paginacion. Sin ``page`` conserva la
    respuesta de array para clientes anteriores, pero ya no recorta el resultado.
    """
    import traceback
    try:
        page_raw = request.args.get("page", "").strip()
        if not page_raw:
            sql, params = _build_vision_stops_query()
            rows = execute_query(sql, params, fetch="all") or []
            return jsonify(_serialize_vision_stops(rows))

        try:
            page = max(1, int(page_raw))
        except ValueError:
            page = 1
        try:
            per_page = int(request.args.get("per_page", 1000))
        except (TypeError, ValueError):
            per_page = 1000
        per_page = max(1, min(per_page, 1000))

        count_sql, count_params = _build_vision_stops_count_query()
        count_row = execute_query(count_sql, count_params, fetch="one") or {}
        total = int(count_row.get("n", 0))
        total_stop_seconds = float(count_row.get("total_stop_seconds") or 0)
        total_pages = (total + per_page - 1) // per_page if total else 0
        if total_pages:
            page = min(page, total_pages)

        offset = (page - 1) * per_page
        sql, params = _build_vision_stops_query(per_page, offset)
        rows = execute_query(sql, params, fetch="all") or []
        return jsonify({
            "rows": _serialize_vision_stops(rows),
            "total": total,
            "total_stop_seconds": total_stop_seconds,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
        })
    except Exception as e:
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


def _serialize_vision_stops(rows):
    """Serializar paros una sola vez para la tabla y la exportacion Excel."""
    ajustes_by_uid = _fetch_ajustes_for_stops(rows)
    result = []
    for row in rows:
        real = row.get("real_stop_seconds")
        prov = row.get("real_stop_prov")
        result.append({
            "linea": _vision_format_value(row.get("linea", "")) or "",
            "numero_parte": _vision_format_value(row.get("part_code", "")) or "",
            "stop_datetime": _vision_format_value(row.get("stop_datetime", "")) or "",
            "stable_run_datetime": _vision_format_value(row.get("stable_run_datetime", "")) or "",
            "real_stop_seconds": float(real) if real is not None else None,
            "real_stop_prov": float(prov) if prov is not None else None,
            "run_attempt_count": int(row.get("run_attempt_count") or 0),
            "recovery_status": row.get("recovery_status", ""),
            "ajustes": ajustes_by_uid.get(row.get("source_uid"), []),
        })
    return result


@bp.route("/api/vision/stops/export")
@login_requerido
def export_vision_stops_excel():
    """Exportar los paros de Vision filtrados, sin la columna de estado."""
    import traceback
    try:
        sql, params = _build_vision_stops_query()
        rows = execute_query(sql, params, fetch="all") or []
        stops = _serialize_vision_stops(rows)
        keys = [
            "linea", "numero_parte", "stop_datetime", "stable_run_datetime",
            "paro_real_seconds", "run_attempt_count",
            "tecnico_ajuste",
        ]
        items = []
        for stop in stops:
            confirmed = stop.get("recovery_status") == "confirmed"
            paro_real = (
                stop.get("real_stop_seconds")
                if confirmed
                else stop.get("real_stop_prov")
            )
            ajustes = stop.get("ajustes") or []
            tecnico_ajuste = " | ".join(
                (
                    f"{ajuste.get('tecnico')}: "
                    if ajuste.get("tecnico")
                    else ""
                )
                + f"{ajuste.get('inicio_local') or ''} - {ajuste.get('fin_local') or ''}"
                for ajuste in ajustes
            )
            items.append({
                "linea": stop.get("linea", ""),
                "numero_parte": stop.get("numero_parte", ""),
                "stop_datetime": stop.get("stop_datetime", ""),
                "stable_run_datetime": stop.get("stable_run_datetime", ""),
                "paro_real_seconds": paro_real if paro_real is not None else "",
                "run_attempt_count": stop.get("run_attempt_count", 0),
                "tecnico_ajuste": tecnico_ajuste,
            })

        headers = [
            "Linea", "Numero de parte", "STOP", "RUN estable",
            "Paro real (s)", "Intentos", "Tecnico / Ajuste",
        ]
        filename = f"paros_vision_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        return excel_response_ict(
            items,
            headers,
            keys,
            widths=[16, 24, 24, 24, 16, 12, 48],
            sheet="Paros Vision",
            filename=filename,
        )
    except Exception as e:
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


@bp.route("/api/vision/image-info")
@login_requerido
def vision_image_info_api():
    """Resolver metadata de la imagen asociada a un registro de history_vision."""
    import traceback
    record_id = request.args.get("id", "").strip()
    if not re.fullmatch(r"\d+", record_id):
        return jsonify({"error": "ID de registro invalido."}), 400

    try:
        record = _get_history_vision_record(int(record_id))
        if not record:
            return jsonify({"error": "Registro de vision no encontrado."}), 404

        resolution = _resolve_history_vision_image(record)
        response_payload = {
            "record_id": record.get("id"),
            "linea": _vision_format_value(record.get("machine_name", "")) or "",
            "numero_parte": _vision_format_value(record.get("part_code", "")) or "",
            "resultado": _vision_format_value(record.get("result", "")) or "",
            "qr": _vision_format_value(
                record.get("qr_payload") or record.get("serial_qr", "")
            ) or "",
            "barcode": _vision_format_value(record.get("barcode", "")) or "",
            "fecha_hora": resolution.get("reference_datetime") or "",
            "resolved_path": resolution.get("resolved_path", ""),
            "share_name": resolution.get("share_name", ""),
            "side_folder": resolution.get("side_folder", ""),
            "delta_seconds": resolution.get("delta_seconds"),
            "searched_paths": resolution.get("searched_paths", []),
            "source_file": _vision_format_value(record.get("source_file", "")) or "",
            "machine_ip": _vision_format_value(record.get("machine_ip", "")) or "",
            "image_url": "",
        }

        if resolution.get("resolved_path"):
            response_payload["image_url"] = url_for(
                "historial_vision.vision_image_file_api", id=record.get("id")
            )
            return jsonify(response_payload)

        response_payload["error"] = resolution.get(
            "error", "No se encontro imagen para el registro."
        )
        return jsonify(response_payload), 404
    except Exception as e:
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


@bp.route("/api/vision/image-file")
@login_requerido
def vision_image_file_api():
    """Servir la imagen resuelta de un registro de history_vision."""
    import traceback
    record_id = request.args.get("id", "").strip()
    if not re.fullmatch(r"\d+", record_id):
        return jsonify({"error": "ID de registro invalido."}), 400

    try:
        record = _get_history_vision_record(int(record_id))
        if not record:
            return jsonify({"error": "Registro de vision no encontrado."}), 404

        resolution = _resolve_history_vision_image(record)
        resolved_path = resolution.get("resolved_path", "")
        share_roots = [Path(path) for path in resolution.get("share_roots", [])]

        if not resolved_path:
            return (
                jsonify({
                    "error": resolution.get(
                        "error", "No se encontro imagen para el registro."
                    ),
                    "searched_paths": resolution.get("searched_paths", []),
                }),
                404,
            )

        resolved_file = Path(resolved_path)
        if not _vision_is_safe_path(resolved_file, share_roots):
            return jsonify({"error": "La ruta resuelta no es segura."}), 403

        if not resolved_file.is_file():
            return (
                jsonify({
                    "error": "La imagen resuelta ya no esta disponible.",
                    "resolved_path": str(resolved_file),
                }),
                404,
            )

        mimetype_map = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".bmp": "image/bmp",
        }
        mimetype = mimetype_map.get(
            resolved_file.suffix.lower(), "application/octet-stream"
        )

        return send_file(
            str(resolved_file),
            mimetype=mimetype,
            as_attachment=False,
            download_name=resolved_file.name,
            conditional=True,
        )
    except Exception as e:
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


@bp.route("/api/vision/export")
@login_requerido
def export_vision_excel():
    """Exportar el historial Vision filtrado a un archivo de Excel."""
    import traceback
    try:
        sql, params = _build_history_vision_query()
        rows = execute_query(sql, params, fetch="all") or []

        keys = ["linea", "fecha", "hora", "numero_parte", "qr", "barcode", "resultado"]
        items = [
            {key: _vision_format_value(row.get(key, "")) or "" for key in keys}
            for row in rows
        ]
        headers = [
            "Linea", "Fecha", "Hora", "Numero de parte", "QR", "Barcode", "Resultado",
        ]
        filename = f"historial_vision_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        return excel_response_ict(
            items, headers, keys, widths=[22, 14, 14, 28, 36, 24, 14],
            sheet="Historial Vision", filename=filename,
        )
    except Exception as e:
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500
