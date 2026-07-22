import hashlib
from datetime import date

import pytest

from app.api.portal import ai_plan_tools


def _proposal_result():
    return {
        "proposal_id": "11111111-1111-4111-8111-111111111111",
        "version": 1,
        "engine_version": "mrp-capacity-v2",
        "date_from": "2099-07-20",
        "date_to": "2099-07-25",
        "proposals": [
            {
                "fecha": "2099-07-20",
                "linea": "M1",
                "turno": "DIA",
                "numero_parte": "EBR80757421",
                "cantidad": 200,
                "ct": 36.0,
                "uph": 100,
                "horas_requeridas": 2.0,
                "inventario_antes": -150,
                "inventario_despues": 50,
                "fecha_shortage": "2099-07-20",
                "excepciones": [],
                "part_no": "EBR80757421",
                "sched_date": "2099-07-20",
                "qty": 200,
            }
        ],
        "partes": 1,
        "total_qty": 200,
        "line_summary": [
            {
                "fecha": "2099-07-20",
                "linea": "M1",
                "turno": "DIA",
                "horas": 2.0,
                "horas_max": 9.0,
                "lotes": 1,
                "cantidad": 200,
                "excede": False,
            }
        ],
        "omitidas_count": 0,
        "excluded_parts": ["EBR30299365", "EBR30299369"],
        "exceptions": [],
        "schedule_changes": [
            {
                "accion": "AGREGAR",
                "part_no": "EBR80757421",
                "sched_date": "2099-07-20",
                "antes_qty": 0,
                "despues_qty": 200,
                "antes_linea": None,
                "despues_linea": "M1",
                "turno": "DIA",
            }
        ],
        "schedule_change_summary": {
            "CONSERVAR": 0, "MODIFICAR": 0, "AGREGAR": 1, "ELIMINAR": 0,
        },
        "capacidad_libre": {"por_linea": {"M1": 7.0}, "total": 7.0,
                            "lineas_con_espacio": ["M1"]},
        "expandido_dias": 0,
    }


def _tool_names(username="ana"):
    return {tool["name"] for tool in ai_plan_tools.tool_schemas(username)}


def test_tool_schemas_son_estrictos_y_separan_permisos(monkeypatch):
    monkeypatch.setattr(ai_plan_tools, "_has_plan", lambda _username: True)
    monkeypatch.setattr(ai_plan_tools, "_has_projection", lambda _username: False)

    plan_tools = ai_plan_tools.tool_schemas("ana")
    assert {tool["name"] for tool in plan_tools} == {
        "plan_estado_faltantes",
        "plan_importar_preparar",
        "plan_generar_preparar",
    }

    monkeypatch.setattr(ai_plan_tools, "_has_plan", lambda _username: False)
    monkeypatch.setattr(ai_plan_tools, "_has_projection", lambda _username: True)

    projection_tools = ai_plan_tools.tool_schemas("ana")
    assert {tool["name"] for tool in projection_tools} == {
        "plan_part_sincronizar_preparar",
        "plan_propuesta_preparar",
    }

    for tool in plan_tools + projection_tools:
        parameters = tool["parameters"]
        assert tool["type"] == "function"
        assert tool["strict"] is True
        assert parameters["type"] == "object"
        assert parameters["additionalProperties"] is False
        # En schemas estrictos de OpenAI, incluso los campos anulables deben
        # aparecer en required; la nulabilidad expresa que son opcionales.
        assert set(parameters["required"]) == set(parameters["properties"])

    monkeypatch.setattr(ai_plan_tools, "_has_projection", lambda _username: False)
    assert ai_plan_tools.tool_schemas("ana") == []


