import datetime as dt
import time
from pathlib import Path

from flask import render_template

from app import routes
from app.api.control_resultados import historial_produccion_ensamble as modulo


def _login_superadmin(client, monkeypatch):
    monkeypatch.setattr(
        routes.auth_system,
        "obtener_rol_principal_usuario",
        lambda _username: "superadmin",
    )
    with client.session_transaction() as session:
        session["usuario"] = "test"
        session["_last_activity_touch_ts"] = int(time.time())


def test_sidebar_reemplaza_boton_smt_por_historial_ensamble():
    path = Path("app/templates/LISTAS/LISTA_DE_CONTROL_DE_RESULTADOS.html")
    html = path.read_text(encoding="utf-8")

    assert "Consultar cantidad consumida de produccion SMT" not in html
    assert 'data-permiso-boton="Historial de produccion ensamble"' in html
    assert "mostrarHistorialProduccionEnsamble" in html


def test_template_tiene_columnas_y_paginacion_solicitadas(app):
    with app.test_request_context("/control_resultados/historial_produccion_ensamble"):
        html = render_template(
            "Control de resultados/historial_produccion_ensamble_ajax.html",
            hoy="2026-09-18",
        )

    for heading in ("Línea", "Fecha", "Hora", "QR", "Barcode", "Lote"):
        assert f">{heading}<" in html
    assert html.count("data-hpe-filter-field=") == 6
    assert 'id="hpe-pagination"' in html
    assert '<option value="1000" selected>1000</option>' in html
    assert "historial_produccion_ensamble.js" in html


def test_api_pagina_filtra_ts_y_numera_absoluto(client, monkeypatch):
    captured = []

    def fake_execute_query(sql, params, fetch):
        captured.append((sql, params, fetch))
        if fetch == "one":
            return {"n": 450}
        return [
            {
                "id": 99,
                "fecha": dt.date(2026, 9, 18),
                "hora": dt.time(8, 5, 7),
                "linea": "M1",
                "qr": "I123;MAIN;LOT-9",
                "barcode": "EBR123456789",
                "lote": "LOT-9",
            }
        ]

    monkeypatch.setattr(modulo, "execute_query", fake_execute_query)
    _login_superadmin(client, monkeypatch)

    response = client.get(
        "/api/control_resultados/historial_produccion_ensamble"
        "?page=2&per_page=200"
        "&fecha_desde=2026-09-17&fecha_hasta=2026-09-18"
        "&hora_desde=07%3A30&hora_hasta=18%3A15"
        "&linea=M1&qr=I123&barcode=EBR123&lote=LOT-9"
        "&cf_fecha=2026-09-18&cf_hora=08%3A05"
        "&cf_linea=M1&cf_qr=MAIN&cf_barcode=6789&cf_lote=LOT"
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload == {
        "success": True,
        "rows": [
            {
                "numero": 201,
                "linea": "M1",
                "fecha": "2026-09-18",
                "hora": "08:05:07",
                "qr": "I123;MAIN;LOT-9",
                "barcode": "EBR123456789",
                "lote": "LOT-9",
            }
        ],
        "total": 450,
        "page": 2,
        "per_page": 200,
        "total_pages": 3,
    }

    count_sql, count_params, count_fetch = captured[0]
    data_sql, data_params, data_fetch = captured[1]
    assert count_fetch == "one"
    assert data_fetch == "all"
    assert "FROM input_main" in count_sql
    assert "ts >= %s" in count_sql
    assert "ts < DATE_ADD(%s, INTERVAL 1 DAY)" in count_sql
    assert "TIME(ts) >= %s" in count_sql
    assert "TIME(ts) <= %s" in count_sql
    assert "CAST(DATE(ts) AS CHAR) LIKE %s" in count_sql
    assert "CAST(TIME(ts) AS CHAR) LIKE %s" in count_sql
    assert "ORDER BY ts DESC, id DESC" in data_sql
    assert count_params[:4] == (
        "2026-09-17 00:00:00",
        "2026-09-18 00:00:00",
        "07:30:00",
        "18:15:00",
    )
    assert data_params[-2:] == (200, 200)


def test_api_rechaza_fecha_invalida_sin_consultar_db(client, monkeypatch):
    monkeypatch.setattr(
        modulo,
        "execute_query",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("No debe consultar")),
    )
    _login_superadmin(client, monkeypatch)

    response = client.get(
        "/api/control_resultados/historial_produccion_ensamble?fecha_desde=18-09-2026",
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 400
    assert "AAAA-MM-DD" in response.get_json()["error"]


def test_api_esta_registrada_y_exige_sesion(client):
    response = client.get(
        "/api/control_resultados/historial_produccion_ensamble",
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code in {302, 401}
