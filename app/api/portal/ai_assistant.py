"""Blueprint HTTP del asistente IA global del MES."""

from __future__ import annotations

import json
import logging
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from flask import Blueprint, Response, jsonify, request, send_file, session, stream_with_context

from app.api.shared import auth_system
from app.api.shared.permisos import permisos_botones, puede_boton, requiere_permiso_dropdown
from app.db import get_db_connection

from .ai_artifacts import (
    artifact_tool_schema,
    create_artifact,
    get_artifact,
    list_artifacts,
    public_artifact,
    regenerate_artifact,
)
from .ai_openai import AIConfigurationError, AIProviderError, model_name, stream_response
from . import ai_plan_tools
from .ai_reports import allowed_reports, compact_report_result, query_tool_schema, run_report
from .ai_store import (
    AI_PAGE,
    AI_PERMISSION_ARTIFACTS,
    AI_PERMISSION_AUDIT,
    AI_PERMISSION_LIMITS,
    AI_PERMISSION_USE,
    AI_SECTION,
    add_message,
    check_quota,
    create_conversation,
    delete_conversation,
    effective_limits,
    get_conversation,
    get_message_by_client_id,
    get_pending_plan_confirmation,
    get_usage,
    increment_usage,
    list_audit_conversations,
    list_conversations,
    list_messages,
    now_local,
    recent_model_messages,
    refresh_conversation_summary,
    record_tool_execution,
    update_conversation,
    update_message,
)

logger = logging.getLogger(__name__)

bp = Blueprint("ai_assistant", __name__, url_prefix="/api/ai")

_BOM_DEFINITIONAL = re.compile(
    r"\b(?:qu[eé]\s+es|explica(?:me)?|definici[oó]n|what\s+is|explain|meaning)\b.*\bbom\b"
    r"|\bbom\b.*(?:이\s*뭐|뜻)",
    re.IGNORECASE,
)
_BOM_QUALIFIER = (
    r"(?:el|la|los|the|de|del|para|of|for|family|familia|model|modelo|"
    r"number|n[uú]mero|no\.?|completo|completa|complete|full|#|:)"
)
_BOM_AFTER = re.compile(
    rf"\bbom\b\s*(?:{_BOM_QUALIFIER}\s*){{0,6}}([A-Z0-9][A-Z0-9._/-]{{2,39}})",
    re.IGNORECASE,
)
_BOM_BEFORE = re.compile(r"\b([A-Z0-9][A-Z0-9._/-]{2,39})\s+\bbom\b", re.IGNORECASE)
_LARGE_DATA_REQUEST = re.compile(
    r"\b(?:todos?|todas?|complet[oa]s?|listado\s+completo|sin\s+omitir|"
    r"all|every|full|complete|entire|전체|모두|전부)\b",
    re.IGNORECASE,
)
_PLAN_CONFIRMATION = re.compile(
    r"^\s*(?:s[ií]|confirmo|confirmar|adelante|yes|confirm|ok|네|확인|동의)"
    r"(?:\s+(?:por\s+favor|please))?[\s.!]*$",
    re.IGNORECASE,
)
_PLAN_EXCEL_REQUEST = re.compile(
    r"\b(?:excel|xlsx)\b|"
    r"\b(?:p[aá]same|dame|genera(?:me)?|crea(?:me)?|exporta(?:me)?)\b"
    r".{0,24}\b(?:archivo|file)\b",
    re.IGNORECASE,
)


def _automatic_bom_filters(content: str) -> dict[str, str] | None:
    """Detecta una consulta BOM concreta; preguntas conceptuales no generan archivos."""
    if not re.search(r"\bbom\b", content, re.IGNORECASE) or _BOM_DEFINITIONAL.search(content):
        return None
    match = _BOM_AFTER.search(content) or _BOM_BEFORE.search(content)
    if not match:
        return None
    identifier = match.group(1).strip(".,;:()[]{}")
    if not any(character.isdigit() for character in identifier):
        return None
    return {"q": identifier[:120]}


def _artifact_language(preference: str, content: str) -> str:
    if preference in {"es", "en", "ko"}:
        return preference
    if re.search(r"[\uac00-\ud7af]", content):
        return "ko"
    if re.search(r"\b(?:please|show|give|get|need|export|for)\b", content, re.IGNORECASE):
        return "en"
    return "es"


def _plan_proposal_excel_text(language: str, row_count: int) -> str:
    """Respuesta determinista para exportar una propuesta sin aplicarla."""
    if language == "ko":
        return (
            f"완료했습니다. 부품 번호, 라인, 수량, CT, UPH 및 시간이 포함된 "
            f"보류 중인 생산 계획 제안 Excel을 첨부했습니다(**{row_count:,}**행). "
            "제안은 MES에 적용되지 않았습니다."
        )
    if language == "en":
        return (
            "Done. I attached the pending production-plan proposal as Excel with "
            f"part number, line, quantity, CT, UPH, and hours (**{row_count:,}** rows). "
            "The proposal has not been applied to MES."
        )
    return (
        "Listo, adjunté el Excel de la propuesta pendiente con número de parte, "
        f"línea, cantidad, CT, UPH y horas (**{row_count:,}** filas). "
        "La propuesta sigue sin aplicarse al MES."
    )