def test_sincronizar_part_prepara_y_ejecuta_el_mismo_archivo(monkeypatch):
    file_bytes = b"part-n-test"
    calls = []
    monkeypatch.setattr(ai_plan_tools, "_has_plan", lambda _username: False)
    monkeypatch.setattr(ai_plan_tools, "_has_projection", lambda _username: True)

    def fake_sync(data, filename, username, *, aplicar=False, alcance="todos"):
        calls.append((data, filename, username, aplicar, alcance))
        return {
            "success": True,
            "sheet_name": "Part 16",
            "parts": 31,
            "schedules": 353,
            "date_from": "2026-07-13",
            "date_to": "2026-09-16",
            "applied": aplicar,
            **({"replaced": 120} if aplicar else {}),
        }

    monkeypatch.setattr(
        ai_plan_tools.pp, "_pp_sincronizar_schedule_excel", fake_sync
    )
    lookup = lambda _ref: (file_bytes, "plan.xlsm")

    prepared = ai_plan_tools.execute(
        "plan_part_sincronizar_preparar",
        {"alcance": "main"},
        username="ana",
        file_lookup=lookup,
    )

    assert prepared["resumen"]["sheet_name"] == "Part 16"
    assert prepared["resumen"]["schedules"] == 353
    token_payload = ai_plan_tools._read_token(
        prepared["confirm_token"], "sincronizar_part_schedule"
    )
    assert token_payload["sha"]

    applied = ai_plan_tools.execute(
        "plan_part_sincronizar_ejecutar",
        {"confirm_token": prepared["confirm_token"]},
        username="ana",
        file_lookup=lookup,
    )

    assert applied["applied"] is True
    assert applied["replaced"] == 120
    assert calls == [
        (file_bytes, "plan.xlsm", "ana", False, "main"),
        (file_bytes, "plan.xlsm", "ana", True, "main"),
    ]


def test_sincronizar_part_rechaza_archivo_distinto_al_confirmar(monkeypatch):
    monkeypatch.setattr(ai_plan_tools, "_has_plan", lambda _username: False)
    monkeypatch.setattr(ai_plan_tools, "_has_projection", lambda _username: True)
    monkeypatch.setattr(
        ai_plan_tools.pp,
        "_pp_sincronizar_schedule_excel",
        lambda *_args, **_kwargs: {
            "sheet_name": "Part 16", "parts": 1, "schedules": 1,
            "date_from": "2026-07-13", "date_to": "2026-07-20",
        },
    )
    prepared = ai_plan_tools.execute(
        "plan_part_sincronizar_preparar",
        {"alcance": "main"},
        username="ana",
        file_lookup=lambda _ref: (b"original", "plan.xlsm"),
    )

    with pytest.raises(ValueError, match="archivo cambio"):
        ai_plan_tools.execute(
            "plan_part_sincronizar_ejecutar",
            {"confirm_token": prepared["confirm_token"]},
            username="ana",
            file_lookup=lambda _ref: (b"modificado", "plan.xlsm"),
        )


def test_execute_rechaza_herramientas_del_permiso_equivocado(monkeypatch):
    monkeypatch.setattr(ai_plan_tools, "_has_plan", lambda _username: True)
    monkeypatch.setattr(ai_plan_tools, "_has_projection", lambda _username: False)
    with pytest.raises(PermissionError, match="Proyeccion"):
        ai_plan_tools.execute(
            "plan_propuesta_preparar",
            {"fecha_inicio": None, "fecha_fin": None, "objetivo": None},
            username="ana",
            file_lookup=lambda _ref: (None, None),
        )

    monkeypatch.setattr(ai_plan_tools, "_has_plan", lambda _username: False)
    monkeypatch.setattr(ai_plan_tools, "_has_projection", lambda _username: True)
    with pytest.raises(PermissionError, match="Plan de produccion"):
        ai_plan_tools.execute(
            "plan_estado_faltantes",
            {"fecha": None},
            username="ana",
            file_lookup=lambda _ref: (None, None),
        )


