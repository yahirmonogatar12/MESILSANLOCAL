from datetime import datetime
import time

from flask import render_template

from app.api.shared import vision_helpers
from app.api.control_resultados import historial_vision


def test_build_history_vision_query_supports_pagination_and_column_filters(app):
    with app.test_request_context(
        "/api/vision/data?fecha_desde=2026-06-26&cf_numero_parte=EBR4103"
        "&cf_resultado=OK"
    ):
        sql, params = vision_helpers._build_history_vision_query(1000, 1000)
        count_sql, count_params = vision_helpers._build_history_vision_count_query()

    assert "part_code LIKE %s" in sql
    assert "result LIKE %s" in sql
    assert sql.endswith("LIMIT %s OFFSET %s")
    assert params == ("2026-06-26", "%EBR4103%", "%OK%", 1000, 1000)
    assert count_sql.startswith("SELECT COUNT(*) AS n")
    assert " LIMIT " not in count_sql
    assert count_params == ("2026-06-26", "%EBR4103%", "%OK%")


def test_build_vision_stops_query_has_no_global_result_limit(app):
    with app.test_request_context(
        "/api/vision/stops?fecha_desde=2026-06-26&fecha_hasta=2026-06-26"
        "&linea=M1"
    ):
        sql, params = vision_helpers._build_vision_stops_query()

    assert "s.stop_datetime IS NOT NULL" in sql
    assert "s.recovery_status IN ('open', 'confirmed')" in sql
    assert "ORDER BY s.stop_datetime DESC" in sql
    assert " LIMIT " not in sql
    assert params == ("2026-06-26", "2026-06-26", "M1")


def test_build_vision_stops_query_applies_page_and_column_filters(app):
    with app.test_request_context(
        "/api/vision/stops?cf_numero_parte=EBR4103&cf_run_attempt_count=1"
    ):
        sql, params = vision_helpers._build_vision_stops_query(100, 200)
        count_sql, count_params = vision_helpers._build_vision_stops_count_query()

    assert "s.part_code LIKE %s" in sql
    assert "CAST(s.run_attempt_count AS CHAR) LIKE %s" in sql
    assert sql.endswith("LIMIT %s OFFSET %s")
    assert params == ("%EBR4103%", "%1%", 100, 200)
    assert count_sql.startswith("SELECT COUNT(*) AS n")
    assert "AS total_stop_seconds" in count_sql
    assert " LIMIT " not in count_sql
    assert count_params == ("%EBR4103%", "%1%")


def test_build_vision_stops_query_can_audit_failed_recoveries(app):
    with app.test_request_context("/api/vision/stops?estado=failed_recovery"):
        sql, params = vision_helpers._build_vision_stops_query()

    assert "s.recovery_status = %s" in sql
    assert params == ("failed_recovery",)


def test_fetch_ajustes_for_stops_batches_and_groups(monkeypatch):
    captured = {}

    def fake_execute_query(sql, params, fetch):
        captured.update(sql=sql, params=params, fetch=fetch)
        return [
            {
                "linea": "M1",
                "session_id": "adjust-1",
                "tecnico": "Yahir",
                "inicio_local": datetime(2026, 6, 26, 11, 21, 19),
                "fin_local": datetime(2026, 6, 26, 11, 22, 46),
            }
        ]

    monkeypatch.setattr(vision_helpers, "execute_query", fake_execute_query)
    rows = [
        {
            "source_uid": "stop-1",
            "linea": "M1",
            "stop_datetime": datetime(2026, 6, 26, 11, 21, 15, 155000),
            "stable_run_datetime": datetime(2026, 6, 26, 11, 23, 8, 935000),
        },
        {
            "source_uid": "stop-2",
            "linea": "M2",
            "stop_datetime": datetime(2026, 6, 26, 12, 0),
            "stable_run_datetime": None,
        },
    ]

    grouped = vision_helpers._fetch_ajustes_for_stops(rows)

    assert "station_events_QA" in captured["sql"]
    assert "JSON_EXTRACT" in captured["sql"]
    assert captured["fetch"] == "all"
    assert grouped["stop-1"] == [
        {
            "session_id": "adjust-1",
            "tecnico": "Yahir",
            "inicio_local": "2026-06-26 11:21:19",
            "fin_local": "2026-06-26 11:22:46",
        }
    ]
    assert "stop-2" not in grouped


def test_vision_stops_route_is_registered(app):
    rules = {rule.rule for rule in app.url_map.iter_rules()}
    assert "/api/vision/stops" in rules
    assert "/api/vision/stops/export" in rules


