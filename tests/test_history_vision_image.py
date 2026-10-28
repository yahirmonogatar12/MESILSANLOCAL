"""Imagen y detalle de NG del historial Vision segun la fuente del registro.

SHT (.txt de resultados): log_datetime es el sello exacto de la foto (al milisegundo) y el
nombre de la foto trae el ultimo codigo leido. shlog: log_datetime es el fin de la
inspeccion, 0.2-0.4 s despues de la foto.
"""

import os
import time
from datetime import datetime
from pathlib import Path

import pytest

from app.api.control_resultados import historial_vision
from app.api.shared import vision_helpers

QR = "I20261012-016-00072;MAIN;EBR30299370;1;"
SHOT = datetime(2026, 10, 22, 15, 41, 45, 137000)
_REAL_DEVICEHUB_IP = vision_helpers._vision_devicehub_ip
_REAL_SHT_TWIN = vision_helpers._get_history_vision_sht_twin


@pytest.fixture(autouse=True)
def _sin_mysql(monkeypatch):
    """DeviceHub y el gemelo SHT consultan MySQL: los tests no tocan la BD del .env."""
    monkeypatch.setattr(vision_helpers, "_vision_devicehub_ip", lambda _name: None)
    monkeypatch.setattr(vision_helpers, "_get_history_vision_sht_twin", lambda _record: None)


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


# ── IP vigente (DeviceHub), acceso al share y gemelo SHT ───────────────────────────


def test_current_ip_from_devicehub_replaces_the_stored_one(monkeypatch):
    # Caso real: M2 paso de .156 a .110 y sus registros viejos buscaban en una PC que ya no esta.
    record = _record(
        r"\\192.168.2.156\Result M2\EBR37437070\Data\2026\10\상부\f_20261022.txt", SHOT,
        machine_name="M2", machine_ip="192.168.2.156",
    )
    monkeypatch.setattr(vision_helpers, "_vision_devicehub_ip", lambda name: "192.168.2.110" if name == "M2" else None)

    assert vision_helpers._vision_candidate_share_roots(record) == [
        Path(r"\\192.168.2.110\Result M2"), Path(r"\\192.168.2.110\Result"),
    ]
    assert vision_helpers._vision_current_source_file(record) == (
        r"\\192.168.2.110\Result M2\EBR37437070\Data\2026\10\상부\f_20261022.txt"
    )

    # Sin respuesta de DeviceHub: como antes, con la IP guardada en el registro.
    monkeypatch.setattr(vision_helpers, "_vision_devicehub_ip", lambda _name: None)
    assert vision_helpers._vision_candidate_share_roots(record)[0] == Path(r"\\192.168.2.156\Result M2")
    assert vision_helpers._vision_current_source_file(record) == record["source_file"]


def test_devicehub_lookup_is_cached_and_tolerates_errors(monkeypatch):
    calls = []

    def fake_query(sql, params, fetch):
        calls.append(params)
        return {"current_ip": "192.168.2.110"}

    monkeypatch.setattr(vision_helpers, "_vision_devicehub_ip", _REAL_DEVICEHUB_IP)
    monkeypatch.setattr(vision_helpers, "_vision_devicehub_cache", {})
    monkeypatch.setattr(vision_helpers, "execute_query", fake_query)
    assert vision_helpers._vision_devicehub_ip("M2") == "192.168.2.110"
    assert vision_helpers._vision_devicehub_ip("M2") == "192.168.2.110"
    assert calls == [("VISION-M2",)]  # la segunda vez sale del cache

    def broken(sql, params, fetch):
        raise RuntimeError("Conexion MySQL no disponible")

    monkeypatch.setattr(vision_helpers, "execute_query", broken)
    assert vision_helpers._vision_devicehub_ip("M4") is None


def test_unreachable_share_is_not_reported_as_missing_photo(tmp_path, monkeypatch):
    monkeypatch.delenv("VISION_SHARE_USER", raising=False)
    result = _resolve(monkeypatch, tmp_path / "Result M3", _record(r"\\h\Result M3\x.txt", SHOT))

    assert result["share_inaccessible"] is True
    assert result["error"].startswith("Sin acceso a la carpeta de la vision")


