import datetime as dt
from io import BytesIO
import time
from pathlib import Path

from flask import render_template
from openpyxl import load_workbook

from app import routes
from app.api.control_resultados import historial_produccion_smt as modulo


def _login_superadmin(client, monkeypatch):
    monkeypatch.setattr(
        routes.auth_system,
        "obtener_rol_principal_usuario",
        lambda _username: "superadmin",
    )
    with client.session_transaction() as session:
        session["usuario"] = "test"
        session["_last_activity_touch_ts"] = int(time.time())


def test_sidebar_conserva_ensamble_y_agrega_historial_smt():
    path = Path("app/templates/LISTAS/LISTA_DE_CONTROL_DE_RESULTADOS.html")
    html = path.read_text(encoding="utf-8")
    catalogo = Path("app/static/permisos_dropdowns.js").read_text(encoding="utf-8")

    assert "Consultar cantidad consumida de produccion SMT" not in html
    assert "Consultar cantidad consumida de produccion SMT" not in catalogo
    assert 'data-permiso-boton="Historial de produccion ensamble"' in html
    assert 'data-permiso-boton="Historial de produccion SMT"' in html
    assert ">Historial de input ensamble</li>" in html
    assert ">Historial de input SMT</li>" in html
    assert '"boton": "Historial de produccion ensamble"' in catalogo
    assert '"boton": "Historial de produccion SMT"' in catalogo
    assert "mostrarHistorialProduccionSmt" in html


def test_template_tiene_columnas_sin_barcode_y_paginacion(app):
    with app.test_request_context("/control_resultados/historial_produccion_smt"):
        html = render_template(
            "Control de resultados/historial_produccion_smt_ajax.html",
            hoy="2026-09-18",
        )

    for heading in ("Línea", "Fecha", "Hora", "QR", "Lote"):
        assert f">{heading}<" in html
    assert ">Barcode<" not in html
    assert html.count("data-hps-filter-field=") == 5
    assert 'id="hps-pagination"' in html
    assert 'id="hps-btn-export-excel"' in html
    assert "Exportar Excel" in html
    assert "Historial de input SMT" in html
    assert '<option value="1000" selected>1000</option>' in html
    assert "historial_produccion_smt.js" in html


def test_api_pagina_filtra_ts_y_numera_absoluto_sin_barcode(client, monkeypatch):
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
                "linea": "SMT-1",
                "qr": "I123;SMT;LOT-9",
                "lote": "LOT-9",
            }
        ]

    monkeypatch.setattr(modulo, "execute_query", fake_execute_query)
    _login_superadmin(client, monkeypatch)

    response = client.get(
        "/api/control_resultados/historial_produccion_smt"
        "?page=2&per_page=200"
        "&fecha_desde=2026-09-17&fecha_hasta=2026-09-18"
        "&hora_desde=07%3A30&hora_hasta=18%3A15"
        "&linea=SMT-1&qr=I123&lote=LOT-9"
        "&cf_fecha=2026-09-18&cf_hora=08%3A05"
        "&cf_linea=SMT&cf_qr=SMT&cf_lote=LOT"
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload == {
        "success": True,
        "rows": [
            {
                "numero": 201,
                "linea": "SMT-1",
                "fecha": "2026-09-18",
                "hora": "08:05:07",
                "qr": "I123;SMT;LOT-9",
                "lote": "LOT-9",
            }
        ],
        "total": 450,
        "page": 2,
        "per_page": 200,
        "total_pages": 3,
    }
    assert "barcode" not in payload["rows"][0]

    count_sql, count_params, count_fetch = captured[0]
    data_sql, data_params, data_fetch = captured[1]
    assert count_fetch == "one"
    assert data_fetch == "all"
    assert "FROM input_smt" in count_sql
    assert "ts >= %s" in count_sql
    assert "ts < DATE_ADD(%s, INTERVAL 1 DAY)" in count_sql
    assert "TIME(ts) >= %s" in count_sql
    assert "TIME(ts) <= %s" in count_sql
    assert "CAST(DATE(ts) AS CHAR) LIKE %s" in count_sql
    assert "CAST(TIME(ts) AS CHAR) LIKE %s" in count_sql
    assert "line AS linea" in data_sql
    assert "raw AS qr" in data_sql
    assert "raw_barcode" not in data_sql
    assert "ORDER BY ts DESC, id DESC" in data_sql
    assert count_params[:4] == (
        "2026-09-17 00:00:00",
        "2026-09-18 00:00:00",
        "07:30:00",
        "18:15:00",
    )
    assert data_params[-2:] == (200, 200)


def test_api_rechaza_hora_invalida_sin_consultar_db(client, monkeypatch):
    monkeypatch.setattr(
        modulo,
        "execute_query",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("No debe consultar")),
    )
    _login_superadmin(client, monkeypatch)

    response = client.get(
        "/api/control_resultados/historial_produccion_smt?hora_desde=25%3A10",
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 400
    assert "HH:MM" in response.get_json()["error"]


def test_export_excel_descarga_pagina_visible_sin_barcode(client, monkeypatch):
    captured = []

    def fake_execute_query(sql, params, fetch):
        captured.append((sql, params, fetch))
        return [
            {
                "id": 99,
                "fecha": dt.date(2026, 9, 18),
                "hora": dt.time(7, 4, 3),
                "linea": "SMT-1",
                "qr": "QR-SMT",
                "lote": "LOT-SMT",
            }
        ]

    monkeypatch.setattr(modulo, "execute_query", fake_execute_query)
    _login_superadmin(client, monkeypatch)

    response = client.get(
        "/api/control_resultados/historial_produccion_smt/export"
        "?page=2&per_page=100&linea=SMT-1&cf_lote=LOT"
    )

    assert response.status_code == 200
    assert response.mimetype == (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert "historial_input_smt_" in response.headers["Content-Disposition"]
    sheet = load_workbook(BytesIO(response.data)).active
    assert sheet.title == "Input SMT"
    assert sheet.freeze_panes == "A2"
    assert [cell.value for cell in sheet[1]] == [
        "#", "Línea", "Fecha", "Hora", "QR", "Lote",
    ]
    assert [cell.value for cell in sheet[2]] == [
        101, "SMT-1", "2026-09-18", "07:04:03", "QR-SMT", "LOT-SMT",
    ]
    assert "Barcode" not in [cell.value for cell in sheet[1]]
    sql, params, fetch = captured[0]
    assert fetch == "all"
    assert "FROM input_smt" in sql
    assert "raw_barcode" not in sql
    assert params[-2:] == (100, 100)


def test_api_esta_registrada_y_exige_sesion(client):
    response = client.get(
        "/api/control_resultados/historial_produccion_smt",
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code in {302, 401}
    export_response = client.get(
        "/api/control_resultados/historial_produccion_smt/export"
    )
    assert export_response.status_code in {302, 401}
