"""Parseo del numero de parte desde `box_scans.serial` (2026-09-23).

El criterio lo fija el parser del proyecto ESCANEO_INPUT
(`backend/src/domain/parser.js`); estos casos son sus dos formatos mas la
variante con teclado espanol que aparece en datos historicos.
"""

import pytest

from app.api.shared.scan_serial import part_no_desde_serial, part_no_desde_serial_sql


CASOS = [
    # QR: el numero de parte es el tercer campo. Es el unico formato en D1/M1,
    # que van en modo qrOnly.
    ("I20260921-013-00480;MAIN;EBR76683912;1;", "EBR76683912"),
    ("I20260921-013-00001;MAIN;EBR76683912;1;", "EBR76683912"),
    # Mismo QR con separadores de teclado espanol (ñ por ;, ' por -).
    ("I20260123'0027'00481ñMAINñEBR23966209ñ1ñ", "EBR23966209"),
    # Barcode: los 11 primeros caracteres.
    ("ACQ30372826922609220001", "ACQ30372826"),
    ("EBR2396621192260417079111", "EBR23966211"),
    # Por debajo de 15 caracteres parser.js no lo toma como barcode: se
    # devuelve tal cual en vez de inventar un recorte.
    ("TEST123", "TEST123"),
    ("", ""),
    (None, ""),
]


@pytest.mark.parametrize("serial,esperado", CASOS)
def test_parseo_en_python(serial, esperado):
    assert part_no_desde_serial(serial) == esperado


def test_la_expresion_sql_no_lleva_comodines():
    """Un '%' literal rompe el formateo de pymysql si la query lleva params.

    Las tres queries que usan esta expresion los llevan, asi que un LIKE aqui
    las tumbaria en runtime (no en los tests, que no tocan MySQL).
    """
    sql = part_no_desde_serial_sql("b.serial")
    assert "%" not in sql
    assert "LIKE" not in sql.upper()


def test_la_expresion_sql_usa_la_columna_que_se_le_pasa():
    sql = part_no_desde_serial_sql("x.serial")
    assert "b.serial" not in sql
    assert sql.count("x.serial") >= 4


def test_el_qr_gana_sobre_la_regla_de_longitud():
    """Un QR mide mas de 15 caracteres: si se evaluara primero la rama de
    barcode devolveria `I20260921-0` en vez del numero de parte."""
    assert part_no_desde_serial("I20260921-013-00480;MAIN;EBR76683912;1;") == "EBR76683912"
