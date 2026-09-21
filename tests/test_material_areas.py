import time
from decimal import Decimal

import pytest
from flask import Flask

from app.api.control_material import material_smd as m
from app.api.shared import permisos


def where(query):
    with Flask(__name__).test_request_context("/?" + query):
        return m._where(m._vista())


def test_entradas_y_salidas_filtran_por_su_fecha_sin_cancelados():
    sql, params = where("vista=entradas&start=2026-09-01&end=2026-09-02")
    assert "COALESCE(cancelado, 0) = %s" in sql and "fecha_recibo >= %s" in sql
    assert params == [0, "2026-09-01", "2026-09-02"]

    sql, params = where("vista=salidas&start=2026-09-01")
    assert "cms.fecha_salida >= %s" in sql and params == [0, "2026-09-01", "2026-09-01"]


def test_inventario_ignora_fechas_y_siempre_lleva_params():
    # Sin params execute_query no formatea y los %% de DATE_FORMAT quedarian dobles.
    sql, params = where("vista=inventario&start=2026-09-01")
    assert "fecha" not in sql and params == [0]


def test_inventario_general_filtra_sobre_los_totales():
    sql, params = where("vista=inventario_general&start=2026-09-01&cf_stock=100")
    assert "g.stock > %s" in sql and "COALESCE(CAST(g.stock AS CHAR), '') LIKE %s" in sql
    assert "fecha" not in sql and params == [0, "%100%"]


def test_filtros_de_columna_solo_de_la_vista():
    sql, params = where("vista=salidas&start=2026-09-01&cf_proceso=Mount&cf_cliente=X&cf_zz=1;DROP")
    assert "cms.proceso_salida" in sql and "cliente" not in sql and "DROP" not in sql
    assert params[-1] == "%Mount%"


def test_vista_invalida_y_decimales():
    with pytest.raises(ValueError):
        where("vista=otra")
    assert m._numero(Decimal("500.00")) == 500 and m._numero(Decimal("1.5")) == 1.5


class SinPermiso:
    def obtener_rol_principal_usuario(self, _username):
        return "consulta"

    def verificar_permiso_boton(self, *_args, **_kwargs):
        return False


@pytest.mark.parametrize("ruta", ["/material/smd", "/api/material/smd", "/api/material/smd/export"])
def test_sin_permiso_responde_403(client, monkeypatch, ruta):
    monkeypatch.setattr(permisos, "_auth", lambda: SinPermiso())
    with client.session_transaction() as sess:
        sess["usuario"] = "consulta"
        sess["_last_activity_touch_ts"] = int(time.time())
    assert client.get(ruta, headers={"Content-Type": "application/json"}).status_code == 403
