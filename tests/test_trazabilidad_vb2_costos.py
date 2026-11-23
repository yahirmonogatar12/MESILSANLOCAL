"""Costo por etiqueta de Verificacion BOM 2.0 (plan, seccion 7, puntos 3 a 5)."""

from decimal import Decimal

from app.api.control_resultados.trazabilidad_vb2 import lote_base_smt, resolver_costos


def test_real_heredado_estimado_y_sin_costo():
    propios = {
        "A-1": {"costo": Decimal("0.5"), "fuente": "INVOICE", "estimado": False},
        "PADRE-1": {"costo": Decimal("0.2"), "fuente": "LISTA_COMPRAS", "estimado": False},
        "HIJO-1": {"costo": None, "fuente": "SIN_COSTO", "estimado": True},
        "C-1": {"costo": Decimal("0.9"), "fuente": "CONTROL_MATERIAL", "estimado": True},
    }
    padres = {"NIETO-1": "HIJO-1", "HIJO-1": "PADRE-1"}
    r = resolver_costos(
        [("A-1", "A"), ("NIETO-1", "N"), ("C-1", "C"), ("X-1", "X"), ("K-1", "K"), ("Z-1", "Z"), (None, "A")],
        propios,
        padres,
        ultimo_real={"X": Decimal("0.3"), "A": Decimal("0.7")},
        material_costos={"K": Decimal("9")},
        ks_precio_krw={"K": Decimal("1000"), "Z": Decimal("1400")},
        krw_usd=Decimal("0.0007"),
    )
    assert r[("A-1", "A")] == {"costo": Decimal("0.5"), "real": True, "fuente": "INVOICE"}
    # sublote de sublote sin costo propio: hereda el real del abuelo
    assert r[("NIETO-1", "N")] == {"costo": Decimal("0.2"), "real": True, "fuente": "LISTA_COMPRAS (lote padre)"}
    assert r[("C-1", "C")]["real"] is False  # costo de control de material: estimado
    assert r[("X-1", "X")] == {"costo": Decimal("0.3"), "real": False, "fuente": "ULTIMO_REAL_PARTE"}
    assert r[("K-1", "K")]["fuente"] == "MATERIAL_COSTOS"  # va antes que el K-system
    assert r[("Z-1", "Z")] == {"costo": Decimal("0.98"), "real": False, "fuente": "K_SYSTEM"}
    assert r[(None, "A")]["fuente"] == "ULTIMO_REAL_PARTE"  # material sin lote: solo estimado


def test_costo_cero_no_cuenta_como_real():
    # 21 % de las etiquetas con fuente INVOICE traen costo 0: se hereda del padre o se va al estimado.
    propios = {
        "CERO-1": {"costo": Decimal("0"), "fuente": "INVOICE", "estimado": False},
        "HIJO-0": {"costo": Decimal("0.0000"), "fuente": "INVOICE", "estimado": False},
        "PADRE-9": {"costo": Decimal("1.5"), "fuente": "INVOICE", "estimado": False},
    }
    r = resolver_costos([("CERO-1", "C"), ("HIJO-0", "H")], propios, {"HIJO-0": "PADRE-9"}, {"C": Decimal("0.4")}, {}, {}, None)
    assert r[("CERO-1", "C")] == {"costo": Decimal("0.4"), "real": False, "fuente": "ULTIMO_REAL_PARTE"}
    assert r[("HIJO-0", "H")] == {"costo": Decimal("1.5"), "real": True, "fuente": "INVOICE (lote padre)"}


def test_costos_acepta_bolsa_vacia(monkeypatch):
    # Carretes de SMT con etiqueta generica llegan con bolsa None: antes tronaba al ordenar.
    from app.api.control_resultados import trazabilidad_vb2 as t

    monkeypatch.setattr(t, "_q", lambda sql, params=None: [])
    r = t._costos([(None, "A"), ("B-1", "B"), (None, "C")])
    assert set(r) == {(None, "A"), ("B-1", "B"), (None, "C")}
    assert all(v["fuente"] == "SIN_COSTO" for v in r.values())


def test_lote_base_smt_une_reprogramados_con_su_top():
    assert lote_base_smt("SMT-261110-007-01") == "SMT-261110-007"
    assert lote_base_smt("SMT-261110-007") == "SMT-261110-007"
    assert lote_base_smt("LOTE-X-1-2") == "LOTE-X-1-2"


def test_sin_tipo_de_cambio_no_se_inventa_el_precio_del_k_system():
    r = resolver_costos([("Z-1", "Z")], {}, {}, {}, {}, {"Z": Decimal("1400")}, None)
    assert r[("Z-1", "Z")] == {"costo": None, "real": False, "fuente": "SIN_COSTO"}
