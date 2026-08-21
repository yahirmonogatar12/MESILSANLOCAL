from datetime import datetime
from flask import Flask
from unittest.mock import patch

from app.api.control_proceso import almacen_embarques as ae


def _aplicar_filtros(query_string=""):
    app = Flask(__name__)
    path = f"/api/almacen-embarques/entradas{query_string}"
    with app.test_request_context(path):
        return ae._aplicar_filtros_historial_embarques(
            "SELECT * FROM embarques_entrada_material WHERE 1=1",
            [],
            ["entry_folio", "part_number"],
        )


def _obtener_limite(query_string=""):
    app = Flask(__name__)
    path = f"/api/almacen-embarques/entradas{query_string}"
    with app.test_request_context(path):
        return ae._obtener_limite_historial_embarques()


def test_historial_embarques_sin_fecha_limita_a_periodo_vigente():
    sql, params = _aplicar_filtros()

    assert ae.SHIPPING_TABLES["inventory_closures"] in sql
    assert "MAX(closed_at)" in sql
    assert params == []


def test_historial_embarques_con_rango_fecha_permite_periodos_cerrados():
    sql, params = _aplicar_filtros("?fecha_desde=2026-05-01&fecha_hasta=2026-05-31")

    assert ae.SHIPPING_TABLES["inventory_closures"] not in sql
    assert "DATE(COALESCE(movement_at, created_at)) >= %s" in sql
    assert "DATE(COALESCE(movement_at, created_at)) <= %s" in sql
    assert params == ["2026-05-01", "2026-05-31"]


def test_historial_embarques_con_fecha_y_busqueda_mantiene_parametros():
    sql, params = _aplicar_filtros("?fecha_desde=2026-05-01&search=ABC123")

    assert ae.SHIPPING_TABLES["inventory_closures"] not in sql
    assert "COALESCE(entry_folio, '') LIKE %s" in sql
    assert "COALESCE(part_number, '') LIKE %s" in sql
    assert params == ["2026-05-01", "%ABC123%", "%ABC123%"]


def test_limite_historial_embarques_sin_filtros_usa_carga_inicial():
    assert _obtener_limite() == 300


def test_limite_historial_embarques_con_fecha_usa_limite_de_export():
    assert _obtener_limite("?fecha_desde=2026-05-01&fecha_hasta=2026-05-31") == 5000


def test_limite_historial_embarques_con_busqueda_usa_limite_de_export():
    assert _obtener_limite("?search=ABC123") == 5000


def test_limite_historial_embarques_con_tipo_usa_limite_de_export():
    assert _obtener_limite("?tipo=OS%26D") == 5000


def test_historial_retorno_filtra_tipo_normalizado():
    app = Flask(__name__)
    with patch.object(ae, "execute_query", return_value=[]) as mocked_query:
        with app.test_request_context(
            "/api/almacen-embarques/retorno?fecha_desde=2026-08-12&fecha_hasta=2026-08-12&tipo=OS%26D"
        ):
            rows = ae._obtener_historial_retorno_almacen_embarques(limit=3)

    sql, params = mocked_query.call_args.args[:2]
    assert rows == []
    assert "SUBSTRING_INDEX(COALESCE(reason, ''), '/', 1)" in sql
    assert params == ("2026-08-12", "2026-08-12", "OS&D", 3)


def _movimiento_retorno_row(quantity_primary, quantity_secondary, detail="Exceso"):
    return {
        "movement_type": "return",
        "movement_label": "Retorno",
        "record_id": 15,
        "fecha": "2026-08-12",
        "hora": "11:54:16",
        "folio": "EMB-RET-20260812-115416-985",
        "part_number": "ACQ30500846",
        "quantity_primary": quantity_primary,
        "quantity_secondary": quantity_secondary,
        "product_model": "pending",
        "customer": "LG",
        "zone_code": "pending",
        "location_value": "",
        "detail": detail,
        "departure_code": None,
        "registered_by": "Rubi Garcia",
        "last_adjusted_by": None,
        "last_adjusted_at": None,
    }


def _obtener_movimientos_con_rows(rows):
    app = Flask(__name__)
    with patch.object(ae, "execute_query", return_value=rows):
        with app.test_request_context("/api/almacen-embarques/movimientos?tipo=return"):
            return ae._obtener_movimientos_editables_almacen_embarques(limit=5)


