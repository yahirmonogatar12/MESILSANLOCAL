import importlib.util
from decimal import Decimal
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "reparar_costo_invoice", Path(__file__).parents[1] / "tools" / "reparar_costo_invoice.py"
)
reparar = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(reparar)


def _excel(line_no, parte, cantidad, unit):
    return {
        "line_no": line_no,
        "raw_part_num": parte,
        "cantidad": Decimal(cantidad),
        "costo_unitario": Decimal(unit),
        "raw_unit_cost": unit,
    }


def _bd(line_id, line_no, parte, cantidad, unit, total):
    return {
        "id": line_id,
        "line_no": line_no,
        "raw_part_num": parte,
        "cantidad": Decimal(cantidad),
        "costo_unitario": Decimal(unit),
        "costo_total": Decimal(total),
    }


def test_cambios_solo_lineas_en_cero_que_coinciden():
    excel = [
        _excel(1, "6600RRT001Z", "20000", "0.0111"),  # TOTAL distinto: se corrige y avisa
        _excel(2, "EAH64252901", "8000", "0.1208"),
        _excel(3, "EAX65150407-1.0", "4032", "1.4379"),  # en BD ya tiene costo
        _excel(4, "EBC38096602", "16000", "0.3247"),  # en BD cambio la cantidad
        _excel(5, "EBJ62670305", "2200", "0"),  # sin PRECIO en el Excel
    ]
    bd = [
        _bd(11, 1, "6600RRT001Z", "20000", "0", "555"),
        _bd(12, 2, "EAH64252901", "8000", "0", "966.4"),
        _bd(13, 3, "EAX65150407-1.0", "4032", "1.4", "5797.6128"),
        _bd(14, 4, "EBC38096602", "15000", "0", "5194.8"),
        _bd(15, 5, "EBJ62670305", "2200", "0", "2072.664"),
    ]

    nuevos, distintas, incoherentes = reparar.cambios(excel, bd)

    assert nuevos == [(11, Decimal("0.0111"), "0.0111"), (12, Decimal("0.1208"), "0.1208")]
    assert distintas == [4]
    assert len(incoherentes) == 1 and incoherentes[0].startswith("No. 1 6600RRT001Z")
