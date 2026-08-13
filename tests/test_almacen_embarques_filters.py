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
