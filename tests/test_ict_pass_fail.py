"""Tests de la regla de clasificacion ICT Pass/Fail.

Cubre _ict_pass_fail_real_counts, incluida la regla del 2026-05-28:
si la pieza fue reparada pero el ICT estuvo OK en todos los intentos
(ng_count == 0) se ignora la reparacion y se cuenta como OK_REAL
(la clase FALSO_NEGATIVO ya no existe).
"""

from app.api.control_resultados.historial_ict_pass_fail import (
    _ict_pass_fail_real_counts,
    _parse_numeros_parte,
)


def test_parse_numeros_parte_separa_dedup_y_cap():
    assert _parse_numeros_parte("EBR1, EBR2\nEBR3 EBR1") == ["EBR1", "EBR2", "EBR3"]
    assert _parse_numeros_parte("") == []
    assert _parse_numeros_parte("   ") == []
    assert len(_parse_numeros_parte("\n".join(f"P{i}" for i in range(500)))) == 200


def test_reparada_con_ng_es_defecto_detectado():
    r = _ict_pass_fail_real_counts(intentos=2, ok_count=1, ng_count=1, fue_reparacion=True)
    assert r["criterio_real"] == "DEFECTO_DETECTADO"
    assert r["defectos_detectados"] == 1
    assert r["correcto_real"] == 1
    assert r["falsos_negativos"] == 0


def test_reparada_sin_ng_se_ignora_y_es_ok_real():
    r = _ict_pass_fail_real_counts(intentos=1, ok_count=1, ng_count=0, fue_reparacion=True)
    assert r["criterio_real"] == "OK_REAL"
    assert r["correcto_real"] == 1
    assert r["falla_real"] == 0
    assert r["falsos_negativos"] == 0


def test_sin_reparar_con_ng_es_falso_fail():
    r = _ict_pass_fail_real_counts(intentos=3, ok_count=2, ng_count=1, fue_reparacion=False)
    assert r["criterio_real"] == "FALSO_FAIL"
    assert r["falsos_fail"] == 1
    assert r["correcto_real"] == 2


def test_sin_reparar_sin_ng_es_ok_real():
    r = _ict_pass_fail_real_counts(intentos=1, ok_count=1, ng_count=0, fue_reparacion=False)
    assert r["criterio_real"] == "OK_REAL"
    assert r["falsos_fail"] == 0


def test_nunca_emite_falso_negativo():
    for fue_rep in (True, False):
        for ng in (0, 1, 2):
            r = _ict_pass_fail_real_counts(1, 1, ng, fue_rep)
            assert r["falsos_negativos"] == 0
