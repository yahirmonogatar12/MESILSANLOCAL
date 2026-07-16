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
        "exceptions": [],
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

    def fake_crear(fecha_inicio, fecha_fin, username, *, source, objective):
        created.append((fecha_inicio, fecha_fin, username, source, objective))
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
        )
    ]
    assert pending == [(result["proposal_id"], "ana")]
    assert file_lookups == []
    assert result["items"] == 1
    assert result["partes"] == 1
    assert result["total_qty"] == 200
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
    }


def test_plan_propuesta_de_hoy_exige_proceso_actual(monkeypatch):
    monkeypatch.setattr(ai_plan_tools, "_has_plan", lambda _username: False)
    monkeypatch.setattr(ai_plan_tools, "_has_projection", lambda _username: True)
    hoy = date.today().isoformat()

    with pytest.raises(ValueError, match="en que proceso o lote van"):
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
