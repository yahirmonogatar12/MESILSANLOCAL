from flask import Flask

from app.api.control_proceso import control_scrap as m


def test_filtros_de_columna_solo_lista_blanca():
    app = Flask(__name__)
    url = "/?start=2026-09-01&end=2026-09-02&cf_motivo=FALT&cf_xx=1;DROP&cf_cantidad=0"
    with app.test_request_context(url):
        where, params = m._filtros()
    assert "COALESCE(motivo_scrap_texto, '') LIKE %s" in where
    assert "CAST(cantidad AS CHAR) LIKE %s" in where
    assert "DROP" not in where and "%1;DROP%" not in params
    assert params[-2:] == ["%FALT%", "%0%"]