def test_movimientos_editables_retorno_entrada_muestra_cantidad_retorno():
    rows = _obtener_movimientos_con_rows([_movimiento_retorno_row(14, 0)])

    assert rows[0]["display_quantity"] == 14
    assert rows[0]["return_quantity"] == 14
    assert rows[0]["loss_quantity"] == 0
    assert rows[0]["return_movement_kind"] == "entry"


def test_movimientos_editables_salida_retorno_muestra_cantidad_salida():
    rows = _obtener_movimientos_con_rows([_movimiento_retorno_row(0, 13)])

    assert rows[0]["display_quantity"] == 13
    assert rows[0]["return_quantity"] == 0
    assert rows[0]["loss_quantity"] == 13
    assert rows[0]["return_movement_kind"] == "exit"


def test_historial_modificaciones_movimientos_filtra_y_normaliza():
    row = {
        "id": 7,
        "movement_type": "exit",
        "record_id": 99,
        "folio": "EMB-SAL-20260821-153000-001",
        "part_number": "EBR30299355",
        "adjustment_action": "update",
        "previous_values_json": '{"quantity": 4, "departure_code": "NPX1"}',
        "new_values_json": '{"quantity": 5, "departure_code": "NPX2"}',
        "changed_fields_json": '{"quantity": {"previous": 4, "new": 5}, "departure_code": {"previous": "NPX1", "new": "NPX2"}}',
        "notes": "Correccion manual",
        "adjusted_by": "Jesus Gamez",
        "adjusted_at": datetime(2026, 8, 21, 15, 30, 5),
    }
    app = Flask(__name__)

    with patch.object(ae, "execute_query", return_value=[row]) as mocked_query:
        with app.test_request_context(
            "/api/almacen-embarques/movimientos/historial"
            "?search=EBR302&tipo=exit&accion=update"
            "&fecha_desde=2026-08-21&fecha_hasta=2026-08-21"
        ):
            payload = ae._obtener_historial_modificaciones_almacen_embarques(limit=5)

    sql, params = mocked_query.call_args.args[:2]
    assert "a.movement_type = %s" in sql
    assert "a.adjustment_action = %s" in sql
    assert "DATE(a.adjusted_at) >= %s" in sql
    assert "DATE(a.adjusted_at) <= %s" in sql
    assert params[:4] == ("exit", "update", "2026-08-21", "2026-08-21")
    assert params[-1] == 5
    assert payload["summary"]["total_records"] == 1
    assert payload["rows"][0]["fecha"] == "2026-08-21"
    assert payload["rows"][0]["hora"] == "15:30:05"
    assert payload["rows"][0]["movement_label"] == "Salida"
    assert payload["rows"][0]["action_label"] == "Modificacion"
    assert payload["rows"][0]["changed_fields"] == "Cantidad, Departure"
    assert "Cantidad: 4" in payload["rows"][0]["previous_values"]
    assert "Departure: NPX1" in payload["rows"][0]["previous_values"]
    assert "Cantidad: 5" in payload["rows"][0]["new_values"]
    assert "Departure: NPX2" in payload["rows"][0]["new_values"]


def test_historial_eliminaciones_movimientos_resume_snapshot_operativo():
    row = {
        "id": 8,
        "movement_type": "exit",
        "record_id": 100,
        "folio": "EMB-SAL-20260821-132553-970",
        "part_number": "EAV62074702",
        "adjustment_action": "delete",
        "previous_values_json": (
            '{"id": 7172, "folio": "EMB-SAL-20260821-132553-970", '
            '"part_number": "EAV62074702", "quantity": 720, '
            '"previous_quantity": -131040, "new_quantity": -131760, '
            '"product_model": "pending", "customer": "LG"}'
        ),
        "new_values_json": "{}",
        "changed_fields_json": '{"deleted": true}',
        "notes": "OKOKOK",
        "adjusted_by": "Rubi Garcia",
        "adjusted_at": datetime(2026, 8, 21, 14, 45, 39),
    }
    app = Flask(__name__)

    with patch.object(ae, "execute_query", return_value=[row]):
        with app.test_request_context(
            "/api/almacen-embarques/movimientos/historial?accion=delete"
        ):
            payload = ae._obtener_historial_modificaciones_almacen_embarques(limit=5)

    previous_values = payload["rows"][0]["previous_values"]
    assert payload["rows"][0]["action_label"] == "Eliminacion"
    assert payload["rows"][0]["changed_fields"] == "Registro eliminado"
    assert previous_values == (
        "Folio: EMB-SAL-20260821-132553-970 | "
        "No. parte: EAV62074702 | Cantidad: 720"
    )
    assert payload["rows"][0]["new_values"] == ""
