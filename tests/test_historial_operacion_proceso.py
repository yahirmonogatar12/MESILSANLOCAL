from flask import Flask

from app.api.control_proceso import historial_operacion_proceso as m


def consulta(query):
    with Flask(__name__).test_request_context("/?" + query):
        return m._consulta()


def test_une_los_tres_procesos_y_filtra_por_uno():
    sql, params = consulta("start=2026-09-01&end=2026-09-02")
    assert all(t in sql for t in ("plan_smt", "plan_imd", "plan_main"))
    assert sql.count("%s") == len(params) == 6

    sql, params = consulta("start=2026-09-01&end=2026-09-02&proceso=imt")
    assert "plan_imd" in sql and "plan_smt" not in sql and "plan_main" not in sql
    assert params == ["2026-09-01", "2026-09-02"]


def test_filtros_de_columna_solo_lista_blanca():
    sql, params = consulta("start=2026-09-01&cf_wo=WO-26&cf_xx=1;DROP&cf_output=5")
    assert "COALESCE(wo, '') LIKE %s" in sql and "CAST(output_count AS CHAR) LIKE %s" in sql
    assert "DROP" not in sql
    assert params[-2:] == ["%WO-26%", "%5%"] and sql.count("%s") == len(params)


def test_output_na_solo_en_smt_e_imt(monkeypatch):
    filas = [
        {"proceso": "SMT", "output_count": None},
        {"proceso": "IMT", "output_count": None},
        {"proceso": "ASSY", "output_count": 0},
    ]
    monkeypatch.setattr(m, "execute_query", lambda *a, **k: filas)
    with Flask(__name__).test_request_context("/?start=2026-09-01"):
        rows = m._registros()
    assert [r["output_count"] for r in rows] == ["N/A", "N/A", 0]
