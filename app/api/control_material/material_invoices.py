"""Rutas Flask para Facturas / Invoice de Control de material.

La logica vive en `invoice_core/` y `costing_core/`; este archivo queda como
adaptador HTTP del blueprint.
"""

from flask import Blueprint, jsonify, render_template, request

from app.api.control_material.invoice_core.export import export_invoice
from app.api.control_material.invoice_core.service import (
    apply_invoice,
    create_alias,
    deactivate_alias,
    get_invoice_candidates,
    get_invoice_detail,
    import_aliases,
    list_aliases,
    list_invoices,
    reapply_invoice,
    unapply_invoice,
    upload_invoice,
)
from app.api.shared import login_requerido, requiere_permiso_dropdown

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
    return render_template("Control de material/material_invoices_ajax.html")


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


@bp.route("/api/material_admin/invoices/<int:invoice_id>", methods=["GET"])
@login_requerido
@requiere_permiso_dropdown(*PERMISO_INVOICES)
def api_invoice_detail(invoice_id):
    return _json_result(get_invoice_detail(invoice_id))


@bp.route("/api/material_admin/invoices/<int:invoice_id>/candidates", methods=["GET"])
@login_requerido
@requiere_permiso_dropdown(*PERMISO_INVOICES)
def api_invoice_candidates(invoice_id):
    return _json_result(get_invoice_candidates(invoice_id, request.args))


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


@bp.route("/api/material_admin/invoices/<int:invoice_id>/export", methods=["GET"])
@login_requerido
@requiere_permiso_dropdown(*PERMISO_INVOICES)
def api_invoice_export(invoice_id):
    payload, status = export_invoice(invoice_id)
    if status == 200 and not isinstance(payload, dict):
        return payload
    return jsonify(payload), status


@bp.route("/api/material_admin/invoices/aliases", methods=["POST"])
@login_requerido
@requiere_permiso_dropdown(*PERMISO_INVOICES)
def api_create_alias():
    return _json_result(create_alias(request.get_json(silent=True) or {}))


@bp.route("/api/material_admin/invoices/aliases", methods=["GET"])
@login_requerido
@requiere_permiso_dropdown(*PERMISO_INVOICES)
def api_list_aliases():
    return _json_result(list_aliases(request.args))


@bp.route("/api/material_admin/invoices/aliases/import", methods=["POST"])
@login_requerido
@requiere_permiso_dropdown(*PERMISO_INVOICES)
def api_import_aliases():
    return _json_result(import_aliases(request.files, request.form))


@bp.route("/api/material_admin/invoices/aliases/<int:alias_id>", methods=["DELETE"])
@login_requerido
@requiere_permiso_dropdown(*PERMISO_INVOICES)
def api_deactivate_alias(alias_id):
    return _json_result(deactivate_alias(alias_id))
