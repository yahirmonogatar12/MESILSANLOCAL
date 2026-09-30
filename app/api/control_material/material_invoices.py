"""Rutas Flask para Facturas / Invoice de Control de material.

La logica vive en `invoice_core/` y `costing_core/`; este archivo queda como
adaptador HTTP del blueprint.
"""

from functools import wraps

from flask import Blueprint, g, jsonify, render_template, request, send_file

from app.api.control_material.invoice_core.export import export_invoice
from app.api.control_material.invoice_core.service import (
    apply_invoice,
    delete_invoice,
    delete_invoice_line,
    get_invoice_candidates,
    get_invoice_detail,
    get_partial_packing_for_part,
    list_invoices,
    preview_invoice,
    reapply_invoice,
    resolve_invoice_file,
    set_manual_receipt,
    set_invoice_closed,
    unapply_invoice,
    update_invoice_line,
    upload_invoice,
)
from app.api.control_material.invoice_core.constants import (
    AMBITO_ALMACEN,
    PERMISOS_POR_AMBITO,
    normalizar_ambito,
)
from app.api.shared import login_requerido
from app.api.shared.datetime_helpers import obtener_fecha_mexico
from app.api.shared.permisos import puede_boton
from flask import session

bp = Blueprint("material_invoices", __name__)

# Permiso del ambito de almacen. Se conserva el nombre historico
# "Facturas / Invoice" aunque el boton se muestre como "Invoice Almacen":
# renombrarlo obligaria a migrar permisos_botones y rol_permisos_botones.
PERMISO_INVOICES = PERMISOS_POR_AMBITO[AMBITO_ALMACEN]


def _json_result(result):
    payload, status = result
    return jsonify(payload), status


def _ambito_solicitado():
    """Ambito pedido en la request, o None si el valor no es valido.

    Se busca en la ruta, la query, el form y el JSON. Sin valor se asume
    ALMACEN: es el comportamiento historico y deja funcionando las URLs
    anteriores, que no mandaban ambito.
    """
    crudo = (request.view_args or {}).get("ambito")
    if crudo is None:
        crudo = request.args.get("ambito")
    if crudo is None and request.form:
        crudo = request.form.get("ambito")
    if crudo is None and request.is_json:
        crudo = (request.get_json(silent=True) or {}).get("ambito")
    if crudo is None:
        return AMBITO_ALMACEN
    return normalizar_ambito(crudo)


def requiere_permiso_ambito(f):
    """Exige el permiso del ambito pedido y lo deja en `g.ambito_invoice`.

    No sirve `requiere_permiso_dropdown` porque sus tres argumentos son fijos
    y aqui el permiso depende del ambito que trae la request (WF_001/WF_005).
    """

    @wraps(f)
    def wrapper(*args, **kwargs):
        ambito = _ambito_solicitado()
        if not ambito:
            return jsonify({"success": False, "error": "Ambito de invoice invalido."}), 400
        if not puede_boton(session.get("usuario"), *PERMISOS_POR_AMBITO[ambito]):
            return (
                jsonify({
                    "success": False,
                    "error": "No tienes permiso para los invoices de este ambito.",
                }),
                403,
            )
        g.ambito_invoice = ambito
        # El ambito viaja por `g`; las vistas no lo reciben como argumento.
        kwargs.pop("ambito", None)
        return f(*args, **kwargs)

    return wrapper


@bp.route("/material/invoices")
@bp.route("/material/invoices/<ambito>")
@login_requerido
@requiere_permiso_ambito
def material_invoices_ajax():
    # Fecha de hoy (zona Mexico) para inicializar los filtros de fecha.
    return render_template(
        "Control de material/material_invoices_ajax.html",
        fecha_hoy=obtener_fecha_mexico(),
        ambito=g.ambito_invoice,
    )


@bp.route("/api/material_admin/invoices", methods=["GET"])
@login_requerido
@requiere_permiso_ambito
def api_list_invoices():
    return _json_result(list_invoices(request.args, g.ambito_invoice))


@bp.route("/api/material_admin/invoices/upload", methods=["POST"])
@login_requerido
@requiere_permiso_ambito
def api_upload_invoice():
    return _json_result(upload_invoice(request.files, request.form, g.ambito_invoice))


@bp.route("/api/material_admin/invoices/preview", methods=["POST"])
@login_requerido
@requiere_permiso_ambito
def api_preview_invoice():
    return _json_result(preview_invoice(request.files, request.form, g.ambito_invoice))


