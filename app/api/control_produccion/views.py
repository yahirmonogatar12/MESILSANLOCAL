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


def login_requerido(f):
    """Proxy del decorador real definido en `app.routes`."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from app import routes as _r
        return _r.login_requerido(f)(*args, **kwargs)

    return decorated_function


def obtener_fecha_hora_mexico():
    """Proxy del helper definido en `app.routes`."""
    from app import routes as _r
    return _r.obtener_fecha_hora_mexico()


bp = Blueprint("control_produccion_views", __name__)


@bp.route("/control_produccion/control_embarque")
@login_requerido
def control_embarque():
    """Cargar la pagina de Control de Embarque"""
    try:
        return render_template("Control de produccion/Control de embarque.html")
    except Exception as e:
        print(f"Error al cargar Control de embarque: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@bp.route("/Control de embarque")
@login_requerido
def control_embarque_ajax():
    """Ruta AJAX para cargar dinamicamente el contenido de Control de embarque"""
    try:
        return render_template("Control de produccion/Control de embarque.html")
    except Exception as e:
        print(f"Error al cargar template Control de embarque AJAX: {e}")
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
        print(f"Error al cargar Crear Plan de Produccion: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@bp.route("/control_produccion/plan_smt")
@login_requerido
def plan_smt_ajax():
    """Ruta AJAX para cargar dinamicamente el contenido de PLAN SMT"""
    try:
        return render_template("Control de produccion/plan_smd_interfaz.html")
    except Exception as e:
        print(f"Error al cargar template PLAN SMT AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500
