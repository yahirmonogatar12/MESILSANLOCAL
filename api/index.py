from app.routes import app
from app.smt_routes_clean import register_smt_routes
from app.api_po_wo import registrar_rutas_po_wo
from app.aoi_api import aoi_api

# Registrar todas las rutas
register_smt_routes(app)
registrar_rutas_po_wo(app)
app.register_blueprint(aoi_api)

@app.get("/")
def health():
    return "ok", 200

# Vercel detectará la variable `app` como aplicación WSGI