def test_plan_propuesta_preparar_persiste_borrador_y_emite_token(monkeypatch):
    created = []
    pending = []
    file_lookups = []

    monkeypatch.setattr(ai_plan_tools, "_has_plan", lambda _username: False)
    monkeypatch.setattr(ai_plan_tools, "_has_projection", lambda _username: True)

    def fake_crear(
        fecha_inicio, fecha_fin, username, *, source, objective, excluded_parts,
        lotes_corriendo=None, agregados=None, expandir_dias=0
    ):
        created.append(
            (fecha_inicio, fecha_fin, username, source, objective, excluded_parts)
        )
        assert lotes_corriendo == {}  # rango futuro: nada corriendo
        assert agregados == [] and expandir_dias == 0
        return _proposal_result()

    monkeypatch.setattr(ai_plan_tools.pp, "_ppy_crear_propuesta", fake_crear)
    monkeypatch.setattr(
        ai_plan_tools.pp,
        "_ppy_mark_proposal_pending",
        lambda proposal_id, username: pending.append((proposal_id, username)),
    )

    result = ai_plan_tools.execute(
        "plan_propuesta_preparar",
        {
            "fecha_inicio": "2099-07-20",
            "fecha_fin": "2099-07-25",
            "objetivo": "Priorizar faltantes críticos",
            "proceso_actual": None,
            "partes_excluidas": ["EBR30299365", "EBR30299369"],
        },
        username="ana",
        file_lookup=lambda ref: file_lookups.append(ref),
    )

    assert created == [
        (
            date(2099, 7, 20),
            date(2099, 7, 25),
            "ana",
            "AI",
            "Priorizar faltantes críticos",
            ["EBR30299365", "EBR30299369"],
        )
    ]
    assert pending == [(result["proposal_id"], "ana")]
    assert file_lookups == []
    assert result["items"] == 1
    assert result["partes"] == 1
    assert result["total_qty"] == 200
    assert result["excluded_parts"] == ["EBR30299365", "EBR30299369"]
    assert result["sample"][0] == {
        "fecha": "2099-07-20",
        "linea": "M1",
        "turno": "DIA",
        "numero_parte": "EBR80757421",
        "cantidad": 200,
        "ct": 36.0,
        "uph": 100,
        "horas_requeridas": 2.0,
        "inventario_antes": -150,
        "inventario_despues": 50,
        "fecha_shortage": "2099-07-20",
        "excepciones": [],
    }
    token_payload = ai_plan_tools._read_token(
        result["confirm_token"], "aplicar_propuesta"
    )
    assert token_payload == {
        "proposal_id": result["proposal_id"],
        "version": 1,
        "username": "ana",
        "items": [],  # sin ajustes manuales
    }
    assert result["ajustes_manuales"] == []


def _mock_preparar_con_item(monkeypatch, pack_size=20):
    """preparar mockeado + el item del borrador para resolver ajustes por parte."""
    monkeypatch.setattr(ai_plan_tools, "_has_plan", lambda _username: False)
    monkeypatch.setattr(ai_plan_tools, "_has_projection", lambda _username: True)
    monkeypatch.setattr(
        ai_plan_tools.pp, "_ppy_crear_propuesta",
        lambda *a, **k: _proposal_result())
    monkeypatch.setattr(
        ai_plan_tools.pp, "_ppy_mark_proposal_pending", lambda *a, **k: None)
    # _ajustes_a_items consulta los items del borrador (parte -> item_id/pack)
    monkeypatch.setattr(
        ai_plan_tools, "execute_query",
        lambda *a, **k: [{"public_id": "item-abc", "part_no": "EBR80757421",
                          "pack_size": pack_size}])


def _preparar(monkeypatch, ajustes):
    return ai_plan_tools.execute(
        "plan_propuesta_preparar",
        {"fecha_inicio": "2099-07-20", "fecha_fin": "2099-07-20",
         "objetivo": None, "proceso_actual": None, "partes_excluidas": [],
         "ajustes": ajustes},
        username="ana", file_lookup=lambda _ref=None: (None, None),
    )


