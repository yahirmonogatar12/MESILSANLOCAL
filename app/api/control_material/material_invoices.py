"""Rutas Flask para Facturas / Invoice de Control de material.

La logica vive en `invoice_core/` y `costing_core/`; este archivo queda como
adaptador HTTP del blueprint.
"""

from flask import Blueprint, jsonify, render_template, request, send_file

from app.api.control_material.invoice_core.export import export_invoice
from app.api.control_material.invoice_core.service import (
    apply_invoice,
    delete_invoice,
    get_invoice_candidates,
    get_invoice_detail,
    get_partial_packing_for_part,
    list_invoices,
    preview_invoice,
    reapply_invoice,
    resolve_invoice_file,
    set_invoice_closed,
    unapply_invoice,
    update_invoice_line,
    upload_invoice,
)
from app.api.shared import login_requerido, requiere_permiso_dropdown
from app.api.shared.datetime_helpers import obtener_fecha_mexico

bp = Blueprint("material_invoices", __name__)

PERMISO_INVOICES = (
    "LISTA_DE_MATERIALES",
    "Control de material",
    "Facturas / Invoice",
)


def _json_result(result):
    payload, status = result
    return jsonify(payload), status


@bp.route("/material/invoices")
@login_requerido
@requiere_permiso_dropdown(*PERMISO_INVOICES)
def material_invoices_ajax():
    # Fecha de hoy (zona Mexico) para inicializar los filtros de fecha.
    return render_template(
        "Control de material/material_invoices_ajax.html",
        fecha_hoy=obtener_fecha_mexico(),
    )


@bp.route("/api/material_admin/invoices", methods=["GET"])
@login_requerido
@requiere_permiso_dropdown(*PERMISO_INVOICES)
def api_list_invoices():
    return _json_result(list_invoices(request.args))


@bp.route("/api/material_admin/invoices/upload", methods=["POST"])
@login_requerido
@requiere_permiso_dropdown(*PERMISO_INVOICES)
def api_upload_invoice():
    return _json_result(upload_invoice(request.files, request.form))


@bp.route("/api/material_admin/invoices/preview", methods=["POST"])
@login_requerido
@requiere_permiso_dropdown(*PERMISO_INVOICES)
def api_preview_invoice():
    return _json_result(preview_invoice(request.files, request.form))


@bp.route("/api/material_admin/invoices/<int:invoice_id>", methods=["GET"])
@login_requerido
@requiere_permiso_dropdown(*PERMISO_INVOICES)
def api_invoice_detail(invoice_id):
    return _json_result(get_invoice_detail(invoice_id))


@bp.route("/api/material_admin/invoices/<int:invoice_id>", methods=["DELETE"])
@login_requerido
@requiere_permiso_dropdown(*PERMISO_INVOICES)
def api_delete_invoice(invoice_id):
    return _json_result(delete_invoice(invoice_id))


@bp.route("/api/material_admin/invoices/<int:invoice_id>/lines/<int:line_id>", methods=["PATCH"])
@login_requerido
@requiere_permiso_dropdown(*PERMISO_INVOICES)
def api_update_invoice_line(invoice_id, line_id):
    return _json_result(update_invoice_line(invoice_id, line_id, request.get_json(silent=True) or {}))


@bp.route("/api/material_admin/invoices/<int:invoice_id>/close", methods=["POST"])
@login_requerido
@requiere_permiso_dropdown(*PERMISO_INVOICES)
def api_close_invoice(invoice_id):
    # cerrado=false reabre. Body: {"cerrado": true/false}
    data = request.get_json(silent=True) or {}
    cerrado = data.get("cerrado", True)
    return _json_result(set_invoice_closed(invoice_id, cerrado))


@bp.route("/api/material_admin/invoices/<int:invoice_id>/candidates", methods=["GET"])
@login_requerido
@requiere_permiso_dropdown(*PERMISO_INVOICES)
def api_invoice_candidates(invoice_id):
    return _json_result(get_invoice_candidates(invoice_id, request.args))


@bp.route("/api/material_admin/invoices/<int:invoice_id>/partial-packing", methods=["GET"])
@login_requerido
@requiere_permiso_dropdown(*PERMISO_INVOICES)
def api_invoice_partial_packing(invoice_id):
    """Packing lines parciales de la parte de un lote, para linkear un lote que
    llego en pallet distinto a un packing parcial."""
    return _json_result(get_partial_packing_for_part(invoice_id, request.args))


@bp.route("/api/material_admin/invoices/<int:invoice_id>/apply", methods=["POST"])
@login_requerido
@requiere_permiso_dropdown(*PERMISO_INVOICES)
def api_apply_invoice(invoice_id):
    return _json_result(apply_invoice(invoice_id, request.get_json(silent=True) or {}))


@bp.route("/api/material_admin/invoices/<int:invoice_id>/unapply", methods=["POST"])
@login_requerido
@requiere_permiso_dropdown(*PERMISO_INVOICES)
def api_unapply_invoice(invoice_id):
    return _json_result(unapply_invoice(invoice_id, request.get_json(silent=True) or {}))


@bp.route("/api/material_admin/invoices/<int:invoice_id>/reapply", methods=["POST"])
@login_requerido
@requiere_permiso_dropdown(*PERMISO_INVOICES)
def api_reapply_invoice(invoice_id):
    return _json_result(reapply_invoice(invoice_id, request.get_json(silent=True) or {}))


@bp.route("/api/material_admin/invoices/<int:invoice_id>/file", methods=["GET"])
@login_requerido
@requiere_permiso_dropdown(*PERMISO_INVOICES)
def api_invoice_file(invoice_id):
    """Descarga/streamea el Excel original guardado de la invoice."""
    info, status = resolve_invoice_file(invoice_id)
    if status != 200:
        return jsonify(info), status
    as_attachment = request.args.get("download") in ("1", "true", "yes")
    return send_file(
        info["path"],
        mimetype=info["mimetype"],
        as_attachment=as_attachment,
        download_name=info["download_name"],
    )


@bp.route("/api/material_admin/invoices/<int:invoice_id>/export", methods=["GET"])
@login_requerido
@requiere_permiso_dropdown(*PERMISO_INVOICES)
def api_invoice_export(invoice_id):
    payload, status = export_invoice(invoice_id)
    if status == 200 and not isinstance(payload, dict):
        return payload
    return jsonify(payload), status
