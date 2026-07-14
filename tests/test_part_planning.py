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
