"""Configuracion compartida de pytest.

Fija variables de entorno seguras para que la app arranque en CI / local
sin tocar inicializaciones de BD ni depender de un MySQL real:

  - MES_SKIP_STARTUP_INIT=1  -> no corre DDL/workers al crear la app.
  - SECRET_KEY               -> evita la clave efimera (sesiones estables).
"""

import json
import os
from types import SimpleNamespace

os.environ.setdefault("MES_SKIP_STARTUP_INIT", "1")
os.environ.setdefault("SECRET_KEY", "test-secret-key-do-not-use-in-prod")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

import pytest

from app.api.control_produccion import plan_assy
from app.api.portal import ai_assistant, ai_openai, ai_plan_tools

PARTE_A = "EBR80757421"
PARTE_B = "EBR12345678"


@pytest.fixture(scope="session")
def app():
    from app_factory import create_app

    application = create_app()
    application.config.update(TESTING=True)
    return application


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def _subidas_aisladas(monkeypatch, tmp_path):
    """Ningun test lee instance/ai_uploads: ahi viven archivos reales de usuarios.

    Ademas los evita abrir: un .xlsm de 3.6 MB tarda 4 s en load_workbook y se
    pagaba en cada test que tocara el asistente.
    """
    from app.api.portal import ai_assistant

    raiz = tmp_path / "ai_uploads"
    raiz.mkdir()
    monkeypatch.setattr(ai_assistant, "_upload_root", lambda: raiz)


class _Mundo:
    """MySQL en memoria: mensajes, ai_tool_executions y escrituras al motor."""

    def __init__(self):
        self.mensajes: list[dict] = []
        self.ejecuciones: list[dict] = []
        self.escrituras: list[tuple] = []
        self.vistas_por_el_modelo: list[list] = []
        self.prompts: list[str] = []
        self.guion: list[list] = []
        self.limite_historial: list[int] = []

    def preparaciones(self):
        """Solo las ejecuciones de plan_propuesta_preparar, en orden."""
        return [f["result"] for f in self.ejecuciones
                if f["tool_name"] == "plan_propuesta_preparar"
                and f["status"] == "success"]

    def historial(self, _conv_id, limit=12):
        self.limite_historial.append(limit)
        return [{"role": msg["role"], "content": msg["content"]}
                for msg in self.mensajes[-limit:]]

    def pendiente(self, _conv_id, _username):
        """Misma semantica que ai_store.get_pending_plan_confirmation."""
        pares = {"plan_propuesta_preparar": "plan_propuesta_aplicar"}
        for fila in reversed(self.ejecuciones):
            if fila["status"] != "success":
                continue
            nombre = fila["tool_name"]
            if nombre in pares.values():
                return None
            destino = pares.get(nombre)
            if not destino:
                continue
            resultado = fila.get("result") or {}
            token = resultado.get("confirm_token")
            if not token:
                return None
            return {
                "prepare_tool": nombre,
                "execute_tool": destino,
                "confirm_token": token,
                "proposal_id": resultado.get("proposal_id"),
            }
        return None


class _ModeloFake:
    """OpenAI simulado, guiado por mundo.guion (una lista por turno)."""

    def __init__(self, mundo):
        self.mundo = mundo
        self.responses = self
        self.pendientes = []

    def create(self, **kwargs):
        self.mundo.vistas_por_el_modelo.append(kwargs.get("input") or [])
        self.mundo.prompts.append(kwargs.get("instructions") or "")
        if not self.pendientes:
            self.pendientes = list(self.mundo.guion.pop(0)) if self.mundo.guion else ["Listo."]
        accion = self.pendientes.pop(0)
        # Sin herramientas declaradas el modelo no puede llamarlas: se salta
        # las acciones de tool hasta la primera respuesta de texto.
        if not kwargs.get("tools"):
            while not isinstance(accion, str):
                accion = self.pendientes.pop(0) if self.pendientes else "Listo."
        if isinstance(accion, str):
            eventos = [
                {"type": "response.output_text.delta", "delta": accion},
                {"type": "response.completed", "response": _resp([])},
            ]
        else:
            # Una lista = varias llamadas en la MISMA vuelta (tool calls en paralelo).
            grupo = accion if isinstance(accion, list) else [accion]
            eventos = [{
                "type": "response.completed",
                "response": _resp([{
                    "type": "function_call",
                    "name": a["tool"],
                    "call_id": "call_" + a["tool"] + "_" + str(i),
                    "arguments": json.dumps(a.get("args") or {}),
                } for i, a in enumerate(grupo)]),
            }]
        return iter(eventos)


