"""Tests de la fachada de permisos por boton (app/api/shared/permisos.py)."""

from app.api.shared import permisos


def test_normalizar_boton_con_dict():
    out = permisos._normalizar_boton({"boton": "Crear", "descripcion": "desc"})
    assert out == {"boton": "Crear", "descripcion": "desc"}


def test_normalizar_boton_con_string():
    out = permisos._normalizar_boton("Crear")
    assert out == {"boton": "Crear", "descripcion": None}


def test_normalizar_boton_dict_parcial():
    out = permisos._normalizar_boton({"boton": "X"})
    assert out == {"boton": "X", "descripcion": None}


def test_requiere_permiso_dropdown_importable_desde_shared():
    from app.api.shared import requiere_permiso_dropdown

    assert requiere_permiso_dropdown.__module__ == "app.api.shared.permisos"


def test_routes_reexporta_el_mismo_decorador():
    from app import routes

    assert routes.requiere_permiso_dropdown is permisos.requiere_permiso_dropdown


def test_blueprints_usan_el_decorador_centralizado():
    # Los 7 proxies se eliminaron; ahora importan el canonico.
    import app.api.control_produccion.plan_assy as pa

    assert pa.requiere_permiso_dropdown is permisos.requiere_permiso_dropdown


def test_permisos_botones_normaliza_a_dict(monkeypatch):
    # auth_system devuelve la mezcla dict/string; la fachada normaliza todo a dict.
    fake = {
        "PAGINA": {
            "Seccion": [
                {"boton": "Crear", "descripcion": "d"},
                "Editar",  # string suelto
            ]
        }
    }

    class _FakeAuth:
        def obtener_permisos_botones_usuario(self, username, pagina=None):
            return fake

    monkeypatch.setattr(permisos, "_auth", lambda: _FakeAuth())

    out = permisos.permisos_botones("u")
    botones = out["PAGINA"]["Seccion"]
    assert botones == [
        {"boton": "Crear", "descripcion": "d"},
        {"boton": "Editar", "descripcion": None},
    ]


def test_puede_boton_delega_en_auth_system(monkeypatch):
    llamado = {}

    class _FakeAuth:
        def verificar_permiso_boton(self, username, pagina, seccion, boton):
            llamado["args"] = (username, pagina, seccion, boton)
            return True

    monkeypatch.setattr(permisos, "_auth", lambda: _FakeAuth())

    assert permisos.puede_boton("u", "P", "S", "B") is True
    assert llamado["args"] == ("u", "P", "S", "B")


def test_decorador_sin_sesion_devuelve_401(app):
    @permisos.requiere_permiso_dropdown("P", "S", "B")
    def vista():
        return "ok"

    # Sin sesion -> 401 JSON (no entra a la vista).
    with app.test_request_context("/x"):
        resp = vista()
        body, status = resp if isinstance(resp, tuple) else (resp, 200)
        assert status == 401
