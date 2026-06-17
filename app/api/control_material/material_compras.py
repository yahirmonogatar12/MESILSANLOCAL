"""Rutas Flask para Lista de compras de Control de material.

Registro de compras historicas/vivas (hoja 'Compras totales'). La logica vive en
`compras_core/`; este archivo es el adaptador HTTP del blueprint.
"""

import os

from flask import Blueprint, jsonify, render_template, request, send_file

from app.api.control_material.compras_core.service import (
    delete_carga,
    get_transaccion_detail,
    list_cargas,
    list_transacciones,
    preview_compras,
    resolve_compras_file,
    upload_compras,
)
from app.api.control_material.compras_core.service import EXCEL_MIME
from app.api.control_material.invoice_core.storage import absolute_path
from app.api.shared import login_requerido, requiere_permiso_dropdown
from app.api.shared.datetime_helpers import obtener_fecha_mexico

bp = Blueprint("material_compras", __name__)

PERMISO_COMPRAS = (
    "LISTA_DE_MATERIALES",
    "Control de material",
    "Lista de compras",
)


def _json_result(result):
    payload, status = result
    return jsonify(payload), status


@bp.route("/material/compras")
@login_requerido
@requiere_permiso_dropdown(*PERMISO_COMPRAS)
def material_compras_ajax():
    return render_template(
        "Control de material/material_compras_ajax.html",
        fecha_hoy=obtener_fecha_mexico(),
    )


@bp.route("/api/material_admin/compras/transacciones", methods=["GET"])
@login_requerido
@requiere_permiso_dropdown(*PERMISO_COMPRAS)
def api_list_transacciones():
    return _json_result(list_transacciones(request.args))


@bp.route("/api/material_admin/compras/transacciones/<path:numero>", methods=["GET"])
@login_requerido
@requiere_permiso_dropdown(*PERMISO_COMPRAS)
def api_transaccion_detail(numero):
    return _json_result(get_transaccion_detail(numero))


@bp.route("/api/material_admin/compras/upload", methods=["POST"])
@login_requerido
@requiere_permiso_dropdown(*PERMISO_COMPRAS)
def api_upload_compras():
    return _json_result(upload_compras(request.files, request.form))


@bp.route("/api/material_admin/compras/preview", methods=["POST"])
@login_requerido
@requiere_permiso_dropdown(*PERMISO_COMPRAS)
def api_preview_compras():
    return _json_result(preview_compras(request.files, request.form))


@bp.route("/api/material_admin/compras/cargas", methods=["GET"])
@login_requerido
@requiere_permiso_dropdown(*PERMISO_COMPRAS)
def api_list_cargas():
    return _json_result(list_cargas(request.args))


@bp.route("/api/material_admin/compras/cargas/<int:carga_id>", methods=["DELETE"])
@login_requerido
@requiere_permiso_dropdown(*PERMISO_COMPRAS)
def api_delete_carga(carga_id):
    return _json_result(delete_carga(carga_id))


@bp.route("/api/material_admin/compras/cargas/<int:carga_id>/file", methods=["GET"])
@login_requerido
@requiere_permiso_dropdown(*PERMISO_COMPRAS)
def api_compras_file(carga_id):
    ruta, nombre = resolve_compras_file(carga_id)
    full = absolute_path(ruta) if ruta else None
    if not full or not os.path.isfile(full):
        return jsonify({"success": False, "error": "Archivo no encontrado."}), 404
    as_attachment = request.args.get("download") in ("1", "true", "yes")
    return send_file(
        full,
        mimetype=EXCEL_MIME,
        as_attachment=as_attachment,
        download_name=nombre or "compras.xlsx",
    )
