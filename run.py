import os
from waitress import serve
from app_factory import create_app

# En ejecución productiva con waitress no usamos reloader.
os.environ.setdefault("MES_USE_RELOADER", "0")

app = create_app()

if __name__ == '__main__':
    serve(app, host='0.0.0.0', port=5000, threads=8)
