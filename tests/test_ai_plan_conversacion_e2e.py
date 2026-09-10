"""Simulacro de una conversacion real de Plan LG, de punta a punta.

Corre de verdad: HTTP -> blueprint -> build_instructions -> loop de function
calling -> dispatch de ai_plan_tools -> token HMAC -> confirmacion del servidor.
Se simula solo el modelo (OpenAI) y el motor de calculo (part_planning), que es
lo unico que necesita MySQL.

Cubre el ciclo que mas importa:
  1. "haz una propuesta"      -> preparar, NO escribe
  2. "quita EBR80757421"      -> re-preparar con exclusion
  3. "tambien quita EBR1234"  -> conserva AMBAS exclusiones
  4. charla intercalada       -> la propuesta sigue viva
  5. "confirmo"               -> aplica con el token guardado en el servidor
"""

import json

import pytest

from app.api.portal import ai_plan_tools
from conftest import PARTE_A, PARTE_B, _turno


def test_conversacion_de_plan_completa(client, mundo):
    mundo.guion = [
        [{"tool": "plan_propuesta_preparar", "args": {"objetivo": "semana"}},
         "Propuesta lista: 1200 pzs en M1."],
        [{"tool": "plan_propuesta_preparar",
          "args": {"objetivo": "semana", "partes_excluidas": [PARTE_A]}},
         "Quite " + PARTE_A + "."],
        [{"tool": "plan_propuesta_preparar",
          "args": {"objetivo": "semana", "partes_excluidas": [PARTE_A, PARTE_B]}},
         "Ahora sin " + PARTE_A + " ni " + PARTE_B + "."],
        ["El CT de esa parte es 12.5 s."],
        ["La linea M1 corre 9 h al dia."],
    ]

    # 1. Preparar no escribe, pero si emite un token valido.
    _turno(client, "haz una propuesta del plan para esta semana")
    assert mundo.escrituras == [], "preparar NO debe escribir en el MES"
    assert mundo.ejecuciones[0]["tool_name"] == "plan_propuesta_preparar"
    token = mundo.preparaciones()[0]["confirm_token"]
    assert ai_plan_tools._read_token(token, "aplicar_propuesta")["username"] == "ana"

    # 2-3. Las exclusiones se acumulan y siguen sin escribir.
    _turno(client, "quita la parte " + PARTE_A)
    _turno(client, "tambien quita " + PARTE_B)
    assert mundo.preparaciones()[-1]["excluded_parts"] == [PARTE_A, PARTE_B]
    assert mundo.escrituras == [], "ajustar la propuesta tampoco escribe"

    # 4. Charla intercalada: la propuesta sobrevive.
    _turno(client, "de paso, cual es el CT de esa parte?")
    _turno(client, "y cuantas horas corre M1 al dia?")

    # El token nunca viaja al proveedor de IA: vive solo en el servidor.
    visto = json.dumps(mundo.vistas_por_el_modelo, ensure_ascii=False, default=str)
    assert token not in visto
    assert "confirm_token" not in visto

    # 5. Confirmar aplica con el token del servidor, sin consultar al modelo.
    vistas_antes = len(mundo.vistas_por_el_modelo)
    _turno(client, "confirmo")
    assert len(mundo.vistas_por_el_modelo) == vistas_antes, "confirmar no debe llamar a OpenAI"
    assert len(mundo.escrituras) == 1, "ahora si escribe, exactamente una vez"
    proposal_id, usuario, _kwargs = mundo.escrituras[0]
    assert usuario == "ana"
    assert proposal_id == mundo.preparaciones()[-1]["proposal_id"]

    # La preparacion queda consumida: un segundo "confirmo" no re-aplica.
    mundo.guion = [["Ya quedo aplicado."]]
    _turno(client, "confirmo")
    assert len(mundo.escrituras) == 1, "no debe re-aplicar una propuesta ya aplicada"


def test_las_exclusiones_de_turnos_viejos_siguen_visibles(client, mundo):
    """Lo que arregla la ventana de 20: con 12 esto se caia del contexto."""
    mundo.guion = [[
        {"tool": "plan_propuesta_preparar", "args": {"partes_excluidas": [PARTE_A]}},
        "Quite " + PARTE_A + ".",
    ]]
    _turno(client, "haz la propuesta pero quita " + PARTE_A)

    for i in range(6):
        mundo.guion = [["Respuesta " + str(i) + "."]]
        _turno(client, "pregunta suelta " + str(i))

    ultimo = json.dumps(mundo.vistas_por_el_modelo[-1], ensure_ascii=False, default=str)
    assert PARTE_A in ultimo, "el modelo olvido la exclusion pedida hace 7 turnos"
    assert mundo.limite_historial == [20] * 7, mundo.limite_historial


def test_confirmacion_de_otro_usuario_es_rechazada(mundo):
    token = ai_plan_tools._make_token("aplicar_propuesta", {
        "proposal_id": "prop-0", "version": 1, "username": "ana", "items": [],
    })
    with pytest.raises(PermissionError):
        ai_plan_tools.execute(
            "plan_propuesta_aplicar", {"confirm_token": token},
            username="beto", file_lookup=lambda *_a: None,
        )
    assert mundo.escrituras == []


def test_pedido_mixto_de_analisis_y_plan_conserva_las_tools_del_plan(client, mundo):
    """Un mensaje que pide analisis de almacen Y toca el plan perdia las 13
    tools del plan: _detailed_analysis_report matchea "analisis" + "almacen"."""
    mundo.guion = [[
        {"tool": "plan_propuesta_preparar", "args": {"objetivo": "ajuste"}},
        "Analisis listo y propuesta ajustada.",
    ]]
    _turno(client, "analiza el almacen de este mes y ajusta la propuesta del plan")

    assert mundo.preparaciones(), "el modelo no pudo llamar a la tool del plan"
    assert mundo.escrituras == [], "un analisis no debe escribir"
