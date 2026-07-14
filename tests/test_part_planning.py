import io
from datetime import date, datetime

import openpyxl

from app.api.control_produccion.part_planning import (
    _parse_lg_workbook,
    _parse_part10_workbook,
    _pp_filas_segun_modo,
)


def _workbook_bytes(sheet_name="LG", fechas=None, filas=None):
    """Construye un xlsx en memoria con el layout del plan LG.

    fechas: lista de valores para la fila 3 desde la columna C.
    filas: lista de (part_no, [cantidades]) desde la fila 4.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sheet_name
    for i, valor in enumerate(fechas or []):
        ws.cell(row=3, column=3 + i, value=valor)
    for r, (parte, cantidades) in enumerate(filas or [], start=4):
        ws.cell(row=r, column=2, value=parte)
        for i, qty in enumerate(cantidades):
            ws.cell(row=r, column=3 + i, value=qty)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_parse_fechas_datetime_completas():
    data = _workbook_bytes(
        fechas=[datetime(2026, 7, 9), datetime(2026, 7, 10)],
        filas=[("MDS64531211", [536, 700]), ("EAV64632103", [0, 1356])],
    )
    parsed, err = _parse_lg_workbook(data, "plan.xlsx")
    assert err is None
    assert parsed["plan_year"] == 2026
    assert parsed["date_from"] == date(2026, 7, 9)
    assert parsed["date_to"] == date(2026, 7, 10)
    assert parsed["parts_count"] == 2
    assert parsed["records_count"] == 3  # 536, 700, 1356
    assert parsed["zero_records_count"] == 1
    assert parsed["records"][("MDS64531211", date(2026, 7, 9))] == 536


def test_parse_fechas_string_toma_anio_del_filename():
    data = _workbook_bytes(fechas=["09-Jul"], filas=[("P1", [10])])
    parsed, err = _parse_lg_workbook(data, "plan de produccion 20260710 W28.xlsx")
    assert err is None
    assert parsed["records"][("P1", date(2026, 7, 9))] == 10


def test_parse_override_year_gana_sobre_filename():
    data = _workbook_bytes(fechas=["09-Jul"], filas=[("P1", [10])])
    parsed, err = _parse_lg_workbook(data, "plan 20260710.xlsx", override_year=2027)
    assert err is None
    assert ("P1", date(2027, 7, 9)) in parsed["records"]


def test_partes_duplicadas_se_consolidan_sumando():
    data = _workbook_bytes(
        fechas=[datetime(2026, 7, 9)],
        filas=[("MDS64531211", [536]), ("MDS64531211", [120])],
    )
    parsed, err = _parse_lg_workbook(data, "plan.xlsx")
    assert err is None
    assert parsed["records"][("MDS64531211", date(2026, 7, 9))] == 656
    assert parsed["duplicated_parts"] == ["MDS64531211"]
    assert parsed["parts_count"] == 1


def test_cantidad_negativa_se_ajusta_a_cero_con_warning():
    data = _workbook_bytes(
        fechas=[datetime(2026, 7, 9)], filas=[("P1", [-5]), ("P2", [3])]
    )
    parsed, err = _parse_lg_workbook(data, "plan.xlsx")
    assert err is None
    assert parsed["records"][("P1", date(2026, 7, 9))] == 0
    assert any("negativa" in w for w in parsed["warnings"])


def test_errores_bloqueantes():
    # Extension invalida
    _, err = _parse_lg_workbook(b"x", "plan.txt")
    assert err[1] == 400 and "Formato" in err[0]["errors"][0]
    # Vacio
    _, err = _parse_lg_workbook(b"", "plan.xlsx")
    assert "vacio" in err[0]["errors"][0]
    # No es Excel
    _, err = _parse_lg_workbook(b"no soy zip", "plan.xlsx")
    assert "corrupto" in err[0]["errors"][0]
    # Sin hoja LG
    data = _workbook_bytes(sheet_name="Otra", fechas=[datetime(2026, 7, 9)], filas=[("P1", [1])])
    _, err = _parse_lg_workbook(data, "plan.xlsx")
    assert "hoja 'LG'" in err[0]["errors"][0]
    # Sin fechas validas
    data = _workbook_bytes(fechas=["no-fecha"], filas=[("P1", [1])])
    _, err = _parse_lg_workbook(data, "plan.xlsx")
    assert "fechas validas" in err[0]["errors"][0]
    # Sin partes
    data = _workbook_bytes(fechas=[datetime(2026, 7, 9)], filas=[])
    _, err = _parse_lg_workbook(data, "plan.xlsx")
    assert "numeros de parte" in err[0]["errors"][0]


def _part10_bytes():
    """Hoja 'Part 10' minima: encabezado con PART NUMBER + bloque P/S/I."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Part 10"
    # encabezado (fila 30 en el real; la posicion no importa, se busca)
    ws.cell(row=5, column=3, value="PART NUMBER")
    ws.cell(row=5, column=17, value=datetime(2026, 6, 29))
    ws.cell(row=5, column=18, value=datetime(2026, 6, 30))
    # bloque P/S/I
    ws.cell(row=6, column=3, value="EBR80757421")
    ws.cell(row=6, column=4, value="EAX66946005")
    ws.cell(row=6, column=5, value=399)   # LGEMM
    ws.cell(row=6, column=6, value=408)   # ISEMM
    ws.cell(row=6, column=7, value=-63)   # SVC
    ws.cell(row=6, column=11, value=15)   # smt
    ws.cell(row=6, column=12, value=8)    # imd
    ws.cell(row=6, column=13, value="R1")
    ws.cell(row=6, column=14, value="P")
    ws.cell(row=7, column=14, value="S")
    ws.cell(row=7, column=18, value=540)  # schedule 06-30
    ws.cell(row=8, column=14, value="I")
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_parse_part10():
    parsed, err = _parse_part10_workbook(_part10_bytes(), "plan.xlsx")
    assert err is None
    assert parsed["ref_date"] == date(2026, 6, 29)
    inv = parsed["inventory"]["EBR80757421"]
    assert inv["lgemm"] == 399 and inv["isemm"] == 408 and inv["svc"] == -63
    assert inv["smt"] == 15 and inv["imd"] == 8
    assert inv["line"] == "R1" and inv["board"] == "EAX66946005"
    assert parsed["schedules"][("EBR80757421", date(2026, 6, 30))] == 540


