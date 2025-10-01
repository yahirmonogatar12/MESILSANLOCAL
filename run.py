from app.routes import app
from app.smt_routes_clean import register_smt_routes
from app.api_po_wo import registrar_rutas_po_wo
from app.aoi_api import aoi_api
from app.py.control_modelos_smt import control_modelos_bp
from app.api_raw_modelos import api_raw

# Registrar todas las rutas
register_smt_routes(app)
registrar_rutas_po_wo(app)
app.register_blueprint(aoi_api)
app.register_blueprint(control_modelos_bp)
# Registrar API RAW solo si no fue registrado por app.routes
if 'api_raw' not in app.blueprints:
    app.register_blueprint(api_raw)

@app.get("/")
def health():
    return "ok", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

# waitress-serve --port=5002 app.routes:app
