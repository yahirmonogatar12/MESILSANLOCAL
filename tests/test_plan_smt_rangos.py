from app.api.control_produccion.plan_smt import ARRAY_RANGE, QR_RANGE, _int_en_rango


def test_int_en_rango_acepta_cero_y_acota():
    assert _int_en_rango(0, 1, *QR_RANGE) == 0  # 0 = modelo sin QR
    assert _int_en_rango("0", 1, *ARRAY_RANGE) == 0
    assert _int_en_rango("3", 1, *QR_RANGE) == 3
    assert _int_en_rango(99, 1, *QR_RANGE) == 20
    assert _int_en_rango(-5, 1, *ARRAY_RANGE) == 0
    for vacio in (None, "", "abc", float("nan")):
        assert _int_en_rango(vacio, 1, *QR_RANGE) == 1
