from flask import Flask

from app.api.control_resultados import inventario_imd as m


def _como_pymysql(llamadas):
    """Imita a pymysql: con parametros aplica `sql % params`."""

    def fake(sql, params=None, fetch=None):
        if params:
            sql % tuple(params)
        llamadas.append((sql, params))
        return []

    return fake


def _llamar(monkeypatch, vista, url):
    llamadas = []
    monkeypatch.setattr(m, "execute_query", _como_pymysql(llamadas))
    with Flask(__name__).test_request_context(url):
        resp = vista.__wrapped__()
    assert not isinstance(resp, tuple), resp[0].get_json()
    return llamadas[0]


def test_inventario_general_filtra_sin_romper_el_formato_de_fecha(monkeypatch):
    sql, params = _llamar(
        monkeypatch,
        m.api_inventario_general,
        "/api/inventario_general?q=EBR37437083&stock=>0",
    )
    assert params == [
        m.FECHA_HORA_SQL,
        m.FECHA_HORA_SQL,
        "%EBR37437083%",
        "%EBR37437083%",
    ]
    assert "'%Y" not in sql


def test_inventario_general_sin_filtros_tambien_usa_parametros(monkeypatch):
    _, params = _llamar(monkeypatch, m.api_inventario_general, "/api/inventario_general")
    assert params == [m.FECHA_HORA_SQL, m.FECHA_HORA_SQL]


def test_ubicacion_con_fechas_y_busqueda(monkeypatch):
    sql, params = _llamar(
        monkeypatch,
        m.api_ubicacion,
        "/api/ubicacion?desde=2026-11-01&hasta=2026-11-20&q=EBR&ubicacion=A1",
    )
    assert params == [
        m.FECHA_SQL,
        "2026-11-01",
        m.FECHA_SQL,
        "2026-11-20",
        "%EBR%",
        "%EBR%",
        "%EBR%",
        "%EBR%",
        "A1",
        m.FECHA_SQL,
    ]
    assert "'%Y" not in sql
