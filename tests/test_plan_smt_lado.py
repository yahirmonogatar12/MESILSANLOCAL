"""Lado de la PCB en el plan SMT (2026-09-24).

Un modelo de doble cara se corre dos veces: BOTTOM (el QR queda arriba y se
escanean sus N QR) y TOP (el QR queda debajo de la PCB: 0 QR, cuenta el
sensor). El TOP nace ligado a su BOTTOM como sublote "<BOTTOM>-T".
"""

import io
import time

import pandas as pd

from app.api.control_produccion import plan_smt

# Columnas finales de cada INSERT: qr_required_count, array_size, lado, lote_padre.
FIN = slice(-4, None)


def _login(client):
    with client.session_transaction() as session:
        session["usuario"] = "test"
        session["_last_activity_touch_ts"] = int(time.time())


class _Mysql:
    """Graba las escrituras del modulo; los SELECT devuelven lo minimo."""

    def __init__(self, planes=None):
        self.escrituras = []
        self.planes = planes or []

    def __call__(self, sql, params=None, fetch=None):
        texto = sql.strip().upper()
        if texto.startswith(("INSERT", "UPDATE")):
            self.escrituras.append((sql, params))
            return None
        if "MAX(CAST" in sql:
            return {"max_seq": 2}
        if "COUNT(*)" in sql:
            return {"c": 0}
        if "FROM PLAN_SMT WHERE LOT_NO IN" in " ".join(texto.split()):
            return self.planes
        return None if fetch == "one" else []


def test_bottom_crea_su_top_ligado(client, monkeypatch):
    db = _Mysql()
    monkeypatch.setattr(plan_smt, "execute_query", db)
    _login(client)

    r = client.post("/api/plan-smt", json={
        "working_date": "2026-09-24", "part_no": "EBR39120001", "line": "SA",
        "plan_count": 400, "qr_required_count": 4, "array_size": 4, "lado": "bottom",
    })

    assert r.status_code == 200, r.get_json()
    assert r.get_json()["lot_no"] == "SMT-260924-003"
    assert r.get_json()["lot_top"] == "SMT-260924-003-T"
    (_, bottom), (_, top) = db.escrituras
    assert bottom[0] == "SMT-260924-003"
    assert bottom[FIN] == (4, 4, "BOTTOM", None)
    # TOP: el QR queda debajo -> 0 QR (sensor), mismo array, ligado al BOTTOM.
    assert top[0] == "SMT-260924-003-T"
    assert top[FIN] == (0, 4, "TOP", "SMT-260924-003")
    assert top[1:-4] == bottom[1:-4], "misma parte, linea, fecha y cantidad"


def test_una_cara_no_crea_top(client, monkeypatch):
    db = _Mysql()
    monkeypatch.setattr(plan_smt, "execute_query", db)
    _login(client)

    r = client.post("/api/plan-smt", json={
        "working_date": "2026-09-24", "part_no": "EBR11110000", "line": "SB",
        "plan_count": 100, "lado": "algo-raro",
    })

    assert r.get_json()["lot_top"] is None
    [(_, fila)] = db.escrituras
    assert fila[FIN] == (1, 1, "", None)


def test_import_bottom_genera_su_top_y_omite_top_sueltos(client, monkeypatch):
    db = _Mysql()
    monkeypatch.setattr(plan_smt, "execute_query", db)
    _login(client)
    archivo = io.BytesIO()
    pd.DataFrame([
        {"line": "SA", "part_no": "EBR39120001", "plan_count": 400, "qr": 4, "array": 4, "lado": "BOTTOM"},
        {"line": "SA", "part_no": "EBR39120001", "plan_count": 400, "qr": 0, "array": 4, "lado": "TOP"},
        {"line": "SB", "part_no": "EBR11110000", "plan_count": 100, "qr": 1, "array": 1, "lado": ""},
    ]).to_excel(archivo, index=False)
    archivo.seek(0)

    r = client.post(
        "/api/plan-smt/import-excel",
        data={"file": (archivo, "plan.xlsx"), "working_date": "2026-09-24"},
        content_type="multipart/form-data",
    )

    body = r.get_json()
    assert body["imported"] == 3, body
    assert "1 fila(s) TOP omitidas" in body["message"]
    [(_, params)] = db.escrituras
    filas = [params[i:i + 20] for i in range(0, len(params), 20)]
    assert [(f[0], f[4], *f[FIN]) for f in filas] == [
        ("SMT-260924-003", "SA", 4, 4, "BOTTOM", None),
        ("SMT-260924-003-T", "SA", 0, 4, "TOP", "SMT-260924-003"),
        ("SMT-260924-004", "SB", 1, 1, "", None),
    ]


def test_reprogramar_top_conserva_sufijo_y_padre(client, monkeypatch):
    plan_top = {
        "lot_no": "SMT-260924-003-T", "plan_count": 400, "produced_count": 380,
        "line": "SA", "part_no": "EBR39120001", "qr_required_count": 0,
        "array_size": 4, "lado": "TOP", "lote_padre": "SMT-260924-003",
    }
    db = _Mysql(planes=[plan_top])
    consultas = []

    def espia(sql, params=None, fetch=None):
        consultas.append(params)
        return db(sql, params, fetch)

    monkeypatch.setattr(plan_smt, "execute_query", espia)
    _login(client)

    r = client.post("/api/plan-smt/reschedule", json={
        "lot_nos": ["SMT-260924-003-T"], "new_working_date": "2026-09-25",
    })

    assert r.get_json()["created"] == 1, r.get_json()
    # Solo cuenta sublotes -NN del TOP, no los del BOTTOM.
    assert ("^SMT-260924-003-T-[0-9]+$",) in consultas
    (_, nuevo), (_, cierre) = db.escrituras
    assert nuevo[0] == "SMT-260924-003-T-01"
    assert nuevo[10] == 20, "pendiente = 400 - 380"
    assert nuevo[FIN] == (0, 4, "TOP", "SMT-260924-003")
    assert cierre == (380, "SMT-260924-003-T")
