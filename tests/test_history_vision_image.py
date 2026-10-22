"""Imagen y detalle de NG del historial Vision segun la fuente del registro.

SHT (.txt de resultados): log_datetime es el sello exacto de la foto (al milisegundo) y el
nombre de la foto trae el ultimo codigo leido. shlog: log_datetime es el fin de la
inspeccion, 0.2-0.4 s despues de la foto.
"""

import time
from datetime import datetime

from app.api.control_resultados import historial_vision
from app.api.shared import vision_helpers

QR = "I20261012-016-00072;MAIN;EBR30299370;1;"
SHOT = datetime(2026, 10, 22, 15, 41, 45, 137000)


def _photo_tree(tmp_path, names, part="EBR30299370", result="OK"):
    """Result share falso: <root>/<parte>/Image(Process)/2026/10/22/15/상부/<OK|NG>/<fotos>."""
    root = tmp_path / "Result M3"
    folder = root / part / "Image(Process)" / "2026" / "10" / "22" / "15" / "상부" / result
    folder.mkdir(parents=True)
    for name in names:
        (folder / name).write_bytes(b"jpg")
    return root


def _record(source_file, log_datetime, **extra):
    record = {
        "id": 1,
        "machine_name": "M3",
        "part_code": "EBR30299370",
        "result": "OK",
        "log_datetime": log_datetime,
        "source_file": source_file,
        "qr_payload": QR,
        "serial_qr": "I20261012-016-00072",
        "barcode": "EBR30299370922610220516",
    }
    record.update(extra)
    return record


def _resolve(monkeypatch, root, record):
    monkeypatch.setattr(vision_helpers, "_vision_candidate_share_roots", lambda _r: [root])
    return vision_helpers._resolve_history_vision_image(record)


def test_record_source():
    assert vision_helpers._vision_record_source({"source_file": r"\\h\Result M3\x\a_20261022.txt"}) == "SHT"
    assert vision_helpers._vision_record_source({"source_file": r"\\h\Log\2026\10\20261022.shlog"}) == "shlog"
    assert vision_helpers._vision_record_source({}) == "shlog"


def test_sht_finds_exact_photo_with_code_in_name(tmp_path, monkeypatch):
    root = _photo_tree(tmp_path, [
        f"EBR30299370_상부_{QR}_20261022_154145137_OK.jpg",  # la pieza
        "EBR30299370_상부_I20261012-016-00073;MAIN;EBR30299370;1;_20261022_154159022_OK.jpg",
    ])
    result = _resolve(monkeypatch, root, _record(r"\\h\Result M3\EBR30299370\Data\f.txt", SHOT))

    assert result["fuente"] == "SHT"
    assert result["match_type"] == "exacta (hora y codigo)"
    assert result["delta_seconds"] == 0
    assert result["resolved_path"].endswith("_20261022_154145137_OK.jpg")


def test_sht_ignores_photo_of_another_piece_at_nearby_time(tmp_path, monkeypatch):
    # Hora parecida pero otro QR en el nombre: es otra pieza, no se muestra.
    root = _photo_tree(tmp_path, [
        "EBR30299370_상부_I20261012-016-00099;MAIN;EBR30299370;1;_20261022_154145400_OK.jpg",
    ])
    result = _resolve(monkeypatch, root, _record(r"\\h\Result M3\x.txt", SHOT))

    assert result["resolved_path"] == ""
    assert "error" in result


def test_shlog_uses_nearest_photo_before_end_of_inspection(tmp_path, monkeypatch):
    root = _photo_tree(tmp_path, [
        f"EBR30299370_상부_{QR}_20261022_154145137_OK.jpg",
        # la pieza siguiente, ~13 s despues
        "EBR30299370_상부_I20261012-016-00073;MAIN;EBR30299370;1;_20261022_154159022_OK.jpg",
    ])
    # El .shlog guarda el fin (csZone.Run), 0.35 s despues de la foto.
    end = datetime(2026, 10, 22, 15, 41, 45, 487000)
    result = _resolve(monkeypatch, root, _record(r"\\h\Log\2026\10\20261022.shlog", end))

    assert result["fuente"] == "shlog"
    assert result["match_type"] == "por hora mas cercana"
    assert result["resolved_path"].endswith("_20261022_154145137_OK.jpg")


def test_shlog_with_mispaired_code_still_finds_photo_by_time(tmp_path, monkeypatch):
    # Caso real M3 11:20:06: el .shlog le pego el QR -00474 (escaner de mano), la foto
    # trae -00467 (leido por la camara), 0.22 s antes del fin de la inspeccion.
    root = _photo_tree(
        tmp_path,
        ["EBR30299369-MAJESTY_상부_I20261021-018-00467;MAIN;EBR30299369;1;_20261022_154145137_OK.jpg"],
        part="EBR30299369-MAJESTY",
    )
    record = _record(
        r"\\h\Log\2026\10\20261022.shlog",
        datetime(2026, 10, 22, 15, 41, 45, 360000),
        part_code="EBR30299369",
        qr_payload="I20261021-018-00474;MAIN;EBR30299369;1;",
        serial_qr="I20261021-018-00474",
        barcode="",
    )
    result = _resolve(monkeypatch, root, record)

    assert result["match_type"] == "por hora mas cercana"
    assert "MAJESTY" in result["resolved_path"]


