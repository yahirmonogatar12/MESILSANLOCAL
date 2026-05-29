"""Renders HTML de la seccion Control de produccion.

Migrado desde `app/routes.py` (2026-05-25). Sin cambios funcionales.

Rutas:
  GET /control_produccion/control_embarque  -> render Control de embarque.html
  GET /Control de embarque                  -> alias AJAX (path con espacios)
  GET /control_produccion/crear_plan        -> render Crear plan de produccion.html
  GET /control_produccion/plan_smt          -> render plan_smd_interfaz.html

NOTA: `/control-cuchillas-corte-ajax` esta en `cuchillas_corte.py`
(va junto con sus 17 endpoints API y comparte el decorator de permiso).
"""

from functools import wraps

from flask import Blueprint, render_template, session

from app.api.shared.datetime_helpers import obtener_fecha_hora_mexico


# Decorador de auth centralizado (antes era un proxy duplicado en cada
# modulo). app.api.shared lo reexporta desde app.routes de forma lazy.
from app.api.shared import login_requerido

import logging
logger = logging.getLogger(__name__)


bp = Blueprint("control_produccion_views", __name__)


@bp.route("/control_produccion/control_embarque")
@login_requerido
def control_embarque():
    """Cargar la pagina de Control de Embarque"""
    try:
        return render_template("Control de produccion/Control de embarque.html")
    except Exception as e:
        logger.error(f"Error al cargar Control de embarque: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@bp.route("/Control de embarque")
@login_requerido
def control_embarque_ajax():
    """Ruta AJAX para cargar dinamicamente el contenido de Control de embarque"""
    try:
        return render_template("Control de produccion/Control de embarque.html")
    except Exception as e:
        logger.error(f"Error al cargar template Control de embarque AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@bp.route("/control_produccion/crear_plan")
@login_requerido
def crear_plan_produccion():
    """Cargar la pagina de Crear Plan de Produccion"""
    try:
        fecha_hoy = obtener_fecha_hora_mexico().strftime("%Y-%m-%d")
        usuario_logueado = session.get("usuario", "")
        return render_template(
            "Control de produccion/Crear plan de produccion.html",
            fecha_hoy=fecha_hoy,
            usuario_logueado=usuario_logueado,
        )
    except Exception as e:
        logger.error(f"Error al cargar Crear Plan de Produccion: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@bp.route("/control_produccion/plan_smt")
@login_requerido
def plan_smt_ajax():
    """Ruta AJAX para cargar dinamicamente el contenido de PLAN SMT"""
    try:
        return render_template("Control de produccion/plan_smd_interfaz.html")
    except Exception as e:
        logger.error(f"Error al cargar template PLAN SMT AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500
