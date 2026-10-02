"""Trazabilidad de PCB: ASSY/IMD salen del snapshot por PCB (2026-10-02).

Antes del snapshot, de los consumos de relleno_historial. pcb_material_link/_imd
(poller apagado el 2026-09-11) ya no se lee: ligaba un material por PCB y en M3
el 85% era uno que la PCB no consumio.
"""

import time

from app.api.control_resultados import trazabilidad_pcb as tp


def _login(client):
    with client.session_transaction() as session:
        session["usuario"] = "test"
        session["_last_activity_touch_ts"] = int(time.time())


def _capturar(monkeypatch, respuestas=None):
    """Guarda la ultima consulta en `capturado` y todas en capturado['todas'].
    respuestas: lista de resultados a devolver en orden (luego [])."""
    capturado = {"todas": []}
    pendientes = list(respuestas or [])

    def fake_execute_query(sql, params=None, fetch=None):
        capturado.update(sql=sql, params=params)
        capturado.setdefault("todas", []).append((sql, params))
        return pendientes.pop(0) if pendientes else []

    monkeypatch.setattr(tp, "execute_query", fake_execute_query)
    return capturado


def _sin_poller(sql):
    assert "pcb_material_link" not in sql


def test_por_pcb_lee_snapshot_y_consumos_sin_poller(client, monkeypatch):
    capturado = _capturar(monkeypatch)
    _login(client)

    assert client.get("/api/trazabilidad_pcb/por_pcb?pcb=EBR123").status_code == 200

    snapshot, *consumos = capturado["todas"]
    assert "s.modo = 'MAIN'" in snapshot[0] and "s.modo = 'IMD'" in snapshot[0]
    assert "s.captured_at" in snapshot[0]  # hora del servidor, no la de la estacion
    # Una consulta de consumos por area, solo para PCBs sin snapshot.
    assert [("relleno_historial h" in s, "relleno_historial_imd h" in s) for s, _ in consumos] == [
        (True, False), (False, True)]
    for sql, params in capturado["todas"]:
        _sin_poller(sql)
        assert sql.count("%s") == len(params)
    assert all("NOT EXISTS (SELECT 1 FROM pcb_scan_snapshot s" in s for s, _ in consumos)


def test_por_pcb_lote_de_las_bolsas_previas_al_consumo(client, monkeypatch):
    # Un consumo (id 50) de un relleno que recibio dos bolsas antes y una despues.
    consumo = {"proceso": "ASSY", "input_main_id": 1, "pcb_serial": "EBR1", "ts": "2026-06-22 16:08:05",
               "lot_no": "L", "linea": "M3", "part_no": "P", "material_code": "EAE63087201",
               "posicion": "0", "consumo_id": 50, "relleno_id": 7, "saldo": 80, "refill_number": 1,
               "cantidad_inicial": 50, "cantidad_restante": 0, "qty_per_pcb": 1, "ubicacion": "", "spec": ""}
    entradas = [{"relleno_id": 7, "id": i, "bolsa": b, "cantidad_delta": 50}
                for i, b in ((10, "B1"), (20, "B2"), (60, "B3"))]
    lotes = [{"bolsa": "B1", "lote": "LOTE-A"}, {"bolsa": "B2", "lote": "LOTE-A"}, {"bolsa": "B3", "lote": "LOTE-B"}]
    _capturar(monkeypatch, respuestas=[[], [consumo], entradas, lotes])
    _login(client)

    items = client.get("/api/trazabilidad_pcb/por_pcb?pcb=EBR1&proceso=ASSY").get_json()["items"]

    assert len(items) == 1
    # Quedaban 80: B2 (50) no alcanza, B1 tambien estaba. B3 entro despues.
    # B1 y B2 son del mismo lote: el lote es seguro aunque la bolsa no.
    assert items[0]["numero_lote_material"] == "LOTE-A"
    assert items[0]["codigo_material_recibido"] == "2 bolsas posibles"
    assert items[0]["role"] == "CONSUMO" and items[0]["refill_number"] == 1


def test_por_proveedor_lee_snapshot_y_consumos_sin_poller(client, monkeypatch):
    capturado = _capturar(monkeypatch)
    _login(client)

    assert client.get("/api/trazabilidad_pcb/por_proveedor?material=2026061800843").status_code == 200

    sql = capturado["sql"]
    _sin_poller(sql)
    assert "m.modo='MAIN'" in sql and "m.modo='IMD'" in sql
    assert "FROM relleno_historial b" in sql and "FROM relleno_historial_imd b" in sql
    # 2 ramas ASSY + 2 IMD + SMT, cada una con material y lote.
    assert capturado["params"] == ["2026061800843%"] * 10
    assert sql.count("%s") == len(capturado["params"])


def test_materiales_por_lote_lee_snapshot_y_acota_sin_lote(client, monkeypatch):
    capturado = _capturar(monkeypatch)
    _login(client)

    data = client.get("/api/trazabilidad_pcb/materiales?fecha_inicio=2026-09-01&fecha_fin=2026-10-02").get_json()

    sql, params = capturado["sql"], capturado["params"]
    assert "s.modo = 'MAIN'" in sql and "s.modo = 'IMD'" in sql
    for tabla in ("trazabilidad_material_pcb t", "trazabilidad_material_pcb_imd t"):
        rama = sql.split(f"FROM {tabla}", 1)[1].split("UNION ALL", 1)[0]
        assert "NOT EXISTS (SELECT 1 FROM pcb_scan_snapshot x" in rama, tabla
    assert "NOT EXISTS" not in sql.split("FROM trazabilidad_material_pcb_smt t", 1)[1]
    assert sql.count("%s") == len(params)
    # Sin lote, el snapshot arranca 2 dias antes del fin, no el 1-sep.
    assert params.count("2026-09-30") == 2  # una vez por rama de snapshot (MAIN, IMD)
    assert "limita a 3 dias" in data["message"]

    capturado.clear()
    data = client.get("/api/trazabilidad_pcb/materiales?lot_no=ASSYLINE-260930").get_json()
    assert data["message"] == ""
    assert "s.pcb_ts >=" not in capturado["sql"]  # con lote no se acota por fecha


def test_por_proveedor_con_filtro_de_proceso_conserva_los_alias(client, monkeypatch):
    # El SELECT exterior lee d.proceso/d.pcb_serial: la primera rama del UNION
    # (la que queda con el filtro) tiene que nombrarlas.
    capturado = _capturar(monkeypatch)
    _login(client)
    for proceso in ("ASSY", "IMD", "SMT"):
        url = f"/api/trazabilidad_pcb/por_proveedor?material=X&proceso={proceso}"
        assert client.get(url).status_code == 200
        primera = capturado["sql"].split("FROM (", 1)[1].split("FROM ", 1)[0]
        assert f"'{proceso}' AS proceso" in primera, proceso


def test_bolsas_presentes_descarta_las_ya_gastadas():
    entradas = [{"id": i, "bolsa": f"B{i}", "cantidad_delta": 50} for i in (1, 2, 3, 4)]
    assert tp._bolsas_presentes(entradas, consumo_id=4, saldo=30) == ["B3"]
    assert tp._bolsas_presentes(entradas, consumo_id=4, saldo=60) == ["B2", "B3"]
    assert tp._bolsas_presentes(entradas, consumo_id=4, saldo=0) == ["B3"]
    assert tp._bolsas_presentes(entradas, consumo_id=4, saldo=999) == ["B1", "B2", "B3"]
