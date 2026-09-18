import datetime as dt
from io import BytesIO
import time
from pathlib import Path

from flask import render_template
from openpyxl import load_workbook

from app import routes
from app.api.control_resultados import historial_prueba_electrica as modulo


def _login_superadmin(client, monkeypatch):
    monkeypatch.setattr(
        routes.auth_system,
        "obtener_rol_principal_usuario",
        lambda _username: "superadmin",
    )
    with client.session_transaction() as session:
        session["usuario"] = "test"
        session["_last_activity_touch_ts"] = int(time.time())


def test_sidebar_agrega_prueba_electrica_despues_de_vision_pass_fail():
    menu = Path(
        "app/templates/LISTAS/LISTA_DE_CONTROL_DE_RESULTADOS.html"
    ).read_text(encoding="utf-8")
    catalogo = Path("app/static/permisos_dropdowns.js").read_text(encoding="utf-8")
    auth = Path("app/auth_system.py").read_text(encoding="utf-8")

    assert menu.index("Historial de maquina Vision % Pass/Fail</li>") < menu.index(
        "Historial de prueba electrica</li>"
    )
    assert 'data-permiso-seccion="Historial de maquinas calidad"' in menu
    assert 'data-permiso-boton="Historial de prueba electrica"' in menu
    assert '"boton": "Historial de prueba electrica"' in catalogo
    assert "'Historial de prueba electrica'" in auth
    assert "mostrarHistorialPruebaElectrica" in menu


def test_template_tiene_columnas_sin_barcode_paginacion_y_excel(app):
    with app.test_request_context(
        "/control_resultados/historial_prueba_electrica"
    ):
        html = render_template(
            "Control de resultados/historial_prueba_electrica_ajax.html",
            hoy="2026-09-18",
        )

    for heading in ("Línea", "Fecha", "Hora", "QR", "Lote", "Resultado"):
        assert f">{heading}<" in html
    assert ">Barcode<" not in html
    assert html.count("data-hpel-filter-field=") == 6
    assert 'id="hpel-pagination"' in html
    assert 'id="hpel-btn-export-excel"' in html
    assert "Exportar Excel" in html
    assert "Historial de prueba electrica" in html
    assert '<option value="1000" selected>1000</option>' in html
    assert "historial_prueba_electrica.js" in html


def test_api_filtra_ts_history_prueba_electrica_y_numera_pagina(client, monkeypatch):
    captured = []

    def fake_execute_query(sql, params, fetch):
        captured.append((sql, params, fetch))
        if fetch == "one":
            return {"n": 450}
        return [
            {
                "id": 852,
                "fecha": dt.date(2026, 9, 18),
                "hora": dt.time(8, 5, 7),
                "linea": "D2",
                "qr": "QR-PRUEBA-ELECTRICA",
                "lote": "ASSYLINE-260918-001",
                "resultado": "OK",
            }
        ]

    monkeypatch.setattr(modulo, "execute_query", fake_execute_query)
    _login_superadmin(client, monkeypatch)

    response = client.get(
        "/api/control_resultados/historial_prueba_electrica"
        "?page=2&per_page=200"
        "&fecha_desde=2026-09-17&fecha_hasta=2026-09-18"
        "&hora_desde=07%3A30&hora_hasta=18%3A15"
        "&linea=D2&qr=PRUEBA&lote=ASSYLINE"
        "&cf_fecha=2026-09-18&cf_hora=08%3A05"
        "&cf_linea=D2&cf_qr=ELECTRICA&cf_lote=260918&cf_resultado=OK"
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload == {
        "success": True,
        "rows": [
            {
                "numero": 201,
                "linea": "D2",
                "fecha": "2026-09-18",
                "hora": "08:05:07",
                "qr": "QR-PRUEBA-ELECTRICA",
                "lote": "ASSYLINE-260918-001",
                "resultado": "OK",
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
    assert "FROM history_prueba_electrica" in count_sql
    assert "ts >= %s" in count_sql
    assert "ts < DATE_ADD(%s, INTERVAL 1 DAY)" in count_sql
    assert "TIME(ts) >= %s" in count_sql
    assert "TIME(ts) <= %s" in count_sql
    assert "CAST(DATE(ts) AS CHAR) LIKE %s" in count_sql
    assert "CAST(TIME(ts) AS CHAR) LIKE %s" in count_sql
    assert "resultado LIKE %s" in count_sql
    assert "linea, raw AS qr" in data_sql
    assert "lot_no AS lote, resultado" in data_sql
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
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("No debe consultar")
        ),
    )
    _login_superadmin(client, monkeypatch)

    response = client.get(
        "/api/control_resultados/historial_prueba_electrica?hora_desde=25%3A10",
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
                "id": 852,
                "fecha": dt.date(2026, 9, 18),
                "hora": dt.time(7, 4, 3),
                "linea": "D2",
                "qr": "QR-PRUEBA-ELECTRICA",
                "lote": "ASSYLINE-260918-001",
                "resultado": "NG",
            }
        ]

    monkeypatch.setattr(modulo, "execute_query", fake_execute_query)
    _login_superadmin(client, monkeypatch)

    response = client.get(
        "/api/control_resultados/historial_prueba_electrica/export"
        "?page=2&per_page=100&linea=D2&cf_lote=ASSYLINE"
    )

    assert response.status_code == 200
    assert response.mimetype == (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert "historial_prueba_electrica_" in response.headers["Content-Disposition"]
    sheet = load_workbook(BytesIO(response.data)).active
    assert sheet.title == "Prueba electrica"
    assert sheet.freeze_panes == "A2"
    assert [cell.value for cell in sheet[1]] == [
        "#", "Línea", "Fecha", "Hora", "QR", "Lote", "Resultado",
    ]
    assert [cell.value for cell in sheet[2]] == [
        101,
        "D2",
        "2026-09-18",
        "07:04:03",
        "QR-PRUEBA-ELECTRICA",
        "ASSYLINE-260918-001",
        "NG",
    ]
    assert "Barcode" not in [cell.value for cell in sheet[1]]
    sql, params, fetch = captured[0]
    assert fetch == "all"
    assert "FROM history_prueba_electrica" in sql
    assert "raw_barcode" not in sql
    assert params[-2:] == (100, 100)


def test_rutas_estan_registradas_y_exigen_sesion(client):
    response = client.get(
        "/api/control_resultados/historial_prueba_electrica",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code in {302, 401}

    export_response = client.get(
        "/api/control_resultados/historial_prueba_electrica/export"
    )
    assert export_response.status_code in {302, 401}
