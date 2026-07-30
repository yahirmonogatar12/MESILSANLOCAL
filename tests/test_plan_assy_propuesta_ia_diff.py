"""Recalculo del dia: la propuesta se aplica sobre los lotes que ya existen."""

from datetime import date


GRID = {
    "version": 3,
    "grupos": [
        {"bloque": "B1", "lotes": [
            # mismo lote del plan pero con menos cantidad
            {"part_no": "EBR1", "fecha": "2026-07-30", "linea": "M1", "turno": "DIA",
             "qty": 400, "uph": 100, "ct": 36.0, "sec": 1},
            # ya arranco produccion: se propone el cambio pero no se aplica
            {"part_no": "EBR2", "fecha": "2026-07-30", "linea": "M1", "turno": "DIA",
             "qty": 250, "uph": 100, "ct": 36.0, "sec": 2},
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
    # PAUSADO se ve editable por status, pero ya produjo: no se debe tocar
    {"lot_no": "L2", "f": date(2026, 7, 30), "part_no": "EBR2", "line": "M1",
     "plan_count": 300, "produced_count": 80, "output": 0, "status": "PAUSADO",
     "group_no": 1, "sequence": 2},
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
    # Lote con produccion capturada: se reporta pero no es aplicable
    assert por_lote["L2"]["bloqueado"] == "ya tiene produccion capturada"


def test_diff_no_inventa_lotes_ni_toca_los_que_sobran(monkeypatch):
    d = _diff(monkeypatch)

    # La parte sin lote capturado NO se inserta: se reporta aparte
    assert [n["part_no"] for n in d["nuevos"]] == ["NUEVA"]
    # El lote que la propuesta ya no incluye solo se lista
    assert [s["lot_no"] for s in d["sobran"]] == ["L4"]
    # El CANCELADO no cuenta como lote existente ni estorba el emparejamiento
    assert "L5" not in {c["lot_no"] for c in d["cambios"]}
    assert "L5" not in {s["lot_no"] for s in d["sobran"]}


def test_aplicar_cambios_omite_lotes_con_produccion(client, monkeypatch):
    from app.api.control_produccion import plan_assy
    from app.api.shared import permisos

    updates = []

    def fake_query(sql, params=(), fetch=None):
        s = " ".join(str(sql).split())
        if s.startswith("SELECT status"):
            row = next(r for r in PLAN_MAIN if r["lot_no"] == params[0])
            return {k: row[k] for k in ("status", "produced_count", "output")}
        if s.startswith("UPDATE plan_main"):
            updates.append(params)
        return None

    monkeypatch.setattr(plan_assy, "execute_query", fake_query)
    monkeypatch.setattr(permisos, "puede_boton", lambda *_a, **_k: True)
    with client.session_transaction() as sess:
        sess["usuario"] = "ana"
        sess["roles"] = ["superadmin"]

    r = client.post("/api/plan/propuesta-ia/aplicar-cambios", json={"cambios": [
        {"lot_no": "L1", "cantidad": 400, "linea": "M1", "grupo": 1, "secuencia": 1},
        {"lot_no": "L2", "cantidad": 250, "linea": "M1", "grupo": 1, "secuencia": 2},
    ]}).get_json()

    assert r["aplicados"] == 1
    assert r["omitidos"] == [{"lot_no": "L2", "motivo": "ya tiene produccion capturada"}]
    assert [u[0] for u in updates] == [400]          # solo se actualizo L1
    assert updates[0][4] == "L1"