def _plan_completion_text(action: str, result: dict[str, Any], language: str) -> str:
    """Respuesta determinista tras consumir una confirmación del usuario."""
    if action == "plan_importar_ejecutar":
        # El Schedule (renglon S) no se sincroniza en el import; si el archivo
        # trae hoja Part N con renglones S, se pregunta si sincronizarlos.
        sched_disp = int(result.get("schedules_disponibles") or 0)
        preguntar_sched = bool(result.get("inventario_encontrado")) and sched_disp > 0
        if language == "ko":
            base = (
                "**가져오기가 완료되었습니다.**\n\n"
                f"- 계획 부품: **{int(result.get('plan_partes') or 0):,}**\n"
                f"- 계획 레코드: **{int(result.get('plan_registros') or 0):,}**\n"
                f"- 날짜: **{int(result.get('plan_fechas') or 0):,}** ({result.get('rango') or 'N/D'})\n"
                f"- 재고 부품: **{int(result.get('inventario_partes') or 0):,}**\n\n"
                f"가져오기 ID: **{result.get('import_id') or 'N/D'}**."
            )
            if preguntar_sched:
                base += (
                    f"\n\n재고와 수요를 동기화했습니다. 파일에 Planning의 스케줄"
                    f"(S행) **{sched_disp:,}**건이 있습니다. **스케줄도 동기화할까요?** (예/아니오)"
                )
            return base
        if language == "en":
            base = (
                "**Import completed successfully.**\n\n"
                f"- Plan parts: **{int(result.get('plan_partes') or 0):,}**\n"
                f"- Plan records: **{int(result.get('plan_registros') or 0):,}**\n"
                f"- Dates: **{int(result.get('plan_fechas') or 0):,}** ({result.get('rango') or 'N/A'})\n"
                f"- Inventory parts: **{int(result.get('inventario_partes') or 0):,}**\n\n"
                f"Import ID: **{result.get('import_id') or 'N/A'}**."
            )
            if preguntar_sched:
                base += (
                    f"\n\nInventory and demand are synced. The file has "
                    f"**{sched_disp:,}** Planning schedule rows (row S). "
                    f"**Do you want to sync the Schedule too?** (yes/no)"
                )
            return base
        base = (
            "**Importación completada correctamente.**\n\n"
            f"- Partes del plan: **{int(result.get('plan_partes') or 0):,}**\n"
            f"- Registros del plan: **{int(result.get('plan_registros') or 0):,}**\n"
            f"- Fechas: **{int(result.get('plan_fechas') or 0):,}** ({result.get('rango') or 'N/D'})\n"
            f"- Partes de inventario: **{int(result.get('inventario_partes') or 0):,}**\n\n"
            f"ID de importación: **{result.get('import_id') or 'N/D'}**."
        )
        if preguntar_sched:
            base += (
                f"\n\nEl inventario y la demanda quedaron sincronizados. El archivo "
                f"trae **{sched_disp:,}** renglones de Schedule (renglón S) de "
                f"Planning. **¿Quieres sincronizar también el Schedule?** (sí/no)"
            )
        return base

    if action == "plan_part_sincronizar_ejecutar":
        parts = int(result.get("parts") or 0)
        schedules = int(result.get("schedules") or 0)
        replaced = int(result.get("replaced") or 0)
        scope = str(result.get("scope") or "todos").upper()
        excluded = int(result.get("excluded_by_scope") or 0)
        skipped = int(result.get("skipped_without_active_line") or 0)
        skipped_parts = ", ".join(
            str(part) for part in (result.get("skipped_parts_without_active_line") or [])
        )
        date_range = (
            f"{result.get('date_from') or 'N/D'} a {result.get('date_to') or 'N/D'}"
        )
        if language == "ko":
            return (
                f"**Part 일정 동기화 완료.** 부품 **{parts:,}**개, 일정 "
                f"**{schedules:,}**개를 반영하고 기존 레코드 **{replaced:,}**개를 "
                f"교체했습니다. 범위: **{scope}**; 제외: **{excluded:,}**. 기간: "
                f"**{date_range}**. 활성 Assy line이 없어 건너뜀: **{skipped:,}**"
                + (f" ({skipped_parts})" if skipped_parts else "")
                + ". 재고와 LG 계획은 변경하지 않았습니다."
            )
        if language == "en":
            return (
                f"**Part schedule synchronized.** Updated **{parts:,}** parts and "
                f"**{schedules:,}** schedules, replacing **{replaced:,}** prior records. "
                f"Scope: **{scope}**; excluded: **{excluded:,}**. Range: "
                f"**{date_range}**. Skipped without an active Assy line: "
                f"**{skipped:,}**"
                + (f" ({skipped_parts})" if skipped_parts else "")
                + ". Inventory and the LG plan were not changed."
            )
        return (
            f"**Schedule del Part sincronizado.** Se actualizaron **{parts:,}** partes "
            f"y **{schedules:,}** schedules, reemplazando **{replaced:,}** registros "
            f"anteriores. Alcance: **{scope}**; excluidas: **{excluded:,}**. Rango: "
            f"**{date_range}**. Omitidas por no tener Assy line activa: "
            f"**{skipped:,}**"
            + (f" ({skipped_parts})" if skipped_parts else "")
            + ". No se modificaron inventario ni plan LG."
        )

    if action == "plan_propuesta_aplicar":
        applied = int(result.get("aplicadas") or 0)
        modified = int(result.get("modificadas") or 0)
        excluded = int(result.get("excluidas") or 0)
        total_qty = int(result.get("total_qty") or 0)
        if language == "ko":
            return (
                f"**계획 제안이 적용되었습니다.** **{applied:,}**개 일정, "
                f"**{total_qty:,}**개 수량이 반영되었습니다. 수정 **{modified:,}**, "
                f"제외 **{excluded:,}**."
            )
        if language == "en":
            return (
                f"**Plan proposal applied.** **{applied:,}** schedule entries and "
                f"**{total_qty:,}** units were applied. Modified: **{modified:,}**; "
                f"excluded: **{excluded:,}**."
            )
        return (
            f"**Propuesta de plan aplicada.** Se actualizaron **{applied:,}** capturas "
            f"del schedule por **{total_qty:,}** piezas. Modificadas: **{modified:,}**; "
            f"excluidas: **{excluded:,}**."
        )

    generated = int(result.get("generados") or 0)
    assigned = int(result.get("asignados") or 0)
    unassigned = int(result.get("sin_asignar") or 0)
    if language == "ko":
        return f"**생성이 완료되었습니다.** 생성: **{generated:,}**, 배정: **{assigned:,}**, 미배정: **{unassigned:,}**."
    if language == "en":
        return f"**Generation completed.** Generated: **{generated:,}**, assigned: **{assigned:,}**, unassigned: **{unassigned:,}**."
    return f"**Generación completada.** Generados: **{generated:,}**, asignados: **{assigned:,}**, sin asignar: **{unassigned:,}**."


def _large_data_request(content: str) -> bool:
    """Reconoce solicitudes amplias que deben entregarse como archivo y no como tabla en el chat."""
    return bool(_LARGE_DATA_REQUEST.search(str(content or "")))


def _compact_warehouse_count_request(content: str) -> bool:
    """Identifica conteos simples para reducir historial, herramientas y tokens."""
    text = str(content or "")
    if re.search(r"\b(?:excel|xlsx|powerpoint|pptx|archivo|exporta|export)\b", text, re.IGNORECASE):
        return False
    warehouse = re.search(r"\b(?:almac[eé]n|warehouse)\b|창고", text, re.IGNORECASE)
    movement = re.search(
        r"\b(?:entradas?|salidas?|retornos?|recibos?|entries|incoming|outgoing|returns?)\b|입고|출고|반품",
        text,
        re.IGNORECASE,
    )
    compact_scope = re.search(
        r"\b(?:cu[aá]nt[oa]s?|conteo|count|how\s+many|turno|shift|hoy|today|noche|night)\b|몇",
        text,
        re.IGNORECASE,
    )
    return bool(warehouse and movement and compact_scope)


def _detailed_analysis_report(content: str) -> str | None:
    """Enruta análisis explícitos a reportes agrupados, no a conteos compactos."""
    text = str(content or "")
    if not re.search(r"\b(?:an[aá]lisis|analiza|analysis)\b|분석", text, re.IGNORECASE):
        return None
    if re.search(r"\bLQC\b|엘큐씨", text, re.IGNORECASE):
        return "quality_lqc_analysis"
    warehouse = re.search(
        r"\b(?:almac[eé]n|warehouse|control\s+de\s+material)\b|창고",
        text,
        re.IGNORECASE,
    )
    entries_and_exits = (
        re.search(r"\bentradas?\b|\bentries\b|입고", text, re.IGNORECASE)
        and re.search(r"\bsalidas?\b|\boutgoing\b|출고", text, re.IGNORECASE)
    )
    if warehouse or entries_and_exits:
        return "warehouse_analysis"
    return None


def _artifact_request_key(report_key: str, filters: dict[str, Any] | None) -> str:
    """Evita generar dos veces el mismo reporte durante un turno con varias herramientas."""
    return json.dumps(
        {"report": report_key, "filters": filters or {}},
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    )


def _should_auto_export_report(
    report_key: str,
    result: dict[str, Any],
    *,
    large_request: bool,
    threshold: int,
) -> bool:
    """Exporta listados amplios; el estado de líneas ya tiene una vista visual compacta."""
    if report_key == "system_help":
        return False
    if report_key in {"line_status_today", "quality_status_today"}:
        return bool(result.get("truncated"))
    if result.get("truncated") or large_request:
        return True
    return int(result.get("row_count") or 0) >= threshold


