import time

import pytest

from app.api.shared import permisos

RUTAS = [
    "/control-salida-lineas-ajax",
    "/api/control-salida-lineas",
    "/api/control-salida-lineas/export",
]


class SinPermiso:
    def obtener_rol_principal_usuario(self, _username):
        return "consulta"

    def verificar_permiso_boton(self, *_args, **_kwargs):
        return False


@pytest.mark.parametrize("ruta", RUTAS)
def test_sin_permiso_de_boton_responde_403(client, monkeypatch, ruta):
    monkeypatch.setattr(permisos, "_auth", lambda: SinPermiso())
    with client.session_transaction() as sess:
        sess["usuario"] = "consulta"
        sess["_last_activity_touch_ts"] = int(time.time())
    resp = client.get(ruta, headers={"Content-Type": "application/json"})
    assert resp.status_code == 403
    assert "Control de salida de lineas" in resp.get_json()["error"]
