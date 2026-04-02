import os
import sys

# Agregar el directorio raíz al path para imports.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Solo cargar .env si existe (desarrollo local).
try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

# En serverless evitamos bootstraps pesados en el request path.
# El bootstrap explícito se ejecuta fuera del request con `python migrate.py`.
os.environ.setdefault("MES_SKIP_STARTUP_INIT", "1")

from app_factory import create_app

app = create_app()


@app.get("/debug/env")
def debug_env():
    """Endpoint temporal para verificar variables de entorno en Vercel."""
    return {
        "mysql_host": os.getenv("MYSQL_HOST", "NOT_SET"),
        "mysql_port": os.getenv("MYSQL_PORT", "NOT_SET"),
        "mysql_database": os.getenv("MYSQL_DATABASE", "NOT_SET"),
        "mysql_user": os.getenv("MYSQL_USER", "NOT_SET"),
        "mysql_password_set": "YES" if os.getenv("MYSQL_PASSWORD") else "NO",
        "mysql_password_length": len(os.getenv("MYSQL_PASSWORD", "")),
        "mes_skip_startup_init": os.getenv("MES_SKIP_STARTUP_INIT", "NOT_SET"),
    }, 200
