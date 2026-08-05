"""Tests de la conversion fila de Tracking -> historial de etapas.

Cubre _fila_a_item (orden del flujo, las etapas que no son booleanas y la
precedencia del estado global) y el modo lote: leer los codigos de un Excel y
mapear cada codigo pedido a su fila.
"""

import io
from datetime import datetime

from openpyxl import Workbook

from app.api.control_reporte import production_tracking as pt
from app.api.control_reporte.production_tracking import (
    _ETAPAS,
    _buscar_lote,
    _codigos_desde_excel,
    _fila_a_item,
)


def _fila(**kw):
    """Fila de Tracking vacia (todas las etapas en 0) con overrides."""
    row = {"QR": "I2026;MAIN;EBR1;1;", "Barcode": "EBR1922606180027"}
    for col, col_at, _ in _ETAPAS:
        row[col] = None if col == "Embarques" else 0
        row[col_at] = None
    row.update(kw)
    return row


def test_pieza_sin_etapas():
    item = _fila_a_item(_fila())
    assert item["registradas"] == 0
    assert item["estado_global"] == "Sin registro de proceso"
    assert item["ultima_etapa"] == ""
    assert len(item["etapas"]) == len(_ETAPAS)


def test_etapas_de_excepcion_no_alcanzadas_son_na_y_el_resto_pendiente():
    """Reparaciones y scrap sin tocar = "N/A" (normal); el resto = "-" (falto)."""
    por_etapa = {e["etapa"]: e for e in _fila_a_item(_fila())["etapas"]}

    for etapa in ("Reparacion SMD", "Reparacion Assy", "Scrap"):
        assert por_etapa[etapa]["estado"] == "N/A"
        assert por_etapa[etapa]["clase"] == "na"

    for etapa in ("SMT", "IMD", "Assy", "Vision", "ICT", "FCT",
                  "Packing QA", "Releases OQC", "Embarques"):
        assert por_etapa[etapa]["estado"] == "-"
        assert por_etapa[etapa]["clase"] == "pendiente"


def test_orden_de_etapas_es_el_del_flujo():
    etapas = [e["etapa"] for e in _fila_a_item(_fila())["etapas"]]
    assert etapas[:4] == ["SMT", "IMD", "Assy", "Vision"]
    # Primer paso, y despues el bloque de retorno por exceso.
    assert etapas[9:12] == ["Releases OQC", "Embarques", "Scrap"]
    assert etapas[12:] == ["Entrada Exceso", "ICT retorno", "FCT retorno",
                           "Packing retorno", "Salida Exceso (OQC)"]


def test_ultima_etapa_es_la_mas_reciente_no_la_ultima_columna():
    # Assy se registro DESPUES de ICT (relojes de estacion desfasados).
    item = _fila_a_item(_fila(
        Assy=1, Assy_At=datetime(2026, 7, 2, 10, 0),
        ICT_QA=1, ICT_QA_At=datetime(2026, 7, 1, 8, 0),
    ))
    assert item["registradas"] == 2
    assert item["ultima_etapa"] == "Assy"
    assert item["estado_global"] == "Assy"


def _etapa(item, nombre):
    return next(e for e in item["etapas"] if e["etapa"] == nombre)


def test_embarques_es_enum_no_booleano():
    en = _fila_a_item(_fila(Embarques="EN_EMBARQUES", Embarques_At=datetime(2026, 8, 3, 10, 0)))
    assert en["estado_global"] == "En embarques"
    assert _etapa(en, "Embarques")["estado"] == "EN EMBARQUES"
    assert _etapa(en, "Embarques")["clase"] == "embarques"

    salio = _fila_a_item(_fila(Embarques="SALIO", Embarques_At=datetime(2026, 8, 3, 10, 0)))
    assert salio["estado_global"] == "Salio de embarques"
    assert _etapa(salio, "Embarques")["clase"] == "salio"


