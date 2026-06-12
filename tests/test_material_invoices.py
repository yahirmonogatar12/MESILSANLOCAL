from io import BytesIO

from openpyxl import Workbook

from app.api.control_material.invoice_core.normalizers import normalizar_pallet_no
from app.api.control_material.invoice_core.matcher import resolve_aliases
from app.api.control_material.invoice_core.parser import parse_invoice_workbook


def _workbook_bytes():
    wb = Workbook()
    ws = wb.active
    ws.title = "INVOICE(total)"
    ws.append(["Texto previo", "", "", ""])
    ws.append(["MAKER", "ORIGIN", "PART NUM.", "DESCRIPTION", "QTY", "UOM", "UNIT COST", "TT COST"])
    ws.append(["ILS", "KR", "abc-001", "Capacitor", "10", "EA", "1.25", "12.50"])
    packing = wb.create_sheet("PACKING LIST 원본")
    packing.append(["PACKING LIST"])
    packing.append([])
    packing.append(["", "", "NO", "품번", "품명", "수량", "", "", "", "", "", "", ""])
    packing.append(["", "", "01", "abc-001", "Capacitor", "10", "EA", "1", "PALLET", "2.5", "KG", "0.1", "CBM"])
    packing.append(["", "", "", "abc-001", "Capacitor", "5", "EA", "", "", "", "", "", ""])
    packing.append(["", "", "02", "COMMERCIAL", "", "10", "EA", "1", "PALLET", "", "", "", ""])
    packing.append(["", "", "", "zero-001", "Free sample", "0", "EA", "", "", "", "", "", ""])
    aux = wb.create_sheet("INVOICE(copy)")
    aux.append(["MAKER", "ORIGIN", "PART NUM.", "DESCRIPTION", "QTY", "UOM", "UNIT COST", "TT COST"])
    aux.append(["ILS", "KR", "ignored-001", "Aux", "99", "EA", "9.99", "989.01"])
    equivalences = wb.create_sheet("Hoja1")
    equivalences.append(["TARIMA", "PART NO", "Part Sys", "ITEM", "SPEC", "QTY"])
    equivalences.append([1, "abc-001", "SYS-001", "CAPACITOR", "x", 10])
    equivalences.append([None, "zero-001", "ZERO-SYS", "CAPACITOR", "x", 0])
    out = BytesIO()
    wb.save(out)
    return out.getvalue()


def test_normalizar_pallet_no_variantes():
    assert normalizar_pallet_no(1) == "1"
    assert normalizar_pallet_no("01") == "1"
    assert normalizar_pallet_no("PALLET 1") == "1"
    assert normalizar_pallet_no("Pallet-01") == "1"


def test_parse_invoice_workbook_detecta_invoice_y_packing_con_raw_values():
    parsed = parse_invoice_workbook(_workbook_bytes(), "INV-001.xlsx")

    assert len(parsed["invoice_lines"]) == 1
    assert len(parsed["packing_lines"]) == 2

    line = parsed["invoice_lines"][0]
    assert line["raw_part_num"] == "abc-001"
    assert line["numero_parte_invoice"] == "ABC-001"
    assert line["numero_parte_sistema"] == "ABC-001"
    assert line["raw_qty"] == "10"
    assert line["raw_unit_cost"] == "1.25"
    assert str(line["costo_total"]) == "12.5000"

    packing = parsed["packing_lines"][0]
    assert packing["pallet_no_original"] == "01"
    assert packing["pallet_no"] == "1"
    assert packing["numero_parte_packing"] == "ABC-001"
    assert packing["numero_parte_sistema"] == "ABC-001"
    assert str(packing["kg"]) == "2.5000"
    assert str(packing["cbm"]) == "0.1000"
    assert parsed["packing_lines"][1]["pallet_no_original"] == "01"
    assert parsed["packing_lines"][1]["pallet_no"] == "1"


def test_parse_invoice_workbook_requiere_hoja_invoice_total():
    wb = Workbook()
    ws = wb.active
    ws.title = "INVOICE(copy)"
    ws.append(["MAKER", "ORIGIN", "PART NUM.", "DESCRIPTION", "QTY", "UOM", "UNIT COST", "TT COST"])
    ws.append(["ILS", "KR", "abc-001", "Capacitor", "10", "EA", "1.25", "12.50"])
    out = BytesIO()
    wb.save(out)

    parsed = parse_invoice_workbook(out.getvalue(), "INV-001.xlsx")

    assert parsed["invoice_lines"] == []
    assert "INVOICE(total)" in parsed["warnings"][0]


def test_material_invoice_blueprints_registran_rutas(app):
    rules = {str(rule) for rule in app.url_map.iter_rules()}

    assert "/material/invoices" in rules
    assert "/api/material_admin/invoices/upload" in rules
    assert "/api/material_admin/invoices/aliases" in rules
    assert "/api/material_admin/invoices/aliases/import" in rules
    assert "/api/material_admin/invoices/<int:invoice_id>/apply" in rules
    assert "/api/material_admin/inventory/valuation" in rules
    assert "/api/material_admin/inventory/valuation/backfill" in rules
    assert "/api/informacion_basica/control_material/numeros-originales/import" in rules
    assert "/api/informacion_basica/control_material/numeros-originales/preview" in rules


class _AliasCursor:
    def __init__(self):
        self.calls = 0

    def execute(self, query, params):
        self.calls += 1

    def fetchall(self):
        if self.calls == 1:
            return [
                {
                    "numero_parte_original": "EAH63473601",
                    "numero_parte_sistema": "EAH63473601",
                    "tipo": "LG",
                },
                {
                    "numero_parte_original": "EAH63473601",
                    "numero_parte_sistema": "XAH63473601",
                    "tipo": "ILSAN",
                },
                {
                    "numero_parte_original": "EAH63473601",
                    "numero_parte_sistema": "GLOBAL-IGNORADO",
                    "tipo": "",
                },
            ]
        return []


def test_resolve_aliases_prioriza_tipo_especifico():
    records = [{"numero_parte_sistema": "EAH63473601", "cantidad": 1}]

    resolve_aliases(_AliasCursor(), records, "LG", "numero_parte_sistema")

    assert records[0]["numero_parte_sistema"] == "EAH63473601"
    assert records[0]["estado_match"] == "ALIAS"
