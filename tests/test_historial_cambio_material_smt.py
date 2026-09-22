"""Historial de cambio de material de SMT (reescrito 2026-09-22).

Cubre lo que no es trivial: la normalizacion de ScanDate/ScanTime (llegan en
dos formatos y a veces con basura) y el armado del WHERE con paginacion.
"""

import time

from flask import render_template

from app.api.control_calidad import smt_historial


def _login(client):
    with client.session_transaction() as session:
        session["usuario"] = "test"
        session["_last_activity_touch_ts"] = int(time.time())


def test_formatea_scan_date_y_time_en_ambos_formatos():
    assert smt_historial._fmt_fecha("20260922") == "2026-09-22"
    assert smt_historial._fmt_fecha("2026-09-22") == "2026-09-22"
    assert smt_historial._fmt_hora("135510") == "13:55:10"
    assert smt_historial._fmt_hora("13:55:10") == "13:55:10"
    # Basura del equipo: se devuelve tal cual, no revienta ni inventa fechas.
    assert smt_historial._fmt_fecha("Update") == "Update"
    assert smt_historial._fmt_fecha("-") == "-"
    assert smt_historial._fmt_hora("") == ""


def test_template_renderiza_columnas_y_paginacion(app):
    with app.test_request_context("/historial-cambio-material-smt-ajax"):
        html = render_template(
            "Control de calidad/historial_cambio_material_smt_ajax.html"
        )

    assert html.count("data-smt-filter-field=") == 15
    assert '<option value="1000" selected>1000</option>' in html
    assert "historial_cambio_material_smt.js" in html


def test_data_api_pagina_y_filtra(client, monkeypatch):
    capturado = {}

    def fake_execute_query(sql, params=None, fetch=None):
        if fetch == "one":
            return {"n": 2500}
        capturado.update(sql=sql, params=params)
        return []

    monkeypatch.setattr(smt_historial, "execute_query", fake_execute_query)
    _login(client)

    response = client.get(
        "/api/smt-historial/data?page=2&fecha_desde=2026-09-01"
        "&fecha_hasta=2026-09-22&linea=1line&cf_parte=EAN"
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["total"] == 2500
    assert payload["page"] == 2
    assert payload["per_page"] == 1000
    assert payload["total_pages"] == 3

    # Fechas normalizadas a 8 digitos + guarda contra ScanDate corrupto.
    assert "CHAR_LENGTH(REPLACE(ScanDate,'-',''))=8" in capturado["sql"]
    assert capturado["params"][:3] == ("20260901", "20260922", "1line")
    assert capturado["params"][3] == "%EAN%"
    assert capturado["params"][-2:] == (1000, 1000)


def test_data_api_ignora_filtros_de_columna_desconocidos(client, monkeypatch):
    capturado = {}

    def fake_execute_query(sql, params=None, fetch=None):
        if fetch == "one":
            return {"n": 0}
        capturado.update(sql=sql, params=params)
        return []

    monkeypatch.setattr(smt_historial, "execute_query", fake_execute_query)
    _login(client)

    response = client.get("/api/smt-historial/data?cf_DROP=1&cf_operador=x")

    assert response.status_code == 200
    assert "DROP" not in capturado["sql"]
    assert capturado["params"] == (1000, 0)
