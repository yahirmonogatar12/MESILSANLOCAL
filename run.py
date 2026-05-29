import os
from waitress import serve

from app.api.shared.logging_config import configure_logging
from app_factory import create_app

# Configurar logging antes de crear la app (reemplaza los print()).
configure_logging()

os.environ.setdefault("MES_USE_RELOADER", "0")
# Saltar inicializaciones de BD por defecto: las tablas ya existen.
# Para forzar una corrida (despues de cambios de schema):
#   set MES_SKIP_STARTUP_INIT=0 & set MES_FORCE_STARTUP_INIT=1
os.environ.setdefault("MES_SKIP_STARTUP_INIT", "1")
app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    print(f"Servidor iniciado en http://0.0.0.0:{port}")
    serve(app, host='0.0.0.0', port=port, threads=8)