def test_photo_without_code_in_name_uses_nearest_time(tmp_path, monkeypatch):
    # Receta sin lectura de codigos (M1 EBR24212302): <modelo>_<zona>_<fecha>_<hora>_NG.jpg
    root = _photo_tree(
        tmp_path,
        ["EBR24212302_상부_20261022_154145137_NG.jpg", "EBR24212302_상부_20261022_154150000_NG.jpg"],
        part="EBR24212302",
        result="NG",
    )
    record = _record(
        r"\\h\Log\2026\10\20261022.shlog",
        datetime(2026, 10, 22, 15, 41, 45, 400000),
        part_code="EBR24212302",
        result="NG",
        qr_payload="",
        serial_qr="",
        barcode="",
    )
    result = _resolve(monkeypatch, root, record)

    assert result["match_type"] == "por hora mas cercana"
    assert result["resolved_path"].endswith("_20261022_154145137_NG.jpg")


def test_history_query_adds_failures_and_filters(app, monkeypatch):
    monkeypatch.setattr(vision_helpers, "_vision_defects_table_available", lambda: True)
    with app.test_request_context("/api/vision/data?cf_componente=Conector&cf_tipo_falla=INVERTIDO"):
        sql, params = vision_helpers._build_history_vision_query(100, 0)

    assert "AS fallas" in sql
    assert "AS fuente" not in sql  # la fuente solo se usa por dentro para la imagen
    assert "FROM history_vision_defects d WHERE d.source_uid = history_vision.source_uid" in sql
    assert sql.count("source_uid IN (SELECT d.source_uid FROM history_vision_defects d") == 2
    # Sin '%' literal: execute_query formatea los %s con params.
    assert "%" not in sql.replace("%s", "")
    assert params == ("%Conector%", "%INVERTIDO%", 100, 0)


def test_defect_columns_split_component_type_and_value():
    cols = vision_helpers._vision_defect_columns
    assert cols("Switch", "2", "Maker_Axis", "cantidad:1,coincidencia:75.4567% <- NG", 75.4567) == {
        "componente": "Switch 2", "tipo_falla": "Maker_Axis", "valor": 75.46, "unidad": "%",
    }
    # Un 0 medido es un valor, no "vacio".
    assert cols("FUSE", "D2", "Measurement-Count", "0", 0.0)["valor"] == 0.0
    # Color promedio: no hay un solo numero, queda el texto.
    assert cols("Condenser_Right", "CE34", "Measurement-Color", "26,27,25", None)["valor"] == "26,27,25"
    # Lectura de codigo NG: sin sub-prueba, el tipo es el motivo.
    assert cols("Barcode (ASSY)", "", "", "no leyo la etiqueta", None) == {
        "componente": "Barcode (ASSY)", "tipo_falla": "no leyo la etiqueta", "valor": "", "unidad": "",
    }
    # Etiqueta de otro modelo (M2 real): tipo corto para agrupar, el codigo leido en el valor.
    assert cols(
        "Barcode (ASSY)", "", "", "etiqueta no corresponde al modelo: EBR23966204922507070020", None
    ) == {
        "componente": "Barcode (ASSY)", "tipo_falla": "etiqueta no corresponde al modelo",
        "valor": "EBR23966204922507070020", "unidad": "",
    }


def test_parse_fallas_from_json_column():
    raw = (
        '[{"test_name": "Conector", "position": "CN20", "sub_test": "INVERTIDO", '
        '"value_text": "57.6213", "value_num": 57.6213}, '
        '{"test_name": "Conector", "position": "CN20", "sub_test": "Measurement-Color", '
        '"value_text": "1982,1434,824", "value_num": null}]'
    )
    fallas = vision_helpers._vision_parse_fallas(raw)
    assert [(f["componente"], f["tipo_falla"], f["valor"]) for f in fallas] == [
        ("Conector CN20", "INVERTIDO", 57.62),
        ("Conector CN20", "Measurement-Color", "1982,1434,824"),
    ]
    assert vision_helpers._vision_parse_fallas(None) == []
    assert vision_helpers._vision_parse_fallas("no es json") == []