def _bom_excel_options(content: str) -> dict[str, bool]:
    """Activa elementos analíticos de un BOM sólo cuando se piden expresamente."""
    summary_term = r"(?:resumen|summary|요약)"
    chart_term = r"(?:gr[aá]fic(?:a|as|o|os)|chart|charts|graph|graphs|차트)"
    negative_prefix = r"(?:sin|without|no\s+(?:incluyas?|agregues?|generes?|quiero))"

    def requested(term: str) -> bool:
        if re.search(rf"\b{negative_prefix}\b.{{0,25}}\b{term}\b", content, re.IGNORECASE):
            return False
        return bool(re.search(rf"\b{term}\b", content, re.IGNORECASE))

    return {
        "include_summary": requested(summary_term),
        "include_charts": requested(chart_term),
    }


def _roles() -> list[str]:
    raw = session.get("roles") or []
    result = []
    for item in raw:
        value = item.get("nombre") if isinstance(item, dict) else item
        if value:
            result.append(str(value))
    primary = session.get("rol_principal")
    if primary and primary not in result:
        result.append(str(primary))
    return result


def _username() -> str:
    return str(session.get("usuario") or "")


def _has(button: str) -> bool:
    return bool(_username() and puede_boton(_username(), AI_PAGE, AI_SECTION, button))


def _owner_conversation(public_id: str) -> dict[str, Any] | None:
    row = get_conversation(public_id)
    if not row or row.get("username") != _username():
        return None
    return row


def _accessible_artifact(public_id: str) -> dict[str, Any] | None:
    row = get_artifact(public_id)
    if not row:
        return None
    if row.get("username") == _username() or _has(AI_PERMISSION_AUDIT):
        return row
    return None


def _audit(action: str, description: str, details: dict[str, Any] | None = None, result: str = "EXITOSO") -> None:
    try:
        auth_system.registrar_auditoria(
            _username() or "sistema",
            "ASISTENTE_IA",
            action,
            description,
            datos_despues=details,
            resultado=result,
        )
    except Exception as exc:
        logger.warning("No se pudo registrar auditoría IA: %s", exc)


def _json_default(value: Any):
    if isinstance(value, datetime):
        return value.isoformat(sep=" ")
    return str(value)


def _sse(event: str, data: Any) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=_json_default)}\n\n"


@bp.get("/bootstrap")
@requiere_permiso_dropdown(AI_PAGE, AI_SECTION, AI_PERMISSION_USE)
def bootstrap():
    username = _username()
    reports = allowed_reports(username)
    usage = get_usage(username, model_name())
    limits = effective_limits(username, _roles())
    permissions = permisos_botones(username)
    return jsonify(
        {
            "success": True,
            "configured": bool(os.getenv("OPENAI_API_KEY", "").strip()),
            "model": model_name(),
            "current_user": {
                "username": username,
                "display_name": session.get("nombre_completo") or username,
                "department": session.get("departamento"),
                "roles": _roles(),
            },
            "language": "auto",
            "languages": ["auto", "es", "en", "ko"],
            "can_generate_artifacts": _has(AI_PERMISSION_ARTIFACTS),
            "can_audit": _has(AI_PERMISSION_AUDIT),
            "can_manage_limits": _has(AI_PERMISSION_LIMITS),
            "can_use_plan": ai_plan_tools._has(username),
            "reports": reports,
            "permissions": permissions,
            "usage": usage,
            "limits": limits,
        }
    )


def _upload_root() -> Path:
    root = Path(__file__).resolve().parents[3] / "instance" / "ai_uploads"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _upload_lookup(conversation_id: int):
    """Devuelve un callable file_ref -> (bytes, filename) para las tools del plan.

    Solo lee dentro del directorio de la conversacion; file_ref es el uuid del
    archivo subido (sin extension), no una ruta, asi que no hay path traversal.
    """
    base = (_upload_root() / str(int(conversation_id))).resolve()

    def _read(path):
        try:
            path.resolve().relative_to(base)
        except ValueError:
            return None, None
        meta = path.with_suffix(".name")
        filename = meta.read_text("utf-8")[:255] if meta.is_file() else path.name
        return path.read_bytes(), filename

    def lookup(file_ref):
        ref = re.sub(r"[^A-Za-z0-9_-]", "", str(file_ref or ""))[:64]
        if ref:
            for path in base.glob(f"{ref}.*"):
                if path.suffix.lower() in (".xlsx", ".xlsm"):
                    return _read(path)
        # Sin file_ref valido: usa el ultimo Excel subido a esta conversacion
        if not base.is_dir():
            return None, None
        candidatos = [p for p in base.glob("*") if p.suffix.lower() in (".xlsx", ".xlsm")]
        if not candidatos:
            return None, None
        ultimo = max(candidatos, key=lambda p: p.stat().st_mtime)
        return _read(ultimo)

    return lookup


def _uploaded_file_info(conversation_id: int, file_ref: str | None) -> dict[str, Any] | None:
    """Obtiene metadatos seguros del adjunto exacto enviado en este turno."""
    raw_ref = str(file_ref or "").strip()
    ref = re.sub(r"[^A-Za-z0-9_-]", "", raw_ref)[:64]
    if not ref or ref != raw_ref:
        return None
    base = (_upload_root() / str(int(conversation_id))).resolve()
    if not base.is_dir():
        return None
    for path in base.glob(f"{ref}.*"):
        if path.suffix.lower() not in (".xlsx", ".xlsm"):
            continue
        try:
            resolved = path.resolve()
            resolved.relative_to(base)
        except ValueError:
            continue
        meta = resolved.with_suffix(".name")
        filename = meta.read_text("utf-8")[:255] if meta.is_file() else resolved.name
        return {
            "filename": filename,
            "extension": resolved.suffix.lower(),
            "size_bytes": resolved.stat().st_size,
            "kind": "excel",
        }
    return None


@bp.post("/conversations/<public_id>/upload")
@requiere_permiso_dropdown(AI_PAGE, AI_SECTION, AI_PERMISSION_USE)
def upload_file(public_id: str):
    """Sube un Excel al chat para que las tools del plan lo procesen."""
    conversation = _owner_conversation(public_id)
    if not conversation:
        return jsonify({"success": False, "error": "Conversación no encontrada"}), 404
    if not ai_plan_tools._has(_username()):
        return jsonify({"success": False, "error": "No tienes permiso para las acciones del Plan"}), 403
    archivo = request.files.get("file")
    if archivo is None or not archivo.filename:
        return jsonify({"success": False, "error": "No se recibió archivo"}), 400
    ext = os.path.splitext(archivo.filename)[1].lower()
    if ext not in (".xlsx", ".xlsm"):
        return jsonify({"success": False, "error": "Solo .xlsx o .xlsm"}), 400
    data = archivo.read()
    if not data or len(data) > 20 * 1024 * 1024:
        return jsonify({"success": False, "error": "Archivo vacío o mayor a 20 MB"}), 400

    conv_dir = (_upload_root() / str(int(conversation["id"]))).resolve()
    conv_dir.mkdir(parents=True, exist_ok=True)
    file_ref = uuid.uuid4().hex
    (conv_dir / f"{file_ref}{ext}").write_bytes(data)
    (conv_dir / f"{file_ref}.name").write_text(archivo.filename[:255], "utf-8")
    _audit("SUBIR_ARCHIVO", f"Archivo subido al chat IA: {archivo.filename}",
           {"conversation_id": public_id, "file_ref": file_ref})
    return jsonify({"success": True, "file_ref": file_ref, "filename": archivo.filename})


