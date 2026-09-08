import hashlib
import hmac
import json

from app.services import fpa_micom_client


class _Response:
    ok = True
    status_code = 200
    text = ""

    def json(self):
        return {"success": True, "data": {"folio": "FPA-TEST-1"}}


def test_fpa_blueprint_routes_are_registered(app):
    rules = {rule.rule for rule in app.url_map.iter_rules()}
    assert "/informacion_basica/control_fpa" in rules
    assert "/api/control-fpa/requests" in rules
    assert "/api/control-fpa/requests/<int:request_id>/quantities" in rules


def test_fpa_view_renders_for_superadmin(client, monkeypatch):
    from app.api.informacion_basica import control_fpa

    monkeypatch.setattr(
        control_fpa.auth_system, "obtener_rol_principal_usuario", lambda _username: "superadmin"
    )
    with client.session_transaction() as flask_session:
        flask_session["usuario"] = "admin-prueba"
    response = client.get("/informacion_basica/control_fpa")
    assert response.status_code == 200
    assert b'id="fpa-module"' in response.data
    assert b"Solicitar a MICOM" in response.data


def test_micom_client_signs_the_exact_utf8_body(monkeypatch):
    monkeypatch.setenv("MICOM_API_URL", "http://micom.test:3012")
    monkeypatch.setenv("MICOM_INTEGRATION_SECRET", "shared-secret")
    captured = {}

    def fake_request(method, url, **kwargs):
        captured.update(method=method, url=url, **kwargs)
        return _Response()

    monkeypatch.setattr(fpa_micom_client.requests, "request", fake_request)
    payload = {"fpaPartNumber": "ÁBC", "micomQuantity": 2}
    result = fpa_micom_client.request_micom(
        "POST", "/api/fpa/requests", actor="usuario", payload=payload,
        idempotency_key="idem-1",
    )

    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    body_hash = hashlib.sha256(body).hexdigest()
    timestamp = captured["headers"]["X-MES-Timestamp"]
    canonical = f"{timestamp}\nPOST\n/api/fpa/requests\nusuario\n{body_hash}".encode()
    expected = hmac.new(b"shared-secret", canonical, hashlib.sha256).hexdigest()
    assert captured["data"] == body
    assert captured["headers"]["X-MES-Signature"] == expected
    assert captured["headers"]["Idempotency-Key"] == "idem-1"
    assert result["success"] is True
