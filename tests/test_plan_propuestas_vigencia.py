"""Las propuestas sin confirmar se cierran y dejan de listarse a los 2 dias."""


def test_expirar_solo_toca_borradores_sin_confirmar(monkeypatch):
    from app.api.control_produccion import part_planning as pp

    visto = {}

    def fake_query(sql, params=(), fetch=None):
        visto["sql"] = " ".join(str(sql).split())
        visto["params"] = params

    monkeypatch.setattr(pp, "execute_query", fake_query)
    pp._ppy_expirar_propuestas()

    assert "SET status='EXPIRED'" in visto["sql"]
    assert "status IN ('DRAFT','PENDING_CONFIRMATION')" in visto["sql"]
    assert "created_at < NOW() - INTERVAL %s DAY" in visto["sql"]
    # Las aplicadas son historial: no se reescriben
    assert "APPLIED" not in visto["sql"]
    assert visto["params"] == (pp.PPY_PROPUESTA_VIGENCIA_DIAS,)


def test_la_lista_solo_trae_las_vigentes(client, monkeypatch):
    from app.api.control_produccion import plan_assy, part_planning as pp
    from app.api.shared import permisos

    consultas = []

    def fake_query(sql, params=(), fetch=None):
        consultas.append((" ".join(str(sql).split()), params))
        return []

    monkeypatch.setattr(plan_assy, "execute_query", fake_query)
    monkeypatch.setattr(pp, "execute_query", fake_query)
    monkeypatch.setattr(permisos, "puede_boton", lambda *_a, **_k: True)
    with client.session_transaction() as sess:
        sess["usuario"] = "ana"
        sess["roles"] = ["superadmin"]

    assert client.get("/api/plan/propuestas-ia").get_json() == []

    # Primero cierra las vencidas, luego lista acotando por la misma vigencia
    assert "SET status='EXPIRED'" in consultas[0][0]
    listado, params = consultas[1]
    assert "created_at >= NOW() - INTERVAL %s DAY" in listado
    assert params == ("ana", pp.PPY_PROPUESTA_VIGENCIA_DIAS)
