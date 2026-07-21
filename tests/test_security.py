"""Verifica los endurecimientos de seguridad (2026-05-29)."""


def test_session_cookie_httponly_y_samesite(app):
    assert app.config["SESSION_COOKIE_NAME"] == "mes_ilsan_session"
    assert app.config["SESSION_COOKIE_PATH"] == "/"
    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"


def test_secret_key_no_es_el_fallback_publico(app):
    assert app.secret_key
    assert app.secret_key != "fallback_key_for_development_only"


def test_errorhandler_global_de_excepciones_registrado(app):
    # Red de seguridad que acompana al execute_query fail-loud.
    specs = app.error_handler_spec.get(None, {})
    exc_handlers = {}
    for _code, mapping in specs.items():
        exc_handlers.update(mapping or {})
    assert Exception in exc_handlers