def test_vision_stops_api_serializes_rows(client, monkeypatch):
    row = {
        "source_uid": "stop-1",
        "linea": "M1",
        "part_code": "EBR43713604",
        "stop_datetime": datetime(2026, 6, 26, 11, 21, 15, 155000),
        "stable_run_datetime": datetime(2026, 6, 26, 11, 23, 8, 935000),
        "real_stop_seconds": 113.78,
        "real_stop_prov": 113.78,
        "reaccion_seconds": 4.946,
        "run_attempt_count": 2,
        "recovery_status": "confirmed",
    }
    monkeypatch.setattr(historial_vision, "_build_vision_stops_query", lambda: ("sql", ()))
    monkeypatch.setattr(
        historial_vision,
        "execute_query",
        lambda sql, params, fetch: [row],
    )
    monkeypatch.setattr(
        historial_vision,
        "_fetch_ajustes_for_stops",
        lambda rows: {
            "stop-1": [
                {
                    "session_id": "adjust-1",
                    "tecnico": "Yahir",
                    "inicio_local": "2026-06-26 11:21:19",
                    "fin_local": "2026-06-26 11:22:46",
                }
            ]
        },
    )
    with client.session_transaction() as session:
        session["usuario"] = "test"
        session["_last_activity_touch_ts"] = int(time.time())

    response = client.get("/api/vision/stops")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload[0]["real_stop_seconds"] == 113.78
    assert payload[0]["run_attempt_count"] == 2
    assert payload[0]["ajustes"][0]["tecnico"] == "Yahir"


def test_vision_stops_api_returns_pagination_metadata(client, monkeypatch):
    captured = {}
    row = {
        "source_uid": "stop-401",
        "linea": "M4",
        "part_code": "EBR41039122",
        "stop_datetime": datetime(2026, 6, 26, 17, 3, 29),
        "stable_run_datetime": datetime(2026, 6, 26, 17, 3, 30),
        "real_stop_seconds": 1.0,
        "real_stop_prov": 1.0,
        "reaccion_seconds": 0.5,
        "run_attempt_count": 1,
        "recovery_status": "confirmed",
    }
    monkeypatch.setattr(
        historial_vision,
        "_build_vision_stops_count_query",
        lambda: ("count sql", ()),
    )

    def fake_build_query(limit=None, offset=0):
        captured.update(limit=limit, offset=offset)
        return "data sql", (limit, offset)

    monkeypatch.setattr(historial_vision, "_build_vision_stops_query", fake_build_query)

    def fake_execute_query(sql, params, fetch):
        if fetch == "one":
            return {"n": 401, "total_stop_seconds": 3661.651}
        return [row]

    monkeypatch.setattr(historial_vision, "execute_query", fake_execute_query)
    monkeypatch.setattr(historial_vision, "_fetch_ajustes_for_stops", lambda rows: {})
    with client.session_transaction() as session:
        session["usuario"] = "test"
        session["_last_activity_touch_ts"] = int(time.time())

    response = client.get("/api/vision/stops?page=3&per_page=200")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["total"] == 401
    assert payload["total_stop_seconds"] == 3661.651
    assert payload["page"] == 3
    assert payload["per_page"] == 200
    assert payload["total_pages"] == 3
    assert payload["rows"][0]["numero_parte"] == "EBR41039122"
    assert captured == {"limit": 200, "offset": 400}


def test_vision_data_api_paginates_1000_by_default(client, monkeypatch):
    captured = {}
    row = {
        "id": 1501,
        "linea": "M4",
        "fecha": "2026-06-26",
        "hora": "17:04:45",
        "numero_parte": "EBR41039122",
        "qr": "QR-1501",
        "barcode": "BAR-1501",
        "resultado": "OK",
    }
    monkeypatch.setattr(
        historial_vision,
        "_build_history_vision_count_query",
        lambda: ("count sql", ()),
    )

    def fake_build_query(limit=None, offset=0):
        captured.update(limit=limit, offset=offset)
        return "data sql", (limit, offset)

    monkeypatch.setattr(historial_vision, "_build_history_vision_query", fake_build_query)

    def fake_execute_query(sql, params, fetch):
        return {"n": 1501} if fetch == "one" else [row]

    monkeypatch.setattr(historial_vision, "execute_query", fake_execute_query)
    with client.session_transaction() as session:
        session["usuario"] = "test"
        session["_last_activity_touch_ts"] = int(time.time())

    response = client.get("/api/vision/data?page=2")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["total"] == 1501
    assert payload["page"] == 2
    assert payload["per_page"] == 1000
    assert payload["total_pages"] == 2
    assert payload["rows"][0]["id"] == 1501
    assert captured == {"limit": 1000, "offset": 1000}


