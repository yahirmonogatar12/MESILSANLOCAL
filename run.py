"""run.py - Punto de entrada para ejecutar la aplicación MES

Todas las APIs y blueprints se registran centralizadamente en app/__init__.py
Este archivo solo inicia el servidor de desarrollo.
"""
import os
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# Importar la app desde el nuevo __init__.py (estructura modular)
# Todas las APIs se registran automáticamente en create_app()
from app import app

if __name__ == '__main__':
    # Activar debug para desarrollo
    # Deshabilitado reloader por incompatibilidad con conexiones MySQL
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
