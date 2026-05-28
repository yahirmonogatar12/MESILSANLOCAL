"""Renders AJAX cortos del sidebar Control de proceso.

Migrado desde `app/routes.py` el 2026-05-28 (Fase 3.1). Copia 1:1 sin cambios
funcionales — solo cambia `@app.route` por `@bp.route` y el blueprint se
registra en `app/api/__init__.py::_MODULOS_REGISTRADOS`.

Cubre 16 renders del sidebar Control de proceso (cada uno solo devuelve
`render_template("Control de proceso/<archivo>.html")`):

  Sidebar -> Submódulo                          URL
  -----------------------------------------     -----------------------------------
  Historial de operacion de proceso             /historial-operacion-proceso-ajax
  BOM Management Process                        /bom-management-process-ajax
  Reporte diario inspeccion SMT                 /reporte-diario-inspeccion-smt-ajax
  Control diario inspeccion SMT                 /control-diario-inspeccion-smt-ajax
  Reporte diario inspeccion proceso             /reporte-diario-inspeccion-proceso-ajax
  Control unidad empaque modelo                 /control-unidad-empaque-modelo-ajax
  Packaging Register Management                 /packaging-register-management-ajax
  Search Packaging History                      /search-packaging-history-ajax
  Shipping Register Management                  /shipping-register-management-ajax
  Search Shipping History                       /search-shipping-history-ajax
  Registro movimiento identificacion            /registro-movimiento-identificacion-ajax
  Control otras identificaciones                /control-otras-identificaciones-ajax
  Control movimiento NS producto                /control-movimiento-ns-producto-ajax
  Model SN Management                           /model-sn-management-ajax
  Control Scrap                                 /control-scrap-ajax
  Inventario IMD terminado (alias 301)          /control_proceso/inventario_imd_terminado

El alias 301 redirige a `/control_resultados/inventario_imd_terminado`
(ya migrado en 2026-05-27 al blueprint `control_resultados.inventario_imd`).
"""

from flask import Blueprint, redirect, render_template

from app.api.shared import login_requerido

bp = Blueprint("control_proceso_renders", __name__)


@bp.route("/historial-operacion-proceso-ajax")
@login_requerido
def historial_operacion_proceso_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Historial de operación de proceso"""
    try:
        return render_template(
            "Control de proceso/historial_operacion_proceso_ajax.html"
        )
    except Exception as e:
        print(f"Error al cargar template Historial de operación de proceso AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@bp.route("/bom-management-process-ajax")
@login_requerido
def bom_management_process_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de BOM Management Process"""
    try:
        return render_template("Control de proceso/bom_management_process_ajax.html")
    except Exception as e:
        print(f"Error al cargar template BOM Management Process AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@bp.route("/reporte-diario-inspeccion-smt-ajax")
@login_requerido
def reporte_diario_inspeccion_smt_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Reporte diario de inspección SMT"""
    try:
        return render_template(
            "Control de proceso/reporte_diario_inspeccion_smt_ajax.html"
        )
    except Exception as e:
        print(f"Error al cargar template Reporte diario de inspección SMT AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@bp.route("/control-diario-inspeccion-smt-ajax")
@login_requerido
def control_diario_inspeccion_smt_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Control diario de inspección SMT"""
    try:
        return render_template(
            "Control de proceso/control_diario_inspeccion_smt_ajax.html"
        )
    except Exception as e:
        print(f"Error al cargar template Control diario de inspección SMT AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@bp.route("/reporte-diario-inspeccion-proceso-ajax")
@login_requerido
def reporte_diario_inspeccion_proceso_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Reporte diario de inspección de proceso"""
    try:
        return render_template(
            "Control de proceso/reporte_diario_inspeccion_proceso_ajax.html"
        )
    except Exception as e:
        print(
            f"Error al cargar template Reporte diario de inspección de proceso AJAX: {e}"
        )
        return f"Error al cargar el contenido: {str(e)}", 500


@bp.route("/control-unidad-empaque-modelo-ajax")
@login_requerido
def control_unidad_empaque_modelo_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Control de unidad de empaque modelo"""
    try:
        return render_template(
            "Control de proceso/control_unidad_empaque_modelo_ajax.html"
        )
    except Exception as e:
        print(f"Error al cargar template Control de unidad de empaque modelo AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@bp.route("/packaging-register-management-ajax")
@login_requerido
def packaging_register_management_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Packaging Register Management"""
    try:
        return render_template(
            "Control de proceso/packaging_register_management_ajax.html"
        )
    except Exception as e:
        print(f"Error al cargar template Packaging Register Management AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@bp.route("/search-packaging-history-ajax")
@login_requerido
def search_packaging_history_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Search Packaging History"""
    try:
        return render_template("Control de proceso/search_packaging_history_ajax.html")
    except Exception as e:
        print(f"Error al cargar template Search Packaging History AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@bp.route("/shipping-register-management-ajax")
@login_requerido
def shipping_register_management_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Shipping Register Management"""
    try:
        return render_template(
            "Control de proceso/shipping_register_management_ajax.html"
        )
    except Exception as e:
        print(f"Error al cargar template Shipping Register Management AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@bp.route("/search-shipping-history-ajax")
@login_requerido
def search_shipping_history_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Search Shipping History"""
    try:
        return render_template("Control de proceso/search_shipping_history_ajax.html")
    except Exception as e:
        print(f"Error al cargar template Search Shipping History AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@bp.route("/registro-movimiento-identificacion-ajax")
@login_requerido
def registro_movimiento_identificacion_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Registro Movimiento Identificación"""
    try:
        return render_template(
            "Control de proceso/registro_movimiento_identificacion_ajax.html"
        )
    except Exception as e:
        print(f"Error al cargar template Registro Movimiento Identificación AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@bp.route("/control-otras-identificaciones-ajax")
@login_requerido
def control_otras_identificaciones_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Control Otras Identificaciones"""
    try:
        return render_template(
            "Control de proceso/control_otras_identificaciones_ajax.html"
        )
    except Exception as e:
        print(f"Error al cargar template Control Otras Identificaciones AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@bp.route("/control-movimiento-ns-producto-ajax")
@login_requerido
def control_movimiento_ns_producto_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Control Movimiento NS Producto"""
    try:
        return render_template(
            "Control de proceso/control_movimiento_ns_producto_ajax.html"
        )
    except Exception as e:
        print(f"Error al cargar template Control Movimiento NS Producto AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@bp.route("/model-sn-management-ajax")
@login_requerido
def model_sn_management_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Model SN Management"""
    try:
        return render_template("Control de proceso/model_sn_management_ajax.html")
    except Exception as e:
        print(f"Error al cargar template Model SN Management AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@bp.route("/control-scrap-ajax")
@login_requerido
def control_scrap_ajax():
    """Ruta AJAX para cargar dinámicamente el contenido de Control Scrap"""
    try:
        return render_template("Control de proceso/control_scrap_ajax.html")
    except Exception as e:
        print(f"Error al cargar template Control Scrap AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


# Migracion 2026-05-27: ruta canonica de inventario IMD terminado vive en
# app/api/control_resultados/inventario_imd.py
# (/control_resultados/inventario_imd_terminado). Esta ruta legacy queda
# como redirect 301 para no romper sidebars cacheados.
@bp.route("/control_proceso/inventario_imd_terminado")
def inventario_imd_terminado_legacy_redirect():
    return redirect("/control_resultados/inventario_imd_terminado", code=301)
