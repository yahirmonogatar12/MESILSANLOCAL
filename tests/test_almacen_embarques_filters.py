from flask import Flask

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