def test_scrap_manda_sobre_embarques_y_sobre_la_ultima_etapa():
    # Caso real: 158 piezas tienen Scrap=1 junto con Releases_OQC=1.
    item = _fila_a_item(_fila(
        Releases_OQC=1, Releases_OQC_At=datetime(2026, 7, 1, 8, 0),
        Embarques="SALIO", Embarques_At=datetime(2026, 7, 2, 8, 0),
        Scrap=1, Scrap_At=datetime(2026, 6, 1, 8, 0),
    ))
    assert item["estado_global"] == "SCRAP"
    assert item["clase_global"] == "scrap"


def test_reparacion_se_distingue_de_una_etapa_normal():
    item = _fila_a_item(_fila(Rep_SMD=1, Rep_SMD_At=datetime(2026, 7, 1, 8, 0)))
    rep = next(e for e in item["etapas"] if e["etapa"] == "Reparacion SMD")
    assert rep["clase"] == "rep"
    assert rep["ok"] is True


def test_etapa_marcada_sin_fecha_cuenta_pero_no_fija_la_ultima():
    item = _fila_a_item(_fila(SMT=1, SMT_At=None))
    assert item["registradas"] == 1
    assert item["ultima_etapa"] == ""
    assert item["estado_global"] == "Sin registro de proceso"


def test_sin_barcode_las_etapas_que_cruzan_por_barcode_son_indeterminables():
    """M1/D1/D2 no escanean barcode en ASSY: para esas piezas ICT/FCT/Packing/
    OQC/Embarques no se pueden saber, y un "-" se leeria como "no paso"."""
    item = _fila_a_item(_fila(Barcode=None, Assy=1, Assy_At=datetime(2026, 7, 1, 8, 0)))
    por_etapa = {e["etapa"]: e for e in item["etapas"]}

    assert item["sin_barcode"] is True
    for etapa in ("ICT", "FCT", "Packing QA", "Releases OQC", "Embarques"):
        assert por_etapa[etapa]["estado"] == "BARCODE NO VINCULADO"
        assert por_etapa[etapa]["clase"] == "nd"

    # Las que cruzan por QR siguen siendo "-": esas si faltaron de verdad.
    assert por_etapa["SMT"]["estado"] == "-"
    assert por_etapa["Vision"]["estado"] == "-"
    # Y el denominador no cuenta lo indeterminable: 12 - 5 = 7.
    assert item["total"] == 7
    assert item["registradas"] == 1


def test_con_barcode_nada_es_indeterminable():
    item = _fila_a_item(_fila(Assy=1, Assy_At=datetime(2026, 7, 1, 8, 0)))
    assert item["sin_barcode"] is False
    # Todas menos el bloque de retorno, que no aplica si nunca fue a exceso.
    assert item["total"] == len(_ETAPAS) - len(pt._ETAPAS_RETORNO)
    assert not any(e["clase"] == "nd" for e in item["etapas"])


def test_barcode_en_blanco_cuenta_como_sin_barcode():
    assert _fila_a_item(_fila(Barcode="   "))["sin_barcode"] is True


def test_sin_qr_las_etapas_que_cruzan_por_qr_son_indeterminables():
    """El espejo del caso anterior: una pieza con barcode que nunca se vinculo
    a un QR no puede tener SMT/IMD/Assy, que se cruzan solo por QR."""
    item = _fila_a_item(_fila(QR=None, ICT_QA=1, ICT_QA_At=datetime(2026, 7, 1, 8, 0)))
    por_etapa = {e["etapa"]: e for e in item["etapas"]}

    assert item["sin_qr"] is True
    for etapa in ("SMT", "IMD", "Assy"):
        assert por_etapa[etapa]["estado"] == "QR NO VINCULADO"
        assert por_etapa[etapa]["clase"] == "nd"

    # Vision y las de reparacion aceptan cualquiera de los dos codigos, asi que
    # para estas piezas si son determinables: se quedan en "-" / "N/A".
    assert por_etapa["Vision"]["estado"] == "-"
    assert por_etapa["Reparacion SMD"]["estado"] == "N/A"
    assert item["total"] == 9  # 12 - 3


