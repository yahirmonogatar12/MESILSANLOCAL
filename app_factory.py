import os

from dotenv import load_dotenv

load_dotenv()

_cached_app = None


def _env_flag(name, default=False):
    val = os.getenv(name)
    if val is None:
        return default
    return str(val).strip().lower() in ("1", "true", "yes", "on", "si")


def should_run_startup_init():
    if _env_flag("MES_FORCE_STARTUP_INIT", False):
        return True
    if _env_flag("MES_SKIP_STARTUP_INIT", False):
        return False
    if _env_flag("MES_USE_RELOADER", False):
        return os.environ.get("WERKZEUG_RUN_MAIN") == "true"
    return True


def create_app():
    global _cached_app
    if _cached_app is not None:
        return _cached_app

    # Importes diferidos para evitar side-effects pesados antes de configurar entorno.
    from app.routes import app
    from app.startup_init import run_startup_init

    # Paquete app.api/ organizado por seccion del navbar.
    # Cada modulo es un Flask Blueprint en app/api/<seccion>/<modulo>.py
    # y se auto-registra via _MODULOS_REGISTRADOS en app/api/__init__.py.
    from app.api import registrar_blueprints_api

    if not getattr(app, "_mes_factory_initialized", False):
        # Registrar todos los blueprints del paquete app.api/
        # Migrados hasta ahora:
        #   - admin.permisos                          (ex admin_api.py)
        #   - admin.usuarios                          (ex user_admin.py)
        #   - informacion_basica.control_modelos_smt  (ex app/py/control_modelos_smt.py)
        #   - control_material.material_admin         (ex Almacen_api.py)
        #   - control_material.smd_inventory          (ex smd_inventory_api.py)
        #   - control_calidad.smt_historial_simple    (ex smt_routes_date_fixed.py)
        #   - control_calidad.smt_historial           (ex smt_routes_clean.py)
        #   - control_resultados.aoi                  (ex aoi_api.py)
        #   - control_produccion.po_wo                (ex api_po_wo.py)
        #   - shared.raw_modelos                      (ex api_raw_modelos.py)
        #   - portal.tickets                          (ex tickets_portal.py)
        #   - pda.shipping                            (ex shipping_api.py)
        #   - pda.shipping_material                   (ex shipping_material_api.py)
        registrar_blueprints_api(app)

        # Inicializaciones de BD + arranque de workers (respeta MES_SKIP_STARTUP_INIT)
        run_startup_init()

        if "health" not in app.view_functions:
            @app.get("/")
            def health():
                return "ok", 200

        app._mes_factory_initialized = True

    _cached_app = app
    return app
