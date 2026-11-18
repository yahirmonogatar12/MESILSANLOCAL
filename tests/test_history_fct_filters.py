import time

from flask import render_template

from app.api.control_resultados import historial_fct


def test_history_fct_template_has_filters_for_both_tables(app):
    with app.test_request_context("/historial_fct/ajax"):
        html = render_template("Control de resultados/history_fct.html")

    assert html.count('data-fct-filter-table="history"') == 12
    assert html.count('data-fct-filter-table="steps"') == 10
    assert 'aria-label="Historial de máquina FCT"' in html
    assert 'aria-label="Pasos de la prueba FCT"' in html


def test_fct_data_api_applies_header_column_filters(client, monkeypatch):
    captured = []

    def fake_execute_query(sql, params, fetch):
        captured.append((sql, params, fetch))
        return {"n": 0} if fetch == "one" else []

    monkeypatch.setattr(historial_fct, "execute_query", fake_execute_query)
    monkeypatch.setattr(historial_fct, "fct_attach_operator", lambda rows: None)
    with client.session_transaction() as session:
        session["usuario"] = "test"
        session["_last_activity_touch_ts"] = int(time.time())

    response = client.get(
        "/api/fct/data?page=1"
        "&cf_fecha=2026-11-18"
        "&cf_hora=08%3A11"
        "&cf_linea=M2"
        "&cf_estacion=FCT1"
        "&cf_resultado=PASS"
        "&cf_no_parte=EBR"
        "&cf_serial_number=2261118"
        "&cf_fuente_archivo=DATA"
        "&cf_failed_step=12"
        "&cf_failed_test_name=Voltage"
        "&cf_failed_value=3.3%20V"
    )

    assert response.status_code == 200
    count_sql, count_params, _ = captured[0]
    assert "CAST(f.folder_date AS CHAR) LIKE %s" in count_sql
    assert "CAST(TIME(" in count_sql
    assert "f.station LIKE %s" in count_sql
    assert "f.final_result LIKE %s" in count_sql
    assert "f.part_number LIKE %s" in count_sql
    assert "f.serial_number LIKE %s" in count_sql
    assert "f.source_file LIKE %s" in count_sql
    assert "COALESCE(f.failed_step, '') LIKE %s" in count_sql
    assert "COALESCE(f.failed_test_name, '') LIKE %s" in count_sql
    assert "COALESCE(f.failed_measured_value, '')" in count_sql
    assert count_params == (
        "%2026-11-18%",
        "%08:11%",
        "%M2%",
        "%FCT1%",
        "%PASS%",
        "%EBR%",
        "%2261118%",
        "%DATA%",
        "%12%",
        "%Voltage%",
        "%3.3 V%",
    )
