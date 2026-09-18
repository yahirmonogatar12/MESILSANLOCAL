import datetime as dt
from io import BytesIO
import time
from pathlib import Path

from flask import render_template
from openpyxl import load_workbook

from app import routes
from app.api.control_resultados import historial_verificacion_display as modulo


def _login_superadmin(client, monkeypatch):
    monkeypatch.setattr(
        routes.auth_system,
        "obtener_rol_principal_usuario",
        lambda _username: "superadmin",
    )
    with client.session_transaction() as session:
        session["usuario"] = "test"
        session["_last_activity_touch_ts"] = int(time.time())


def test_sidebar_registra_display_despues_de_ensamble_y_en_catalogo():
    menu = Path(
        "app/templates/LISTAS/LISTA_DE_CONTROL_DE_RESULTADOS.html"
    ).read_text(encoding="utf-8")
    catalogo = Path("app/static/permisos_dropdowns.js").read_text(encoding="utf-8")

    assert menu.index("Historial de input SMT</li>") < menu.index(
        "Historial de input IMD</li>"
    )
    assert menu.index("Historial de input IMD</li>") < menu.index(
        "Historial de input ensamble</li>"
    )
    assert menu.index("Historial de input ensamble</li>") < menu.index(
        "Historial de verificacion display</li>"
    )
    assert 'data-permiso-boton="Historial de verificacion display"' in menu
    assert '"boton": "Historial de verificacion display"' in catalogo
    assert "mostrarHistorialVerificacionDisplay" in menu


def test_template_tiene_columnas_paginacion_y_excel(app):
    with app.test_request_context(
        "/control_resultados/historial_verificacion_display"
    ):
        html = render_template(
            "Control de resultados/historial_verificacion_display_ajax.html",
            hoy="2026-09-18",
        )

    for heading in ("Línea", "Fecha", "Hora", "QR", "Barcode", "Lote"):
        assert f">{heading}<" in html
    assert html.count("data-hvd-filter-field=") == 6
    assert 'id="hvd-pagination"' in html
    assert 'id="hvd-btn-export-excel"' in html
    assert "Exportar Excel" in html
    assert "Historial de verificacion display" in html
    assert '<option value="1000" selected>1000</option>' in html
    assert "historial_verificacion_display.js" in html


def test_api_filtra_ouput_main_y_numera_pagina(client, monkeypatch):
    captured = []

    def fake_execute_query(sql, params, fetch):
        captured.append((sql, params, fetch))
        if fetch == "one":
            return {"n": 450}
        return [
            {
                "id": 52,
                "fecha": dt.date(2026, 9, 18),
                "hora": dt.time(9, 6, 4),
                "linea": "M2",
                "qr": "QR-DISPLAY",
                "barcode": "BC-DISPLAY",
                "lote": "LOT-D",
            }
        ]

    monkeypatch.setattr(modulo, "execute_query", fake_execute_query)
    _login_superadmin(client, monkeypatch)

    response = client.get(
        "/api/control_resultados/historial_verificacion_display"
        "?page=2&per_page=200"
        "&fecha_desde=2026-09-17&fecha_hasta=2026-09-18"
        "&hora_desde=07%3A30&hora_hasta=18%3A15"
        "&linea=M2&qr=DISPLAY&barcode=BC&lote=LOT-D"
        "&cf_fecha=2026-09-18&cf_hora=09%3A06"
        "&cf_linea=M2&cf_qr=QR&cf_barcode=DISPLAY&cf_lote=LOT"
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["rows"] == [
        {
            "numero": 201,
            "linea": "M2",
            "fecha": "2026-09-18",
            "hora": "09:06:04",
            "qr": "QR-DISPLAY",
            "barcode": "BC-DISPLAY",
            "lote": "LOT-D",
        }
    ]
    assert payload["total"] == 450
    assert payload["page"] == 2
    assert payload["per_page"] == 200
    assert payload["total_pages"] == 3

    count_sql, count_params, count_fetch = captured[0]
    data_sql, data_params, data_fetch = captured[1]
    assert count_fetch == "one"
    assert data_fetch == "all"
    assert "FROM ouput_main" in count_sql
    assert "ts >= %s" in count_sql
    assert "ts < DATE_ADD(%s, INTERVAL 1 DAY)" in count_sql
    assert "TIME(ts) >= %s" in count_sql
    assert "TIME(ts) <= %s" in count_sql
    assert "CAST(DATE(ts) AS CHAR) LIKE %s" in count_sql
    assert "CAST(TIME(ts) AS CHAR) LIKE %s" in count_sql
    assert "raw AS qr" in data_sql
    assert "raw_barcode AS barcode" in data_sql
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
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("No debe consultar")
        ),
    )
    _login_superadmin(client, monkeypatch)

    response = client.get(
        "/api/control_resultados/historial_verificacion_display"
        "?fecha_desde=18-09-2026",
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 400
    assert "AAAA-MM-DD" in response.get_json()["error"]


def test_export_excel_descarga_pagina_visible_con_barcode(client, monkeypatch):
    captured = []

    def fake_execute_query(sql, params, fetch):
        captured.append((sql, params, fetch))
        return [
            {
                "id": 52,
                "fecha": dt.date(2026, 9, 18),
                "hora": dt.time(9, 6, 4),
                "linea": "M2",
                "qr": "QR-DISPLAY",
                "barcode": "BC-DISPLAY",
                "lote": "LOT-D",
            }
        ]

    monkeypatch.setattr(modulo, "execute_query", fake_execute_query)
    _login_superadmin(client, monkeypatch)

    response = client.get(
        "/api/control_resultados/historial_verificacion_display/export"
        "?page=2&per_page=200&linea=M2&cf_qr=DISPLAY"
    )

    assert response.status_code == 200
    assert response.mimetype == (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert "historial_verificacion_display_" in response.headers["Content-Disposition"]
    sheet = load_workbook(BytesIO(response.data)).active
    assert sheet.title == "Verificacion display"
    assert sheet.freeze_panes == "A2"
    assert [cell.value for cell in sheet[1]] == [
        "#", "Línea", "Fecha", "Hora", "QR", "Barcode", "Lote",
    ]
    assert [cell.value for cell in sheet[2]] == [
        201, "M2", "2026-09-18", "09:06:04", "QR-DISPLAY", "BC-DISPLAY", "LOT-D",
    ]
    sql, params, fetch = captured[0]
    assert fetch == "all"
    assert "FROM ouput_main" in sql
    assert "raw_barcode AS barcode" in sql
    assert params[-2:] == (200, 200)


def test_rutas_estan_registradas_y_exigen_sesion(client):
    response = client.get(
        "/api/control_resultados/historial_verificacion_display",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code in {302, 401}

    export_response = client.get(
        "/api/control_resultados/historial_verificacion_display/export"
    )
    assert export_response.status_code in {302, 401}
