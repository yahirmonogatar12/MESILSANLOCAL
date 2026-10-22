from datetime import date, datetime

from flask import Flask

from app.api.control_calidad import historial_liberacion_lqc as lqc


class _FakeCursor:
    """Devuelve un resultado por cada execute(), en orden."""

    def __init__(self, results):
        self._results = list(results)
        self._current = []

    def execute(self, query, params=None):
        self._current = self._results.pop(0)

    def fetchall(self):
        return self._current

    def close(self):
        pass


class _FakeConn:
    def close(self):
        pass


def test_lqc_datos_agrupa_seriales_que_solo_difieren_en_mayusculas(monkeypatch):
    # Caso real: la misma pieza escaneada el 01/10 en minusculas y el 22/10
    # normal. MySQL (utf8mb4_unicode_ci) los cuenta como el mismo serial y
    # devolvia la variante en minusculas en el GROUP BY -> KeyError.
    upper = "I20260929-009-00009;MAIN;EBR76683912;1;"
    lower = upper.lower()
    rows = [
        {
            "linea": "M1",
            "fecha": date(2026, 10, 22),
            "part": "EBR76683912",
            "model_code": "",
            "lot_no": "",
            "box_code": "LGB922610134257",
            "scan_id": 8196398,
            "serial": upper,
            "box_status": "Unico",
            "first_scan": datetime(2026, 10, 22, 16, 42, 0),
            "last_scan": datetime(2026, 10, 22, 16, 42, 20),
            "turno": "DIA",
        }
    ]
    repetidos = [{"serial": lower}]
    historico = [
        {
            "id": 4843865,
            "serial": lower,
            "fecha_operativa": date(2026, 10, 1),
            "last_scan": datetime(2026, 10, 1, 12, 54, 14),
        },
        {
            "id": 8196398,
            "serial": upper,
            "fecha_operativa": date(2026, 10, 22),
            "last_scan": datetime(2026, 10, 22, 16, 42, 20),
        },
    ]
    cursor = _FakeCursor([rows, repetidos, historico])
    monkeypatch.setattr(lqc, "get_pooled_connection", lambda: _FakeConn())
    monkeypatch.setattr(lqc, "get_dict_cursor", lambda conn: cursor)

    app = Flask(__name__)
    with app.test_request_context(
        "/api/lqc/datos?fecha_inicio=2026-10-21&fecha_fin=2026-10-22"
    ):
        resp = lqc.lqc_datos_api.__wrapped__()

    assert not isinstance(resp, tuple), resp[0].get_json()
    record = resp.get_json()["records"][0]
    assert record["status"] == "Duplicado"
    assert record["duplicado_historico"] is True
    assert record["total_repeticiones"] == 2
    assert record["fechas_repetidas"] == "2026-10-01"
