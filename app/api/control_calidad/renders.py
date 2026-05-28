"""Renders AJAX cortos del sidebar Control de calidad (no asociados a un
modulo con logica propia).

Migrado desde `app/routes.py` el 2026-05-28 (Fase 3.3). Copia 1:1 sin cambios
funcionales.

Cubre 6 renders:
  Control de resultado de reparacion       /control-resultado-reparacion-ajax
  Control de item reparado                 /control-item-reparado-ajax
  Historial de uso de pegamento soldadura  /historial-uso-pegamento-soldadura-ajax
  Process interlock History                /process-interlock-history-ajax
  Control de Master Sample de SMT          /control-master-sample-smt-ajax
  Historial inspeccion Master Sample SMT   /historial-inspeccion-master-sample-smt-ajax
  Control de inspeccion de OQC             /control-inspeccion-oqc-ajax
"""

from flask import Blueprint, render_template

from app.api.shared import login_requerido

bp = Blueprint("control_calidad_renders", __name__)


@bp.route("/control-resultado-reparacion-ajax")
@login_requerido
def control_resultado_reparacion_ajax():
    """Template para Control de resultado de reparación"""
    return render_template("Control de calidad/control_resultado_reparacion_ajax.html")


@bp.route("/control-item-reparado-ajax")
@login_requerido
def control_item_reparado_ajax():
    """Template para Control de item reparado"""
    return render_template("Control de calidad/control_item_reparado_ajax.html")


@bp.route("/historial-uso-pegamento-soldadura-ajax")
@login_requerido
def historial_uso_pegamento_soldadura_ajax():
    """Template para Historial de uso de pegamento de soldadura"""
    return render_template(
        "Control de calidad/historial_uso_pegamento_soldadura_ajax.html"
    )


@bp.route("/process-interlock-history-ajax")
@login_requerido
def process_interlock_history_ajax():
    """Template para Process interlock History"""
    return render_template("Control de calidad/process_interlock_history_ajax.html")


@bp.route("/control-master-sample-smt-ajax")
@login_requerido
def control_master_sample_smt_ajax():
    """Template para Control de Master Sample de SMT"""
    return render_template("Control de calidad/control_master_sample_smt_ajax.html")


@bp.route("/historial-inspeccion-master-sample-smt-ajax")
@login_requerido
def historial_inspeccion_master_sample_smt_ajax():
    """Template para Historial de inspección de Master Sample de SMT"""
    return render_template(
        "Control de calidad/historial_inspeccion_master_sample_smt_ajax.html"
    )


@bp.route("/control-inspeccion-oqc-ajax")
@login_requerido
def control_inspeccion_oqc_ajax():
    """Template para Control de inspección de OQC"""
    return render_template("Control de calidad/control_inspeccion_oqc_ajax.html")
