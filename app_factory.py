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
    from app.smt_routes_clean import register_smt_routes
    from app.api_po_wo import registrar_rutas_po_wo
    from app.aoi_api import aoi_api
    from app.py.control_modelos_smt import control_modelos_bp
    from app.api_raw_modelos import api_raw
    from app.shipping_api import register_shipping_routes
    from app.startup_init import run_startup_init

    # Nuevo: paquete app.api/ organizado por seccion del navbar.
    # Reemplaza imports sueltos como `from app.Almacen_api import ...`.
    from app.api import registrar_blueprints_api

    if not getattr(app, "_mes_factory_initialized", False):
        register_smt_routes(app)
        registrar_rutas_po_wo(app)

        if "aoi_api" not in app.blueprints:
            app.register_blueprint(aoi_api)

        if "control_modelos_bp" not in app.blueprints:
            app.register_blueprint(control_modelos_bp)

        if "api_raw" not in app.blueprints:
            app.register_blueprint(api_raw)

        # Registrar todos los blueprints del paquete app.api/
        # (incluye material_admin migrado desde Almacen_api.py).
        registrar_blueprints_api(app)

        register_shipping_routes(app)

        # Inicializaciones de BD + arranque de workers (respeta MES_SKIP_STARTUP_INIT)
        run_startup_init()

        if "health" not in app.view_functions:
            @app.get("/")
            def health():
                return "ok", 200

        app._mes_factory_initialized = True

    _cached_app = app
    return app
