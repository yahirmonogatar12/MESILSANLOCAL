"""Smoke test: la app se construye, registra rutas y el logging/dedup funcionan."""


def test_create_app_registra_muchas_rutas(app):
    total = sum(1 for _ in app.url_map.iter_rules())
    assert total > 100


def test_public_api_routes():
    from app.api.shared.public_routes import is_public_api_route

    assert is_public_api_route("/api/shipping/auth/login") is True
    assert is_public_api_route("/api/mysql") is False


def test_obtener_fecha_hora_mexico_devuelve_datetime():
    from app.api.shared import obtener_fecha_hora_mexico

    assert obtener_fecha_hora_mexico().__class__.__name__ == "datetime"


def test_login_requerido_centralizado_en_routes():
    # Los proxies duplicados se eliminaron; los blueprints usan el real.
    import app.api.control_produccion.plan_assy as pa

    assert pa.login_requerido.__module__ == "app.routes"


def test_configure_logging_idempotente():
    import app.api.shared.logging_config as lc

    lc.configure_logging()
    assert lc._CONFIGURED is True
    # Una segunda llamada no debe fallar ni reconfigurar (idempotente).
    lc.configure_logging()
    assert lc._CONFIGURED is True


def test_health_endpoint(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "OK"
