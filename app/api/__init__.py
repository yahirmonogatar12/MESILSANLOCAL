"""Paquete `app.api`: endpoints HTTP organizados por seccion del navbar.

Estructura espejo de `app/templates/`:

    app/api/
      informacion_basica/      <- LISTA_INFORMACIONBASICA
      control_material/        <- LISTA_DE_MATERIALES
      control_produccion/      <- LISTA_CONTROLDEPRODUCCION
      control_proceso/         <- LISTA_CONTROL_DE_PROCESO
      control_calidad/         <- LISTA_CONTROL_DE_CALIDAD
      control_resultados/      <- LISTA_DE_CONTROL_DE_RESULTADOS
      control_reporte/         <- LISTA_DE_CONTROL_DE_REPORTE
      configuracion/           <- LISTA_DE_CONFIGPG
      shared/                  <- helpers comunes (auth, db, decoradores)

Cada modulo define un Flask Blueprint y lo expone como atributo `bp`.
`registrar_blueprints_api()` importa cada modulo y lo registra en la app.

Convencion de nuevos modulos:
    from app.api.shared import login_requerido, execute_query
    from flask import Blueprint

    bp = Blueprint("mi_modulo", __name__)

    @bp.route("/api/mi_modulo/algo")
    @login_requerido
    def algo():
        ...
"""

# Lista de modulos a registrar (ruta de import relativa al paquete app.api).
# Se llena conforme se migran archivos legacy a esta estructura.
# Formato: "seccion.modulo" -> se importa como `app.api.<seccion>.<modulo>`
# y se espera que exponga un atributo `bp` (Flask Blueprint).
_MODULOS_REGISTRADOS = [
    "control_material.material_admin",
]


def registrar_blueprints_api(app):
    """Registra todos los blueprints de `app.api.*` en la Flask app dada.

    Idempotente: si un blueprint ya esta registrado (mismo `name`), lo salta.
    """
    import importlib

    for ruta in _MODULOS_REGISTRADOS:
        modulo = importlib.import_module(f"app.api.{ruta}")
        bp = getattr(modulo, "bp", None)
        if bp is None:
            raise RuntimeError(
                f"app.api.{ruta} no define un atributo 'bp' (Flask Blueprint)"
            )
        if bp.name in app.blueprints:
            continue
        app.register_blueprint(bp)
