"""Tests de helpers de catalogo de modelos."""

from app.api.shared.model_catalog import (
    bom_suffix_from_part_no,
    ensure_raw_model_for_smd,
    family_prefix_from_part_no,
    infer_bom_kind,
    normalize_part_no,
)
from app.api.shared import model_catalog


def test_normaliza_part_no_y_deriva_familia():
    assert normalize_part_no(" ebr30299301 ") == "EBR30299301"
    assert family_prefix_from_part_no("EBR30299301") == "EBR302993"
    assert bom_suffix_from_part_no("EBR30299301") == "01"


def test_infiere_tipo_bom_por_origen_local():
    assert infer_bom_kind("raw", {"part_no": "ABQ74229132"}) == "MASTER"
    assert infer_bom_kind("raw_smd", {"linea": "PANA A"}) == "SMD"
    assert infer_bom_kind("raw_smd", {"linea": "IMD A"}) == "IMD"
    assert infer_bom_kind("raw_smd", {"bom_kind": "OTHER"}) == "OTHER"


def test_ensure_raw_model_for_smd_no_pisa_padre_existente(monkeypatch):
    calls = []

    def fake_execute_query(query, params=None, fetch=None):
        calls.append((query, params, fetch))
        assert fetch == "one"
        return {"id": 7, "part_no": "EBR30299301"}

    monkeypatch.setattr(model_catalog, "execute_query", fake_execute_query)

    result = ensure_raw_model_for_smd({"part_no": " ebr30299301 "}, user_name="Captura")

    assert result["ok"] is True
    assert result["exists"] is True
    assert result["inserted"] is False
    assert result["raw_id"] == 7
    assert len(calls) == 1


def test_ensure_raw_model_for_smd_crea_padre_si_falta(monkeypatch):
    calls = []

    def fake_execute_query(query, params=None, fetch=None):
        calls.append((query, params, fetch))
        if fetch == "one":
            return None
        return 1

    monkeypatch.setattr(model_catalog, "execute_query", fake_execute_query)

    result = ensure_raw_model_for_smd(
        {
            "part_no": "ebr30299301",
            "model": "Modelo SMT",
            "maindisplay": "Display",
            "ct": "12.5",
            "uph": "288",
            "horadia": "24",
            "linea": "PANA 1",
            "usuario": "Operador",
        },
        user_name="Captura",
    )

    insert_query, insert_params, insert_fetch = calls[1]
    assert result["ok"] is True
    assert result["inserted"] is True
    assert "INSERT INTO raw" in insert_query
    assert insert_fetch is None
    assert insert_params == (
        "EBR30299301",
        "Modelo SMT",
        "Display",
        "12.5",
        "288",
        "24",
        "PANA 1",
        "Operador",
    )