def test_fila_sintetica_arma_la_forma_de_tracking_desde_las_fuentes():
    fila = pt._fila_sintetica("EBR9", {
        "ICT_QA": datetime(2026, 7, 1, 8, 0),
        "Embarques": "SALIO",
        "Embarques_At": datetime(2026, 7, 3, 9, 0),
    })
    assert fila["QR"] is None and fila["Barcode"] == "EBR9"
    assert fila["ICT_QA"] == 1 and fila["ICT_QA_At"] == datetime(2026, 7, 1, 8, 0)
    assert fila["Embarques"] == "SALIO"
    assert fila["FCT"] == 0 and fila["FCT_At"] is None

    item = _fila_a_item(fila)
    assert item["sin_qr"] is True
    assert item["estado_global"] == "Salio de embarques"


# ---------------------------------------------------------------------------
# Retorno por exceso QA
# ---------------------------------------------------------------------------


def test_sin_entrada_a_exceso_todo_el_bloque_de_retorno_es_na():
    por_etapa = {e["etapa"]: e for e in _fila_a_item(_fila())["etapas"]}
    for etapa in ("Entrada Exceso", "ICT retorno", "FCT retorno",
                  "Packing retorno", "Salida Exceso (OQC)"):
        assert por_etapa[etapa]["estado"] == "N/A"
    # Y no se cuentan en el denominador de una pieza que nunca fue a exceso.
    assert _fila_a_item(_fila())["total"] == len(_ETAPAS) - len(pt._ETAPAS_RETORNO)


def test_en_exceso_sin_reproceso_deja_las_de_retorno_pendientes():
    """La señal operativa: la pieza llego a exceso y aun no se vuelve a probar."""
    item = _fila_a_item(_fila(
        Exceso_In=1, Exceso_In_At=datetime(2026, 8, 4, 12, 0),
        Ret_ICT=0, Ret_FCT=0, Ret_Packing=0, Exceso_Out=0,
    ))
    por_etapa = {e["etapa"]: e for e in item["etapas"]}

    assert item["en_exceso"] is True
    assert item["estado_global"] == "En exceso QA"
    assert por_etapa["Entrada Exceso"]["estado"] == "OK"
    # "-" y no "N/A": aqui si falta que pase, es lo que se esta esperando.
    for etapa in ("ICT retorno", "FCT retorno", "Salida Exceso (OQC)"):
        assert por_etapa[etapa]["estado"] == "-"
        assert por_etapa[etapa]["clase"] == "pendiente"
    assert item["total"] == len(_ETAPAS)


def test_liberado_de_exceso_manda_sobre_embarques():
    """Si la pieza volvio y ya se libero, el estado de embarques del primer
    paso quedo viejo y no debe ser el que se muestre."""
    item = _fila_a_item(_fila(
        Embarques="SALIO", Embarques_At=datetime(2026, 5, 1, 8, 0),
        Exceso_In=1, Exceso_In_At=datetime(2026, 5, 29, 23, 59),
        Exceso_Out=1, Exceso_Out_At=datetime(2026, 8, 5, 8, 20),
    ))
    assert item["estado_global"] == "Liberado de exceso"


def test_scrap_sigue_mandando_sobre_exceso():
    item = _fila_a_item(_fila(
        Scrap=1, Scrap_At=datetime(2026, 6, 1, 8, 0),
        Exceso_In=1, Exceso_In_At=datetime(2026, 5, 29, 23, 59),
    ))
    assert item["estado_global"] == "SCRAP"


def test_retorno_se_busca_por_qr_y_por_barcode(monkeypatch):
    """scan_code de qa_exceso_* viene mezclado (barcodes y QRs), asi que la
    fila se debe resolver por cualquiera de sus dos codigos."""
    monkeypatch.setattr(pt, "_retorno_exceso",
                        lambda claves: {"EBR1922606180027": {"Exceso_In": datetime(2026, 8, 4)}})
    fila = pt._aplicar_retorno([_fila()])[0]
    assert fila["Exceso_In"] == 1
    assert fila["Exceso_In_At"] == datetime(2026, 8, 4)
    assert fila["Ret_ICT"] == 0 and fila["Ret_ICT_At"] is None


