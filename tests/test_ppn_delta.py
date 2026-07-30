"""Consumo real de LG a partir de dos snapshots del PPN (app/.../ppn.py)."""
import datetime as dt
import io

import openpyxl
import pytest

from app.api.control_produccion import part_planning as pp
from app.api.control_produccion import ppn
from app.api.portal import ai_plan_tools

DIA = dt.date(2026, 7, 29)


def _wos_ayer():
    return {
        "A": {"modelo": "M1", "partes": {"P1", "P2"}, "sin_bom": False,
              "plan": 100, "result": 0, "dias": {DIA: 100}},
        "B": {"modelo": "M2", "partes": {"P1"}, "sin_bom": False,
              "plan": 50, "result": 10, "dias": {DIA: 40}},
        "C": {"modelo": "M3", "partes": {"P3"}, "sin_bom": False,
              "plan": 30, "result": 0, "dias": {DIA + dt.timedelta(days=1): 30}},
    }


def test_sobrante_atraso_y_cierre():
    base = ppn.baseline(DIA, _wos_ayer())
    # A construyo 60 de 100 -> 40 sin consumir. B desaparecio = cerrado (40, sin
    # atraso). C no estaba programado ese dia.
    hoy = {"A": {"result": 60}}
    renglones, partes = ppn.sobrante(base, hoy)
    assert {r[0] for r in renglones} == {"A", "B"}
    assert partes == {"P1": 40, "P2": 40}


def test_sobrante_topa_en_lo_programado():
    """Un W/O no puede consumir mas de lo que tenia programado ese dia."""
    wos = _wos_ayer()
    wos["A"]["dias"][DIA] = 20  # programado 20, construyo 60 (de varios dias)
    base = ppn.baseline(DIA, wos)
    _, partes = ppn.sobrante(base, {"A": {"result": 60}})
    assert partes == {}


def test_sin_atraso_no_hay_sobrante():
    base = ppn.baseline(DIA, _wos_ayer())
    hoy = {"A": {"result": 100}, "B": {"result": 50}}
    assert ppn.sobrante(base, hoy)[1] == {}


def test_demanda_explota_por_parte():
    assert ppn.demanda({"A": _wos_ayer()["A"]}) == {("P1", DIA): 100, ("P2", DIA): 100}