def test_parse_part10_sin_hoja():
    data = _workbook_bytes(fechas=[datetime(2026, 7, 9)], filas=[("P1", [1])])
    _, err = _parse_part10_workbook(data, "plan.xlsx")
    assert "Part 10" in err[0]["errors"][0]


def test_filas_segun_modo():
    data = _workbook_bytes(
        fechas=[datetime(2026, 7, 9), datetime(2026, 7, 10)],
        filas=[("P1", [5, 0])],
    )
    parsed, _ = _parse_lg_workbook(data, "plan.xlsx")

    todas = _pp_filas_segun_modo(parsed, "upsert", include_zero=True)
    assert len(todas) == 2
    sin_ceros = _pp_filas_segun_modo(parsed, "upsert", include_zero=False)
    assert len(sin_ceros) == 1 and sin_ceros[0][2] == 5
    solo_positivos = _pp_filas_segun_modo(parsed, "only_positive", include_zero=True)
    assert len(solo_positivos) == 1


# ---------- Plan Proyectado (generador de lotes tipo hoja LOTE N) ----------

def test_ppy_qty_pack_redondeo_caja_cerrada():
    from app.api.control_produccion.part_planning import _ppy_qty_pack

    # faltante 510 +10% = 561 -> multiplo de 20 arriba = 580
    assert _ppy_qty_pack(510, 20) == 580
    # sin pack (None/0) -> solo el +10% redondeado arriba
    assert _ppy_qty_pack(510, None) == 561
    assert _ppy_qty_pack(510, 0) == 561
    # exacto: 100 +10% = 110, pack 10 -> 110
    assert _ppy_qty_pack(100, 10) == 110
    # siempre cierra caja aunque el 10% ya pase el multiplo
    assert _ppy_qty_pack(95, 20) == 120  # 104.5 -> 120