@pytest.mark.skipif(os.name != "nt", reason="net use solo existe en Windows")
def test_share_is_mounted_with_env_credentials(tmp_path, monkeypatch):
    root = tmp_path / "Result M2"
    runs = []

    def fake_run(command, **kwargs):
        runs.append(command)
        root.mkdir()  # net use exitoso: la carpeta ya responde
        return vision_helpers.subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setenv("VISION_SHARE_USER", "user")
    monkeypatch.setenv("VISION_SHARE_PASSWORD", "1111")
    monkeypatch.setattr(vision_helpers, "_vision_share_retry_at", {})
    monkeypatch.setattr(vision_helpers.subprocess, "run", fake_run)

    assert vision_helpers._vision_share_available(root) is True
    assert runs == [["net", "use", str(root), "1111", "/user:user", "/persistent:no"]]
    assert vision_helpers._vision_share_available(root) is True and len(runs) == 1  # ya responde

    # Share que sigue sin responder: no se repite net use en cada busqueda.
    other = tmp_path / "Result M9"
    monkeypatch.setattr(
        vision_helpers.subprocess, "run",
        lambda command, **kwargs: runs.append(command) or vision_helpers.subprocess.CompletedProcess(command, 2, "", "x"),
    )
    assert vision_helpers._vision_share_available(other) is False
    assert vision_helpers._vision_share_available(other) is False
    assert len(runs) == 2


def test_shlog_ng_photo_up_to_3_seconds_before_the_end(tmp_path, monkeypatch):
    # Caso real M2 13:22:09.213: NG sin lectura de codigo, foto 1.009 s antes del fin.
    root = _photo_tree(tmp_path, ["EBR30299370_상부_20261022_154145137_NG.jpg"], result="NG")
    end = datetime(2026, 10, 22, 15, 41, 46, 146000)
    result = _resolve(monkeypatch, root, _record(r"\\h\Log\x.shlog", end, result="NG"))
    assert result["resolved_path"].endswith("_20261022_154145137_NG.jpg")

    # La foto nunca es posterior al fin de la inspeccion: 2 s despues es otra pieza.
    before = datetime(2026, 10, 22, 15, 41, 43, 137000)
    result = _resolve(monkeypatch, root, _record(r"\\h\Log\x.shlog", before, result="NG"))
    assert result["resolved_path"] == ""


def test_share_not_mounted_when_another_candidate_responds(tmp_path, monkeypatch):
    root = _photo_tree(tmp_path, [f"EBR30299370_상부_{QR}_20261022_154145137_OK.jpg"])
    mounted = []
    monkeypatch.setattr(vision_helpers, "_vision_mount_share", lambda r: mounted.append(r) or False)
    monkeypatch.setattr(vision_helpers, "_vision_candidate_share_roots", lambda _r: [root, tmp_path / "Result"])

    result = vision_helpers._resolve_history_vision_image(_record(r"\\h\Result M3\x.txt", SHOT))

    assert result["resolved_path"] and mounted == []  # \\IP\Result no existe: no se intenta net use


def test_shlog_duplicate_takes_the_photo_of_its_sht_twin(tmp_path, monkeypatch):
    # Caso real M4: el .shlog escribio la pieza -00458 a las 08:17:08.752; el SHT la misma
    # pieza a las 08:17:31.228, que es el sello de su foto (22 s despues).
    root = _photo_tree(tmp_path, [f"EBR30299370_상부_{QR}_20261022_154145137_OK.jpg"])
    shlog = _record(r"\\h\Log\2026\10\20261022.shlog", datetime(2026, 10, 22, 15, 41, 22, 661000), id=7)
    twin = _record(r"\\h\Result M3\EBR30299370\Data\f.txt", SHOT, id=8)
    monkeypatch.setattr(vision_helpers, "_get_history_vision_sht_twin", lambda record: twin if record["id"] == 7 else None)

    result = _resolve(monkeypatch, root, shlog)

    assert result["resolved_path"].endswith("_20261022_154145137_OK.jpg")
    assert result["twin_record_id"] == 8 and "registro SHT 8" in result["match_type"]
    assert result["record_id"] == 7 and result["fuente"] == "shlog"
    assert result["reference_datetime"] == "2026-10-22 15:41:22.661000"  # la hora del registro mostrado


