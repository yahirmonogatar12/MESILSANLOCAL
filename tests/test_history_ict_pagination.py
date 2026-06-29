import time

from flask import render_template

from app.api.control_resultados import historial_ict


def test_history_ict_template_selects_1000_by_default(app):
    with app.test_request_context("/historial_ict/ajax"):
        html = render_template("Control de resultados/history_ict.html")

    assert '<option value="1000" selected>1000</option>' in html
    assert '<option value="200" selected>200</option>' not in html


def test_ict_data_api_paginates_1000_by_default(client, monkeypatch):
    captured = {}

    def fake_execute_query(sql, params, fetch):
        if fetch == "one":
            return {"n": 1501}
        captured.update(sql=sql, params=params)
        return []

    monkeypatch.setattr(historial_ict, "execute_query", fake_execute_query)
    monkeypatch.setattr(historial_ict, "_ict_attach_operator", lambda rows: None)
    with client.session_transaction() as session:
        session["usuario"] = "test"
        session["_last_activity_touch_ts"] = int(time.time())

    response = client.get("/api/ict/data?page=2")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["total"] == 1501
    assert payload["page"] == 2
    assert payload["per_page"] == 1000
    assert payload["total_pages"] == 2
    assert captured["params"][-2:] == (1000, 1000)