def test_ppy_familia_y_uph():
    from app.api.control_produccion.part_planning import _ppy_familia, _ppy_parse_uph

    assert _ppy_familia("EBR80757421") == "EBR807574"
    assert _ppy_familia("EBR80757422") == _ppy_familia("EBR80757412")
    assert _ppy_parse_uph("240") == 240
    assert _ppy_parse_uph(240.0) == 240
    assert _ppy_parse_uph("") is None
    assert _ppy_parse_uph(None) is None
    assert _ppy_parse_uph("0") is None
    assert _ppy_parse_uph("N/A") is None


def test_ppy_armar_lotes_capacidad_y_adelantos():
    from app.api.control_produccion.part_planning import _ppy_armar_lotes

    hoy = date(2026, 7, 14)
    manana = date(2026, 7, 15)

    def cand(part, falt_total, falt_hoy, primera, uph=100, pack=20, line=None):
        return {"part_no": part, "falt_total": falt_total, "falt_hoy": falt_hoy,
                "primera_falta": primera, "line": line, "uph": uph, "pack": pack,
                "model": None, "main_sub": None}

    # 1) Prioridad: faltante de HOY entra antes que el adelanto cuando no hay horas
    horas = {"M1": 1.0}  # 1 h a 100 uph = 100 pzs
    lotes, fuera = _ppy_armar_lotes(
        [cand("FUTURO0001", 500, 0, manana), cand("URGENTE001", 500, 500, hoy)],
        ["M1"], horas)
    assert lotes[0]["part_no"] == "URGENTE001"
    assert lotes[0]["qty"] == 100  # parcial a caja cerrada por horas
    assert "parcial" in lotes[0]["comentario"]
    assert fuera and fuera[0]["part_no"] == "FUTURO0001"

    # 2) Adelanto: cabe completo (+10% a pack) y trae comentario de adelanto
    horas = {"M1": 9.0}
    lotes, fuera = _ppy_armar_lotes([cand("FUTURO0001", 500, 0, manana)], ["M1"], horas)
    assert not fuera
    assert lotes[0]["qty"] == 560  # 550 -> pack 20 -> 560
    assert lotes[0]["comentario"].startswith("Adelanto")
    assert abs(horas["M1"] - (9.0 - 5.6)) < 1e-6

    # 3) Familia junta en la misma linea aunque otra este mas libre
    horas = {"M1": 9.0, "M2": 9.0}
    lotes, _ = _ppy_armar_lotes(
        [cand("EBR8075741A", 400, 400, hoy, line="M1"),
         cand("EBR8075742B", 400, 400, hoy)],
        ["M1", "M2"], horas)
    assert {l["part_no"][:9] for l in lotes} == {"EBR807574"}
    assert len({l["linea"] for l in lotes}) == 1  # misma linea la familia

    # 4) Sin UPH o sin pack: la parte NO se genera (visible en no_incluidos)
    horas = {"M1": 9.0}
    lotes, fuera = _ppy_armar_lotes(
        [cand("SINUPH0001", 100, 100, hoy, uph=None),
         cand("SINPACK001", 100, 100, hoy, pack=None),
         cand("SINNADA001", 100, 0, manana, uph=None, pack=None),
         cand("COMPLETA01", 100, 100, hoy)],
        ["M1"], horas)
    assert [l["part_no"] for l in lotes] == ["COMPLETA01"]
    motivos = {f["part_no"]: f["motivo"] for f in fuera}
    assert "UPH" in motivos["SINUPH0001"]
    assert "pack" in motivos["SINPACK001"]
    assert "UPH" in motivos["SINNADA001"] and "pack" in motivos["SINNADA001"]