def test_shlog_without_photo_nor_twin_explains_it(tmp_path, monkeypatch):
    root = _photo_tree(tmp_path, [f"EBR30299370_상부_{QR}_20261022_154145137_OK.jpg"])
    result = _resolve(monkeypatch, root, _record(r"\\h\Log\x.shlog", datetime(2026, 10, 22, 15, 41, 22)))

    assert result["resolved_path"] == ""
    assert "ni un registro SHT de la misma pieza" in result["error"]


def test_sht_twin_query_matches_by_code_and_never_by_empty_code(monkeypatch):
    seen = {}

    def fake_query(sql, params, fetch):
        seen.update(sql=sql, params=params)
        return None

    monkeypatch.setattr(vision_helpers, "execute_query", fake_query)
    twin_lookup = _REAL_SHT_TWIN

    assert twin_lookup(_record(r"\\h\Log\x.shlog", SHOT, serial_qr="", barcode="")) is None
    assert not seen  # sin QR ni barcode no se consulta

    twin_lookup(_record(r"\\h\Log\x.shlog", SHOT, serial_qr="", barcode="EBR1"))
    params = seen["params"]
    assert params[0] == "OK" and params[3] == "M3" and params[4] == "%.txt"
    assert params[5] is None and params[6] == "EBR1"  # QR vacio: NULL, no empata filas sin codigo
    assert "%" not in seen["sql"].replace("%s", "")


def test_history_query_adds_failures_and_filters(app, monkeypatch):
    monkeypatch.setattr(vision_helpers, "_vision_defects_table_available", lambda: True)
    with app.test_request_context("/api/vision/data?cf_tipo=Conector&cf_componente=CN20&cf_tipo_falla=INVERTIDO"):
        sql, params = vision_helpers._build_history_vision_query(100, 0)

    assert "AS fallas" in sql
    assert "AS fuente" not in sql  # la fuente solo se usa por dentro para la imagen
    assert "FROM history_vision_defects d WHERE d.source_uid = history_vision.source_uid" in sql
    assert sql.count("source_uid IN (SELECT d.source_uid FROM history_vision_defects d") == 3
    # Sin '%' literal: execute_query formatea los %s con params.
    assert "%" not in sql.replace("%s", "")
    assert params == ("%Conector%", "%CN20%", "%INVERTIDO%", 100, 0)