def test_history_vision_template_contains_stops_tab(app):
    with app.test_request_context("/historial_vision/ajax"):
        html = render_template("Control de resultados/history_vision.html")

    assert 'data-tab="paros"' in html
    assert 'id="vision-paros-panel"' in html
    assert 'id="vision-stops-table"' in html
    assert 'id="vision-stops-loading"' in html
    assert 'id="vision-btn-export-stops"' in html
    assert 'id="vision-stops-pagination"' in html
    assert 'id="vision-stops-per-page"' in html
    assert 'id="vision-stops-page-input"' in html
    assert 'id="vision-stops-total-time"' in html
    assert 'id="vision-records-pagination"' in html
    assert 'id="vision-records-per-page"' in html
    assert 'id="vision-records-page-input"' in html
    assert html.count('<option value="1000" selected>1000</option>') == 2
    assert 'id="vision-preview-qr"' in html
    assert 'id="vision-preview-barcode"' in html
    assert html.count("data-vision-filter-field=") == 14
    assert 'data-vision-filter-table="records"' in html
    assert 'data-vision-filter-table="stops"' in html
    stops_panel = html.split('id="vision-paros-panel"', 1)[1].split(
        'id="vision-preview-modal"', 1
    )[0]
    assert "<th>Estado</th>" not in stops_panel
    assert "Reaccion" not in stops_panel


def test_export_vision_stops_excel_reuses_filtered_rows(client, monkeypatch):
    captured = {}
    row = {
        "source_uid": "stop-1",
        "linea": "M4",
        "part_code": "EBR41039122",
        "stop_datetime": datetime(2026, 6, 26, 17, 3, 29, 921000),
        "stable_run_datetime": datetime(2026, 6, 26, 17, 3, 30, 378000),
        "real_stop_seconds": 18.256,
        "real_stop_prov": 18.256,
        "reaccion_seconds": 17.917,
        "run_attempt_count": 1,
        "recovery_status": "confirmed",
    }
    monkeypatch.setattr(historial_vision, "_build_vision_stops_query", lambda: ("sql", ()))
    monkeypatch.setattr(
        historial_vision,
        "execute_query",
        lambda sql, params, fetch: [row],
    )
    monkeypatch.setattr(
        historial_vision,
        "_fetch_ajustes_for_stops",
        lambda rows: {
            "stop-1": [
                {
                    "tecnico": "Yahir",
                    "inicio_local": "2026-06-26 17:03:10",
                    "fin_local": "2026-06-26 17:03:31",
                }
            ]
        },
    )

    def fake_excel_response(items, headers, keys, **kwargs):
        captured.update(items=items, headers=headers, keys=keys, kwargs=kwargs)
        return historial_vision.jsonify({"success": True})

    monkeypatch.setattr(historial_vision, "excel_response_ict", fake_excel_response)
    with client.session_transaction() as session:
        session["usuario"] = "test"
        session["_last_activity_touch_ts"] = int(time.time())

    response = client.get(
        "/api/vision/stops/export?fecha_desde=2026-06-26&fecha_hasta=2026-06-26&linea=M4"
    )

    assert response.status_code == 200
    assert "Estado" not in captured["headers"]
    assert "recovery_status" not in captured["keys"]
    assert "Reaccion (s)" not in captured["headers"]
    assert "reaccion_seconds" not in captured["keys"]
    assert captured["items"][0]["paro_real_seconds"] == 18.256
    assert "Yahir" in captured["items"][0]["tecnico_ajuste"]
    assert captured["kwargs"]["sheet"] == "Paros Vision"


def test_vision_image_info_includes_qr_and_barcode(client, monkeypatch):
    monkeypatch.setattr(
        historial_vision,
        "_get_history_vision_record",
        lambda record_id: {
            "id": record_id,
            "machine_name": "M4",
            "part_code": "EBR41039122",
            "result": "OK",
            "qr_payload": "QR-EBR41039122-20260626",
            "serial_qr": "QR-FALLBACK",
            "barcode": "BAR-00123456789",
            "source_file": "vision.log",
            "machine_ip": "192.168.1.52",
        },
    )
    monkeypatch.setattr(
        historial_vision,
        "_resolve_history_vision_image",
        lambda record: {
            "reference_datetime": "2026-06-26 17:04:31.750000",
            "resolved_path": r"\\192.168.1.52\Result M4\image.jpg",
            "share_name": "Result M4",
            "side_folder": "OK",
            "delta_seconds": 0.2,
            "searched_paths": [],
        },
    )
    with client.session_transaction() as session:
        session["usuario"] = "test"
        session["_last_activity_touch_ts"] = int(time.time())

    response = client.get("/api/vision/image-info?id=123")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["qr"] == "QR-EBR41039122-20260626"
    assert payload["barcode"] == "BAR-00123456789"
