import datetime as dt
from io import BytesIO
from pathlib import Path
import time

from flask import render_template
from openpyxl import load_workbook

from app import routes
from app.api.control_resultados import historial_produccion_imd as modulo


def _login_superadmin(client, monkeypatch):
    monkeypatch.setattr(
        routes.auth_system,
        "obtener_rol_principal_usuario",
        lambda _username: "superadmin",
    )
    with client.session_transaction() as session:
        session["usuario"] = "test"
        session["_last_activity_touch_ts"] = int(time.time())


def test_sidebar_agrega_imd_y_conserva_los_otros_historiales():
    menu = Path(
        "app/templates/LISTAS/LISTA_DE_CONTROL_DE_RESULTADOS.html"
    ).read_text(encoding="utf-8")
    catalogo = Path("app/static/permisos_dropdowns.js").read_text(encoding="utf-8")
    tabs = Path("app/static/js/sidebar-tabs.js").read_text(encoding="utf-8")

    for nombre in (
        "Historial de produccion ensamble",
        "Historial de produccion SMT",
        "Historial de produccion IMD",
    ):
        assert f'data-permiso-boton="{nombre}"' in menu
        assert f'"boton": "{nombre}"' in catalogo
    for etiqueta in (
        "Historial de input ensamble",
        "Historial de input SMT",
        "Historial de input IMD",
    ):
        assert f">{etiqueta}</li>" in menu
        assert f"'{etiqueta}'" in tabs
    assert menu.index("Historial de input SMT</li>") < menu.index("Historial de input IMD</li>")
    assert menu.index("Historial de input IMD</li>") < menu.index("Historial de input ensamble</li>")
    assert "mostrarHistorialProduccionImd" in menu


def test_template_imd_tiene_columnas_paginacion_y_excel_sin_barcode(app):
    with app.test_request_context("/control_resultados/historial_produccion_imd"):
        html = render_template(
            "Control de resultados/historial_produccion_imd_ajax.html",
            hoy="2026-09-18",
        )

    for heading in ("Línea", "Fecha", "Hora", "QR", "Lote"):
        assert f">{heading}<" in html
    assert ">Barcode<" not in html
    assert html.count("data-hpi-filter-field=") == 5
    assert 'id="hpi-pagination"' in html
    assert '<option value="1000" selected>1000</option>' in html
    assert 'id="hpi-btn-export-excel"' in html
    assert "Exportar Excel" in html
    assert "Historial de input IMD" in html
    assert "historial_produccion_imd.js" in html


def test_api_imd_pagina_filtra_ts_y_numera_absoluto(client, monkeypatch):
    captured = []

    def fake_execute_query(sql, params, fetch):
        captured.append((sql, params, fetch))
        if fetch == "one":
            return {"n": 450}
        return [
            {
                "id": 351759,
                "fecha": dt.date(2026, 9, 18),
                "hora": dt.time(9, 6, 5),
                "linea": "IMD-1",
                "qr": "I22609;IMD;LOT-8",
                "lote": "LOT-8",
            }
        ]

    monkeypatch.setattr(modulo, "execute_query", fake_execute_query)
    _login_superadmin(client, monkeypatch)

    response = client.get(
        "/api/control_resultados/historial_produccion_imd"
        "?page=2&per_page=200"
        "&fecha_desde=2026-09-17&fecha_hasta=2026-09-18"
        "&hora_desde=07%3A30&hora_hasta=18%3A15"
        "&linea=IMD-1&qr=I22609&lote=LOT-8"
        "&cf_fecha=2026-09-18&cf_hora=09%3A06"
        "&cf_linea=IMD&cf_qr=IMD&cf_lote=LOT"
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "success": True,
        "rows": [
            {
                "numero": 201,
                "linea": "IMD-1",
                "fecha": "2026-09-18",
                "hora": "09:06:05",
                "qr": "I22609;IMD;LOT-8",
                "lote": "LOT-8",
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
    assert "FROM output_imd" in count_sql
    assert "ts >= %s" in count_sql
    assert "ts < DATE_ADD(%s, INTERVAL 1 DAY)" in count_sql
    assert "TIME(ts) >= %s" in count_sql
    assert "TIME(ts) <= %s" in count_sql
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


def test_export_imd_descarga_pagina_visible_sin_barcode(client, monkeypatch):
    captured = []

    def fake_execute_query(sql, params, fetch):
        captured.append((sql, params, fetch))
        return [
            {
                "id": 351759,
                "fecha": dt.date(2026, 9, 18),
                "hora": dt.time(7, 4, 3),
                "linea": "IMD-1",
                "qr": "QR-IMD",
                "lote": "LOT-IMD",
            }
        ]

    monkeypatch.setattr(modulo, "execute_query", fake_execute_query)
    _login_superadmin(client, monkeypatch)

    response = client.get(
        "/api/control_resultados/historial_produccion_imd/export"
        "?page=2&per_page=100&linea=IMD-1&cf_lote=LOT"
    )

    assert response.status_code == 200
    assert response.mimetype == (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert "historial_input_imd_" in response.headers["Content-Disposition"]
    sheet = load_workbook(BytesIO(response.data)).active
    assert sheet.title == "Input IMD"
    assert sheet.freeze_panes == "A2"
    assert [cell.value for cell in sheet[1]] == [
        "#", "Línea", "Fecha", "Hora", "QR", "Lote",
    ]
    assert [cell.value for cell in sheet[2]] == [
        101, "IMD-1", "2026-09-18", "07:04:03", "QR-IMD", "LOT-IMD",
    ]
    assert "Barcode" not in [cell.value for cell in sheet[1]]
    sql, params, fetch = captured[0]
    assert fetch == "all"
    assert "FROM output_imd" in sql
    assert "raw_barcode" not in sql
    assert params[-2:] == (100, 100)


def test_imd_rechaza_fecha_invalida_y_rutas_exigen_sesion(client, monkeypatch):
    monkeypatch.setattr(
        modulo,
        "execute_query",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("No debe consultar")),
    )
    _login_superadmin(client, monkeypatch)
    response = client.get(
        "/api/control_resultados/historial_produccion_imd?fecha_desde=18-09-2026"
    )
    assert response.status_code == 400
    assert "AAAA-MM-DD" in response.get_json()["error"]

    with client.session_transaction() as session:
        session.clear()
    for path in (
        "/api/control_resultados/historial_produccion_imd",
        "/api/control_resultados/historial_produccion_imd/export",
    ):
        assert client.get(path).status_code in {302, 401}
