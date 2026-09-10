"""Genera un PDF valido con texto, sin dependencias de escritura.

Se arma a mano el PDF mas simple posible (un flujo de texto por pagina) para
poder probar la indexacion y busqueda de PDF grandes: instalar un generador de
PDF solo para los tests no valdria la pena.
"""


def pdf_con_paginas(lineas_por_pagina: list[list[str]]) -> bytes:
    """Devuelve los bytes de un PDF con una pagina por lista de lineas."""
    objetos: list[bytes] = []

    def agregar(cuerpo: bytes) -> int:
        objetos.append(cuerpo)
        return len(objetos)  # los numeros de objeto empiezan en 1

    fuente = agregar(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    # Se reservan los ids de las paginas para poder apuntarlos desde /Kids.
    total = len(lineas_por_pagina)
    id_paginas = len(objetos) + 1
    objetos.append(b"")  # marcador del nodo /Pages
    ids_pagina = []
    for lineas in lineas_por_pagina:
        texto = b"BT /F1 11 Tf 40 750 Td 14 TL\n"
        for linea in lineas:
            escapada = (linea.replace("\\", "").replace("(", "").replace(")", ""))
            texto += b"(" + escapada.encode("latin-1", "replace") + b") Tj T*\n"
        texto += b"ET"
        flujo = agregar(
            b"<< /Length " + str(len(texto)).encode() + b" >>\nstream\n" + texto + b"\nendstream"
        )
        pagina = agregar(
            b"<< /Type /Page /Parent " + str(id_paginas).encode() + b" 0 R "
            b"/MediaBox [0 0 612 792] /Contents " + str(flujo).encode() + b" 0 R "
            b"/Resources << /Font << /F1 " + str(fuente).encode() + b" 0 R >> >> >>"
        )
        ids_pagina.append(pagina)
    kids = b" ".join(str(i).encode() + b" 0 R" for i in ids_pagina)
    objetos[id_paginas - 1] = (
        b"<< /Type /Pages /Count " + str(total).encode() + b" /Kids [" + kids + b"] >>"
    )
    raiz = agregar(b"<< /Type /Catalog /Pages " + str(id_paginas).encode() + b" 0 R >>")

    salida = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for numero, cuerpo in enumerate(objetos, start=1):
        offsets.append(len(salida))
        salida += str(numero).encode() + b" 0 obj\n" + cuerpo + b"\nendobj\n"
    inicio_xref = len(salida)
    salida += b"xref\n0 " + str(len(objetos) + 1).encode() + b"\n"
    salida += b"0000000000 65535 f \n"
    for offset in offsets[1:]:
        salida += ("%010d 00000 n \n" % offset).encode()
    salida += (
        b"trailer\n<< /Size " + str(len(objetos) + 1).encode()
        + b" /Root " + str(raiz).encode() + b" 0 R >>\nstartxref\n"
        + str(inicio_xref).encode() + b"\n%%EOF\n"
    )
    return bytes(salida)
