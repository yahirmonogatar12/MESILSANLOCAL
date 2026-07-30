"""La propuesta de hoy toma del MES en que va cada linea, sin preguntarlo."""

from datetime import date

import pytest


FILAS = [
    {"part_no": "ACQ91482496", "line": "D2"},
    {"part_no": "EBR30299355", "line": "M3"},
]


def test_lotes_corriendo_salen_del_plan_del_dia(monkeypatch):
    from app.api.control_produccion import plan_assy

    visto = {}

    def fake_query(sql, params=(), fetch=None):
        visto["sql"] = " ".join(str(sql).split())
        return list(FILAS)

    monkeypatch.setattr(plan_assy, "execute_query", fake_query)
    out = plan_assy._assy_lotes_corriendo(date(2026, 7, 30))

    assert out == [{"numero_parte": "ACQ91482496", "linea": "D2"},
                   {"numero_parte": "EBR30299355", "linea": "M3"}]
    # Solo lo que ya arranco: un lote nada mas planeado todavia se puede mover
    assert "EN PROGRESO" in visto["sql"] and "produced_count" in visto["sql"]
    assert "status <> 'CANCELADO'" in visto["sql"]


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
    assert "tomado de los lotes de hoy en el MES" in (capturado["objective"] or "")


def test_sigue_preguntando_si_no_hay_nada_arrancado(monkeypatch):
    """Sin lotes arrancados no se puede distinguir 'no empezo' de 'no lo
    capturaron': ahi si conviene preguntar."""
    tools, _capturado, args = _preparar(monkeypatch, [])

    with pytest.raises(ValueError, match="en que lote va cada linea"):
        tools.execute("plan_propuesta_preparar", args,
                      username="ana", file_lookup=None)
