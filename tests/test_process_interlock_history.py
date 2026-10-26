"""Process interlock History (2026-09-22).

Cubre lo que no es trivial: el formateo de duraciones, el total agregado de
tiempo detenido y los filtros que se traducen a milisegundos.
"""

import time

from app.api.control_calidad import process_interlock_history as pih


def _login(client):
    with client.session_transaction() as session:
        session["usuario"] = "test"
        session["_last_activity_touch_ts"] = int(time.time())


def _fake_query(capturado, total=0, ms=0):
    def fake_execute_query(sql, params=None, fetch=None):
        if fetch == "one":
            return {"n": total, "ms": ms}
        capturado.update(sql=sql, params=params)
        return []

    return fake_execute_query


def test_formatea_duraciones():
    assert pih._fmt_duracion(155) == "0.2s"
    assert pih._fmt_duracion(36092) == "36.1s"
    assert pih._fmt_duracion(90000) == "1m 30s"
    assert pih._fmt_duracion(3661000) == "1h 01m 01s"
    assert pih._fmt_duracion(None) == "0.0s"


def test_data_api_devuelve_el_tiempo_detenido_agregado(client, monkeypatch):
    capturado = {}
    monkeypatch.setattr(
        pih, "execute_query", _fake_query(capturado, total=7157, ms=3661000)
    )
    _login(client)

    payload = client.get("/api/process-interlock/data?per_page=100").get_json()

    # El total abarca todo lo filtrado, no solo la pagina: es el dato por el
    # que existe la tabla.
    assert payload["total"] == 7157
    assert payload["total_ms"] == 3661000
    assert payload["total_detenido"] == "1h 01m 01s"
    assert payload["total_pages"] == 72


def test_filtros_de_tarjeta_se_traducen_a_sql(client, monkeypatch):
    capturado = {}
    monkeypatch.setattr(pih, "execute_query", _fake_query(capturado))
    _login(client)

    client.get(
        "/api/process-interlock/data?incluir_cortos=1&fecha_desde=2026-09-01"
        "&linea=SA&turno=DIA&modo=smt&motivo=NOT_SCANNED&min_seg=30&busqueda=PLAN"
    )

    assert capturado["params"][:5] == ("2026-09-01", "SA", "DIA", "smt", "NOT_SCANNED")
    # min_seg llega en segundos y se compara en milisegundos.
    assert capturado["params"][5] == 30000
    # busqueda abarca detalle, lote y parte.
    assert capturado["params"][6:9] == ("%PLAN%", "%PLAN%", "%PLAN%")
    assert capturado["sql"].count("LIKE %s") == 3


def test_filtro_de_columna_duracion_usa_segundos(client, monkeypatch):
    capturado = {}
    monkeypatch.setattr(pih, "execute_query", _fake_query(capturado))
    _login(client)

    client.get("/api/process-interlock/data?incluir_cortos=1&cf_duracion=1.5")
    assert "duration_ms>=%s" in capturado["sql"]
    assert capturado["params"][0] == 1500

    # Texto no numerico no puede devolver la tabla entera.
    capturado = {}
    monkeypatch.setattr(pih, "execute_query", _fake_query(capturado))
    client.get("/api/process-interlock/data?incluir_cortos=1&cf_duracion=abc")
    assert "AND 1=0" in capturado["sql"]


def test_filtros_de_columna_desconocidos_se_ignoran(client, monkeypatch):
    capturado = {}
    monkeypatch.setattr(pih, "execute_query", _fake_query(capturado))
    _login(client)

    client.get("/api/process-interlock/data?incluir_cortos=1&cf_DROP=1&cf_event_id=x")

    assert "DROP" not in capturado["sql"]
    assert "event_id" not in capturado["sql"]
    assert capturado["params"] == (1000, 0)


def test_template_declara_el_contrato_del_js(client, monkeypatch):
    monkeypatch.setattr(pih, "execute_query", _fake_query({}))
    _login(client)

    html = client.get("/process-interlock-history-ajax").get_data(as_text=True)

    assert html.count("data-hist-filter-field=") == len(pih.COLUMNAS) + len(pih.VISION_COLUMNAS)
    assert 'data-modulo="interlock"' in html
    assert 'data-api-base="/api/process-interlock"' in html
    assert "historial_tabla.js" in html
    # Cada filtro declarado debe tener su control en el fragmento.
    for par in html.split('data-filtros="')[1].split('"')[0].split(","):
        sufijo = par.split(":")[0]
        assert f'id="pih-{sufijo}"' in html, sufijo


def test_solo_se_resalta_el_escaneo_rechazado():
    base = {"working_date": None, "duration_ms": 0, "cycle_id": 1}
    assert pih._fmt_row({**base, "stop_reason": "SCAN_REJECTED"})["_destacar"] is True
    assert pih._fmt_row({**base, "stop_reason": "NOT_SCANNED"})["_destacar"] is False


def test_opciones_usa_el_sufijo_del_select_como_clave(client, monkeypatch):
    """historial_tabla.js rellena el <select> cuyo sufijo es la clave.

    Con plurales ("lineas") los selects se quedarian vacios sin fallar.
    """
    monkeypatch.setattr(
        pih, "execute_query", lambda sql, params=None, fetch=None: [{"v": "SA"}]
    )
    _login(client)

    payload = client.get("/api/process-interlock/opciones").get_json()
    html = client.get("/process-interlock-history-ajax").get_data(as_text=True)

    assert set(payload) == {"linea", "turno", "modo", "motivo"}
    for sufijo in payload:
        assert f'id="pih-{sufijo}"' in html, sufijo