def test_export_writes_one_row_per_failure(client, monkeypatch):
    rows = [
        {"linea": "M1", "fecha": "2026-10-22", "hora": "15:46:34", "numero_parte": "EBR24212304",
         "qr": "Q1", "barcode": "", "resultado": "NG",
         "fallas": '[{"test_name": "Conector", "position": "CN20", "sub_test": "INVERTIDO", '
                   '"value_text": "57.6", "value_num": 57.6}, {"test_name": "FUSE", "position": "D2", '
                   '"sub_test": "Measurement-Count", "value_text": "0", "value_num": 0}]'},
        {"linea": "M3", "fecha": "2026-10-22", "hora": "15:48:39", "numero_parte": "EBR30299370",
         "qr": "Q2", "barcode": "EBR1", "resultado": "OK", "fallas": None},
    ]
    monkeypatch.setattr(historial_vision, "_build_history_vision_query", lambda: ("sql", ()))
    monkeypatch.setattr(historial_vision, "execute_query", lambda sql, params, fetch: rows)
    captured = {}

    def fake_excel(items, headers, keys, **kwargs):
        captured.update(items=items, headers=headers, keys=keys)
        return historial_vision.jsonify({"ok": True})

    monkeypatch.setattr(historial_vision, "excel_response_ict", fake_excel)
    with client.session_transaction() as session:
        session["usuario"] = "test"
        session["_last_activity_touch_ts"] = int(time.time())

    assert client.get("/api/vision/export").status_code == 200
    assert captured["headers"][-4:] == ["Componente", "Tipo de falla", "Valor", "Unidad"]
    items = captured["items"]
    assert len(items) == 3  # 2 fallas de la pieza NG + 1 fila de la OK
    assert [(i["qr"], i["componente"], i["tipo_falla"], i["valor"]) for i in items] == [
        ("Q1", "Conector CN20", "INVERTIDO", 57.6),
        ("Q1", "FUSE D2", "Measurement-Count", 0.0),
        ("Q2", "", "", ""),
    ]


def test_date_filter_uses_indexed_datetime_range(app, monkeypatch):
    # log_date no tiene indice (recorria 1.8M filas); (result, log_datetime) si.
    monkeypatch.setattr(vision_helpers, "_vision_defects_table_available", lambda: False)
    with app.test_request_context("/api/vision/data?fecha_desde=2026-10-22&fecha_hasta=2026-10-22"):
        sql, params = vision_helpers._build_history_vision_query(1000, 0)
        count_sql, count_params = vision_helpers._build_history_vision_count_query()
        summary_sql, summary_params = vision_helpers._build_history_vision_pass_fail_summary_query()

    for query in (sql, count_sql, summary_sql):
        assert "result IN ('OK','NG') AND log_datetime >= %s AND log_datetime < %s" in query
        assert "log_date >=" not in query and "log_date <=" not in query
    assert params == ("2026-10-22", "2026-10-23", 1000, 0)  # hasta = dia siguiente, exclusivo
    assert count_params == summary_params == ("2026-10-22", "2026-10-23")

    with app.test_request_context("/api/vision/data"):
        sql, params = vision_helpers._build_history_vision_query(1000, 0)
    assert "result IN" not in sql and params == (1000, 0)  # sin fechas, sin filtro extra


def test_history_query_without_defects_table_keeps_working(app, monkeypatch):
    monkeypatch.setattr(vision_helpers, "_vision_defects_table_available", lambda: False)
    with app.test_request_context("/api/vision/data?cf_componente=Conector"):
        sql, params = vision_helpers._build_history_vision_query(100, 0)

    assert "NULL AS fallas" in sql
    assert "history_vision_defects" not in sql
    assert params == (100, 0)  # el filtro de componente se ignora sin la tabla


def test_image_info_lists_ng_failures(client, monkeypatch):
    monkeypatch.setattr(
        historial_vision,
        "_get_history_vision_record",
        lambda record_id: _record(r"\\h\Result M3\x.txt", SHOT, id=record_id, result="NG", source_uid="uid-1"),
    )
    monkeypatch.setattr(
        historial_vision,
        "_resolve_history_vision_image",
        lambda record: {"resolved_path": r"\\h\Result M3\foto.jpg", "fuente": "SHT",
                        "match_type": "exacta (hora y codigo)", "reference_datetime": "x"},
    )
    seen = {}

    def fake_defects(source_uid):
        seen["uid"] = source_uid
        return [
            {"test_name": "Conector", "position": "2", "sub_test": "Maker-Direction-Percent",
             "value_text": "84.2645", "value_num": 84.2645},
            {"test_name": "Barcode (ASSY)", "position": "", "sub_test": "",
             "value_text": "no leyo la etiqueta", "value_num": None},
        ]

    monkeypatch.setattr(historial_vision, "_get_history_vision_defects", fake_defects)
    with client.session_transaction() as session:
        session["usuario"] = "test"
        session["_last_activity_touch_ts"] = int(time.time())

    payload = client.get("/api/vision/image-info?id=5").get_json()

    assert seen["uid"] == "uid-1"
    assert "fuente" not in payload
    assert payload["match_type"] == "exacta (hora y codigo)"
    assert payload["defects"][0] == {
        "componente": "Conector 2", "tipo_falla": "Maker-Direction-Percent",
        "valor": 84.26, "unidad": "", "detalle": "84.2645",
    }
    assert payload["defects"][1]["tipo_falla"] == "no leyo la etiqueta"
