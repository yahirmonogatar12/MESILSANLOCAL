import os
from waitress import serve
from app_factory import create_app

os.environ.setdefault("MES_USE_RELOADER", "0")
app = create_app()

f __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    print(f"Servidor iniciado en http://0.0.0.0:{port}")
    serve(app, host='0.0.0.0', port=port, threads=8)