def _resp(output):
    return SimpleNamespace(
        id="resp",
        output=output,
        usage={"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
    )


def _propuesta_falsa(*_args, **kwargs):
    """Sustituye al motor deterministico; refleja las exclusiones recibidas."""
    excluidas = list(kwargs.get("excluded_parts") or [])
    item = {
        "fecha": "2026-09-10", "linea": "M1", "turno": "Dia",
        "numero_parte": "EBR99999999", "cantidad": 1200, "ct": 12.5, "uph": 288,
        "horas_requeridas": 4.2, "inventario_antes": 300, "inventario_despues": 1500,
        "fecha_shortage": None, "excepciones": [],
    }
    return {
        "proposal_id": "prop-" + str(len(excluidas)), "version": 1, "engine_version": "v7",
        "date_from": "2026-09-10", "date_to": "2026-09-16", "proposals": [item],
        "partes": 1, "total_qty": 1200, "line_summary": {"M1": 4.2},
        "omitidas_count": len(excluidas), "excluded_parts": excluidas, "exceptions": [],
        "capacidad_libre": {"por_linea": {"M1": 4.8}, "total": 4.8, "lineas_con_espacio": ["M1"]}, "adelanto_max_dias": None, "expandido_dias": 0,
        "max_bloques": None, "sabados": [], "tiempo_extra": False, "adelantar_d1": True,
        "schedule_changes": [], "schedule_change_summary": {},
    }


@pytest.fixture()
def mundo(monkeypatch, tmp_path):
    subida = tmp_path / "subidas"
    subida.mkdir()

    from app.api.shared import permisos

    m = _Mundo()

    class Auth:
        def obtener_rol_principal_usuario(self, _username):
            return "superadmin"

        def verificar_permiso_boton(self, *_args, **_kwargs):
            return True

    monkeypatch.setattr(permisos, "_auth", lambda: Auth())
    monkeypatch.setattr(ai_openai, "_client", lambda: _ModeloFake(m))

    # Motor de calculo: lo unico que toca MySQL de verdad.
    monkeypatch.setattr(ai_plan_tools.pp, "_ppy_crear_propuesta", _propuesta_falsa)
    monkeypatch.setattr(ai_plan_tools.pp, "_ppy_mark_proposal_pending", lambda *_a, **_k: None)

    def _aplicar(proposal_id, username, **kwargs):
        m.escrituras.append((proposal_id, username, kwargs))
        return {"aplicados": 1, "proposal_id": proposal_id}

    monkeypatch.setattr(ai_plan_tools.pp, "_ppy_aplicar_propuesta", _aplicar)
    monkeypatch.setattr(plan_assy, "_assy_lotes_corriendo", lambda *_a, **_k: {})
    monkeypatch.setattr(ai_plan_tools, "_ajustes_a_items", lambda *_a, **_k: [])

    # Persistencia simulada.
    ids = iter(range(1000, 3000))

    def _add(_conv, role, content, **_kwargs):
        mid = next(ids)
        m.mensajes.append({"role": role, "content": content, "_id": mid})
        return mid

    def _update(message_id, *, content="", **_kwargs):
        """El asistente guarda su propia respuesta: asi el turno siguiente la ve."""
        for msg in m.mensajes:
            if msg.get("_id") == message_id:
                msg["content"] = content
                break

    monkeypatch.setattr(ai_assistant, "get_conversation", lambda _p: {
        "id": 7, "public_id": "chat-plan", "username": "ana",
        "title": "Plan", "language": "es",
    })
    monkeypatch.setattr(ai_assistant, "check_quota", lambda *_a, **_k: (True, None, {}, {}))
    monkeypatch.setattr(ai_assistant, "get_message_by_client_id", lambda *_a: None)
    monkeypatch.setattr(ai_assistant, "add_message", _add)
    monkeypatch.setattr(ai_assistant, "recent_model_messages", m.historial)
    monkeypatch.setattr(ai_assistant, "get_pending_plan_confirmation", m.pendiente)
    monkeypatch.setattr(ai_assistant, "record_tool_execution", lambda **kw: m.ejecuciones.append(
        {"tool_name": kw.get("tool_name"), "result": kw.get("result_summary"),
         "status": kw.get("status")}))
    monkeypatch.setattr(ai_assistant, "allowed_reports", lambda *_a: [])
    monkeypatch.setattr(ai_assistant, "query_tool_schema", lambda *_a: None)
    monkeypatch.setattr(ai_assistant, "_has", lambda *_a: True)
    monkeypatch.setattr(ai_assistant, "permisos_botones", lambda *_a: {})
    # _upload_root apunta a un temporal: _uploaded_file_info real sigue sirviendo
    # para las pruebas con adjuntos y devuelve None cuando no hay file_ref.
    monkeypatch.setattr(ai_assistant, "_upload_root", lambda: subida)
    monkeypatch.setattr(ai_assistant, "update_message", _update)
    for nombre in ("increment_usage", "refresh_conversation_summary", "_audit"):
        monkeypatch.setattr(ai_assistant, nombre, lambda *_a, **_k: None)
    return m


_contador = iter(range(1, 9999))


def _turno(client, texto, file_refs=None):
    with client.session_transaction() as sess:
        sess["usuario"] = "ana"
        sess["roles"] = ["superadmin"]
    respuesta = client.post(
        "/api/ai/conversations/chat-plan/messages/stream",
        json={
            "content": texto,
            "language": "es",
            "client_message_id": "00000000-0000-4000-8000-%012d" % next(_contador),
            "file_refs": list(file_refs or []),
        },
    )
    assert respuesta.status_code == 200, respuesta.get_data(as_text=True)
    return respuesta.get_data(as_text=True)