def test_por_defecto_oculta_las_detecciones_cortas(client, monkeypatch):
    """Los NOT_SCANNED de fraccion de segundo son el tiempo de escaneo.

    Un SCAN_REJECTED corto SI es un error real, por eso la regla mira el
    motivo y no solo la duracion.
    """
    capturado = {}
    monkeypatch.setattr(pih, "execute_query", _fake_query(capturado))
    _login(client)

    client.get("/api/process-interlock/data")
    assert "NOT (stop_reason=%s AND duration_ms<%s)" in capturado["sql"]
    assert capturado["params"][:2] == ("NOT_SCANNED", 3000)

    # El checkbox del fragmento las vuelve a incluir.
    capturado = {}
    monkeypatch.setattr(pih, "execute_query", _fake_query(capturado))
    client.get("/api/process-interlock/data?incluir_cortos=1")
    assert "NOT (stop_reason=" not in capturado["sql"]


# ── Pestana "Rechazos escaner ICT" (vision_check_rejections_QA, 2026-10-26) ──


def test_vision_fechas_locales_se_filtran_como_rango_utc(client, monkeypatch):
    """La tabla guarda UTC; el usuario filtra en hora de Mexico (-06:00)."""
    capturado = {}
    monkeypatch.setattr(pih, "execute_query", _fake_query(capturado))
    _login(client)

    client.get(
        "/api/process-interlock/vision/data?fecha_desde=2026-10-26&fecha_hasta=2026-10-26"
        "&linea=M1&estacion=ICT-01&tipo=Sin historial&busqueda=EBR437"
    )

    sql, params = capturado["sql"], capturado["params"]
    # Indice en rejected_at_utc: la columna no se envuelve en funciones.
    assert "rejected_at_utc>=%s" in sql and "rejected_at_utc<%s" in sql
    assert params[:2] == ("2026-10-26 06:00:00", "2026-10-27 06:00:00")
    assert params[2:4] == ("M1", "ICT-01")
    # El select manda la etiqueta; se filtra por el codigo guardado.
    assert params[4] == "SIN_HISTORIAL"
    assert params[5:7] == ("%EBR437%", "%EBR437%")
    assert params[-2:] == (1000, 0)


def test_vision_filtro_de_columna_tipo_acepta_la_etiqueta(client, monkeypatch):
    capturado = {}
    monkeypatch.setattr(pih, "execute_query", _fake_query(capturado))
    _login(client)

    client.get("/api/process-interlock/vision/data?cf_tipo=ng en&cf_hora=2026-10-26 08")
    assert "rejection_type IN (%s)" in capturado["sql"]
    assert "CAST(CONVERT_TZ(rejected_at_utc, '+00:00', '-06:00') AS CHAR) LIKE %s" in capturado["sql"]
    # En el orden de las columnas: Fecha / hora antes que Tipo.
    assert capturado["params"][:2] == ("%2026-10-26 08%", "NG")

    # Texto que no es ningun tipo: sin resultados, no la tabla entera.
    capturado = {}
    monkeypatch.setattr(pih, "execute_query", _fake_query(capturado))
    client.get("/api/process-interlock/vision/data?cf_tipo=zzz")
    assert capturado["params"][0] == ""


def test_vision_fila_legible_y_ng_resaltado():
    from datetime import datetime

    base = {
        "hora": datetime(2026, 10, 26, 8, 16, 32), "station_code": "ICT-01", "line": "M3",
        "code": "EBR41039119922610230504", "reason": "Ultima inspeccion de Vision: NG.",
        "machine": "M3", "inspected_at": datetime(2026, 10, 26, 8, 16, 0),
    }
    ng = pih._fmt_vision_row({**base, "rejection_type": "NG"})
    assert ng["tipo"] == "NG en Vision" and ng["_destacar"] is True
    assert ng["hora"] == "2026-10-26 08:16:32" and ng["inspeccion"] == "2026-10-26 08:16:00"
    sin = pih._fmt_vision_row({**base, "rejection_type": "SIN_HISTORIAL", "inspected_at": None})
    assert sin["tipo"] == "Sin historial" and sin["_destacar"] is False and sin["inspeccion"] == ""


def test_vision_template_y_opciones_cumplen_el_contrato_del_js(client, monkeypatch):
    monkeypatch.setattr(
        pih, "execute_query", lambda sql, params=None, fetch=None: [{"v": "M1"}]
    )
    _login(client)

    html = client.get("/process-interlock-history-ajax").get_data(as_text=True)
    payload = client.get("/api/process-interlock/vision/opciones").get_json()

    assert 'data-modulo="vision-rechazos"' in html
    assert 'data-api-base="/api/process-interlock/vision"' in html
    assert 'data-hist-tab="vision"' in html and 'data-hist-tab-panel="vision"' in html
    filtros = html.split('data-modulo="vision-rechazos"')[1].split('data-filtros="')[1].split('"')[0]
    for par in filtros.split(","):
        assert f'id="pvr-{par.split(":")[0]}"' in html, par
    assert payload["tipo"] == ["Sin historial", "NG en Vision", "No es EBR", "Escaneo repetido"]
    for sufijo in payload:
        assert f'id="pvr-{sufijo}"' in html, sufijo


def test_vision_escaneo_repetido_se_filtra_y_no_se_resalta(client, monkeypatch):
    capturado = {}
    monkeypatch.setattr(pih, "execute_query", _fake_query(capturado))
    _login(client)

    client.get("/api/process-interlock/vision/data?tipo=Escaneo repetido")
    assert capturado["params"][0] == "REPETIDO"

    fila = pih._fmt_vision_row({"rejection_type": "REPETIDO", "code": "EBR1"})
    assert fila["tipo"] == "Escaneo repetido" and fila["_destacar"] is False