@bp.route("/conversations", methods=["GET", "POST"])
@requiere_permiso_dropdown(AI_PAGE, AI_SECTION, AI_PERMISSION_USE)
def conversations():
    username = _username()
    if request.method == "GET":
        include_archived = request.args.get("include_archived") in {"1", "true", "yes"}
        return jsonify(
            {
                "success": True,
                "conversations": list_conversations(
                    username,
                    limit=request.args.get("limit", 50, type=int),
                    include_archived=include_archived,
                ),
            }
        )
    payload = request.get_json(silent=True) or {}
    language = str(payload.get("language") or "auto")
    if language not in {"auto", "es", "en", "ko"}:
        return jsonify({"success": False, "error": "Idioma inválido"}), 400
    row = create_conversation(username, language, model_name())
    _audit("CREAR_CHAT", "Conversación IA creada", {"conversation_id": row["public_id"]})
    return jsonify({"success": True, "conversation": row}), 201


@bp.get("/conversations/<public_id>/messages")
@requiere_permiso_dropdown(AI_PAGE, AI_SECTION, AI_PERMISSION_USE)
def conversation_messages(public_id: str):
    conversation = _owner_conversation(public_id)
    if not conversation:
        return jsonify({"success": False, "error": "Conversación no encontrada"}), 404
    messages = list_messages(
        int(conversation["id"]),
        before_id=request.args.get("before_id", type=int),
        limit=request.args.get("limit", 50, type=int),
    )
    return jsonify({"success": True, "conversation": conversation, "messages": messages})


@bp.patch("/conversations/<public_id>")
@requiere_permiso_dropdown(AI_PAGE, AI_SECTION, AI_PERMISSION_USE)
def patch_conversation(public_id: str):
    if not _owner_conversation(public_id):
        return jsonify({"success": False, "error": "Conversación no encontrada"}), 404
    payload = request.get_json(silent=True) or {}
    try:
        update_conversation(
            public_id,
            _username(),
            title=payload.get("title") if "title" in payload else None,
            status=payload.get("status") if "status" in payload else None,
            language=payload.get("language") if "language" in payload else None,
        )
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    return jsonify({"success": True, "conversation": get_conversation(public_id)})


@bp.delete("/conversations/<public_id>")
@requiere_permiso_dropdown(AI_PAGE, AI_SECTION, AI_PERMISSION_USE)
def remove_conversation(public_id: str):
    if not _owner_conversation(public_id):
        return jsonify({"success": False, "error": "Conversación no encontrada"}), 404
    deleted = delete_conversation(public_id, _username())
    if not deleted:
        return jsonify({"success": False, "error": "Conversación no encontrada"}), 404
    _audit(
        "ELIMINAR_CHAT",
        "Conversación IA eliminada definitivamente",
        {
            "conversation_id": public_id,
            "messages": deleted.get("messages", 0),
            "artifacts": deleted.get("artifacts", 0),
            "files_removed": deleted.get("files_removed", 0),
        },
    )
    return jsonify({"success": True, "deleted": deleted})


