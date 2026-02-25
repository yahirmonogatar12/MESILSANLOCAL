from dotenv import load_dotenv

load_dotenv()

_cached_app = None


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

    if not getattr(app, "_mes_factory_initialized", False):
        register_smt_routes(app)
        registrar_rutas_po_wo(app)

        if 'aoi_api' not in app.blueprints:
            app.register_blueprint(aoi_api)

        if 'control_modelos_bp' not in app.blueprints:
            app.register_blueprint(control_modelos_bp)

        if 'api_raw' not in app.blueprints:
            app.register_blueprint(api_raw)

        if 'health' not in app.view_functions:
            @app.get("/")
            def health():
                return "ok", 200

        app._mes_factory_initialized = True

    _cached_app = app
    return app
