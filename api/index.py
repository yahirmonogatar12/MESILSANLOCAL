import os
import sys

# Agregar el directorio raíz al path para imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Solo cargar .env si existe (desarrollo local)
try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

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
    return {"status": "ok", "message": "ILSAN MES API Running"}, 200

@app.get("/debug/env")
def debug_env():
    """Endpoint temporal para verificar variables de entorno en Vercel"""
    return {
        "mysql_host": os.getenv('MYSQL_HOST', 'NOT_SET'),
        "mysql_port": os.getenv('MYSQL_PORT', 'NOT_SET'),
        "mysql_database": os.getenv('MYSQL_DATABASE', 'NOT_SET'),
        "mysql_user": os.getenv('MYSQL_USER', 'NOT_SET'),
        "mysql_password_set": "YES" if os.getenv('MYSQL_PASSWORD') else "NO",
        "mysql_password_length": len(os.getenv('MYSQL_PASSWORD', ''))
    }, 200

# NO usar 'handler' - Vercel busca 'app' directamente
# La variable 'app' es suficiente para Vercel