def test_plan_propuesta_ajuste_capa_cantidad_y_turno(monkeypatch):
    """'solo produce 160 de X' + 'X llega de noche' -> item con qty y turno."""
    _mock_preparar_con_item(monkeypatch, pack_size=20)
    result = _preparar(monkeypatch, [{
        "numero_parte": "EBR80757421", "cantidad": 160,
        "turno": "NOCHE", "linea": None, "excluir": False,
    }])
    items = ai_plan_tools._read_token(
        result["confirm_token"], "aplicar_propuesta")["items"]
    assert items == [{"item_id": "item-abc", "included": True,
                      "qty": 160, "turno": "NOCHE"}]
    assert result["ajustes_manuales"] == items  # el LLM lo muestra antes de confirmar


def test_plan_propuesta_ajuste_excluir_una_parte(monkeypatch):
    _mock_preparar_con_item(monkeypatch)
    result = _preparar(monkeypatch, [{
        "numero_parte": "EBR80757421", "cantidad": None,
        "turno": None, "linea": None, "excluir": True,
    }])
    items = ai_plan_tools._read_token(
        result["confirm_token"], "aplicar_propuesta")["items"]
    assert items == [{"item_id": "item-abc", "included": False}]


def test_plan_propuesta_ajuste_valida_caja_cerrada_y_parte_inexistente(monkeypatch):
    _mock_preparar_con_item(monkeypatch, pack_size=80)
    # 200 no es multiplo de 80 -> se rechaza ANTES de confirmar
    with pytest.raises(ValueError, match="multiplo del empaque 80"):
        _preparar(monkeypatch, [{
            "numero_parte": "EBR80757421", "cantidad": 200,
            "turno": None, "linea": None, "excluir": False,
        }])
    # una parte que no esta en el plan -> error claro
    with pytest.raises(ValueError, match="no esta en la propuesta"):
        _preparar(monkeypatch, [{
            "numero_parte": "NOEXISTE001", "cantidad": None,
            "turno": None, "linea": None, "excluir": True,
        }])


def test_plan_propuesta_de_hoy_exige_proceso_actual(monkeypatch):
    monkeypatch.setattr(ai_plan_tools, "_has_plan", lambda _username: False)
    monkeypatch.setattr(ai_plan_tools, "_has_projection", lambda _username: True)
    hoy = date.today().isoformat()

    with pytest.raises(ValueError, match="en que lote va cada linea"):
        ai_plan_tools.execute(
            "plan_propuesta_preparar",
            {
                "fecha_inicio": hoy,
                "fecha_fin": hoy,
                "objetivo": None,
                "proceso_actual": None,
            },
            username="ana",
            file_lookup=lambda _ref: (None, None),
        )


def test_plan_propuesta_de_hoy_acepta_lotes_corriendo_como_avance(monkeypatch):
    # Reportar los lotes corriendo satisface el requisito de "hoy" y se fijan.
    monkeypatch.setattr(ai_plan_tools, "_has_plan", lambda _username: False)
    monkeypatch.setattr(ai_plan_tools, "_has_projection", lambda _username: True)
    recibido = {}

    def fake_crear(fecha_inicio, fecha_fin, username, *, source, objective,
                   excluded_parts, lotes_corriendo=None, agregados=None,
                   expandir_dias=0):
        recibido["corriendo"] = lotes_corriendo
        recibido["objective"] = objective
        return _proposal_result()

    monkeypatch.setattr(ai_plan_tools.pp, "_ppy_crear_propuesta", fake_crear)
    monkeypatch.setattr(ai_plan_tools.pp, "_ppy_mark_proposal_pending",
                        lambda *_a: None)
    hoy = date.today().isoformat()
    result = ai_plan_tools.execute(
        "plan_propuesta_preparar",
        {
            "fecha_inicio": hoy, "fecha_fin": hoy, "objetivo": None,
            "proceso_actual": None, "partes_excluidas": [], "ajustes": [],
            "lotes_corriendo": [
                {"linea": "M1", "numero_parte": "EBR42005101"},
                {"linea": "D2", "numero_parte": "ajj30036901"},
            ],
        },
        username="ana",
        file_lookup=lambda _ref: (None, None),
    )
    assert recibido["corriendo"] == {"EBR42005101": "M1", "AJJ30036901": "D2"}
    assert "M1 en EBR42005101" in recibido["objective"]
    assert result["lotes_corriendo_fijados"] == [
        {"linea": "M1", "numero_parte": "EBR42005101"},
        {"linea": "D2", "numero_parte": "AJJ30036901"},
    ]


