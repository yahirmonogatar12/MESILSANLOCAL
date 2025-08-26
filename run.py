from app.routes import app
from app.smt_routes_clean import register_smt_routes
from app.api_po_wo import registrar_rutas_po_wo
from app.aoi_api import aoi_api

# Registrar todas las rutas
register_smt_routes(app)
registrar_rutas_po_wo(app)
app.register_blueprint(aoi_api)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

@app.get("/")
def health():
    return "ok", 200

# waitress-serve --port=5002 app.routes:app