@bp.route("/api/material_admin/invoices/<int:invoice_id>", methods=["GET"])
@login_requerido
@requiere_permiso_ambito
def api_invoice_detail(invoice_id):
    return _json_result(get_invoice_detail(invoice_id, g.ambito_invoice))


@bp.route("/api/material_admin/invoices/<int:invoice_id>", methods=["DELETE"])
@login_requerido
@requiere_permiso_ambito
def api_delete_invoice(invoice_id):
    return _json_result(delete_invoice(invoice_id, g.ambito_invoice))


@bp.route("/api/material_admin/invoices/<int:invoice_id>/lines/<int:line_id>", methods=["PATCH"])
@login_requerido
@requiere_permiso_ambito
def api_update_invoice_line(invoice_id, line_id):
    return _json_result(
        update_invoice_line(invoice_id, line_id, request.get_json(silent=True) or {}, g.ambito_invoice)
    )


@bp.route("/api/material_admin/invoices/<int:invoice_id>/lines/<int:line_id>", methods=["DELETE"])
@login_requerido
@requiere_permiso_ambito
def api_delete_invoice_line(invoice_id, line_id):
    return _json_result(delete_invoice_line(invoice_id, line_id, g.ambito_invoice))


@bp.route("/api/material_admin/invoices/<int:invoice_id>/close", methods=["POST"])
@login_requerido
@requiere_permiso_ambito
def api_close_invoice(invoice_id):
    # cerrado=false reabre. Body: {"cerrado": true/false}
    data = request.get_json(silent=True) or {}
    cerrado = data.get("cerrado", True)
    return _json_result(set_invoice_closed(invoice_id, cerrado, g.ambito_invoice))

@bp.route(
    "/api/material_admin/invoices/<int:invoice_id>/packing/"
    "<int:packing_line_id>/manual-receipt",
    methods=["POST"],
)
@login_requerido
@requiere_permiso_ambito
def api_manual_receipt(invoice_id, packing_line_id):
    return _json_result(
        set_manual_receipt(
            invoice_id,
            packing_line_id,
            request.get_json(silent=True) or {},
            g.ambito_invoice,
        )
    )


@bp.route("/api/material_admin/invoices/<int:invoice_id>/candidates", methods=["GET"])
@login_requerido
@requiere_permiso_ambito
def api_invoice_candidates(invoice_id):
    return _json_result(get_invoice_candidates(invoice_id, request.args, g.ambito_invoice))


@bp.route("/api/material_admin/invoices/<int:invoice_id>/partial-packing", methods=["GET"])
@login_requerido
@requiere_permiso_ambito
def api_invoice_partial_packing(invoice_id):
    """Packing lines parciales de la parte de un lote, para linkear un lote que
    llego en pallet distinto a un packing parcial."""
    return _json_result(get_partial_packing_for_part(invoice_id, request.args, g.ambito_invoice))


@bp.route("/api/material_admin/invoices/<int:invoice_id>/apply", methods=["POST"])
@login_requerido
@requiere_permiso_ambito
def api_apply_invoice(invoice_id):
    return _json_result(apply_invoice(invoice_id, request.get_json(silent=True) or {}, g.ambito_invoice))


@bp.route("/api/material_admin/invoices/<int:invoice_id>/unapply", methods=["POST"])
@login_requerido
@requiere_permiso_ambito
def api_unapply_invoice(invoice_id):
    return _json_result(unapply_invoice(invoice_id, request.get_json(silent=True) or {}, g.ambito_invoice))


@bp.route("/api/material_admin/invoices/<int:invoice_id>/reapply", methods=["POST"])
@login_requerido
@requiere_permiso_ambito
def api_reapply_invoice(invoice_id):
    return _json_result(reapply_invoice(invoice_id, request.get_json(silent=True) or {}, g.ambito_invoice))


@bp.route("/api/material_admin/invoices/<int:invoice_id>/file", methods=["GET"])
@login_requerido
@requiere_permiso_ambito
def api_invoice_file(invoice_id):
    """Descarga/streamea el Excel original guardado de la invoice."""
    info, status = resolve_invoice_file(invoice_id, g.ambito_invoice)
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
@requiere_permiso_ambito
def api_invoice_export(invoice_id):
    payload, status = export_invoice(invoice_id, g.ambito_invoice)
    if status == 200 and not isinstance(payload, dict):
        return payload
    return jsonify(payload), status
