"""Renders AJAX cortos del sidebar Control de produccion (no asociados a un
modulo con logica propia).

Migrado desde `app/routes.py` el 2026-05-28 (Fase 3.2). Copia 1:1 sin cambios
funcionales.

Cubre 4 renders:
  Line Material Status_es                  /line-material-status-ajax
  Estandares sobre control de soldadura    /estandares-soldadura-ajax
  Registro de recibo de soldadura          /registro-recibo-soldadura-ajax
  Control de salida de soldadura           /control-salida-soldadura-ajax
"""

from flask import Blueprint, render_template

from app.api.shared import login_requerido

bp = Blueprint("control_produccion_renders", __name__)


@bp.route("/line-material-status-ajax")
@login_requerido
def line_material_status_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Line Material Status_es"""
    try:
        return render_template(
            "Control de produccion/line_material_status_es_ajax.html"
        )
    except Exception as e:
        print(f"Error al cargar template Line Material Status_es AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@bp.route("/estandares-soldadura-ajax")
@login_requerido
def estandares_soldadura_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Estandares sobre control de soldadura"""
    try:
        return render_template("Control de produccion/estandares_soldadura_ajax.html")
    except Exception as e:
        print(
            f"Error al cargar template Estandares sobre control de soldadura AJAX: {e}"
        )
        return f"Error al cargar el contenido: {str(e)}", 500


@bp.route("/registro-recibo-soldadura-ajax")
@login_requerido
def registro_recibo_soldadura_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Registro de recibo de soldadura"""
    try:
        return render_template(
            "Control de produccion/registro_recibo_soldadura_ajax.html"
        )
    except Exception as e:
        print(f"Error al cargar template Registro de recibo de soldadura AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@bp.route("/control-salida-soldadura-ajax")
@login_requerido
def control_salida_soldadura_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Control de salida de soldadura"""
    try:
        return render_template(
            "Control de produccion/control_salida_soldadura_ajax.html"
        )
    except Exception as e:
        print(f"Error al cargar template Control de salida de soldadura AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500
