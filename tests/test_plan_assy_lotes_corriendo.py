"""La propuesta de hoy usa la hora calculada del MES, sin preguntar el lote."""

from datetime import date, datetime

import pytest


FILAS = [
    {"part_no": "ACQ91482496", "line": "D2"},
    {"part_no": "EBR30299355", "line": "M3"},
]


def test_lotes_fijos_salen_del_estado_o_de_la_hora_calculada(monkeypatch):
    from app.api.control_produccion import plan_assy

    visto = {}

    def fake_query(sql, params=(), fetch=None):
        visto["sql"] = " ".join(str(sql).split())
        visto["params"] = params
        return list(FILAS)

    monkeypatch.setattr(plan_assy, "execute_query", fake_query)
    corte = datetime(2026, 7, 30, 11, 45)
    out = plan_assy._assy_lotes_corriendo(date(2026, 7, 30), ahora=corte)

    assert out == [{"numero_parte": "ACQ91482496", "linea": "D2"},
                   {"numero_parte": "EBR30299355", "linea": "M3"}]
    # Ademas del estado real, planned_start fija solo lo que ya alcanzo el corte.
    assert "EN PROGRESO" in visto["sql"] and "produced_count" in visto["sql"]
    assert "planned_start <= %s" in visto["sql"]
    assert "status <> 'CANCELADO'" in visto["sql"]
    assert visto.get("params") == (date(2026, 7, 30), corte)


class _Sentinela(Exception):
    """Marca que la ejecucion paso el guard y llego a crear la propuesta."""


def _preparar(monkeypatch, filas):
    from app.api.portal import ai_plan_tools
    from app.api.control_produccion import part_planning as pp, plan_assy

    monkeypatch.setattr(plan_assy, "execute_query", lambda *_a, **_k: list(filas))
    monkeypatch.setattr(ai_plan_tools, "_has_projection", lambda *_a: True)
    capturado = {}

    def fake_crear(*_args, **kwargs):
        capturado.update(kwargs)
        raise _Sentinela()

    monkeypatch.setattr(pp, "_ppy_crear_propuesta", fake_crear)
    hoy = date.today().isoformat()
    return ai_plan_tools, capturado, {
        "fecha_inicio": hoy, "fecha_fin": hoy, "objetivo": None,
        "proceso_actual": None, "partes_excluidas": [], "ajustes": [],
        "lotes_corriendo": [], "agregados": [],
    }


def test_no_pregunta_si_el_mes_ya_sabe_que_esta_corriendo(monkeypatch):
    tools, capturado, args = _preparar(monkeypatch, FILAS)

    with pytest.raises(_Sentinela):   # paso el guard: llego a planear
        tools.execute("plan_propuesta_preparar", args,
                      username="ana", file_lookup=None)

    # Los lotes arrancados quedan fijados y el objetivo dice de donde salieron
    assert capturado["lotes_corriendo"] == {"ACQ91482496": "D2",
                                            "EBR30299355": "M3"}
    assert "Corte automatico del MES" in (capturado["objective"] or "")
    assert "hora calculada ya inicio" in (capturado["objective"] or "")


def test_no_pregunta_si_aun_no_llega_la_hora_de_ningun_lote(monkeypatch):
    """Sin inicios vencidos, todo lo pendiente se puede reoptimizar."""
    tools, capturado, args = _preparar(monkeypatch, [])

    with pytest.raises(_Sentinela):
        tools.execute("plan_propuesta_preparar", args,
                      username="ana", file_lookup=None)

    assert capturado["lotes_corriendo"] == {}
    assert "todo lo pendiente se puede reoptimizar" in (
        capturado["objective"] or ""
    )
