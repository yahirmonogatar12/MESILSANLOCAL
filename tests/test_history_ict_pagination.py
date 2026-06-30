import time

from flask import render_template

from app.api.control_resultados import historial_ict


def test_history_ict_template_selects_1000_by_default(app):
    with app.test_request_context("/historial_ict/ajax"):
        html = render_template("Control de resultados/history_ict.html")

    assert '<option value="1000" selected>1000</option>' in html
    assert '<option value="200" selected>200</option>' not in html
    assert html.count('data-ict-filter-table="history"') == 11
    assert html.count('data-ict-filter-table="params"') == 25


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


def test_ict_data_api_applies_header_column_filters(client, monkeypatch):
    captured = []

    def fake_execute_query(sql, params, fetch):
        captured.append((sql, params, fetch))
        return {"n": 0} if fetch == "one" else []

    monkeypatch.setattr(historial_ict, "execute_query", fake_execute_query)
    monkeypatch.setattr(historial_ict, "_ict_attach_operator", lambda rows: None)
    with client.session_transaction() as session:
        session["usuario"] = "test"
        session["_last_activity_touch_ts"] = int(time.time())

    response = client.get(
        "/api/ict/data?page=1"
        "&cf_fecha=2026-06-30"
        "&cf_hora=08%3A11"
        "&cf_linea=M2"
        "&cf_ict=1"
        "&cf_resultado=OK"
        "&cf_no_parte=EBR"
        "&cf_barcode=2260630"
        "&cf_fuente_archivo=ODATA"
        "&cf_defect_code=D1"
        "&cf_defect_valor=0.648"
    )

    assert response.status_code == 200
    count_sql, count_params, _ = captured[0]
    assert "CAST(fecha AS CHAR) LIKE %s" in count_sql
    assert "CAST(TIME(ts) AS CHAR) LIKE %s" in count_sql
    assert "linea LIKE %s" in count_sql
    assert "CAST(ict AS CHAR) LIKE %s" in count_sql
    assert "resultado LIKE %s" in count_sql
    assert "no_parte LIKE %s" in count_sql
    assert "barcode LIKE %s" in count_sql
    assert "fuente_archivo LIKE %s" in count_sql
    assert "defect_code LIKE %s" in count_sql
    assert "defect_valor LIKE %s" in count_sql
    assert count_params == (
        "%2026-06-30%", "%08:11%", "%M2%", "%1%", "%OK%", "%EBR%",
        "%2260630%", "%ODATA%", "%D1%", "%0.648%",
    )
