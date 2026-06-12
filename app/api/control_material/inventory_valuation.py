"""Rutas Flask para Valorizacion de inventario."""

from flask import Blueprint, jsonify, render_template, request

from app.api.control_material.valuation_core.export import export_valuation
from app.api.control_material.valuation_core.service import (
    backfill_valuation,
    list_valuation,
    valuation_summary,
)
from app.api.shared import login_requerido, requiere_permiso_dropdown

bp = Blueprint("inventory_valuation", __name__)

PERMISO_VALUATION = (
    "LISTA_DE_MATERIALES",
    "Control de material",
    "Valorización de inventario",
)


def _json_result(result):
    payload, status = result
    return jsonify(payload), status


@bp.route("/material/inventory_valuation")
@login_requerido
@requiere_permiso_dropdown(*PERMISO_VALUATION)
def inventory_valuation_ajax():
    return render_template("Control de material/inventory_valuation_ajax.html")


@bp.route("/api/material_admin/inventory/valuation", methods=["GET"])
@login_requerido
@requiere_permiso_dropdown(*PERMISO_VALUATION)
def api_inventory_valuation():
    return _json_result(list_valuation(request.args))


@bp.route("/api/material_admin/inventory/valuation/summary", methods=["GET"])
@login_requerido
@requiere_permiso_dropdown(*PERMISO_VALUATION)
def api_inventory_valuation_summary():
    return _json_result(valuation_summary(request.args))


@bp.route("/api/material_admin/inventory/valuation/export", methods=["GET"])
@login_requerido
@requiere_permiso_dropdown(*PERMISO_VALUATION)
def api_inventory_valuation_export():
    payload, status = export_valuation(request.args)
    if status == 200 and not isinstance(payload, dict):
        return payload
    return jsonify(payload), status


@bp.route("/api/material_admin/inventory/valuation/backfill", methods=["POST"])
@login_requerido
@requiere_permiso_dropdown(*PERMISO_VALUATION)
def api_inventory_valuation_backfill():
    return _json_result(backfill_valuation(request.args, request.form))