def test_plan_propuesta_rechaza_excluir_un_lote_corriendo_o_terminado(monkeypatch):
    # Excluir un lote corriendo/terminado borraria produccion real del schedule.
    monkeypatch.setattr(ai_plan_tools, "_has_plan", lambda _username: False)
    monkeypatch.setattr(ai_plan_tools, "_has_projection", lambda _username: True)
    hoy = date.today().isoformat()
    with pytest.raises(ValueError, match="no se pueden excluir"):
        ai_plan_tools.execute(
            "plan_propuesta_preparar",
            {
                "fecha_inicio": hoy, "fecha_fin": hoy, "objetivo": None,
                "proceso_actual": None,
                "partes_excluidas": ["EBR43713702"],
                "ajustes": [],
                "lotes_corriendo": [
                    {"linea": "M1", "numero_parte": "EBR43713702"},
                ],
            },
            username="ana",
            file_lookup=lambda _ref: (None, None),
        )


def test_plan_propuesta_aplicar_usa_solo_el_borrador_firmado(monkeypatch):
    applied = []
    monkeypatch.setattr(ai_plan_tools, "_has_plan", lambda _username: False)
    monkeypatch.setattr(ai_plan_tools, "_has_projection", lambda _username: True)

    token = ai_plan_tools._make_token(
        "aplicar_propuesta",
        {
            "proposal_id": "11111111-1111-4111-8111-111111111111",
            "version": 3,
            "username": "ana",
        },
    )

    def fake_aplicar(proposal_id, username, *, version, items):
        applied.append((proposal_id, username, version, items))
        return {
            "proposal_id": proposal_id,
            "status": "APPLIED",
            "aplicadas": 4,
            "modificadas": 0,
        }

    monkeypatch.setattr(ai_plan_tools.pp, "_ppy_aplicar_propuesta", fake_aplicar)

    result = ai_plan_tools.execute(
        "plan_propuesta_aplicar",
        {"confirm_token": token},
        username="ana",
        file_lookup=lambda _ref: (None, None),
    )

    assert result["status"] == "APPLIED"
    assert applied == [
        ("11111111-1111-4111-8111-111111111111", "ana", 3, None)
    ]

    with pytest.raises(PermissionError, match="otro usuario"):
        ai_plan_tools.execute(
            "plan_propuesta_aplicar",
            {"confirm_token": token},
            username="beatriz",
            file_lookup=lambda _ref: (None, None),
        )
    assert len(applied) == 1


def _fake_import_parsers(monkeypatch, *, ref_nuevo, stored_max):
    """Prepara plan_importar_preparar con hoja Part N presente y controla la
    ref_date del archivo (ref_nuevo) y la mas nueva ya cargada (stored_max)."""
    monkeypatch.setattr(ai_plan_tools, "_has_plan", lambda _u: True)
    monkeypatch.setattr(ai_plan_tools, "_has_projection", lambda _u: True)
    plan = {"parts_count": 5, "dates_count": 3,
            "date_from": date(2026, 7, 20), "date_to": date(2026, 7, 25)}
    monkeypatch.setattr(ai_plan_tools.pp, "_parse_lg_workbook",
                        lambda *_a, **_k: (plan, None))
    monkeypatch.setattr(ai_plan_tools.pp, "_parse_part10_workbook",
                        lambda *_a, **_k: ({"sheet_name": "Part 20",
                                            "inventory": {"EBR1": {}},
                                            "schedules": {("EBR1", date(2026, 7, 21)): 40}},
                                           None))
    monkeypatch.setattr(ai_plan_tools.pp, "_pp_import_mas_reciente",
                        lambda *_a, **_k: None)
    monkeypatch.setattr(ai_plan_tools.pp, "_pp_fecha_archivo",
                        lambda *_a, **_k: date(2026, 7, 20))
    monkeypatch.setattr(ai_plan_tools.pp, "_pp_ref_lunes",
                        lambda *_a, **_k: ref_nuevo)
    monkeypatch.setattr(ai_plan_tools, "execute_query",
                        lambda *_a, **_k: {"m": stored_max})


