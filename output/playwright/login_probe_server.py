"""Servidor temporal para reproducir login/cookie sin credenciales reales."""

import os
import sys
from pathlib import Path

os.environ.setdefault("MES_SKIP_STARTUP_INIT", "1")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.routes import app
from app.api.auth import sesion


if "auth_sesion" not in app.blueprints:
    app.register_blueprint(sesion.bp)

sesion.auth_system.verificar_usuario = lambda username, password: (
    True,
    "Login exitoso",
)
sesion.auth_system.obtener_informacion_usuario = lambda username: {
    "nombre_completo": "Usuario Navegador",
    "email": "navegador@example.com",
    "departamento": "QA",
}
sesion.auth_system.obtener_permisos_usuario = lambda username: (
    {"sistema": ["ver"]},
    1,
)
sesion.auth_system.obtener_roles_usuario = lambda username: ["usuario"]
sesion.auth_system.registrar_auditoria = lambda **kwargs: None


if os.environ.get("LOGIN_PROBE_OLD_MODE") == "1":
    @app.after_request
    def remove_session_cache_headers(response):
        response.headers.pop("Cache-Control", None)
        response.headers.pop("Pragma", None)
        response.headers.pop("Expires", None)
        response.headers.pop("Vary", None)
        return response


if __name__ == "__main__":
    port = int(os.environ.get("LOGIN_PROBE_PORT", "5055"))
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)
