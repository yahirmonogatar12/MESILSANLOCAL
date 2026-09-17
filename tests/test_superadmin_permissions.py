"""Regresiones para que superadmin no dependa de permisos cacheados en sesion."""

from flask import session


def test_main_template_muestra_panel_a_superadmin_sin_diccionario_de_permisos(
    client, monkeypatch
):
    from app import routes

    monkeypatch.setattr(
        routes.auth_system,
        "obtener_rol_principal_usuario",
        lambda _username: "superadmin",
    )

    with client.session_transaction() as flask_session:
        flask_session["usuario"] = "super-prueba"
        flask_session["nombre_completo"] = "Super Prueba"
        flask_session["roles"] = ["superadmin"]
        flask_session["rol_principal"] = "superadmin"
        flask_session["permisos"] = {}

    response = client.get("/ILSAN-ELECTRONICS")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Panel de" in html
    assert "Administración" in html
    assert "window.location.href='/admin/panel'" in html


def test_decorador_de_permiso_da_bypass_a_superadmin_sin_cache(app, monkeypatch):
    from app import routes

    monkeypatch.setattr(
        routes.auth_system,
        "obtener_rol_principal_usuario",
        lambda _username: "superadmin",
    )

    protegido = routes.auth_system.requiere_permiso("sistema", "usuarios")(
        lambda: "permitido"
    )

    with app.test_request_context("/admin/panel"):
        session["usuario"] = "super-prueba"
        session["permisos"] = {}
        assert protegido() == "permitido"