def test_importar_avisa_si_el_inventario_es_mas_viejo_que_el_cargado(monkeypatch):
    _fake_import_parsers(monkeypatch, ref_nuevo=date(2026, 7, 13),
                         stored_max=date(2026, 7, 20))
    res = ai_plan_tools.execute(
        "plan_importar_preparar", {"file_ref": None}, username="ana",
        file_lookup=lambda _ref: (b"xlsm", "plan.xlsm"))
    aviso = res["resumen"].get("aviso_retroceso_inventario")
    assert aviso and "2026-07-13" in aviso and "REVIERTE" in aviso


def test_importar_no_avisa_si_el_inventario_es_igual_o_mas_nuevo(monkeypatch):
    # igual (=), archivo mas nuevo (>), y tabla vacia: nunca avisa retroceso
    for stored in (date(2026, 7, 13), date(2026, 7, 6), None):
        _fake_import_parsers(monkeypatch, ref_nuevo=date(2026, 7, 13),
                             stored_max=stored)
        res = ai_plan_tools.execute(
            "plan_importar_preparar", {"file_ref": None}, username="ana",
            file_lookup=lambda _ref: (b"xlsm", "plan.xlsm"))
        assert "aviso_retroceso_inventario" not in res["resumen"]
        # tiene Part N: tampoco debe decir que no trae inventario
        assert "nota_inventario" not in res["resumen"]


def _import_token(file_bytes):
    return ai_plan_tools._make_token(
        "importar", {"sha": hashlib.sha256(file_bytes).hexdigest()})


def test_importar_ejecutar_no_sincroniza_schedule_y_lo_reporta(monkeypatch):
    # El import trae hoja Part N: sincroniza inventario+demanda, cuenta el
    # Schedule disponible pero NO lo escribe (lo deja para preguntar).
    monkeypatch.setattr(ai_plan_tools, "_has_plan", lambda _u: True)
    file_bytes = b"weekly-xlsm"
    captured = {}

    def fake_import(data, filename, usuario):
        captured["called"] = (filename, usuario)
        return {"import_id": 42, "plan_partes": 487, "inventario_partes": 404,
                "schedules_disponibles": 337, "inventario_encontrado": True}

    monkeypatch.setattr(ai_plan_tools, "_importar_plan_e_inventario", fake_import)
    res = ai_plan_tools.execute(
        "plan_importar_ejecutar", {"confirm_token": _import_token(file_bytes)},
        username="ana", file_lookup=lambda _ref: (file_bytes, "plan.xlsm"))
    # el motor solo devuelve schedules DISPONIBLES, nunca "schedules" sincronizados
    assert res["schedules_disponibles"] == 337
    assert "schedules" not in res
    assert res["inventario_partes"] == 404
    assert captured["called"] == ("plan.xlsm", "ana")


def test_importar_ejecutar_cal_sin_partn_no_reporta_schedule(monkeypatch):
    monkeypatch.setattr(ai_plan_tools, "_has_plan", lambda _u: True)
    file_bytes = b"cal-daily"
    monkeypatch.setattr(
        ai_plan_tools, "_importar_plan_e_inventario",
        lambda *_a, **_k: {"import_id": 43, "plan_partes": 487,
                           "inventario_partes": 0, "schedules_disponibles": 0,
                           "inventario_encontrado": False})
    res = ai_plan_tools.execute(
        "plan_importar_ejecutar", {"confirm_token": _import_token(file_bytes)},
        username="ana", file_lookup=lambda _ref: (file_bytes, "cal.xlsx"))
    assert res["inventario_encontrado"] is False
    assert res["schedules_disponibles"] == 0