def test_celda_de_lote_trae_la_fecha_salvo_en_embarques_y_lo_no_alcanzado():
    item = _fila_a_item(_fila(
        SMT=1, SMT_At=datetime(2026, 7, 1, 8, 0),
        Embarques="SALIO", Embarques_At=datetime(2026, 7, 3, 9, 30),
    ))
    por_etapa = {e["etapa"]: e for e in item["etapas"]}
    assert por_etapa["SMT"]["celda"] == "2026-07-01 08:00:00"
    # En Embarques la fecha sola no dice si entro o salio.
    assert por_etapa["Embarques"]["celda"] == "SALIO 2026-07-03 09:30:00"
    assert por_etapa["IMD"]["celda"] == "-"
    assert por_etapa["Scrap"]["celda"] == "N/A"


# ---------------------------------------------------------------------------
# Modo lote
# ---------------------------------------------------------------------------


def _xlsx(filas):
    wb = Workbook()
    ws = wb.active
    for fila in filas:
        ws.append(fila)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_codigos_desde_excel_lee_todas_las_columnas_en_orden_y_sin_repetir():
    codigos = _codigos_desde_excel(_xlsx([
        ["Codigo", "Nota"],
        ["EBR1", "sobrante"],
        ["EBR2", None],
        ["EBR1", "EBR3"],   # EBR1 repetido, EBR3 en la segunda columna
    ]))
    assert codigos == ["Codigo", "Nota", "EBR1", "sobrante", "EBR2", "EBR3"]


def test_codigos_numericos_no_llegan_como_float():
    """Excel guarda 123456 como float; '123456.0' nunca cruzaria contra Tracking."""
    assert _codigos_desde_excel(_xlsx([[123456], [12.5]])) == ["123456", "12.5"]


def test_codigos_desde_excel_respeta_el_tope():
    codigos = _codigos_desde_excel(_xlsx([[f"C{i}"] for i in range(pt._MAX_CODIGOS_LOTE + 50)]))
    assert len(codigos) == pt._MAX_CODIGOS_LOTE


def test_buscar_lote_devuelve_una_fila_por_codigo_pedido_y_en_su_orden(monkeypatch):
    fila_qr = _fila(QR="QR-A", Barcode="BC-A", SMT=1, SMT_At=datetime(2026, 7, 1, 8, 0))
    fila_bc = _fila(QR="QR-B", Barcode="BC-B")
    monkeypatch.setattr(pt, "execute_query", lambda *a, **k: [fila_qr, fila_bc])

    # Se pide por QR, por Barcode y algo inexistente; el orden es el del archivo.
    items = _buscar_lote(["BC-B", "NO-EXISTE", "QR-A"])

    assert [i["codigo"] for i in items] == ["BC-B", "NO-EXISTE", "QR-A"]
    assert [i["encontrado"] for i in items] == [True, False, True]
    assert items[0]["qr"] == "QR-B"
    assert items[2]["qr"] == "QR-A"
    # El no encontrado trae igual las 12 columnas, para que la tabla no se desalinee.
    assert len(items[1]["etapas"]) == len(_ETAPAS)
    assert items[1]["estado_global"] == "No encontrado"


def test_buscar_lote_parte_en_chunks(monkeypatch):
    """Ninguna sentencia debe recibir mas de un chunk de codigos, ni la busqueda
    en Tracking ni la reconstruccion desde las fuentes."""
    llamadas = []

    def fake(sql, params, fetch):
        llamadas.append(len(params or []))
        return []

    monkeypatch.setattr(pt, "execute_query", fake)
    _buscar_lote([f"C{i}" for i in range(pt._LOTE_CHUNK + 1)])

    # Las dos primeras son la busqueda en Tracking: cada una recibe sus codigos
    # dos veces (QR IN ... OR Barcode IN ...).
    assert llamadas[:2] == [pt._LOTE_CHUNK * 2, 2]
    # Y el resto (fuentes por barcode) tampoco excede el tamaño de tanda.
    assert llamadas and max(llamadas) <= pt._LOTE_CHUNK * 2