def test_defect_columns_split_component_type_and_value():
    cols = vision_helpers._vision_defect_columns
    assert cols("Switch", "2", "Maker_Axis", "cantidad:1,coincidencia:75.4567% <- NG", 75.4567) == {
        "tipo": "Switch", "componente": "2", "tipo_falla": "Maker_Axis", "valor": 75.46, "unidad": "%",
    }
    # Un 0 medido es un valor, no "vacio".
    assert cols("FUSE", "D2", "Measurement-Count", "0", 0.0)["valor"] == 0.0
    # Color promedio: no hay un solo numero, queda el texto.
    assert cols("Condenser_Right", "CE34", "Measurement-Color", "26,27,25", None)["valor"] == "26,27,25"
    # Lectura de codigo NG: sin sub-prueba, el tipo es el motivo.
    assert cols("Barcode (ASSY)", "", "", "no leyo la etiqueta", None) == {
        "tipo": "Barcode (ASSY)", "componente": "", "tipo_falla": "no leyo la etiqueta", "valor": "", "unidad": "",
    }
    # Etiqueta de otro modelo (M2 real): tipo corto para agrupar, el codigo leido en el valor.
    assert cols(
        "Barcode (ASSY)", "", "", "etiqueta no corresponde al modelo: EBR23966204922507070020", None
    ) == {
        "tipo": "Barcode (ASSY)", "componente": "", "tipo_falla": "etiqueta no corresponde al modelo",
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
    assert [(f["tipo"], f["componente"], f["tipo_falla"], f["valor"]) for f in fallas] == [
        ("Conector", "CN20", "INVERTIDO", 57.62),
        ("Conector", "CN20", "Measurement-Color", "1982,1434,824"),
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
    assert captured["headers"][-5:] == ["Tipo", "Componente", "Tipo de falla", "Valor", "Unidad"]
    items = captured["items"]
    assert len(items) == 3  # 2 fallas de la pieza NG + 1 fila de la OK
    assert [(i["qr"], i["tipo"], i["componente"], i["tipo_falla"], i["valor"]) for i in items] == [
        ("Q1", "Conector", "CN20", "INVERTIDO", 57.6),
        ("Q1", "FUSE", "D2", "Measurement-Count", 0.0),
        ("Q2", "", "", "", ""),
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
        "tipo": "Conector", "componente": "2", "tipo_falla": "Maker-Direction-Percent",
        "valor": 84.26, "unidad": "", "detalle": "84.2645",
    }
    assert payload["defects"][1]["tipo_falla"] == "no leyo la etiqueta"
    assert payload["parametros_disponibles"] is True  # registro SHT: boton "Ver parametros"


# ── Parametros de la pieza (solo SHT), leidos del .txt ─────────────────────────────

STAMP = "2026-10-22 16:03:13.412"
SHT_ROW = "\t".join([
    "CAM1", STAMP, "NG", "I20261021-019-00260;MAIN;EBR30299370;1;",
    "Conector", "OK", "0", "0", "1:OK,2:OK,3:OK", "TESTED",
    "Switch", "NG", "0", "0",
    "1:OK,2:NG>Maker_Axis:NG>갯수:1,일치율:75.46468% ← NG,위치:1909.995,-614.8686,각도:0˚,크기:100,100%",
    "TESTED",
    "Condenser_Left", "OK", "0", "0", "OK", "TESTED",
    "Conector J", "NG", "0", "0", "CON1:OK,CON202:NG>FALTANTE:NG>43.52654, INVERTIDO:NG>48.89709", "TESTED",
    "DC Relay", "NG", "0", "0", "", "UNTESTED",
    "Barcode (ASSY)", "NG", "0", "0", "", "TESTED",
    "Barcode (SMD)", "OK", "0", "0", "I20261021-019-00260;MAIN;EBR30299370;1;", "TESTED",
])


def test_parse_sht_parameters_lists_every_test_and_position():
    params = vision_helpers._parse_sht_parameters(SHT_ROW.split("\t"))
    by_name = {t["prueba"]: t for t in params["pruebas"]}

    assert params["fecha"] == STAMP and params["resultado"] == "NG"
    assert [p["posicion"] for p in by_name["Conector"]["posiciones"]] == ["1", "2", "3"]
    switch = by_name["Switch"]["posiciones"]
    assert [(p["posicion"], p["resultado"]) for p in switch] == [("1", "OK"), ("2", "NG")]
    assert switch[1]["detalle"].startswith("Maker_Axis > cantidad:1,coincidencia:75.46468% <- NG,posicion:1909.995")
    # Grupo de una sola posicion.
    assert by_name["Condenser_Left"]["posiciones"] == [{"posicion": "", "resultado": "OK", "detalle": ""}]
    # Dos sub-pruebas de la misma posicion quedan en una sola fila.
    assert by_name["Conector J"]["posiciones"][1] == {
        "posicion": "CON202", "resultado": "NG", "detalle": "FALTANTE > 43.52654; INVERTIDO > 48.89709",
    }
    # Grupo que nunca corre.
    assert by_name["DC Relay"]["ejecutada"] is False and by_name["DC Relay"]["posiciones"] == []
    # Lecturas de codigo: el codigo leido; vacio = no leyo la etiqueta.
    assert by_name["Barcode (SMD)"]["es_lectura"] and by_name["Barcode (SMD)"]["lectura"].startswith("I2026")
    assert by_name["Barcode (ASSY)"]["es_lectura"] and by_name["Barcode (ASSY)"]["lectura"] == ""
    # 1+3 +2 +1 +2 posiciones; NG: Switch 2, CON202 y la lectura ASSY (DC Relay no cuenta).
    assert params["resumen"] == {"pruebas": 7, "posiciones": 8, "ng": 3}


def test_read_sht_row_by_exact_stamp_utf8_and_cp949(tmp_path):
    path = tmp_path / "EBR30299370_상부_20261022.txt"
    other = SHT_ROW.replace(STAMP, "2026-10-22 16:03:00.100")
    cp949_line = "CAM1\t2026-10-22 16:04:00.000\tNG\tx\tSwitch\tNG\t0\t0\t2:NG>Maker_Axis:NG>일치율:70%\tTESTED"
    path.write_bytes(
        b"[NAME-ZONE]\t[DATE]\t[JUDGE]\t[ID]\n"
        + other.encode("utf-8") + b"\r\n"
        + SHT_ROW.encode("utf-8") + b"\r\n"
        + cp949_line.encode("cp949") + b"\n"
    )

    assert vision_helpers._read_sht_row(str(path), STAMP)[2] == "NG"
    assert vision_helpers._read_sht_row(str(path), STAMP)[3].startswith("I20261021-019-00260")
    cp949 = vision_helpers._read_sht_row(str(path), "2026-10-22 16:04:00.000")
    assert "일치율:70%" in cp949[8]
    assert vision_helpers._read_sht_row(str(path), "2026-10-22 23:59:59.999") is None


def _params_client(client, monkeypatch, tmp_path, source_file, roots):
    record = _record(source_file, datetime(2026, 10, 22, 16, 3, 13, 412000), id=9, result="NG")
    monkeypatch.setattr(historial_vision, "_get_history_vision_record", lambda _id: record)
    monkeypatch.setattr(historial_vision, "_vision_candidate_share_roots", lambda _r: roots)
    with client.session_transaction() as session:
        session["usuario"] = "test"
        session["_last_activity_touch_ts"] = int(time.time())
    return client.get("/api/vision/parameters?id=9")


def test_parameters_api_reads_the_piece_row(client, monkeypatch, tmp_path):
    root = tmp_path / "Result M3"
    folder = root / "EBR30299370" / "Data" / "2026" / "10" / "상부"
    folder.mkdir(parents=True)
    txt = folder / "EBR30299370_상부_20261022.txt"
    txt.write_bytes(SHT_ROW.encode("utf-8") + b"\r\n")

    response = _params_client(client, monkeypatch, tmp_path, str(txt), [root])

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["resumen"]["ng"] == 3
    assert payload["archivo"] == txt.name
    assert [t["prueba"] for t in payload["pruebas"]][:2] == ["Conector", "Switch"]


def test_parameters_api_only_for_sht_and_inside_share(client, monkeypatch, tmp_path):
    root = tmp_path / "Result M3"
    root.mkdir()
    # Registro del .shlog: no tiene fila de pruebas.
    shlog = _params_client(client, monkeypatch, tmp_path, r"\\h\Log\2026\10\20261022.shlog", [root])
    assert shlog.status_code == 400
    # .txt fuera del share de resultados de la maquina: no se lee.
    outside = tmp_path / "otro" / "x.txt"
    outside.parent.mkdir()
    outside.write_text("x")
    assert _params_client(client, monkeypatch, tmp_path, str(outside), [root]).status_code == 403
    # Dentro del share pero sin la fila de esa pieza.
    txt = root / "f.txt"
    txt.write_text("[NAME-ZONE]\t[DATE]\n")
    assert _params_client(client, monkeypatch, tmp_path, str(txt), [root]).status_code == 404
