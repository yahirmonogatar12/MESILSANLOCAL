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
    "admin.permisos",
    "admin.usuarios",
    "informacion_basica.control_bom",
    "informacion_basica.control_modelos_smt",
    "informacion_basica.control_modelos_visor",
    "control_material.material_admin",
    # control_calidad.smt_historial_simple DEBE ir antes que smt_historial:
    # ambos definen /api/historial_smt_data y Flask deja responder al primero
    # registrado (preserva comportamiento legacy de smt_routes_date_fixed.py).
    "control_calidad.smt_historial_simple",
    "control_calidad.smt_historial",
    "control_resultados.aoi",
    "control_produccion.po_wo",
    "control_produccion.cuchillas_corte",
    "control_produccion.plan_smt",
    "control_produccion.plan_smd",
    "control_produccion.views",
    # Migracion 2026-05-26: 3 modulos Control de SMT
    "control_produccion.metal_mask",
    "control_produccion.squeegee",
    "control_produccion.caja_metal_mask",
    "shared.raw_modelos",
    "portal.tickets",
    "pda.shipping",
    "pda.shipping_material",
]


def registrar_blueprints_api(app):
    """Registra todos los blueprints de `app.api.*` en la Flask app dada.

    Reconoce dos formas de exportar blueprints en cada modulo:
      - `bp`         (obligatorio): el blueprint principal del modulo.
      - `bp_<sufijo>` (opcional): blueprints adicionales (p.ej. para rutas
        sin url_prefix o que viven fuera del namespace principal).

    Idempotente: si un blueprint ya esta registrado (mismo `name`), lo salta.
    """
    import importlib

    from flask import Blueprint

    for ruta in _MODULOS_REGISTRADOS:
        modulo = importlib.import_module(f"app.api.{ruta}")
        bp = getattr(modulo, "bp", None)
        if bp is None:
            raise RuntimeError(
                f"app.api.{ruta} no define un atributo 'bp' (Flask Blueprint)"
            )

        # Recolectar bp + cualquier bp_<sufijo> adicional.
        blueprints_a_registrar = [bp]
        for atributo in dir(modulo):
            if not atributo.startswith("bp_") or atributo == "bp":
                continue
            extra = getattr(modulo, atributo)
            if isinstance(extra, Blueprint):
                blueprints_a_registrar.append(extra)

        for blueprint in blueprints_a_registrar:
            if blueprint.name in app.blueprints:
                continue
            app.register_blueprint(blueprint)
