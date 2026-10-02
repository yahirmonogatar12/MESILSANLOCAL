"""Pruebas del cruce FCT contra sesiones de operadores QA."""

from datetime import datetime

from app.api.shared import fct_helpers


def _sessions():
    return [
        {
            "session_id": "fct-01",
            "estacion": "FCT-01-02",
            "linea": "M2",
            "usuario": "MARTINEZ SILVA BRENDA ISABEL",
            "username": "1256",
            "estado": "Closed",
            "inicio_local": datetime(2026, 9, 29, 12, 52, 39),
            "fin_local": datetime(2026, 9, 29, 12, 54, 14),
        },
        {
            "session_id": "fct-02",
            "estacion": "FCT-02-02",
            "linea": "M2",
            "usuario": "GARCIA PEREZ LUCIO ALEXIS",
            "username": "2211",
            "estado": "Closed",
            "inicio_local": datetime(2026, 9, 29, 12, 32, 48),
            "fin_local": datetime(2026, 9, 29, 14, 25, 55),
        },
    ]


def test_normaliza_estaciones_fct_del_log_y_de_qa():
    assert fct_helpers._fct_normalize_operator_station("L02FCT1A") == "FCT-01-02"
    assert fct_helpers._fct_normalize_operator_station("L02FCT1B") == "FCT-02-02"
    assert fct_helpers._fct_normalize_operator_station("FCT-01-02") == "FCT-01-02"


def test_fct_attach_operator_no_mezcla_estaciones(monkeypatch):
    monkeypatch.setattr(fct_helpers, "execute_query", lambda *_args, **_kwargs: _sessions())
    rows = [
        {
            "ts": datetime(2026, 9, 29, 12, 53, 34),
            "operator_line": "M2",
            "estacion": "L02FCT1A",
        },
        {
            "ts": datetime(2026, 9, 29, 12, 53, 34),
            "operator_line": "M2",
            "estacion": "L02FCT1B",
        },
    ]

    fct_helpers.fct_attach_operator(rows)

    assert rows[0]["operador"] == "MARTINEZ SILVA BRENDA ISABEL"
    assert rows[1]["operador"] == "GARCIA PEREZ LUCIO ALEXIS"


def test_fct_attach_summary_operator_tambien_distingue_estacion(monkeypatch):
    monkeypatch.setattr(fct_helpers, "execute_query", lambda *_args, **_kwargs: _sessions())
    rows = [
        {
            "primer_test": datetime(2026, 9, 29, 12, 53, 10),
            "ultimo_test": datetime(2026, 9, 29, 12, 53, 58),
            "operator_line": "M2",
            "estacion": "L02FCT1A",
        },
        {
            "primer_test": datetime(2026, 9, 29, 12, 53, 10),
            "ultimo_test": datetime(2026, 9, 29, 12, 53, 58),
            "operator_line": "M2",
            "estacion": "L02FCT1B",
        },
    ]

    fct_helpers.fct_attach_summary_operators(rows)

    assert rows[0]["operador"] == "MARTINEZ SILVA BRENDA ISABEL"
    assert rows[1]["operador"] == "GARCIA PEREZ LUCIO ALEXIS"
