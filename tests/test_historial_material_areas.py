"""Historial de cambio de material de IMD y ASSY (2026-09-22).

Cubre lo que no es trivial: la derivacion de la columna Tipo (en Python y su
equivalente en SQL), la diferencia de columnas entre areas y el WHERE.
"""

import time

from app.api.control_calidad import historial_material_areas as hma


def _login(client):
    with client.session_transaction() as session:
        session["usuario"] = "test"
        session["_last_activity_touch_ts"] = int(time.time())


def _fake_query(capturado, total=0):
    def fake_execute_query(sql, params=None, fetch=None):
        if fetch == "one":
            return {"n": total}
        capturado.update(sql=sql, params=params)
        return []

    return fake_execute_query


def test_tipo_se_deriva_como_en_el_cliente_flutter():
    assert hma._tipo("MD-EAN66257201-202609180001", "0") == "MD"
    assert hma._tipo("C-123", "RACK 4") == "RACK"
    assert hma._tipo("C-123", "POSICION 12") == "CNT"
    # MD gana sobre RACK, igual que el `isMD ? ... : isRack ? ...` del cliente.
    assert hma._tipo("MD-X", "RACK 1") == "MD"


def test_assy_tiene_ubicacion_e_imd_no():
    claves_imd = [c[0] for c in hma._AREAS["imd"]["columnas"]]
    claves_assy = [c[0] for c in hma._AREAS["assy"]["columnas"]]
    assert "ubicacion" not in claves_imd
    assert "ubicacion" in claves_assy
    assert claves_imd[:4] == ["fecha", "hora", "linea", "tipo"]


def test_area_desconocida_da_404(client):
    _login(client)
    assert client.get("/historial-material/main/ajax").status_code == 404
    assert client.get("/api/historial-material/main/data").status_code == 404


def test_template_pinta_una_columna_filtrable_por_campo(client, monkeypatch):
    monkeypatch.setattr(hma, "execute_query", _fake_query({}))
    _login(client)

    html = client.get("/historial-material/assy/ajax").get_data(as_text=True)

    assert html.count("data-mat-filter-field=") == len(hma._AREAS["assy"]["columnas"])
    assert 'data-area="assy"' in html
    assert 'id="mathist-assy-table"' in html
    assert "historial_material_area.js" in html


def test_data_api_pagina_y_filtra(client, monkeypatch):
    capturado = {}
    monkeypatch.setattr(hma, "execute_query", _fake_query(capturado, total=250))
    _login(client)

    response = client.get(
        "/api/historial-material/imd/data?page=2&per_page=100"
        "&fecha_desde=2026-09-01&linea=P3&material=EAF&cf_contenedor=MD-"
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert (payload["total"], payload["page"], payload["total_pages"]) == (250, 2, 3)
    assert "history_material_imd" in capturado["sql"]
    assert capturado["params"][:4] == ("2026-09-01", "P3", "EAF%", "%MD-%")
    assert capturado["params"][-2:] == (100, 100)


def test_filtro_de_columna_tipo_se_traduce_a_sql(client, monkeypatch):
    casos = {
        "MD": ("contenedor LIKE %s", ("MD-%",)),
        "RACK": ("contenedor NOT LIKE %s AND posicion LIKE %s", ("MD-%", "RACK%")),
        "CNT": ("contenedor NOT LIKE %s AND posicion NOT LIKE %s", ("MD-%", "RACK%")),
    }
    _login(client)
    for valor, (sql_esperado, params_esperados) in casos.items():
        capturado = {}
        monkeypatch.setattr(hma, "execute_query", _fake_query(capturado))
        client.get(f"/api/historial-material/assy/data?cf_tipo={valor}")
        assert sql_esperado in capturado["sql"], valor
        assert capturado["params"][: len(params_esperados)] == params_esperados, valor
        # Un '%' literal en el SQL rompe el formateo de pymysql al llevar params.
        assert "'" not in capturado["sql"], valor

    # Un texto que no es ningun tipo no debe devolver toda la tabla.
    capturado = {}
    monkeypatch.setattr(hma, "execute_query", _fake_query(capturado))
    client.get("/api/historial-material/assy/data?cf_tipo=zzz")
    assert "AND 1=0" in capturado["sql"]


def test_filtros_de_columna_desconocidos_se_ignoran(client, monkeypatch):
    capturado = {}
    monkeypatch.setattr(hma, "execute_query", _fake_query(capturado))
    _login(client)

    client.get("/api/historial-material/imd/data?cf_DROP=1&cf_ubicacion=x")

    # cf_DROP no existe y cf_ubicacion no es columna de IMD.
    assert "DROP" not in capturado["sql"]
    assert "ubicacion" not in capturado["sql"]
    assert capturado["params"] == (1000, 0)
