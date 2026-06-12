"""Pruebas de carga baseline para Inventario Exceso QA."""


def test_parse_baseline_csv_permite_codigos_repetidos_con_sufijo_deterministico(tmp_path):
    from app.api.pda.excess_inventory import parse_excess_baseline_csv

    csv_path = tmp_path / "baseline.csv"
    csv_path.write_text(
        "BARCODE\n"
        "EBR80757422922604080325\n"
        "EBR80757422922604080325\n"
        "EBR80757422922604080325\n",
        encoding="utf-8",
    )

    rows, errors = parse_excess_baseline_csv(csv_path, ["EBR80757422"])

    assert errors == []
    assert [row["scan_code"] for row in rows] == [
        "EBR80757422922604080325",
        "EBR80757422922604080325#BASELINE0002",
        "EBR80757422922604080325#BASELINE0003",
    ]
    assert {row["raw_code"] for row in rows} == {"EBR80757422922604080325"}
    assert {row["part_number"] for row in rows} == {"EBR80757422"}


def test_resolver_usa_numero_de_parte_mas_largo():
    from app.api.pda.excess_inventory import resolve_part_number_from_scan_code

    result = resolve_part_number_from_scan_code(
        "EBR80757422922604080325",
        ["EBR807574", "EBR80757422"],
    )

    assert result == "EBR80757422"


def test_resolver_detecta_acq_embebido_en_codigo_largo():
    from app.api.pda.excess_inventory import resolve_part_number_from_scan_code

    result = resolve_part_number_from_scan_code(
        "ACQ30372850922602190026",
        ["ACQ30372850"],
    )

    assert result == "ACQ30372850"