def test_ppy_armar_lotes_lineas_permitidas():
    from app.api.control_produccion.part_planning import _ppy_armar_lotes

    hoy = date(2026, 7, 14)

    def cand(part, permitidas=None, line=None):
        return {"part_no": part, "falt_total": 100, "falt_hoy": 100,
                "primera_falta": hoy, "line": line, "uph": 100, "pack": 20,
                "model": None, "main_sub": None, "permitidas": permitidas}

    # Solo puede ir a D1 aunque M1 este mas libre; sin regla va a la mas libre
    horas = {"M1": 9.0, "D1": 2.0}
    lotes, fuera = _ppy_armar_lotes(
        [cand("SOLOD10001", permitidas=["D1"]),
         cand("LIBRE00001")],
        ["M1", "D1"], horas)
    por_parte = {l["part_no"]: l["linea"] for l in lotes}
    assert por_parte["SOLOD10001"] == "D1"
    assert por_parte["LIBRE00001"] == "M1"

    # Sus lineas no estan activas -> fuera con motivo claro
    horas = {"M1": 9.0}
    lotes, fuera = _ppy_armar_lotes([cand("SOLOH10001", permitidas=["H1"])], ["M1"], horas)
    assert not lotes
    assert "H1" in fuera[0]["motivo"] and "no estan activas" in fuera[0]["motivo"]

    # Permitida activa pero sin horas -> motivo menciona sus lineas
    horas = {"M1": 9.0, "D1": 0.0}
    lotes, fuera = _ppy_armar_lotes([cand("SOLOD10002", permitidas=["D1"])], ["M1", "D1"], horas)
    assert not lotes
    assert "sin horas" in fuera[0]["motivo"] and "D1" in fuera[0]["motivo"]


def test_ppy_armar_lotes_modo_laxo_propuesta_schedule():
    from app.api.control_produccion.part_planning import _ppy_armar_lotes

    hoy = date(2026, 7, 14)

    def cand(part, uph=100, pack=20):
        return {"part_no": part, "falt_total": 100, "falt_hoy": 100,
                "primera_falta": hoy, "line": None, "uph": uph, "pack": pack,
                "model": None, "main_sub": None}

    # Sin pack -> asume 20; sin UPH -> entra sin consumir horas
    horas = {"M1": 9.0}
    lotes, fuera = _ppy_armar_lotes(
        [cand("SINPACK001", pack=None),
         cand("SINUPH0001", uph=None, pack=None),
         cand("NORMAL0001")],
        ["M1"], horas, estricto=False)
    assert not fuera
    por_parte = {l["part_no"]: l for l in lotes}
    assert por_parte["SINPACK001"]["qty"] == 120   # 110 -> pack 20 -> 120
    assert por_parte["SINUPH0001"]["qty"] == 120   # mismo calculo, sin horas
    # solo las partes con UPH consumen horas (120/100 + 120/100 = 2.4)
    assert abs(horas["M1"] - (9.0 - 2.4)) < 1e-6


def test_ppy_acomodo_heuristico_asigna_linea_por_id():
    from app.api.control_produccion.part_planning import _ppy_acomodo_heuristico

    pend = [
        {"id": 1, "part_no": "EBR8075741A", "qty_plan": 200, "uph": 100,
         "estandar_pack": 20, "model": None, "main_sub": None, "permitidas": ["M1"]},
        {"id": 2, "part_no": "EBR8075742B", "qty_plan": 200, "uph": 100,
         "estandar_pack": 20, "model": None, "main_sub": None, "permitidas": None},
        {"id": 3, "part_no": "ABC00000001", "qty_plan": 100, "uph": 100,
         "estandar_pack": 20, "model": None, "main_sub": None, "permitidas": ["H1"]},
    ]
    horas = {"M1": 9.0, "M2": 9.0}
    asig = _ppy_acomodo_heuristico(pend, ["M1", "M2"], horas)
    # id 1 permitido solo M1; familia (1 y 2 = EBR807574) juntas en M1
    assert asig[1] == "M1"
    assert asig[2] == "M1"
    # id 3 solo permite H1 que no esta activa -> no se asigna
    assert 3 not in asig
    # no muta el dict original de horas del caller
    assert horas["M1"] == 9.0
