"""Historial de Sub Material: pasta, mask y squeegee (2026-09-22).

Cubre lo que no es trivial: el formateo de valores que MySQL devuelve como
Decimal/date, que mask y squeegee compartan tabla sin compartir columnas, y
que el filtro de codigo de squeegee mire las dos columnas de herramental.
"""

import time
from datetime import date, datetime
from decimal import Decimal

from app.api.control_calidad import historial_sub_material as hsm


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


def test_formatea_lo_que_mysql_devuelve_como_objeto():
    assert hsm._fmt_valor(datetime(2026, 9, 22, 13, 49, 1)) == "2026-09-22 13:49:01"
    assert hsm._fmt_valor(date(2026, 9, 22)) == "2026-09-22"
    # issued_quantity es DECIMAL(15,4): 500.0000 no debe verse asi en la tabla.
    assert hsm._fmt_valor(Decimal("500.0000")) == "500"
    assert hsm._fmt_valor(Decimal("2.5000")) == "2.5"
    assert hsm._fmt_valor(None) == ""


def test_mask_y_squeegee_comparten_tabla_con_columnas_distintas():
    mask, squeegee = hsm._TIPOS["mask"], hsm._TIPOS["squeegee"]
    assert mask["tabla"] == squeegee["tabla"] == "tooling_plan_assignment_smd"

    claves_mask = [c[0] for c in mask["columnas"]]
    claves_sq = [c[0] for c in squeegee["columnas"]]
    assert "mask" in claves_mask and "squeegee" not in claves_mask
    assert "squeegee" in claves_sq and "squeegee_2" in claves_sq
    assert "mask" not in claves_sq

    # El plan lleva hasta dos squeegees; el filtro de codigo mira los dos.
    assert squeegee["codigo_sql"] == ["squeegee_code", "squeegee_code_2"]
    assert mask["codigo_sql"] == ["metal_mask_code"]


def test_tipo_desconocido_da_404(client):
    _login(client)
    assert client.get("/api/historial-sub-material/zzz/data").status_code == 404
    assert client.get("/api/historial-sub-material/zzz/opciones").status_code == 404


def test_filtro_de_codigo_de_squeegee_cubre_las_dos_columnas(client, monkeypatch):
    capturado = {}
    monkeypatch.setattr(hsm, "execute_query", _fake_query(capturado))
    _login(client)

    client.get("/api/historial-sub-material/squeegee/data?codigo=SQ340")

    assert "squeegee_code LIKE %s OR squeegee_code_2 LIKE %s" in capturado["sql"]
    assert capturado["params"][:2] == ("%SQ340%", "%SQ340%")


def test_cada_tipo_filtra_por_su_columna_de_fecha(client, monkeypatch):
    # La pasta no tiene columna DATE: se filtra sobre removed_from_cold_at.
    esperado = {
        "pasta": "DATE(removed_from_cold_at)>=%s",
        "mask": "working_date>=%s",
        "squeegee": "working_date>=%s",
    }
    _login(client)
    for tipo, clausula in esperado.items():
        capturado = {}
        monkeypatch.setattr(hsm, "execute_query", _fake_query(capturado))
        client.get(f"/api/historial-sub-material/{tipo}/data?fecha_desde=2026-09-01")
        assert clausula in capturado["sql"], tipo
        assert capturado["params"][0] == "2026-09-01", tipo


def test_pasta_resalta_scrap_y_cancelado():
    fila = {"status": "SCRAP"}
    assert hsm._fmt_row(fila, hsm._TIPOS["pasta"])["_destacar"] is True
    assert hsm._fmt_row({"status": "CANCELLED"}, hsm._TIPOS["pasta"])["_destacar"] is True
    assert hsm._fmt_row({"status": "CONSUMED"}, hsm._TIPOS["pasta"])["_destacar"] is False


def test_filtros_de_columna_desconocidos_se_ignoran(client, monkeypatch):
    capturado = {}
    monkeypatch.setattr(hsm, "execute_query", _fake_query(capturado))
    _login(client)

    # cf_DROP no existe; cf_mask no es columna de squeegee.
    client.get("/api/historial-sub-material/squeegee/data?cf_DROP=1&cf_mask=x")

    assert "DROP" not in capturado["sql"]
    assert "metal_mask_code" not in capturado["sql"]
    assert capturado["params"] == (1000, 0)


def test_los_tres_renders_conservan_su_url_historica(client, monkeypatch):
    """El sidebar y los permisos en BD apuntan a estas URLs: no deben cambiar."""
    monkeypatch.setattr(hsm, "execute_query", _fake_query({}))
    _login(client)

    for url, tipo in hsm._RUTAS_RENDER.items():
        html = client.get(url).get_data(as_text=True)
        assert f'data-modulo="submat-{tipo}"' in html, url
        assert f'data-api-base="/api/historial-sub-material/{tipo}"' in html, url
        assert html.count("data-hist-filter-field=") == len(
            hsm._TIPOS[tipo]["columnas"]
        ), url
        # Cada filtro declarado debe tener su control en el fragmento.
        for par in html.split('data-filtros="')[1].split('"')[0].split(","):
            if not par:
                continue
            assert f'id="submat-{tipo}-{par.split(":")[0]}"' in html, (url, par)
