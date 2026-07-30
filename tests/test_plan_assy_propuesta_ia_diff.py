"""Recalculo del dia: la propuesta se aplica sobre los lotes que ya existen."""

from datetime import date


GRID = {
    "version": 3,
    "grupos": [
        {"bloque": "B1", "lotes": [
            # mismo lote del plan pero con menos cantidad
            {"part_no": "EBR1", "fecha": "2026-07-30", "linea": "M1", "turno": "DIA",
             "qty": 400, "uph": 100, "ct": 36.0, "sec": 1,
             "inv_despues": 900, "falta_el": "2026-08-04"},
            # lote arrancado (lleva 80): bajar de 300 a 250 sigue siendo viable
            {"part_no": "EBR2", "fecha": "2026-07-30", "linea": "M1", "turno": "DIA",
             "qty": 250, "uph": 100, "ct": 36.0, "sec": 2,
             "inv_despues": -40, "falta_el": "2026-08-01"},
            # lote arrancado que lleva 200: la propuesta pide 150, ya no se puede
            {"part_no": "EBR4", "fecha": "2026-07-30", "linea": "M1", "turno": "DIA",
             "qty": 150, "uph": 100, "ct": 36.0, "sec": 3},
            # lote arrancado al que la propuesta le SUBE la cantidad: si aplica
            {"part_no": "EBR5", "fecha": "2026-07-30", "linea": "M1", "turno": "DIA",
             "qty": 700, "uph": 100, "ct": 36.0, "sec": 4,
             "inv_despues": 120, "falta_el": "2026-07-30"},
        ]},
        {"bloque": "B3", "lotes": [
            # cambia de linea y de grupo
            {"part_no": "EBR3", "fecha": "2026-07-30", "linea": "M3", "turno": "DIA",
             "qty": 300, "uph": 100, "ct": 36.0, "sec": 1},
            # no hay lote capturado para esta parte
            {"part_no": "NUEVA", "fecha": "2026-07-30", "linea": "M3", "turno": "DIA",
             "qty": 120, "uph": 100, "ct": 36.0, "sec": 2},
        ]},
    ],
}

PLAN_MAIN = [
    {"lot_no": "L1", "f": date(2026, 7, 30), "part_no": "EBR1", "line": "M1",
     "plan_count": 500, "produced_count": 0, "output": 0, "status": "PLAN",
     "group_no": 1, "sequence": 1},
    # Arrancado: la cantidad se ajusta en cualquier direccion, con piso en
    # lo ya producido; linea/grupo/orden no se mueven.
    {"lot_no": "L2", "f": date(2026, 7, 30), "part_no": "EBR2", "line": "M1",
     "plan_count": 300, "produced_count": 80, "output": 0, "status": "EN PROGRESO",
     "group_no": 1, "sequence": 9},
    {"lot_no": "L6", "f": date(2026, 7, 30), "part_no": "EBR4", "line": "M1",
     "plan_count": 500, "produced_count": 200, "output": 0, "status": "PAUSADO",
     "group_no": 1, "sequence": 5},
    {"lot_no": "L7", "f": date(2026, 7, 30), "part_no": "EBR5", "line": "M1",
     "plan_count": 600, "produced_count": 100, "output": 0, "status": "PAUSADO",
     "group_no": 1, "sequence": 6},
    {"lot_no": "L3", "f": date(2026, 7, 30), "part_no": "EBR3", "line": "M1",
     "plan_count": 300, "produced_count": 0, "output": 0, "status": "PLAN",
     "group_no": 1, "sequence": 3},
    {"lot_no": "L4", "f": date(2026, 7, 30), "part_no": "VIEJA", "line": "D2",
     "plan_count": 200, "produced_count": 0, "output": 0, "status": "PLAN",
     "group_no": 2, "sequence": 1},
    {"lot_no": "L5", "f": date(2026, 7, 30), "part_no": "EBR1", "line": "M1",
     "plan_count": 999, "produced_count": 0, "output": 0, "status": "CANCELADO",
     "group_no": 1, "sequence": 4},
]


def _diff(monkeypatch):
    from app.api.control_produccion import plan_assy, part_planning

    monkeypatch.setattr(plan_assy, "execute_query",
                        lambda sql, params=(), fetch=None: list(PLAN_MAIN))
    monkeypatch.setattr(part_planning, "_ppy_propuesta_grid", lambda *_a, **_k: dict(GRID))
    return plan_assy._assy_diff_propuesta("prop-1", "ana")


