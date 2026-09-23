"""Parseo del numero de parte a partir del serial escaneado (`box_scans.serial`).

Los seriales los graban los escaneos del proyecto ESCANEO_INPUT, cuyo parser
canonico es `backend/src/domain/parser.js` (`parseScan`). Ahi conviven dos
formatos y este modulo replica su criterio:

  QR       `I20260921-013-00480;MAIN;EBR76683912;1;`
           Campos separados por `;`. El numero de parte es el TERCERO
           (`parts[2]` en parser.js). Es el unico formato de las lineas en
           modo `qrOnly` — D1 y M1, por `DEFAULT_LINE_MODE_OVERRIDES` en
           `backend/src/utils/serial-persist.js`.

  Barcode  `ACQ30372826922609220001`
           Sin separadores. El numero de parte son los 11 PRIMEROS caracteres
           (`raw.substring(0, 11)`), y solo se considera barcode a partir de
           15 caracteres.

Hay ademas una variante del QR con `ñ` en lugar de `;` (y `'` en lugar de `-`):
`I20260123'0027'00481ñMAINñEBR23966209ñ1ñ`. Sale de un escaner configurado con
layout de teclado en espanol. Son pocas filas historicas, pero se contemplan
porque el campo del numero de parte queda igual de bien delimitado.

Antes se usaba `LEFT(serial, CHAR_LENGTH(serial) - 12)`, que acertaba por
casualidad solo con el barcode de 23 caracteres: en los QR devolvia basura
como `I20260921-013-00480;MAIN;EB`, y en un barcode de 25 se comia dos
caracteres de mas.
"""

# Umbral de parser.js: por debajo de esto no se considera barcode.
_BARCODE_MIN_LEN = 15
# parser.js: `raw.substring(0, 11)`.
_BARCODE_PART_LEN = 11
# El numero de parte es el tercer campo del QR.
_QR_PART_FIELD = 3


def part_no_desde_serial_sql(columna="b.serial"):
    """Expresion SQL que extrae el numero de parte de un serial escaneado.

    `columna` es un identificador del propio codigo (nunca entrada de usuario).
    Devuelve el serial completo cuando no encaja en ningun formato conocido,
    para no perder el dato: los llamadores suelen envolverla en un COALESCE
    con el numero de parte del plan, que tiene prioridad.
    """
    col = columna
    # Sin LIKE a proposito: un '%' literal en el SQL rompe el formateo de
    # pymysql en cuanto la query lleva params, y las tres que usan esto los
    # llevan. LEFT/LOCATE hacen lo mismo sin comodines.
    return (
        "CASE"
        f" WHEN LEFT({col}, 1) = 'I' AND LOCATE(';', {col}) > 0"
        f" THEN SUBSTRING_INDEX(SUBSTRING_INDEX({col}, ';', {_QR_PART_FIELD}), ';', -1)"
        f" WHEN LEFT({col}, 1) = 'I' AND LOCATE('ñ', {col}) > 0"
        f" THEN SUBSTRING_INDEX(SUBSTRING_INDEX({col}, 'ñ', {_QR_PART_FIELD}), 'ñ', -1)"
        f" WHEN CHAR_LENGTH({col}) >= {_BARCODE_MIN_LEN}"
        f" THEN LEFT({col}, {_BARCODE_PART_LEN})"
        f" ELSE {col}"
        " END"
    )


def part_no_desde_serial(serial):
    """Version en Python de `part_no_desde_serial_sql`, para datos ya leidos."""
    texto = str(serial or "").strip()
    if not texto:
        return ""
    if texto.startswith("I"):
        for separador in (";", "ñ"):
            if separador in texto:
                campos = texto.split(separador)
                if len(campos) >= _QR_PART_FIELD:
                    return campos[_QR_PART_FIELD - 1]
    if len(texto) >= _BARCODE_MIN_LEN:
        return texto[:_BARCODE_PART_LEN]
    return texto
