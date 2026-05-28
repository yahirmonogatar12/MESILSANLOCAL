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
      shared/                  <- helpers comunes Y servicios transversales

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

Regla de oro: `app/routes.py` SOLO contiene rutas Flask.
================================================================

Todo lo que NO sea una funcion decorada con `@app.route` debe vivir en
otro lugar. Esto incluye:

    - Endpoints HTTP de un modulo concreto del navbar
        -> blueprint en `app/api/<seccion>/<modulo>.py`
    - Workers daemon, schedulers, threads de background
        -> `app/api/shared/<servicio>.py` (junto a sus endpoints si los tiene)
    - DDL idempotente (CREATE TABLE IF NOT EXISTS ...) llamado al startup
        -> mismo archivo que el servicio que lo usa; arrancado desde
           `app/startup_init.py` con import tardio
    - Funciones de captura/transformacion de datos consumidas por endpoints
        -> mismo blueprint
    - Constantes de modulo (timezone, target_hour, etc.)
        -> mismo archivo que las usa
    - Helpers de auth/decoradores reutilizables entre modulos
        -> `app/api/shared/__init__.py` o `app/api/shared/<helper>.py`

Cuando muevas un servicio compartido a `shared/`, recuerda:
    1. Si tiene rutas HTTP: registrar en `_MODULOS_REGISTRADOS` mas abajo.
    2. Si tiene DDL/workers: actualizar `app/startup_init.py` para importar
       desde el nuevo lugar (con import tardio dentro de la funcion para
       evitar ciclos al levantar la app).
    3. Si otro modulo lo consumia desde routes.py, cambiar el import:
       `from app.routes import x` -> `from app.api.shared.<servicio> import x`.

Ejemplo real: `shared/snapshot_inventario.py` reune (constantes + DDL +
captura + worker daemon + 4 endpoints HTTP) que antes estaban dispersos
en routes.py.
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
    # Migracion 2026-05-28: Historial de liberacion LQC
    "control_calidad.historial_liberacion_lqc",
    "control_resultados.aoi",
    # Migracion 2026-05-27: IMD-SMD TERMINADO a blueprint
    "control_resultados.inventario_imd",
    # Migracion 2026-05-27: 3 modulos ICT (Control de resultados)
    "control_resultados.historial_ict",
    "control_resultados.historial_ict_pass_fail",
    "control_resultados.historial_cambios_parametros_ict",
    # Migracion 2026-05-27: 2 modulos Vision (Control de resultados)
    "control_resultados.historial_vision",
    "control_resultados.historial_vision_pass_fail",
    # Migracion 2026-05-27: snapshots de inventario (servicio compartido)
    "shared.snapshot_inventario",
    "control_produccion.po_wo",
    "control_produccion.cuchillas_corte",
    "control_produccion.plan_smt",
    "control_produccion.plan_smd",
    "control_produccion.views",
    # Migracion 2026-05-26: 3 modulos Control de SMT
    "control_produccion.metal_mask",
    "control_produccion.squeegee",
    "control_produccion.caja_metal_mask",
    # Migracion 2026-05-26: Plan ASSY + Plan IMD a blueprints
    "control_produccion.plan_assy",
    "control_produccion.plan_imd",
    # Migracion 2026-05-27: Almacen de Embarques (6 modulos sidebar Control de proceso)
    "control_proceso.almacen_embarques",
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
