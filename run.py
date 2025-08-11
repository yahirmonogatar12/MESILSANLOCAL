from app.routes import app
from app.smt_routes_clean import register_smt_routes

# Registrar todas las rutas
register_smt_routes(app)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

# waitress-serve --port=5002 app.routes:app