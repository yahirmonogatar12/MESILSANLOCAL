"""Regresiones del flujo login -> cookie -> landing autenticada."""


def _mock_successful_auth(monkeypatch):
    from app.api.auth import sesion

    monkeypatch.setattr(
        sesion.auth_system,
        "verificar_usuario",
        lambda username, password: (True, "Login exitoso"),
    )
    monkeypatch.setattr(
        sesion.auth_system,
        "obtener_informacion_usuario",
        lambda username: {
            "nombre_completo": "Usuario de Prueba",
            "email": "prueba@example.com",
            "departamento": "QA",
        },
    )
    monkeypatch.setattr(
        sesion.auth_system,
        "obtener_permisos_usuario",
        lambda username: ({"sistema": ["ver"]}, 1),
    )
    monkeypatch.setattr(
        sesion.auth_system,
        "obtener_roles_usuario",
        lambda username: ["usuario"],
    )
    monkeypatch.setattr(
        sesion.auth_system,
        "registrar_auditoria",
        lambda **kwargs: None,
    )


def test_login_nativo_conserva_cookie_y_sesion(client, monkeypatch):
    _mock_successful_auth(monkeypatch)

    response = client.post(
        "/login",
        data={"username": "prueba", "password": "correcta"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/inicio")
    assert "mes_ilsan_session=" in response.headers["Set-Cookie"]
    assert "no-store" in response.headers["Cache-Control"]
    assert "Cookie" in response.headers.get("Vary", "")

    landing = client.get("/inicio")
    html = landing.get_data(as_text=True)

    assert landing.status_code == 200
    assert "Usuario de Prueba" in html
    assert '<form class="login-inline-form' not in html
    assert "no-store" in landing.headers["Cache-Control"]


def test_login_fallido_muestra_el_mensaje(client, monkeypatch):
    from app.api.auth import sesion

    monkeypatch.setattr(
        sesion.auth_system,
        "verificar_usuario",
        lambda username, password: (False, "Credenciales incorrectas"),
    )
    monkeypatch.setattr(
        sesion.auth_system,
        "registrar_auditoria",
        lambda **kwargs: None,
    )

    response = client.post(
        "/login",
        data={"username": "prueba", "password": "incorrecta"},
    )
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Usuario o contrasena incorrectos" in html
    assert 'role="alert"' in html
    assert 'value="prueba"' in html
    assert "no-store" in response.headers["Cache-Control"]