def _ppn_workbook(fecha0, renglones):
    """PPN minimo en memoria. renglones: (wo, modelo, partes, plan, result, dias)."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "PPN 30 Jul"
    fechas = [fecha0 + dt.timedelta(days=i) for i in range(ppn.C_DIAN - ppn.C_DIA0)]
    for i, f in enumerate(fechas):
        ws.cell(1, ppn.C_DIA0 + 1 + i, f.day)
    ws.cell(2, 1, "Sum")
    for fila, (wo, modelo, partes, plan, result, dias) in enumerate(renglones, start=3):
        ws.cell(fila, 1, fila - 2)
        ws.cell(fila, ppn.C_WO + 1, wo)
        ws.cell(fila, ppn.C_MODELO + 1, modelo)
        for j, parte in enumerate(partes):
            ws.cell(fila, 9 + j, parte)
        ws.cell(fila, ppn.C_PSTART + 1, dt.datetime.combine(fecha0, dt.time(7, 30)))
        ws.cell(fila, ppn.C_PLAN + 1, plan)
        ws.cell(fila, ppn.C_RESULT + 1, result)
        for f, qty in dias.items():
            ws.cell(fila, ppn.C_DIA0 + 1 + fechas.index(f), qty)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_parse_ppn_rebaja_el_plan_del_dia_que_paso(monkeypatch):
    """El plan de ayer se corrige con lo que LG realmente construyo."""
    hoy = DIA + dt.timedelta(days=1)
    # Ayer: el W/O A tenia 100 programadas y solo construyo 60.
    monkeypatch.setattr(pp, "_pp_ppn_baseline", lambda: (DIA, {
        "A": {"partes": {"P1", "P2"}, "prog": 100, "plan": 100, "result": 0},
    }))
    # P1 ya tenia plan de ayer (120: el Cal traia demanda extra); P2 no tenia.
    monkeypatch.setattr(pp, "execute_query", lambda *_a, **_k: [
        {"part_no": "P1", "plan_qty": 120},
    ])
    data = _ppn_workbook(hoy, [("A", "M1", ["P1", "P2"], 100, 60, {hoy: 40})])

    parsed, err = pp._parse_lg_workbook(data, "PPN 30.07.26.xlsx")

    assert err is None
    # 40 sin consumir: el plan de ayer baja de 120 a 80 y no inventa faltante.
    assert parsed["records"][("P1", DIA)] == 80
    # Sin plan previo no se corrige nada (no se inventan renglones en el pasado).
    assert ("P2", DIA) not in parsed["records"]
    # La demanda de hoy sale de los buckets, ya neta de lo construido.
    assert parsed["records"][("P1", hoy)] == 40
    assert len(parsed["ppn_wo"]) == 1 and parsed["ppn_date"] == hoy


def test_parse_ppn_no_corrige_al_reimportar_el_mismo_dia(monkeypatch):
    """Reimportar el mismo PPN no vuelve a restar el sobrante."""
    monkeypatch.setattr(pp, "_pp_ppn_baseline", lambda: (DIA, {
        "A": {"partes": {"P1"}, "prog": 100, "plan": 100, "result": 0},
    }))
    monkeypatch.setattr(pp, "execute_query", lambda *_a, **_k: [
        {"part_no": "P1", "plan_qty": 120},
    ])
    data = _ppn_workbook(DIA, [("A", "M1", ["P1"], 100, 60, {DIA: 40})])

    parsed, err = pp._parse_lg_workbook(data, "PPN 29.07.26.xlsx")

    assert err is None
    assert parsed["records"][("P1", DIA)] == 40  # el bucket, no el plan corregido


def test_parse_ppn_no_rebaja_dos_veces_con_baseline_explicito(monkeypatch):
    """Reaplicar la misma comparacion no vuelve a descontar el sobrante."""
    hoy = DIA + dt.timedelta(days=1)
    base = {"A": {"partes": {"P1"}, "prog": 100, "plan": 100, "result": 0}}
    # El snapshot guardado ya es del PPN de hoy: la correccion ya se aplico.
    monkeypatch.setattr(pp, "_pp_ppn_baseline", lambda: (hoy, base))
    monkeypatch.setattr(pp, "execute_query", lambda *_a, **_k: [
        {"part_no": "P1", "plan_qty": 80},  # ya rebajado de 120 a 80
    ])
    data = _ppn_workbook(hoy, [("A", "M1", ["P1"], 100, 60, {hoy: 40})])

    parsed, err = pp._parse_lg_workbook(data, "PPN 30.xlsx", ppn_base=(DIA, base))

    assert err is None
    assert ("P1", DIA) not in parsed["records"]
    assert any("ya refleja el PPN" in w for w in parsed["warnings"])


def _lookup_de(*archivos):
    """file_lookup falso: `archivos` va del mas reciente al mas viejo."""
    def lookup(_file_ref=None):
        return archivos[0] if archivos else (None, None)
    lookup.recientes = lambda limite=4: list(archivos[:limite])
    return lookup


def test_tool_ppn_comparar_ordena_por_la_fecha_del_archivo(monkeypatch):
    """Da igual en que orden se suban: manda la fecha de adentro del PPN."""
    monkeypatch.setattr(ai_plan_tools, "_has_plan", lambda _u: True)
    hoy = DIA + dt.timedelta(days=1)
    viejo = _ppn_workbook(DIA, [("A", "M1", ["P1", "P2"], 100, 0, {DIA: 100})])
    nuevo = _ppn_workbook(hoy, [("A", "M1", ["P1", "P2"], 100, 60, {hoy: 40})])

    for archivos in (
        ((nuevo, "PPN 30.xlsx"), (viejo, "PPN 29.xlsx")),   # subidos en orden
        ((viejo, "PPN 29.xlsx"), (nuevo, "PPN 30.xlsx")),   # subidos al reves
    ):
        out = ai_plan_tools.execute(
            "plan_ppn_comparar", {}, username="ana", file_lookup=_lookup_de(*archivos),
        )
        r = out["resumen"]
        assert r["dia_evaluado"] == DIA.isoformat()
        assert (r["unidades_planeadas"], r["unidades_construidas"]) == (100, 60)
        assert r["pzas_sin_consumir"] == 80  # 40 unidades x 2 partes
        assert out["confirm_token"]


def test_propuesta_stale_pide_generar_una_nueva():
    """STALE sale como PPYProposalStaleError -> 409 + code, no como 400 sin salida."""
    err = pp._ppy_estado_no_abierto("STALE", "aplicar")
    assert isinstance(err, pp.PPYProposalStaleError)
    assert "Genera una propuesta nueva" in str(err)
    # Los demas estados siguen siendo un ValueError normal.
    otro = pp._ppy_estado_no_abierto("REJECTED", "aplicar")
    assert isinstance(otro, ValueError) and not isinstance(otro, pp.PPYProposalStaleError)


def _falta_ppn(*_a, **_k):
    raise ValueError("Necesito los dos PPN. Sube primero el del dia anterior...")


def _stub_dia(monkeypatch, schedule_changes):
    """plan_dia_preparar sin BD: solo se ejercita el armado de la salida."""
    monkeypatch.setattr(ai_plan_tools, "_has_plan", lambda _u: True)
    monkeypatch.setattr(ai_plan_tools, "_has_projection", lambda _u: True)
    monkeypatch.setattr(ai_plan_tools, "_ppn_par", lambda *_a, **_k: (
        (DIA, {}, b"ayer", "PPN 29.xlsx"), (DIA, {}, b"hoy", "PPN 30.xlsx")))
    monkeypatch.setattr(ai_plan_tools, "_ppn_comparar", lambda *_a: {
        "dia_evaluado": DIA.isoformat(), "unidades_planeadas": 100,
        "unidades_construidas": 60, "unidades_atrasadas": 40, "pzas_sin_consumir": 80})
    monkeypatch.setattr(ai_plan_tools, "ppn", type("_", (), {"baseline": staticmethod(lambda *_a: {})}))
    monkeypatch.setattr(ai_plan_tools, "_importar_ppn", lambda *_a: {"plan_registros": 10})
    monkeypatch.setattr(ai_plan_tools, "_cal_adjunto", lambda *_a, **_k: (None, None))
    real = ai_plan_tools.execute

    def fake(name, arguments, **kw):
        if name == "plan_propuesta_preparar":
            return {"schedule_changes": schedule_changes, "confirm_token": "tok",
                    "proposal_id": "p1", "schedule_change_summary": {}}
        return real(name, arguments, **kw)

    monkeypatch.setattr(ai_plan_tools, "execute", fake)
    return real


def test_plan_dia_solo_devuelve_lo_que_cambia(monkeypatch):
    cambios = [
        {"accion": "CONSERVAR", "part_no": "P1"},
        {"accion": "AGREGAR", "part_no": "P2"},
        {"accion": "ELIMINAR", "part_no": "P3"},
    ]
    real = _stub_dia(monkeypatch, cambios)
    out = real("plan_dia_preparar", {"fecha": None}, username="ana", file_lookup=None)
    assert [c["part_no"] for c in out["cambios"]] == ["P2", "P3"]
    assert out["sin_cambios"] is False
    assert out["confirm_token"] == "tok"


def test_plan_dia_funciona_con_solo_el_cal(monkeypatch):
    """Sin los dos PPN sigue armando el dia, pero avisa que falta la correccion."""
    real = _stub_dia(monkeypatch, [{"accion": "AGREGAR", "part_no": "P2"}])
    monkeypatch.setattr(ai_plan_tools, "_ppn_par", _falta_ppn)
    monkeypatch.setattr(ai_plan_tools, "_cal_adjunto",
                        lambda *_a, **_k: (b"cal", "Cal_260730.xlsx"))
    monkeypatch.setattr(ai_plan_tools, "_importar_plan_e_inventario",
                        lambda *_a: {"plan_registros": 99})

    out = real("plan_dia_preparar", {"fecha": None}, username="ana", file_lookup=None)

    assert out["lg_ayer"] is None
    assert out["datos_cargados"]["cal"].startswith("99 registros")
    assert "dos PPN" in out["datos_cargados"]["ppn"]
    assert "correccion del consumo real de LG" in out["instruccion"]
    assert out["cambios"] and out["confirm_token"] == "tok"


def test_plan_dia_sin_archivos_utiles_lo_dice(monkeypatch):
    real = _stub_dia(monkeypatch, [])
    monkeypatch.setattr(ai_plan_tools, "_ppn_par", _falta_ppn)
    monkeypatch.setattr(ai_plan_tools, "_cal_adjunto", lambda *_a, **_k: (None, None))
    with pytest.raises(ValueError, match="ni el Cal del dia ni los dos PPN"):
        real("plan_dia_preparar", {"fecha": None}, username="ana", file_lookup=None)


def test_plan_dia_sin_cambios_no_pide_confirmacion(monkeypatch):
    real = _stub_dia(monkeypatch, [{"accion": "CONSERVAR", "part_no": "P1"}])
    out = real("plan_dia_preparar", {"fecha": None}, username="ana", file_lookup=None)
    assert out["sin_cambios"] is True and out["cambios"] == []
    # Sin token no hay confirmacion pendiente que el servidor pueda ejecutar.
    assert "confirm_token" not in out


def test_tool_ppn_comparar_pide_el_segundo_archivo(monkeypatch):
    monkeypatch.setattr(ai_plan_tools, "_has_plan", lambda _u: True)
    solo = _ppn_workbook(DIA, [("A", "M1", ["P1"], 100, 0, {DIA: 100})])
    with pytest.raises(ValueError, match="dos PPN"):
        ai_plan_tools.execute(
            "plan_ppn_comparar", {}, username="ana",
            file_lookup=_lookup_de((solo, "PPN 29.xlsx")),
        )
