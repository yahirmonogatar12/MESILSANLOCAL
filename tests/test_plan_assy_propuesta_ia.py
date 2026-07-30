"""Bajar una propuesta de la IA al plan ASSY (plan_main)."""

from datetime import date


PROPOSAL_ID = "22222222-2222-4222-8222-222222222222"

GRID = {
    "grupos": [
        {"bloque": "B1", "lotes": [
            {"item_id": "i1", "part_no": "EBR1", "fecha": "2026-07-30", "linea": "M1",
             "turno": "DIA", "qty": 500, "uph": 100, "ct": 36.0, "sec": 1},
            {"item_id": "i2", "part_no": "EBR2", "fecha": "2026-07-30", "linea": "M1",
             "turno": "DIA", "qty": 300, "uph": 100, "ct": 36.0, "sec": 2},
        ]},
        {"bloque": "B3", "lotes": [
            {"item_id": "i3", "part_no": "ACQ9", "fecha": "2026-07-30", "linea": "D2",
             "turno": "DIA", "qty": 200, "uph": 150, "ct": 24.0, "sec": 1},
        ]},
    ],
}


def _mock_plan_assy(monkeypatch, ya_en_plan):
    """execute_query falso: devuelve lo que ya hay en plan_main y captura inserts."""
    from app.api.control_produccion import plan_assy, part_planning

    insertados = []

    def fake_query(sql, params=(), fetch=None):
        s = " ".join(str(sql).split())
        if s.startswith("SELECT DATE(working_date)"):
            return list(ya_en_plan)
        if s.startswith("SELECT MAX(sequence)"):
            return {"max_seq": 0}
        if s.startswith("SELECT model, project FROM raw"):
            return {"model": f"MOD-{params[0]}", "project": "P1"}
        if s.startswith("SELECT COUNT(*) AS c FROM plan_main"):
            return {"c": len(insertados)}
        if s.startswith("INSERT INTO plan_main"):
            insertados.append(params)
            return None
        return None

    monkeypatch.setattr(plan_assy, "execute_query", fake_query)
    monkeypatch.setattr(part_planning, "_ppy_propuesta_grid",
                        lambda *_a, **_k: dict(GRID))
    # plan_lot_no usa su propio execute_query importado
    from app.api.shared import plan_lot_no
    monkeypatch.setattr(plan_lot_no, "execute_query", fake_query)
    return insertados


def _post(client, monkeypatch):
    from app.api.shared import permisos
    monkeypatch.setattr(permisos, "puede_boton", lambda *_a, **_k: True)
    with client.session_transaction() as sess:
        sess["usuario"] = "ana"
        sess["roles"] = ["superadmin"]
    return client.post("/api/plan/importar-propuesta-ia",
                       json={"proposal_id": PROPOSAL_ID})


def test_importar_propuesta_mapea_bloque_a_grupo(client, monkeypatch):
    insertados = _mock_plan_assy(monkeypatch, ya_en_plan=[])
    data = _post(client, monkeypatch).get_json()

    assert data["insertados"] == 3 and data["omitidos"] == 0
    # (lot_no, wo, po, fecha, linea, model, part_no, project, qty, ct, uph,
    #  routing, group_no, sequence)
    assert [(p[6], p[4], p[8], p[12], p[13]) for p in insertados] == [
        ("EBR1", "M1", 500, 1, 1),
        ("EBR2", "M1", 300, 1, 2),
        ("ACQ9", "D2", 200, 3, 1),
    ]
    assert insertados[0][3] == date(2026, 7, 30)
    assert insertados[0][0].startswith("ASSYLINE-260730-")


def test_importar_propuesta_no_duplica_lo_que_ya_esta(client, monkeypatch):
    """Reimportar solo mete lo que falta: el lote ya capturado se omite."""
    insertados = _mock_plan_assy(monkeypatch, ya_en_plan=[
        {"f": date(2026, 7, 30), "part_no": "EBR1", "line": "M1", "plan_count": 500},
    ])
    data = _post(client, monkeypatch).get_json()

    assert data["insertados"] == 2 and data["omitidos"] == 1
    assert [p[6] for p in insertados] == ["EBR2", "ACQ9"]