@bp.post("/conversations/<public_id>/messages/stream")
@requiere_permiso_dropdown(AI_PAGE, AI_SECTION, AI_PERMISSION_USE)
def stream_message(public_id: str):
    conversation = _owner_conversation(public_id)
    if not conversation:
        return jsonify({"success": False, "error": "Conversación no encontrada"}), 404
    payload = request.get_json(silent=True) or {}
    content = str(payload.get("content") or "").strip()
    if not content or len(content) > 8000:
        return jsonify({"success": False, "error": "El mensaje debe contener entre 1 y 8,000 caracteres"}), 400
    client_message_id = str(payload.get("client_message_id") or uuid.uuid4())
    try:
        uuid.UUID(client_message_id)
    except ValueError:
        return jsonify({"success": False, "error": "client_message_id inválido"}), 400

    quota_ok, quota_error, usage, limits = check_quota(_username(), model_name(), _roles())
    if not quota_ok:
        return jsonify({"success": False, "error": quota_error, "usage": usage, "limits": limits}), 429

    existing = get_message_by_client_id(int(conversation["id"]), client_message_id)
    if existing:
        return jsonify({"success": False, "error": "El mensaje ya fue procesado", "message_id": existing["id"]}), 409

    last_file_ref = str(payload.get("file_ref") or "").strip() or None
    attachment = _uploaded_file_info(int(conversation["id"]), last_file_ref)
    if not attachment:
        last_file_ref = None

    user_message_id = add_message(
        int(conversation["id"]), "user", content,
        client_message_id=client_message_id,
        model=model_name(),
        content_json={"attachment": attachment} if attachment else None,
    )
    if conversation.get("title") == "Nueva conversación":
        update_conversation(public_id, _username(), title=content[:80])
    analysis_report_key = _detailed_analysis_report(content)
    compact_warehouse_request = bool(
        not analysis_report_key and _compact_warehouse_count_request(content)
    )
    model_messages = recent_model_messages(
        int(conversation["id"]),
        limit=4 if compact_warehouse_request else (6 if analysis_report_key else 12),
    )
    assistant_message_id = add_message(
        int(conversation["id"]), "assistant", "", status="streaming", model=model_name(),
    )

    language = str(payload.get("language") or conversation.get("language") or "auto")
    if language not in {"auto", "es", "en", "ko"}:
        language = "auto"
    page_context = payload.get("page_context") if isinstance(payload.get("page_context"), dict) else {}
    report_catalog = allowed_reports(_username())
    automatic_bom_filters = _automatic_bom_filters(content)
    automatic_large_export_requested = _large_data_request(content)
    automatic_bom_enabled = bool(
        automatic_bom_filters
        and _has(AI_PERMISSION_ARTIFACTS)
        and any(item.get("key") == "bom" for item in report_catalog)
    )
    tools = []
    focused_reports = (
        {"warehouse_shift_activity"}
        if compact_warehouse_request
        else ({analysis_report_key} if analysis_report_key else None)
    )
    report_tool = query_tool_schema(_username(), focused_reports)
    if report_tool:
        tools.append(report_tool)
    if _has(AI_PERMISSION_ARTIFACTS) and not automatic_bom_enabled and not compact_warehouse_request:
        artifact_report_keys = [
            item["key"]
            for item in report_catalog
            if item["key"] != "system_help"
            and (not analysis_report_key or item["key"] == analysis_report_key)
        ]
        artifact_schema = artifact_tool_schema(_username(), artifact_report_keys)
        if artifact_schema:
            tools.append(artifact_schema)

    # Herramientas del Plan de produccion LG (importar, faltantes, generar).
    # Solo si el usuario tiene el permiso "Plan Proyectado".
    plan_tools = ai_plan_tools.tool_schemas(_username())
    if plan_tools and not compact_warehouse_request and not analysis_report_key:
        tools.extend(plan_tools)
    allowed_model_tool_names = {
        str(tool.get("name") or "") for tool in tools if tool.get("name")
    }
    pending_plan_action = (
        get_pending_plan_confirmation(int(conversation["id"]), _username())
        if plan_tools
        and (
            _PLAN_CONFIRMATION.fullmatch(content)
            or _PLAN_EXCEL_REQUEST.search(content)
        )
        else None
    )
    pending_plan_confirmation = (
        pending_plan_action if _PLAN_CONFIRMATION.fullmatch(content) else None
    )
    pending_plan_excel = (
        pending_plan_action
        if pending_plan_action
        and pending_plan_action.get("prepare_tool") == "plan_propuesta_preparar"
        and pending_plan_action.get("proposal_id")
        and _PLAN_EXCEL_REQUEST.search(content)
        else None
    )

    context_reports = (
        [item for item in report_catalog if item.get("key") == "warehouse_shift_activity"]
        if compact_warehouse_request
        else (
            [item for item in report_catalog if item.get("key") == analysis_report_key]
            if analysis_report_key
            else report_catalog
        )
    )
    context = {
        "language": language,
        "department": session.get("departamento"),
        "role": session.get("rol_principal") or (_roles()[0] if _roles() else None),
        "permissions": (
            [] if compact_warehouse_request or analysis_report_key
            else list((permisos_botones(_username()) or {}).keys())
        ),
        "reports": context_reports,
        "page_context": page_context,
        "timezone": os.getenv("TZ", "America/Mexico_City"),
        "current_local_datetime": now_local().isoformat(sep=" ", timespec="seconds"),
        "conversation_summary": conversation.get("summary_text"),
        "automatic_bom_excel": automatic_bom_enabled,
        "automatic_large_export_requested": automatic_large_export_requested,
        "plan_tools_enabled": bool(plan_tools),
        "attachment": attachment,
    }

    @stream_with_context
    def generate():
        assistant_text: list[str] = []
        usage_payload = {"input_tokens": 0, "output_tokens": 0}
        created_artifacts: list[dict[str, Any]] = []
        created_visualizations: list[dict[str, Any]] = []
        exported_report_requests: set[str] = set()
        yield _sse("ack", {"user_message_id": user_message_id, "assistant_message_id": assistant_message_id})

        def execute_tool(
            name: str,
            arguments: dict[str, Any],
            call_id: str,
            *,
            server_confirmed: bool = False,
        ) -> dict[str, Any]:
            started = datetime.now()
            try:
                expected_server_tool = (
                    str(pending_plan_confirmation.get("execute_tool") or "")
                    if pending_plan_confirmation
                    else ""
                )
                if server_confirmed:
                    if name != expected_server_tool:
                        raise PermissionError("Confirmacion de herramienta invalida")
                elif name not in allowed_model_tool_names:
                    raise PermissionError(
                        "El modelo intento ejecutar una herramienta no declarada"
                    )
                if name == "query_mes_report":
                    report_key = arguments["report"]
                    report_filters = arguments.get("filters") or {}
                    result = run_report(
                        _username(), report_key, report_filters,
                        limit=int(os.getenv("AI_TOOL_MAX_ROWS", "200")),
                    )
                    compact = compact_report_result(result, sample_size=8)
                    record_tool_execution(
                        conversation_id=int(conversation["id"]),
                        message_id=assistant_message_id,
                        username=_username(), tool_name=name, arguments=arguments,
                        result_summary=compact, status="success",
                        row_count=result.get("row_count", 0),
                        duration_ms=int((datetime.now() - started).total_seconds() * 1000),
                    )
                    response = {
                        "model_output": compact,
                        "public_summary": {
                            "title": result.get("title"),
                            "row_count": result.get("row_count"),
                            "source": result.get("source"),
                        },
                    }
                    if result.get("visualization"):
                        visualization = {
                            **result["visualization"],
                            "id": f"line-status-{assistant_message_id}-{call_id}",
                        }
                        compact["visualization"] = visualization
                        created_visualizations.append(visualization)
                        response["client_events"] = [
                            {"event": "visualization", "data": visualization}
                        ]
                    threshold = max(
                        10,
                        min(int(os.getenv("AI_AUTO_EXPORT_ROW_THRESHOLD", "50")), 200),
                    )
                    effective_filters = (
                        result.get("filters")
                        if isinstance(result.get("filters"), dict)
                        else report_filters
                    )
                    export_key = _artifact_request_key(report_key, effective_filters)
                    should_export = _should_auto_export_report(
                        report_key,
                        result,
                        large_request=automatic_large_export_requested,
                        threshold=threshold,
                    )
                    if not should_export or export_key in exported_report_requests:
                        return response

                    artifact_error = None
                    artifact = None
                    lqc_analytics = report_key == "quality_lqc"
                    artifact_title = f"{result.get('title') or 'Reporte MES'} completo"
                    if lqc_analytics and effective_filters.get("operational_date"):
                        artifact_title = (
                            f"{result.get('title') or 'Historial LQC'} - "
                            f"{effective_filters['operational_date']}"
                        )
                    artifact_arguments = {
                        "artifact_type": "xlsx",
                        "title": artifact_title,
                        "language": _artifact_language(language, content),
                        "report": report_key,
                        "filters": effective_filters,
                        "include_summary": lqc_analytics,
                        "include_charts": lqc_analytics,
                        "automatic": True,
                        "reason": "large_result",
                    }
                    artifact_started = datetime.now()
                    try:
                        if not _has(AI_PERMISSION_ARTIFACTS):
                            raise PermissionError("No tienes permiso para generar archivos IA")
                        allowed, error, _, _ = check_quota(
                            _username(), model_name(), _roles(), artifact=True
                        )
                        if not allowed:
                            raise PermissionError(error)
                        artifact = create_artifact(
                            username=_username(),
                            conversation_id=int(conversation["id"]),
                            message_id=assistant_message_id,
                            artifact_type="xlsx",
                            title=artifact_arguments["title"],
                            language=artifact_arguments["language"],
                            report_key=report_key,
                            filters=effective_filters,
                            include_summary=lqc_analytics,
                            include_charts=lqc_analytics,
                        )
                        exported_report_requests.add(export_key)
                        created_artifacts.append(artifact)
                        increment_usage(_username(), model_name(), artifacts=1)
                        record_tool_execution(
                            conversation_id=int(conversation["id"]),
                            message_id=assistant_message_id,
                            username=_username(),
                            tool_name="create_artifact",
                            arguments=artifact_arguments,
                            result_summary=artifact,
                            status="success",
                            row_count=artifact.get("row_count", 0),
                            duration_ms=int(
                                (datetime.now() - artifact_started).total_seconds() * 1000
                            ),
                        )
                        context["automatic_artifact"] = artifact
                        compact["automatic_artifact"] = artifact
                        compact["response_policy"] = (
                            "El Excel completo ya está adjunto. Responde en máximo tres oraciones "
                            "y no muestres tablas ni muestras de filas."
                        )
                        response["client_event"] = {
                            "event": "artifact_ready",
                            "data": artifact,
                        }
                        _audit(
                            "GENERAR_ARTEFACTO",
                            f"Excel generado automáticamente por resultado amplio: {artifact.get('filename')}",
                            artifact,
                        )
                    except Exception as exc:
                        artifact_error = str(exc)
                        compact["automatic_artifact_error"] = artifact_error
                        compact["response_policy"] = (
                            "No pegues el resultado masivo en el chat. Explica brevemente que no "
                            "fue posible crear el Excel y solicita filtros más específicos."
                        )
                        response["client_event"] = {
                            "event": "artifact_error",
                            "data": {"message": artifact_error},
                        }
                        record_tool_execution(
                            conversation_id=int(conversation["id"]),
                            message_id=assistant_message_id,
                            username=_username(),
                            tool_name="create_artifact",
                            arguments=artifact_arguments,
                            result_summary={},
                            status="error",
                            duration_ms=int(
                                (datetime.now() - artifact_started).total_seconds() * 1000
                            ),
                            error_text=artifact_error,
                        )
                    return response
                if name == "create_artifact":
                    allowed, error, _, _ = check_quota(_username(), model_name(), _roles(), artifact=True)
                    if not allowed:
                        raise PermissionError(error)
                    if not _has(AI_PERMISSION_ARTIFACTS):
                        raise PermissionError("No tienes permiso para generar archivos IA")
                    presentation = (
                        _bom_excel_options(content)
                        if arguments["report"] == "bom" and arguments["artifact_type"] == "xlsx"
                        else {
                            "include_summary": arguments.get("include_summary"),
                            "include_charts": arguments.get("include_charts"),
                        }
                    )
                    artifact = create_artifact(
                        username=_username(), conversation_id=int(conversation["id"]),
                        message_id=assistant_message_id,
                        artifact_type=arguments["artifact_type"], title=arguments["title"],
                        language=arguments["language"], report_key=arguments["report"],
                        filters=arguments.get("filters") or {},
                        include_summary=presentation["include_summary"],
                        include_charts=presentation["include_charts"],
                    )
                    created_artifacts.append(artifact)
                    exported_report_requests.add(
                        _artifact_request_key(arguments["report"], arguments.get("filters") or {})
                    )
                    increment_usage(_username(), model_name(), artifacts=1)
                    record_tool_execution(
                        conversation_id=int(conversation["id"]), message_id=assistant_message_id,
                        username=_username(), tool_name=name, arguments=arguments,
                        result_summary=artifact, status="success", row_count=artifact.get("row_count", 0),
                        duration_ms=int((datetime.now() - started).total_seconds() * 1000),
                    )
                    _audit("GENERAR_ARTEFACTO", f"Archivo IA generado: {artifact.get('filename')}", artifact)
                    return {
                        "model_output": {"success": True, "artifact": artifact},
                        "public_summary": artifact,
                        "client_event": {"event": "artifact_ready", "data": artifact},
                    }
                if name in ai_plan_tools.TOOL_NAMES:
                    # Si la tool no trae file_ref, usa el ultimo adjunto del turno
                    if name in {
                        "plan_importar_preparar",
                        "plan_part_sincronizar_preparar",
                    } and not arguments.get("file_ref"):
                        arguments = {**arguments, "file_ref": last_file_ref}
                    result = ai_plan_tools.execute(
                        name, arguments,
                        username=_username(),
                        file_lookup=_upload_lookup(int(conversation["id"])),
                    )
                    stored_arguments = {
                        key: ("[redactado]" if key == "confirm_token" else value)
                        for key, value in arguments.items()
                    }
                    record_tool_execution(
                        conversation_id=int(conversation["id"]), message_id=assistant_message_id,
                        username=_username(), tool_name=name, arguments=stored_arguments,
                        result_summary=result, status="success",
                        duration_ms=int((datetime.now() - started).total_seconds() * 1000),
                    )
                    _audit("PLAN_IA", f"Tool de plan ejecutada: {name}",
                           {"tool": name, "conversation_id": public_id})
                    # El token queda exclusivamente en MySQL para que el
                    # servidor procese la confirmacion del siguiente mensaje.
                    model_result = {
                        key: value for key, value in result.items() if key != "confirm_token"
                    }
                    response = {
                        "model_output": model_result,
                        "public_summary": {"tool": name},
                    }
                    if name == "plan_propuesta_preparar" and result.get("proposal_id"):
                        proposal_id = str(result["proposal_id"])
                        proposal_date = str(result.get("date_from") or "").strip()
                        artifact_title = "Plan de producción propuesto"
                        if proposal_date:
                            artifact_title += f" - {proposal_date}"
                        artifact_arguments = {
                            "artifact_type": "xlsx",
                            "title": artifact_title,
                            "language": _artifact_language(language, content),
                            "report": "plan_proposal",
                            "filters": {"proposal_id": proposal_id},
                            "include_summary": True,
                            "include_charts": False,
                            "automatic": True,
                            "reason": "new_plan_proposal",
                        }
                        artifact_started = datetime.now()
                        try:
                            if not _has(AI_PERMISSION_ARTIFACTS):
                                raise PermissionError(
                                    "No tienes permiso para generar archivos IA"
                                )
                            allowed, error, _, _ = check_quota(
                                _username(), model_name(), _roles(), artifact=True
                            )
                            if not allowed:
                                raise PermissionError(error)
                            artifact = create_artifact(
                                username=_username(),
                                conversation_id=int(conversation["id"]),
                                message_id=assistant_message_id,
                                artifact_type="xlsx",
                                title=artifact_title,
                                language=artifact_arguments["language"],
                                report_key="plan_proposal",
                                filters={"proposal_id": proposal_id},
                                include_summary=True,
                                include_charts=False,
                            )
                            created_artifacts.append(artifact)
                            exported_report_requests.add(
                                _artifact_request_key(
                                    "plan_proposal", {"proposal_id": proposal_id}
                                )
                            )
                            increment_usage(_username(), model_name(), artifacts=1)
                            record_tool_execution(
                                conversation_id=int(conversation["id"]),
                                message_id=assistant_message_id,
                                username=_username(),
                                tool_name="create_artifact",
                                arguments=artifact_arguments,
                                result_summary=artifact,
                                status="success",
                                row_count=artifact.get("row_count", 0),
                                duration_ms=int(
                                    (datetime.now() - artifact_started).total_seconds()
                                    * 1000
                                ),
                            )
                            context["automatic_artifact"] = artifact
                            model_result["automatic_artifact"] = artifact
                            model_result["response_policy"] = (
                                "El Excel de esta propuesta ya está adjunto. Menciona el resumen "
                                "del plan, confirma brevemente el archivo y aclara que todavía no "
                                "se aplicó al MES. No llames create_artifact otra vez."
                            )
                            response["client_event"] = {
                                "event": "artifact_ready",
                                "data": artifact,
                            }
                            _audit(
                                "GENERAR_ARTEFACTO",
                                "Excel generado automáticamente con la propuesta: "
                                f"{artifact.get('filename')}",
                                artifact,
                            )
                        except Exception as artifact_exc:
                            artifact_error = str(artifact_exc)
                            context["automatic_artifact_error"] = artifact_error
                            model_result["automatic_artifact_error"] = artifact_error
                            response["client_event"] = {
                                "event": "artifact_error",
                                "data": {"message": artifact_error},
                            }
                            record_tool_execution(
                                conversation_id=int(conversation["id"]),
                                message_id=assistant_message_id,
                                username=_username(),
                                tool_name="create_artifact",
                                arguments=artifact_arguments,
                                result_summary={},
                                status="error",
                                duration_ms=int(
                                    (datetime.now() - artifact_started).total_seconds()
                                    * 1000
                                ),
                                error_text=artifact_error,
                            )
                    return response
                raise ValueError("Herramienta no registrada")
            except Exception as exc:
                error_arguments = {
                    key: ("[redactado]" if key == "confirm_token" else value)
                    for key, value in arguments.items()
                }
                record_tool_execution(
                    conversation_id=int(conversation["id"]), message_id=assistant_message_id,
                    username=_username(), tool_name=name, arguments=error_arguments,
                    result_summary={}, status="error",
                    duration_ms=int((datetime.now() - started).total_seconds() * 1000),
                    error_text=str(exc),
                )
                raise

        try:
            if pending_plan_confirmation:
                action = str(pending_plan_confirmation["execute_tool"])
                call_id = f"confirmed-{assistant_message_id}"
                yield _sse("tool_start", {"name": action, "call_id": call_id})
                executed = execute_tool(
                    action,
                    {"confirm_token": pending_plan_confirmation["confirm_token"]},
                    call_id,
                    server_confirmed=True,
                )
                yield _sse(
                    "tool_end",
                    {
                        "name": action,
                        "call_id": call_id,
                        "summary": executed.get("public_summary"),
                    },
                )
                result = executed.get("model_output") or {}
                final_text = _plan_completion_text(
                    action,
                    result,
                    _artifact_language(language, content),
                )
                assistant_text.append(final_text)
                yield _sse("delta", {"text": final_text})
                update_message(
                    assistant_message_id,
                    content=final_text,
                    status="complete",
                    input_tokens=0,
                    output_tokens=0,
                    content_json={"artifacts": [], "visualizations": []},
                )
                increment_usage(_username(), model_name(), requests=1)
                refresh_conversation_summary(int(conversation["id"]), keep_recent=12)
                _audit(
                    "PLAN_IA_CONFIRMADO",
                    f"Acción del plan confirmada y ejecutada: {action}",
                    {"conversation_id": public_id, "tool": action},
                )
                yield _sse(
                    "done",
                    {
                        "message_id": assistant_message_id,
                        "artifacts": [],
                        "visualizations": [],
                    },
                )
                return

            if pending_plan_excel:
                proposal_id = str(pending_plan_excel["proposal_id"])
                artifact_language = _artifact_language(language, content)
                arguments = {
                    "artifact_type": "xlsx",
                    "title": "Plan de producción propuesto",
                    "language": artifact_language,
                    "report": "plan_proposal",
                    "filters": {"proposal_id": proposal_id},
                    "include_summary": True,
                    "include_charts": False,
                    "automatic": True,
                    "reason": "pending_plan_proposal",
                }
                started = datetime.now()
                yield _sse(
                    "artifact_start",
                    {"type": "xlsx", "title": arguments["title"]},
                )
                yield _sse(
                    "artifact_progress",
                    {"progress": 10, "message": "Leyendo la propuesta pendiente"},
                )
                allowed, error, _, _ = check_quota(
                    _username(), model_name(), _roles(), artifact=True
                )
                if not allowed:
                    raise PermissionError(error)
                if not _has(AI_PERMISSION_ARTIFACTS):
                    raise PermissionError("No tienes permiso para generar archivos IA")
                artifact = create_artifact(
                    username=_username(),
                    conversation_id=int(conversation["id"]),
                    message_id=assistant_message_id,
                    artifact_type="xlsx",
                    title=arguments["title"],
                    language=artifact_language,
                    report_key="plan_proposal",
                    filters={"proposal_id": proposal_id},
                    include_summary=True,
                    include_charts=False,
                )
                created_artifacts.append(artifact)
                increment_usage(_username(), model_name(), artifacts=1)
                record_tool_execution(
                    conversation_id=int(conversation["id"]),
                    message_id=assistant_message_id,
                    username=_username(),
                    tool_name="create_artifact",
                    arguments=arguments,
                    result_summary=artifact,
                    status="success",
                    row_count=artifact.get("row_count", 0),
                    duration_ms=int((datetime.now() - started).total_seconds() * 1000),
                )
                _audit(
                    "GENERAR_ARTEFACTO",
                    f"Excel de propuesta pendiente generado: {artifact.get('filename')}",
                    artifact,
                )
                yield _sse(
                    "artifact_progress",
                    {"progress": 100, "message": "Excel de la propuesta listo"},
                )
                yield _sse("artifact_ready", artifact)
                final_text = _plan_proposal_excel_text(
                    artifact_language,
                    int(artifact.get("row_count") or 0),
                )
                assistant_text.append(final_text)
                yield _sse("delta", {"text": final_text})
                update_message(
                    assistant_message_id,
                    content=final_text,
                    status="complete",
                    input_tokens=0,
                    output_tokens=0,
                    content_json={"artifacts": created_artifacts, "visualizations": []},
                )
                increment_usage(_username(), model_name(), requests=1)
                refresh_conversation_summary(int(conversation["id"]), keep_recent=12)
                yield _sse(
                    "done",
                    {
                        "message_id": assistant_message_id,
                        "artifacts": created_artifacts,
                        "visualizations": [],
                    },
                )
                return

            if automatic_bom_enabled:
                presentation = _bom_excel_options(content)
                arguments = {
                    "artifact_type": "xlsx",
                    "title": f"BOM {automatic_bom_filters['q']}",
                    "language": _artifact_language(language, content),
                    "report": "bom",
                    "filters": automatic_bom_filters,
                    **presentation,
                    "automatic": True,
                }
                started = datetime.now()
                yield _sse("artifact_start", {"type": "xlsx", "title": arguments["title"]})
                yield _sse("artifact_progress", {"progress": 10, "message": "Consultando BOM autorizado"})
                try:
                    allowed, error, _, _ = check_quota(
                        _username(), model_name(), _roles(), artifact=True
                    )
                    if not allowed:
                        raise PermissionError(error)
                    artifact = create_artifact(
                        username=_username(),
                        conversation_id=int(conversation["id"]),
                        message_id=assistant_message_id,
                        artifact_type="xlsx",
                        title=arguments["title"],
                        language=arguments["language"],
                        report_key="bom",
                        filters=automatic_bom_filters,
                        include_summary=presentation["include_summary"],
                        include_charts=presentation["include_charts"],
                    )
                    created_artifacts.append(artifact)
                    exported_report_requests.add(
                        _artifact_request_key("bom", automatic_bom_filters)
                    )
                    increment_usage(_username(), model_name(), artifacts=1)
                    record_tool_execution(
                        conversation_id=int(conversation["id"]),
                        message_id=assistant_message_id,
                        username=_username(),
                        tool_name="create_artifact",
                        arguments=arguments,
                        result_summary=artifact,
                        status="success",
                        row_count=artifact.get("row_count", 0),
                        duration_ms=int((datetime.now() - started).total_seconds() * 1000),
                    )
                    context["automatic_artifact"] = artifact
                    _audit(
                        "GENERAR_ARTEFACTO",
                        f"Excel BOM generado automáticamente: {artifact.get('filename')}",
                        artifact,
                    )
                    yield _sse("artifact_progress", {"progress": 100, "message": "Excel BOM listo"})
                    yield _sse("artifact_ready", artifact)
                except Exception as exc:
                    context["automatic_artifact_error"] = str(exc)
                    record_tool_execution(
                        conversation_id=int(conversation["id"]),
                        message_id=assistant_message_id,
                        username=_username(),
                        tool_name="create_artifact",
                        arguments=arguments,
                        result_summary={},
                        status="error",
                        duration_ms=int((datetime.now() - started).total_seconds() * 1000),
                        error_text=str(exc),
                    )
                    yield _sse("artifact_error", {"message": str(exc)})

            for event in stream_response(
                username=_username(), context=context, messages=model_messages,
                tools=tools, execute_tool=execute_tool,
            ):
                if event["event"] == "delta":
                    assistant_text.append(event["data"].get("text", ""))
                elif event["event"] == "usage":
                    usage_payload.update(event["data"])
                yield _sse(event["event"], event["data"])
            final_text = "".join(assistant_text).strip()
            update_message(
                assistant_message_id, content=final_text, status="complete",
                response_id=usage_payload.get("response_id"),
                input_tokens=usage_payload.get("input_tokens", 0),
                output_tokens=usage_payload.get("output_tokens", 0),
                content_json={
                    "artifacts": created_artifacts,
                    "visualizations": created_visualizations,
                },
            )
            increment_usage(
                _username(), model_name(), requests=1,
                input_tokens=usage_payload.get("input_tokens", 0),
                output_tokens=usage_payload.get("output_tokens", 0),
            )
            refresh_conversation_summary(int(conversation["id"]), keep_recent=12)
            _audit("MENSAJE_IA", "Respuesta IA completada", {"conversation_id": public_id})
            yield _sse(
                "done",
                {
                    "message_id": assistant_message_id,
                    "artifacts": created_artifacts,
                    "visualizations": created_visualizations,
                },
            )
        except (AIConfigurationError, AIProviderError, PermissionError, ValueError) as exc:
            partial = "".join(assistant_text).strip()
            update_message(
                assistant_message_id,
                content=partial,
                status="failed",
                content_json={
                    "error": str(exc),
                    "artifacts": created_artifacts,
                    "visualizations": created_visualizations,
                },
            )
            _audit("MENSAJE_IA", "Respuesta IA fallida", {"error": str(exc)[:500]}, result="ERROR")
            yield _sse("error", {"message": str(exc)})
        except GeneratorExit:
            partial = "".join(assistant_text).strip()
            update_message(
                assistant_message_id,
                content=partial,
                status="cancelled",
                content_json={
                    "cancelled": True,
                    "artifacts": created_artifacts,
                    "visualizations": created_visualizations,
                },
            )
            raise
        except Exception as exc:
            logger.exception("Error inesperado en stream IA")
            partial = "".join(assistant_text).strip()
            update_message(
                assistant_message_id,
                content=partial,
                status="failed",
                content_json={
                    "error": "Error interno",
                    "artifacts": created_artifacts,
                    "visualizations": created_visualizations,
                },
            )
            yield _sse("error", {"message": "Error interno del asistente"})

    return Response(generate(), mimetype="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@bp.get("/conversations/<public_id>/artifacts")
@requiere_permiso_dropdown(AI_PAGE, AI_SECTION, AI_PERMISSION_USE)
def conversation_artifacts(public_id: str):
    conversation = _owner_conversation(public_id)
    if not conversation:
        return jsonify({"success": False, "error": "Conversación no encontrada"}), 404
    return jsonify({"success": True, "artifacts": list_artifacts(int(conversation["id"]))})


@bp.get("/artifacts/<public_id>/download")
@requiere_permiso_dropdown(AI_PAGE, AI_SECTION, AI_PERMISSION_USE)
def download_artifact(public_id: str):
    artifact = _accessible_artifact(public_id)
    if not artifact or artifact.get("status") != "ready":
        return jsonify({"success": False, "error": "Archivo no encontrado o expirado"}), 404
    expires = artifact.get("expires_at")
    if expires and expires <= now_local():
        return jsonify({"success": False, "error": "El archivo expiró; puedes regenerarlo"}), 410
    path = Path(artifact["storage_path"]).resolve()
    from .ai_store import artifact_root

    try:
        path.relative_to(artifact_root())
    except ValueError:
        logger.error("Ruta de artefacto fuera del directorio privado: %s", path)
        return jsonify({"success": False, "error": "Ruta de archivo inválida"}), 500
    if not path.is_file():
        return jsonify({"success": False, "error": "Archivo no disponible; puedes regenerarlo"}), 410
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE ai_artifacts SET downloaded_at = %s WHERE id = %s", (now_local(), artifact["id"]))
        conn.commit()
    finally:
        cursor.close()
        conn.close()
    _audit("DESCARGAR_ARTEFACTO", f"Archivo IA descargado: {artifact.get('filename')}", {"artifact_id": public_id})
    response = send_file(path, mimetype=artifact["mime_type"], as_attachment=True, download_name=artifact["filename"], conditional=True)
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@bp.post("/artifacts/<public_id>/regenerate")
@requiere_permiso_dropdown(AI_PAGE, AI_SECTION, AI_PERMISSION_ARTIFACTS)
def regenerate(public_id: str):
    artifact = _accessible_artifact(public_id)
    if not artifact:
        return jsonify({"success": False, "error": "Archivo no encontrado"}), 404
    allowed, error, usage, limits = check_quota(_username(), model_name(), _roles(), artifact=True)
    if not allowed:
        return jsonify({"success": False, "error": error, "usage": usage, "limits": limits}), 429
    try:
        regenerated = regenerate_artifact(artifact, username=_username())
        increment_usage(_username(), model_name(), artifacts=1)
        _audit("REGENERAR_ARTEFACTO", "Archivo IA regenerado con datos actuales", regenerated)
        return jsonify({"success": True, "artifact": regenerated, "uses_current_data": True}), 201
    except (ValueError, PermissionError) as exc:
        return jsonify({"success": False, "error": str(exc)}), 400


@bp.get("/audit/conversations")
@requiere_permiso_dropdown(AI_PAGE, AI_SECTION, AI_PERMISSION_AUDIT)
def audit_conversations():
    return jsonify(
        {
            "success": True,
            "conversations": list_audit_conversations(
                request.args.get("username"), request.args.get("limit", 100, type=int)
            ),
        }
    )


@bp.get("/audit/conversations/<public_id>/messages")
@requiere_permiso_dropdown(AI_PAGE, AI_SECTION, AI_PERMISSION_AUDIT)
def audit_messages(public_id: str):
    conversation = get_conversation(public_id)
    if not conversation:
        return jsonify({"success": False, "error": "Conversación no encontrada"}), 404
    return jsonify(
        {
            "success": True,
            "conversation": conversation,
            "messages": list_messages(int(conversation["id"]), limit=request.args.get("limit", 100, type=int)),
            "artifacts": list_artifacts(int(conversation["id"])),
        }
    )


@bp.route("/audit/limits", methods=["GET", "PATCH"])
@requiere_permiso_dropdown(AI_PAGE, AI_SECTION, AI_PERMISSION_LIMITS)
def audit_limits():
    if request.method == "GET":
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM ai_usage_limits ORDER BY subject_type, subject_key LIMIT 500")
            return jsonify({"success": True, "limits": cursor.fetchall() or []})
        finally:
            cursor.close()
            conn.close()
    payload = request.get_json(silent=True) or {}
    subject_type = str(payload.get("subject_type") or "")
    subject_key = str(payload.get("subject_key") or "").strip()[:120]
    if subject_type not in {"user", "role"} or not subject_key:
        return jsonify({"success": False, "error": "Sujeto de cuota inválido"}), 400
    values = []
    try:
        for key in ("daily_request_limit", "daily_token_limit", "daily_artifact_limit"):
            raw = payload.get(key)
            values.append(None if raw in (None, "") else max(0, int(raw)))
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "Los límites deben ser números enteros"}), 400
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO ai_usage_limits
                (subject_type, subject_key, daily_request_limit, daily_token_limit,
                 daily_artifact_limit, active, updated_by, updated_at)
            VALUES (%s,%s,%s,%s,%s,1,%s,%s)
            ON DUPLICATE KEY UPDATE
                daily_request_limit=VALUES(daily_request_limit),
                daily_token_limit=VALUES(daily_token_limit),
                daily_artifact_limit=VALUES(daily_artifact_limit),
                active=1, updated_by=VALUES(updated_by), updated_at=VALUES(updated_at)
            """,
            (subject_type, subject_key, *values, _username(), now_local()),
        )
        conn.commit()
    except (TypeError, ValueError):
        conn.rollback()
        return jsonify({"success": False, "error": "Los límites deben ser números enteros"}), 400
    finally:
        cursor.close()
        conn.close()
    _audit("ACTUALIZAR_CUOTA", f"Cuota IA actualizada para {subject_type}:{subject_key}")
    return jsonify({"success": True})
