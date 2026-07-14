"""Persistencia MySQL y ciclo de vida del asistente IA del MES."""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from app.db import get_db_connection

logger = logging.getLogger(__name__)

AI_PAGE = "MAIN_TEMPLATE"
AI_SECTION = "Asistente IA"
AI_PERMISSION_USE = "Usar asistente IA"
AI_PERMISSION_ARTIFACTS = "Generar archivos IA"
AI_PERMISSION_AUDIT = "Auditar conversaciones IA"
AI_PERMISSION_LIMITS = "Administrar cuotas IA"

_DDL = (
    """
    CREATE TABLE IF NOT EXISTS ai_conversations (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        public_id CHAR(36) NOT NULL UNIQUE,
        user_id INT NULL,
        username VARCHAR(120) NOT NULL,
        title VARCHAR(220) NOT NULL,
        language VARCHAR(8) NOT NULL DEFAULT 'auto',
        model VARCHAR(80) NOT NULL,
        summary_text LONGTEXT NULL,
        summary_message_id BIGINT NULL,
        status VARCHAR(20) NOT NULL DEFAULT 'active',
        created_at DATETIME NOT NULL,
        updated_at DATETIME NOT NULL,
        last_message_at DATETIME NULL,
        INDEX idx_ai_conversations_user_status (username, status, updated_at),
        INDEX idx_ai_conversations_user_id (user_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS ai_messages (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        conversation_id BIGINT NOT NULL,
        client_message_id CHAR(36) NULL,
        role VARCHAR(20) NOT NULL,
        content LONGTEXT NOT NULL,
        content_json LONGTEXT NULL,
        status VARCHAR(20) NOT NULL DEFAULT 'complete',
        openai_response_id VARCHAR(180) NULL,
        model VARCHAR(80) NULL,
        input_tokens INT NOT NULL DEFAULT 0,
        output_tokens INT NOT NULL DEFAULT 0,
        estimated_cost_usd DECIMAL(14,6) NOT NULL DEFAULT 0,
        created_at DATETIME NOT NULL,
        completed_at DATETIME NULL,
        UNIQUE KEY uq_ai_message_client (conversation_id, client_message_id),
        INDEX idx_ai_messages_conversation (conversation_id, id),
        CONSTRAINT fk_ai_messages_conversation
            FOREIGN KEY (conversation_id) REFERENCES ai_conversations(id)
            ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS ai_tool_executions (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        conversation_id BIGINT NOT NULL,
        message_id BIGINT NULL,
        username VARCHAR(120) NOT NULL,
        tool_name VARCHAR(120) NOT NULL,
        arguments_json LONGTEXT NULL,
        result_summary_json LONGTEXT NULL,
        status VARCHAR(20) NOT NULL,
        row_count INT NOT NULL DEFAULT 0,
        duration_ms INT NULL,
        error_text VARCHAR(1000) NULL,
        created_at DATETIME NOT NULL,
        INDEX idx_ai_tool_conversation (conversation_id, created_at),
        INDEX idx_ai_tool_username (username, created_at),
        CONSTRAINT fk_ai_tool_conversation
            FOREIGN KEY (conversation_id) REFERENCES ai_conversations(id)
            ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS ai_usage_daily (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        username VARCHAR(120) NOT NULL,
        usage_date DATE NOT NULL,
        model VARCHAR(80) NOT NULL,
        request_count INT NOT NULL DEFAULT 0,
        artifact_count INT NOT NULL DEFAULT 0,
        input_tokens BIGINT NOT NULL DEFAULT 0,
        output_tokens BIGINT NOT NULL DEFAULT 0,
        estimated_cost_usd DECIMAL(14,6) NOT NULL DEFAULT 0,
        updated_at DATETIME NOT NULL,
        UNIQUE KEY uq_ai_usage_daily (username, usage_date, model),
        INDEX idx_ai_usage_date (usage_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS ai_usage_limits (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        subject_type VARCHAR(20) NOT NULL,
        subject_key VARCHAR(120) NOT NULL,
        daily_request_limit INT NULL,
        daily_token_limit BIGINT NULL,
        daily_artifact_limit INT NULL,
        active TINYINT(1) NOT NULL DEFAULT 1,
        updated_by VARCHAR(120) NULL,
        updated_at DATETIME NOT NULL,
        UNIQUE KEY uq_ai_usage_limit_subject (subject_type, subject_key)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS ai_knowledge_documents (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        document_key VARCHAR(160) NOT NULL,
        language VARCHAR(8) NOT NULL,
        title VARCHAR(220) NOT NULL,
        content LONGTEXT NOT NULL,
        required_page VARCHAR(190) NULL,
        required_section VARCHAR(190) NULL,
        required_button VARCHAR(190) NULL,
        active TINYINT(1) NOT NULL DEFAULT 1,
        updated_at DATETIME NOT NULL,
        UNIQUE KEY uq_ai_knowledge_key_language (document_key, language),
        INDEX idx_ai_knowledge_language (language, active)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS ai_artifacts (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        public_id CHAR(36) NOT NULL UNIQUE,
        conversation_id BIGINT NOT NULL,
        message_id BIGINT NULL,
        username VARCHAR(120) NOT NULL,
        artifact_type VARCHAR(12) NOT NULL,
        title VARCHAR(220) NOT NULL,
        filename VARCHAR(255) NOT NULL,
        storage_path VARCHAR(600) NOT NULL,
        mime_type VARCHAR(140) NOT NULL,
        size_bytes BIGINT NOT NULL DEFAULT 0,
        sha256 CHAR(64) NULL,
        query_spec_json LONGTEXT NULL,
        filters_json LONGTEXT NULL,
        source_summary_json LONGTEXT NULL,
        row_count INT NOT NULL DEFAULT 0,
        language VARCHAR(8) NOT NULL DEFAULT 'es',
        status VARCHAR(20) NOT NULL DEFAULT 'ready',
        created_at DATETIME NOT NULL,
        expires_at DATETIME NOT NULL,
        downloaded_at DATETIME NULL,
        INDEX idx_ai_artifact_user_status (username, status, created_at),
        INDEX idx_ai_artifact_conversation (conversation_id, created_at),
        INDEX idx_ai_artifact_expiry (status, expires_at),
        CONSTRAINT fk_ai_artifact_conversation
            FOREIGN KEY (conversation_id) REFERENCES ai_conversations(id)
            ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
)

_KNOWLEDGE = {
    "es": (
        "Guía rápida del MES",
        "El MES organiza Información Básica, Materiales, Producción, Proceso, "
        "Calidad y Resultados. Las opciones visibles dependen de los permisos "
        "del usuario. Usa los menús laterales para abrir módulos AJAX. Los "
        "reportes respetan los filtros de la pantalla y pueden exportarse. Si "
        "una opción no aparece, solicita el permiso al administrador.",
    ),
    "en": (
        "MES quick guide",
        "The MES groups Basic Information, Materials, Production, Process, "
        "Quality and Results. Visible options depend on user permissions. Use "
        "the side menus to open AJAX modules. Reports honor the active filters "
        "and can be exported. Ask an administrator when an option is missing.",
    ),
    "ko": (
        "MES 빠른 안내",
        "MES는 기본 정보, 자재, 생산, 공정, 품질 및 결과 메뉴로 구성됩니다. "
        "표시되는 기능은 사용자 권한에 따라 달라집니다. 왼쪽 메뉴에서 AJAX "
        "모듈을 열 수 있으며 보고서는 적용된 필터를 사용합니다. 메뉴가 보이지 "
        "않으면 관리자에게 권한을 요청하십시오.",
    ),
}

_worker_started = False
_worker_lock = threading.Lock()


def now_local() -> datetime:
    """Fecha local naive, consistente con el resto de tablas MES."""
    try:
        from app.api.shared.datetime_helpers import obtener_fecha_hora_mexico

        return obtener_fecha_hora_mexico().replace(tzinfo=None)
    except Exception:
        return datetime.now()


def json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str, separators=(",", ":"))


def json_loads(value: Any, default: Any = None) -> Any:
    if value in (None, ""):
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return default


def estimated_cost_usd(input_tokens: int = 0, output_tokens: int = 0) -> Decimal:
    """Calcula costo estimado con tarifas configurables, nunca codificadas."""
    try:
        input_rate = Decimal(os.getenv("AI_INPUT_COST_PER_MILLION", "0"))
        output_rate = Decimal(os.getenv("AI_OUTPUT_COST_PER_MILLION", "0"))
    except InvalidOperation:
        logger.warning("Tarifas IA inválidas; se registrará costo estimado 0")
        return Decimal("0")
    cost = (
        Decimal(max(0, int(input_tokens))) * input_rate
        + Decimal(max(0, int(output_tokens))) * output_rate
    ) / Decimal(1_000_000)
    return cost.quantize(Decimal("0.000001"))


def artifact_root(app_root: str | os.PathLike[str] | None = None) -> Path:
    root = Path(app_root or Path(__file__).resolve().parents[3])
    path = root / "instance" / "ai_artifacts"
    path.mkdir(parents=True, exist_ok=True)
    return path.resolve()


def init_ai_assistant_tables() -> None:
    """Crea tablas, catálogo de permisos y guía inicial de forma idempotente."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        for statement in _DDL:
            cursor.execute(statement)

        # CREATE TABLE IF NOT EXISTS no agrega columnas a instalaciones previas.
        # Estas migraciones conservan el inicializador idempotente.
        for table in ("ai_messages", "ai_usage_daily"):
            cursor.execute(f"SHOW COLUMNS FROM {table} LIKE %s", ("estimated_cost_usd",))
            if not cursor.fetchone():
                cursor.execute(
                    f"ALTER TABLE {table} ADD COLUMN estimated_cost_usd "
                    "DECIMAL(14,6) NOT NULL DEFAULT 0"
                )

        for button, description in (
            (AI_PERMISSION_USE, "Permite abrir y usar el asistente IA del MES."),
            (AI_PERMISSION_ARTIFACTS, "Permite generar Excel y PowerPoint desde consultas IA."),
            (AI_PERMISSION_AUDIT, "Permite revisar conversaciones y artefactos de otros usuarios."),
            (AI_PERMISSION_LIMITS, "Permite administrar cuotas de uso del asistente IA."),
        ):
            cursor.execute(
                """
                INSERT IGNORE INTO permisos_botones
                    (pagina, seccion, boton, descripcion, activo, departamento)
                VALUES (%s, %s, %s, %s, 1, NULL)
                """,
                (AI_PAGE, AI_SECTION, button, description),
            )

        stamp = now_local()
        for language, (title, content) in _KNOWLEDGE.items():
            cursor.execute(
                """
                INSERT INTO ai_knowledge_documents
                    (document_key, language, title, content, active, updated_at)
                VALUES ('mes_quick_guide', %s, %s, %s, 1, %s)
                ON DUPLICATE KEY UPDATE
                    title = VALUES(title), content = VALUES(content),
                    active = 1, updated_at = VALUES(updated_at)
                """,
                (language, title, content, stamp),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def cleanup_expired_artifacts() -> int:
    """Elimina binarios vencidos y conserva sus metadatos para regeneración."""
    conn = get_db_connection()
    cursor = conn.cursor()
    removed = 0
    try:
        cursor.execute(
            """
            SELECT id, storage_path FROM ai_artifacts
            WHERE status = 'ready' AND expires_at <= %s
            LIMIT 500
            """,
            (now_local(),),
        )
        rows = cursor.fetchall() or []
        root = artifact_root()
        for row in rows:
            candidate = Path(row["storage_path"]).resolve()
            try:
                candidate.relative_to(root)
                candidate.unlink(missing_ok=True)
            except (ValueError, OSError):
                logger.warning("No se pudo eliminar artefacto IA %s", candidate)
            cursor.execute(
                "UPDATE ai_artifacts SET status = 'expired' WHERE id = %s",
                (row["id"],),
            )
            removed += 1
        conn.commit()
        return removed
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def start_ai_artifact_cleanup_worker() -> None:
    global _worker_started
    if os.getenv("AI_DISABLE_CLEANUP_WORKER", "").lower() in {"1", "true", "yes"}:
        return
    with _worker_lock:
        if _worker_started:
            return
        _worker_started = True

    def _run() -> None:
        while True:
            try:
                cleanup_expired_artifacts()
            except Exception as exc:
                logger.error("Error limpiando artefactos IA: %s", exc)
            time.sleep(24 * 60 * 60)

    threading.Thread(target=_run, name="ai-artifact-cleanup", daemon=True).start()


def get_user_id(username: str) -> int | None:
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT id FROM usuarios_sistema WHERE username = %s LIMIT 1",
            (username,),
        )
        row = cursor.fetchone()
        return int(row["id"]) if row else None
    finally:
        cursor.close()
        conn.close()


def retention_deadline() -> datetime:
    days = max(1, int(os.getenv("AI_ARTIFACT_RETENTION_DAYS", "30")))
    return now_local() + timedelta(days=days)


def _fetchone(sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(sql, params)
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        cursor.close()
        conn.close()


def create_conversation(username: str, language: str, model: str) -> dict[str, Any]:
    import uuid

    public_id = str(uuid.uuid4())
    stamp = now_local()
    user_id = get_user_id(username)
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO ai_conversations
                (public_id, user_id, username, title, language, model, status,
                 created_at, updated_at)
            VALUES (%s,%s,%s,%s,%s,%s,'active',%s,%s)
            """,
            (public_id, user_id, username, "Nueva conversación", language, model, stamp, stamp),
        )
        conversation_id = int(cursor.lastrowid)
        conn.commit()
        return {
            "id": conversation_id,
            "public_id": public_id,
            "username": username,
            "title": "Nueva conversación",
            "language": language,
            "model": model,
            "status": "active",
            "created_at": stamp,
            "updated_at": stamp,
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def get_conversation(public_id: str) -> dict[str, Any] | None:
    return _fetchone(
        "SELECT * FROM ai_conversations WHERE public_id = %s LIMIT 1",
        (public_id,),
    )


def list_conversations(username: str, *, limit: int = 50, include_archived: bool = False) -> list[dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        sql = """
            SELECT public_id, title, language, model, status, created_at,
                   updated_at, last_message_at
            FROM ai_conversations WHERE username = %s
        """
        params: list[Any] = [username]
        if not include_archived:
            sql += " AND status = 'active'"
        sql += " ORDER BY updated_at DESC LIMIT %s"
        params.append(max(1, min(int(limit), 200)))
        cursor.execute(sql, tuple(params))
        return [dict(row) for row in (cursor.fetchall() or [])]
    finally:
        cursor.close()
        conn.close()


def delete_conversation(public_id: str, username: str) -> dict[str, Any] | None:
    """Elimina definitivamente un chat propio y sus artefactos privados."""
    conn = get_db_connection()
    cursor = conn.cursor()
    artifact_paths: list[str] = []
    result: dict[str, Any] | None = None
    try:
        cursor.execute(
            """
            SELECT id, public_id, title FROM ai_conversations
            WHERE public_id = %s AND username = %s
            LIMIT 1 FOR UPDATE
            """,
            (public_id, username),
        )
        conversation = cursor.fetchone()
        if not conversation:
            conn.rollback()
            return None

        conversation_id = int(conversation["id"])
        cursor.execute(
            "SELECT storage_path FROM ai_artifacts WHERE conversation_id = %s",
            (conversation_id,),
        )
        artifact_paths = [
            str(row.get("storage_path") or "")
            for row in (cursor.fetchall() or [])
            if row.get("storage_path")
        ]

        deleted: dict[str, int] = {}
        for table, key in (
            ("ai_tool_executions", "tool_executions"),
            ("ai_artifacts", "artifacts"),
            ("ai_messages", "messages"),
        ):
            cursor.execute(
                f"DELETE FROM {table} WHERE conversation_id = %s",
                (conversation_id,),
            )
            deleted[key] = max(0, int(cursor.rowcount or 0))
        cursor.execute(
            "DELETE FROM ai_conversations WHERE id = %s AND username = %s",
            (conversation_id, username),
        )
        if int(cursor.rowcount or 0) != 1:
            raise RuntimeError("No fue posible eliminar la conversación")
        conn.commit()
        result = {
            "public_id": public_id,
            "title": conversation.get("title") or "",
            **deleted,
            "files_removed": 0,
            "files_failed": 0,
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

    if result is None:
        return None
    root = artifact_root()
    for raw_path in artifact_paths:
        candidate = Path(raw_path).resolve()
        try:
            candidate.relative_to(root)
            existed = candidate.exists()
            candidate.unlink(missing_ok=True)
            if existed:
                result["files_removed"] += 1
        except (ValueError, OSError):
            result["files_failed"] += 1
            logger.warning(
                "No se pudo eliminar el archivo de la conversación IA %s",
                candidate,
            )
    return result


def update_conversation(public_id: str, username: str, *, title: str | None = None, status: str | None = None, language: str | None = None) -> bool:
    updates = ["updated_at = %s"]
    params: list[Any] = [now_local()]
    if title is not None:
        updates.append("title = %s")
        params.append(str(title).strip()[:220] or "Nueva conversación")
    if status is not None:
        if status not in {"active", "archived"}:
            raise ValueError("Estado de conversación inválido")
        updates.append("status = %s")
        params.append(status)
    if language is not None:
        if language not in {"auto", "es", "en", "ko"}:
            raise ValueError("Idioma inválido")
        updates.append("language = %s")
        params.append(language)
    params.extend((public_id, username))
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            f"UPDATE ai_conversations SET {', '.join(updates)} WHERE public_id = %s AND username = %s",
            tuple(params),
        )
        conn.commit()
        return cursor.rowcount > 0
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def add_message(
    conversation_id: int,
    role: str,
    content: str,
    *,
    client_message_id: str | None = None,
    status: str = "complete",
    model: str | None = None,
    content_json: Any = None,
) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    stamp = now_local()
    try:
        cursor.execute(
            """
            INSERT INTO ai_messages
                (conversation_id, client_message_id, role, content, content_json,
                 status, model, created_at, completed_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                conversation_id, client_message_id, role, content,
                json_dumps(content_json) if content_json is not None else None,
                status, model, stamp, stamp if status == "complete" else None,
            ),
        )
        message_id = int(cursor.lastrowid)
        cursor.execute(
            """
            UPDATE ai_conversations
            SET updated_at = %s, last_message_at = %s
            WHERE id = %s
            """,
            (stamp, stamp, conversation_id),
        )
        conn.commit()
        return message_id
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def get_message_by_client_id(conversation_id: int, client_message_id: str) -> dict[str, Any] | None:
    return _fetchone(
        "SELECT * FROM ai_messages WHERE conversation_id = %s AND client_message_id = %s LIMIT 1",
        (conversation_id, client_message_id),
    )


def update_message(
    message_id: int,
    *,
    content: str,
    status: str,
    response_id: str | None = None,
    input_tokens: int = 0,
    output_tokens: int = 0,
    content_json: Any = None,
) -> None:
    estimated_cost = estimated_cost_usd(input_tokens, output_tokens)
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            UPDATE ai_messages
            SET content = %s, content_json = %s, status = %s,
                openai_response_id = %s, input_tokens = %s, output_tokens = %s,
                estimated_cost_usd = %s, completed_at = %s
            WHERE id = %s
            """,
            (
                content,
                json_dumps(content_json) if content_json is not None else None,
                status, response_id, int(input_tokens), int(output_tokens), estimated_cost,
                now_local(), message_id,
            ),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def list_messages(conversation_id: int, *, before_id: int | None = None, limit: int = 50) -> list[dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        sql = """
            SELECT id, client_message_id, role, content, content_json, status,
                   model, input_tokens, output_tokens, estimated_cost_usd,
                   created_at, completed_at
            FROM ai_messages WHERE conversation_id = %s
        """
        params: list[Any] = [conversation_id]
        if before_id:
            sql += " AND id < %s"
            params.append(int(before_id))
        sql += " ORDER BY id DESC LIMIT %s"
        params.append(max(1, min(int(limit), 200)))
        cursor.execute(sql, tuple(params))
        rows = [dict(row) for row in (cursor.fetchall() or [])]
        rows.reverse()
        for row in rows:
            row["content_json"] = json_loads(row.get("content_json"), None)
        return rows
    finally:
        cursor.close()
        conn.close()


def recent_model_messages(conversation_id: int, limit: int = 12) -> list[dict[str, str]]:
    rows = list_messages(conversation_id, limit=limit)
    return [
        {"role": row["role"], "content": row["content"]}
        for row in rows
        if row.get("role") in {"user", "assistant"} and row.get("status") in {"complete", "streaming"}
    ]


def refresh_conversation_summary(conversation_id: int, keep_recent: int = 12) -> None:
    """Mantiene un resumen local compacto de mensajes antiguos sin otra llamada API."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT id, role, content FROM ai_messages
            WHERE conversation_id = %s AND status = 'complete'
              AND id < COALESCE((
                  SELECT MIN(recent.id) FROM (
                      SELECT id FROM ai_messages
                      WHERE conversation_id = %s AND status = 'complete'
                      ORDER BY id DESC LIMIT %s
                  ) AS recent
              ), 9223372036854775807)
            ORDER BY id ASC
            """,
            (conversation_id, conversation_id, int(keep_recent)),
        )
        rows = cursor.fetchall() or []
        if not rows:
            return
        pieces = []
        for row in rows[-40:]:
            label = "Usuario" if row.get("role") == "user" else "Asistente"
            content = " ".join(str(row.get("content") or "").split())[:500]
            if content:
                pieces.append(f"{label}: {content}")
        summary = "\n".join(pieces)[-6000:]
        cursor.execute(
            """
            UPDATE ai_conversations
            SET summary_text = %s, summary_message_id = %s, updated_at = %s
            WHERE id = %s
            """,
            (summary, rows[-1]["id"], now_local(), conversation_id),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def record_tool_execution(
    *,
    conversation_id: int,
    message_id: int | None,
    username: str,
    tool_name: str,
    arguments: Any,
    result_summary: Any,
    status: str,
    row_count: int = 0,
    duration_ms: int | None = None,
    error_text: str | None = None,
) -> None:
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO ai_tool_executions
                (conversation_id, message_id, username, tool_name,
                 arguments_json, result_summary_json, status, row_count,
                 duration_ms, error_text, created_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                conversation_id, message_id, username, tool_name,
                json_dumps(arguments), json_dumps(result_summary), status,
                int(row_count or 0), duration_ms, str(error_text or "")[:1000] or None,
                now_local(),
            ),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def get_pending_plan_confirmation(
    conversation_id: int,
    username: str,
) -> dict[str, Any] | None:
    """Recupera la última acción del plan preparada y todavía no ejecutada.

    El token permanece en MySQL y nunca necesita enviarse al navegador ni al
    proveedor de IA. Una ejecución exitosa posterior consume lógicamente la
    preparación y evita repetir la misma operación.
    """
    prepare_to_execute = {
        "plan_importar_preparar": "plan_importar_ejecutar",
        "plan_generar_preparar": "plan_generar_ejecutar",
    }
    relevant = tuple(prepare_to_execute) + tuple(prepare_to_execute.values())
    placeholders = ",".join(["%s"] * len(relevant))
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            f"""
            SELECT tool_name, result_summary_json, status, created_at
            FROM ai_tool_executions
            WHERE conversation_id = %s AND username = %s
              AND tool_name IN ({placeholders})
            ORDER BY id DESC
            LIMIT 20
            """,
            (int(conversation_id), username, *relevant),
        )
        rows = cursor.fetchall() or []
    finally:
        cursor.close()
        conn.close()

    for row in rows:
        if str(row.get("status") or "") != "success":
            continue
        tool_name = str(row.get("tool_name") or "")
        if tool_name in prepare_to_execute.values():
            return None
        execute_tool = prepare_to_execute.get(tool_name)
        if not execute_tool:
            continue
        result = json_loads(row.get("result_summary_json"), {}) or {}
        token = str(result.get("confirm_token") or "")
        if not token:
            return None
        return {
            "prepare_tool": tool_name,
            "execute_tool": execute_tool,
            "confirm_token": token,
            "prepared_at": row.get("created_at"),
        }
    return None


def get_usage(username: str, model: str) -> dict[str, Any]:
    row = _fetchone(
        """
        SELECT request_count, artifact_count, input_tokens, output_tokens,
               estimated_cost_usd
        FROM ai_usage_daily
        WHERE username = %s AND usage_date = CURDATE() AND model = %s
        """,
        (username, model),
    )
    return row or {
        "request_count": 0, "artifact_count": 0, "input_tokens": 0,
        "output_tokens": 0, "estimated_cost_usd": Decimal("0"),
    }


def effective_limits(username: str, roles: list[str] | None = None) -> dict[str, int]:
    limits = {
        "daily_request_limit": int(os.getenv("AI_DAILY_REQUEST_LIMIT", "50")),
        "daily_token_limit": int(os.getenv("AI_DAILY_TOKEN_LIMIT", "250000")),
        "daily_artifact_limit": int(os.getenv("AI_DAILY_ARTIFACT_LIMIT", "10")),
    }
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        candidates = [("role", role) for role in (roles or [])] + [("user", username)]
        for subject_type, subject_key in candidates:
            cursor.execute(
                """
                SELECT daily_request_limit, daily_token_limit, daily_artifact_limit
                FROM ai_usage_limits
                WHERE subject_type = %s AND subject_key = %s AND active = 1
                LIMIT 1
                """,
                (subject_type, subject_key),
            )
            row = cursor.fetchone()
            if row:
                for key in limits:
                    if row.get(key) is not None:
                        limits[key] = int(row[key])
        return limits
    finally:
        cursor.close()
        conn.close()


def check_quota(username: str, model: str, roles: list[str] | None = None, *, artifact: bool = False) -> tuple[bool, str | None, dict[str, Any], dict[str, int]]:
    usage = get_usage(username, model)
    limits = effective_limits(username, roles)
    if int(usage["request_count"]) >= limits["daily_request_limit"]:
        return False, "Límite diario de solicitudes alcanzado", usage, limits
    if int(usage["input_tokens"]) + int(usage["output_tokens"]) >= limits["daily_token_limit"]:
        return False, "Límite diario de tokens alcanzado", usage, limits
    if artifact and int(usage["artifact_count"]) >= limits["daily_artifact_limit"]:
        return False, "Límite diario de archivos alcanzado", usage, limits
    return True, None, usage, limits


def increment_usage(username: str, model: str, *, requests: int = 0, artifacts: int = 0, input_tokens: int = 0, output_tokens: int = 0) -> None:
    stamp = now_local()
    estimated_cost = estimated_cost_usd(input_tokens, output_tokens)
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO ai_usage_daily
                (username, usage_date, model, request_count, artifact_count,
                 input_tokens, output_tokens, estimated_cost_usd, updated_at)
            VALUES (%s, CURDATE(), %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                request_count = request_count + VALUES(request_count),
                artifact_count = artifact_count + VALUES(artifact_count),
                input_tokens = input_tokens + VALUES(input_tokens),
                output_tokens = output_tokens + VALUES(output_tokens),
                estimated_cost_usd = estimated_cost_usd + VALUES(estimated_cost_usd),
                updated_at = VALUES(updated_at)
            """,
            (username, model, int(requests), int(artifacts), int(input_tokens),
             int(output_tokens), estimated_cost, stamp),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def list_audit_conversations(username: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        sql = """
            SELECT public_id, username, title, language, model, status,
                   created_at, updated_at, last_message_at
            FROM ai_conversations WHERE 1=1
        """
        params: list[Any] = []
        if username:
            sql += " AND username LIKE %s"
            params.append(f"%{username[:120]}%")
        sql += " ORDER BY updated_at DESC LIMIT %s"
        params.append(max(1, min(int(limit), 200)))
        cursor.execute(sql, tuple(params))
        return [dict(row) for row in (cursor.fetchall() or [])]
    finally:
        cursor.close()
        conn.close()
