"""Endpoints HTTP del modulo Control de squeegee.

Migrado desde `app/routes.py` (2026-05-26). Solo render del template; sin
backend de datos (la tabla esta poblada por datos demo hardcoded en
`app/static/js/control-squeegee.js`, fuera de scope de esta migracion).

Rutas:
  GET /control-squeegee-ajax  -> render HTML del modulo
"""

from functools import wraps

from flask import Blueprint, render_template


def login_requerido(f):
    """Proxy del decorador real definido en `app.routes`."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from app import routes as _r
        return _r.login_requerido(f)(*args, **kwargs)

    return decorated_function


def requiere_permiso_dropdown(pagina, seccion, boton):
    """Proxy del decorador real definido en `app.routes`."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from app import routes as _r
            real_decorator = _r.requiere_permiso_dropdown(pagina, seccion, boton)
            return real_decorator(f)(*args, **kwargs)

        return decorated_function

    return decorator


bp = Blueprint("control_produccion_squeegee", __name__)


SQUEEGEE_PERMISO_PAGINA = "LISTA_CONTROLDEPRODUCCION"
SQUEEGEE_PERMISO_SECCION = "Control de SMT"
SQUEEGEE_PERMISO_BOTON = "Control de squeegee"


@bp.route("/control-squeegee-ajax")
@login_requerido
@requiere_permiso_dropdown(
    SQUEEGEE_PERMISO_PAGINA, SQUEEGEE_PERMISO_SECCION, SQUEEGEE_PERMISO_BOTON
)
def control_squeegee_ajax():
    """Ruta AJAX para cargar dinamicamente el contenido de Control de squeegee."""
    try:
        return render_template("Control de produccion/control_squeegee_ajax.html")
    except Exception as e:
        print(f"Error al cargar template Control de squeegee AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


# ---------------------------------------------------------------------------
# Fase 3.3 (2026-05-28): render hermano "Historial de uso de squeegee" (vive
# bajo el sidebar Control de calidad pero pertenece a este modulo).
# ---------------------------------------------------------------------------


@bp.route("/historial-uso-squeegee-ajax")
@login_requerido
def historial_uso_squeegee_ajax():
    """Template para Historial de uso de squeegee"""
    return render_template("Control de calidad/historial_uso_squeegee_ajax.html")