def test_diff_propone_cambios_sobre_los_lotes_existentes(monkeypatch):
    d = _diff(monkeypatch)
    por_lote = {c["lot_no"]: c for c in d["cambios"]}

    # Baja de cantidad sobre el lote que ya existe: conserva su lot_no
    assert por_lote["L1"]["campos"] == ["cantidad"]
    assert por_lote["L1"]["despues"]["cantidad"] == 400
    assert por_lote["L1"]["bloqueado"] is None
    # Cambio de linea + grupo
    assert set(por_lote["L3"]["campos"]) == {"linea", "grupo", "secuencia"}
    assert por_lote["L3"]["despues"]["linea"] == "M3"
    assert por_lote["L3"]["despues"]["grupo"] == 3
    # Lote arrancado: bajar 300 -> 250 con 80 producidas es viable, pero el
    # cambio de grupo NO se aplica (la linea ya esta corriendo).
    assert por_lote["L2"]["bloqueado"] is None
    assert por_lote["L2"]["aplicables"] == ["cantidad"]
    assert set(por_lote["L2"]["campos"]) > {"cantidad"}
    assert por_lote["L2"]["producido"] == 80
    # Bajar por debajo de lo ya producido: no se puede
    assert por_lote["L6"]["bloqueado"] == "ya lleva 200 pzs producidas"
    # Un lote sin faltante cercano no es urgente: el umbral de piezas decide
    assert por_lote["L1"]["urgente"] is False
    # Aunque el ajuste sea chico, si queda faltante siempre vale la pena
    assert por_lote["L2"]["urgente"] is True
    assert por_lote["L2"]["razon"] == "queda faltante aun con este lote"
    # La falta es hoy mismo -> urgente
    assert por_lote["L7"]["urgente"] is True
    assert por_lote["L7"]["razon"] == "cubre el faltante del día"
    # Subirle la cantidad a un lote arrancado si se puede (sigue corriendo)
    assert por_lote["L7"]["bloqueado"] is None
    assert por_lote["L7"]["aplicables"] == ["cantidad"]
    assert por_lote["L7"]["despues"]["cantidad"] == 700


def test_diff_no_inventa_lotes_ni_toca_los_que_sobran(monkeypatch):
    d = _diff(monkeypatch)

    # La parte sin lote capturado NO se inserta: se reporta aparte
    assert [n["part_no"] for n in d["nuevos"]] == ["NUEVA"]
    # El lote que la propuesta ya no incluye solo se lista
    assert [s["lot_no"] for s in d["sobran"]] == ["L4"]
    # El CANCELADO no cuenta como lote existente ni estorba el emparejamiento
    assert "L5" not in {c["lot_no"] for c in d["cambios"]}
    assert "L5" not in {s["lot_no"] for s in d["sobran"]}


def test_aplicar_solo_toca_lo_permitido_por_lote(client, monkeypatch):
    """El servidor revalida contra el lote actual: al arrancado solo le ajusta
    la cantidad, aunque el navegador mande tambien linea y grupo."""
    from app.api.control_produccion import plan_assy
    from app.api.shared import permisos

    updates = []

    schedule = []
    filas = [dict(r) for r in PLAN_MAIN]   # copia mutable: el UPDATE se refleja

    def fake_query(sql, params=(), fetch=None):
        s = " ".join(str(sql).split())
        if s.startswith("SELECT status"):
            row = next(r for r in filas if r["lot_no"] == params[0])
            return dict(row, line=row["line"])
        if s.startswith("UPDATE plan_main"):
            updates.append((s, params))
            if "plan_count=%s" in s:
                next(r for r in filas if r["lot_no"] == params[-1])["plan_count"] = params[0]
        if s.startswith("SELECT COALESCE(SUM(plan_count),0)"):
            # suma de los lotes vigentes de esa parte ese dia
            return {"total": sum(r["plan_count"] for r in filas
                                 if r["part_no"] == params[0] and r["status"] != "CANCELADO")}
        if s.startswith("SELECT line, routing"):
            return {"line": "M1", "routing": 1}
        if s.startswith("INSERT INTO lg_schedule_daily"):
            schedule.append(params)
        return None

    monkeypatch.setattr(plan_assy, "execute_query", fake_query)
    monkeypatch.setattr(permisos, "puede_boton", lambda *_a, **_k: True)
    with client.session_transaction() as sess:
        sess["usuario"] = "ana"
        sess["roles"] = ["superadmin"]

    r = client.post("/api/plan/propuesta-ia/aplicar-cambios", json={"cambios": [
        # sin arrancar: se aplica todo
        {"lot_no": "L1", "cantidad": 400, "linea": "M3", "grupo": 3, "secuencia": 1},
        # arrancado: solo la cantidad, aunque manden linea y grupo
        {"lot_no": "L2", "cantidad": 250, "linea": "M4", "grupo": 5, "secuencia": 9},
        # arrancado y por debajo de lo producido: se omite
        {"lot_no": "L6", "cantidad": 150, "linea": "M1", "grupo": 1, "secuencia": 5},
    ]}).get_json()

    assert r["aplicados"] == 2
    assert r["omitidos"] == [{"lot_no": "L6", "motivo": "ya lleva 200 pzs producidas"}]
    assert "line=%s" in updates[0][0] and updates[0][1] == (400, "M3", 3, "L1")
    # al arrancado solo se le toca plan_count
    assert "line=%s" not in updates[1][0]
    assert updates[1][1] == (250, "L2")
    # El Schedule se reescribe una vez por parte tocada, con la SUMA de sus lotes
    # YA ACTUALIZADOS y sin contar cancelados (EBR1: L1=400, L5=999 CANCELADO).
    assert [(p[0], p[2]) for p in schedule] == [("EBR1", 400), ("EBR2", 250)]
    assert r["schedule"] == {"EBR1": 400, "EBR2": 250}
