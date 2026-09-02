from datetime import date, datetime

from flask import Flask

from app.api.control_calidad import historial_liberacion_oqc as oqc


def test_oqc_filters_swap_dates_and_ignore_invalid_options():
    app = Flask(__name__)

    with app.test_request_context(
        "/?search=  BX-01  &fecha_desde=2026-09-02&fecha_hasta=2026-09-01"
        "&status=nope&source=manual&qc=unknown"
    ):
        filters = oqc._filtros_historial_oqc()

    assert filters["search"] == "BX-01"
    assert filters["fecha_desde"] == date(2026, 9, 1)
    assert filters["fecha_hasta"] == date(2026, 9, 2)
    assert filters["status"] == ""
    assert filters["source"] == "manual"
    assert filters["qc"] == "unknown"


def test_oqc_where_clause_includes_supported_filters():
    filters = {
        "search": "ABC123",
        "fecha_desde": date(2026, 9, 1),
        "fecha_hasta": date(2026, 9, 2),
        "status": "released",
        "source": "batch",
        "qc": "passed",
    }

    where_sql, params = oqc._where_historial_oqc(filters)

    assert "COALESCE(o.released_at, o.created_at) >= %s" in where_sql
    assert "COALESCE(o.released_at, o.created_at) < %s" in where_sql
    assert "o.status = %s" in where_sql
    assert "o.source = %s" in where_sql
    assert "COALESCE(o.qc_passed, 0) = 1" in where_sql
    assert "COALESCE(o.oqc_folio, '') LIKE %s" in where_sql
    assert params[:4] == [
        "2026-09-01 00:00:00",
        "2026-09-03 00:00:00",
        "released",
        "batch",
    ]
    assert params.count("%ABC123%") == 13


def test_oqc_limit_defaults_and_caps_requested_limit():
    app = Flask(__name__)
    no_filters = {
        "search": "",
        "fecha_desde": None,
        "fecha_hasta": None,
        "status": "",
        "source": "",
        "qc": "",
    }

    with app.test_request_context("/"):
        assert oqc._obtener_limite_historial_oqc(no_filters) == oqc.OQC_LIMIT_INICIAL

    with app.test_request_context("/?limit=999999"):
        assert oqc._obtener_limite_historial_oqc(no_filters) == oqc.OQC_LIMIT_FILTRADO


def test_oqc_serializes_release_row_for_table():
    row = {
        "id": 10,
        "release_dt": datetime(2026, 9, 2, 8, 30, 45),
        "oqc_folio": "OQC2609020001",
        "box_code": "BOX-01",
        "part_number": "EBR123",
        "quantity": 12,
        "product_model": "MODEL-A",
        "customer": "LGE",
        "destination": "Embarques",
        "qc_passed": 1,
        "status": "received_shipping",
        "source": "manual",
        "released_by": 126,
        "employee_id": "9001",
        "released_by_name": "QA User",
        "exit_record_folio": "OQC-EXIT-1",
        "entry_folio": "AE-IN-1",
        "entry_at": datetime(2026, 9, 2, 9, 0),
        "exit_folio": "AE-OUT-1",
        "exit_at": datetime(2026, 9, 2, 10, 0),
    }

    payload = oqc._serializar_liberacion_oqc(row)

    assert payload["fecha"] == "2026-09-02"
    assert payload["hora"] == "08:30:45"
    assert payload["qc_result"] == "OK"
    assert payload["status_label"] == "Recibida embarques"
    assert payload["source_label"] == "Manual"
    assert payload["shipping_status"] == "Salida embarques"
