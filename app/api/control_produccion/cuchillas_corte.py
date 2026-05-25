"""Endpoints HTTP y workers del modulo Control de cuchillas de corte (ASSY).

Migrado desde `app/routes.py` (2026-05-25). Sin cambios funcionales.

Contiene:
  - Constantes CUCHILLAS_* (permisos, source metric, intervalo de sync)
  - Helpers `_cuchillas_*` (normalizacion, conversion, queries de plan/config/sesion)
  - Wrapper `_cuchillas_execute_raw` (con fallback a `execute_query`)
  - Worker horario `_cuchillas_hourly_sync_loop` y `iniciar_cuchillas_hourly_sync_worker`
  - Bootstrap `crear_tablas_cuchillas_corte` + `crear_trigger_cuchillas_corte_plan_main`
  - 17 rutas:
        GET  /control-cuchillas-corte-ajax       -> render HTML del modulo
        GET  /api/cuchillas-corte/lineas
        GET  /api/cuchillas-corte/dashboard
        GET  /api/cuchillas-corte/config
        POST /api/cuchillas-corte/config
        GET  /api/cuchillas-corte/config-modelo
        POST /api/cuchillas-corte/config-modelo
        POST /api/cuchillas-corte/config-modelo/eliminar
        GET  /api/cuchillas-corte/modelos-linea
        POST /api/cuchillas-corte/sesion/iniciar
        POST /api/cuchillas-corte/sesion/reemplazar
        GET  /api/cuchillas-corte/sesiones
        POST /api/cuchillas-corte/sesion/eliminar
        GET  /api/cuchillas-corte/estado
        GET  /api/cuchillas-corte/diagnostico
        POST /api/cuchillas-corte/recalcular
        GET  /api/cuchillas-corte/eventos

Reexportado desde `app/routes.py` como `from .api.control_produccion.cuchillas_corte import *`
para preservar consumidores legacy (`startup_init.py`, `app.api.shared`).
"""

import os
import threading
import time
from datetime import date, datetime
from decimal import Decimal

from functools import wraps

from flask import Blueprint, jsonify, render_template, request, session

# Importar directo desde modulos fuente (NO desde app.api.shared) para
# evitar import circular: shared -> routes -> cuchillas_corte -> shared.
from app.auth_system import AuthSystem
from app.db_mysql import execute_query, get_db_connection


# `login_requerido` y `requiere_permiso_dropdown` viven en `app.routes`.
# Se importan dentro de las funciones que los necesitan (tarde) para evitar
# que cuchillas_corte arrastre app.routes al ser importado por shared.
def login_requerido(f):
    """Proxy del decorador real definido en `app.routes`."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from app import routes as _r
        return _r.login_requerido(f)(*args, **kwargs)

    return decorated_function


def requiere_permiso_dropdown(pagina, seccion, boton):
    """Proxy del decorador real definido en `app.routes`."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from app import routes as _r
            real_decorator = _r.requiere_permiso_dropdown(pagina, seccion, boton)
            return real_decorator(f)(*args, **kwargs)

        return decorated_function

    return decorator


def _env_flag(name, default=False):
    val = os.getenv(name)
    if val is None:
        return default
    return str(val).strip().lower() in ("1", "true", "yes", "on", "si")


bp = Blueprint("control_produccion_cuchillas_corte", __name__)


# =============================
# CONTROL DE CUCHILLAS DE CORTE (ASSY)
# =============================

CUCHILLAS_PERMISO_PAGINA = "LISTA_CONTROLDEPRODUCCION"
CUCHILLAS_PERMISO_SECCION = "Control de plan de produccion"
CUCHILLAS_PERMISO_BOTON = "Control de cuchillas de corte"
CUCHILLAS_SOURCE_DEFAULT = "PRODUCED_COUNT"
CUCHILLAS_SOURCE_ALLOWED = {"PRODUCED_COUNT", "PLAN_COUNT"}
CUCHILLAS_HOURLY_SYNC_SECONDS = max(
    60, int(os.getenv("CUCHILLAS_HOURLY_SYNC_SECONDS", "3600"))
)
_cuchillas_sync_thread = None
_cuchillas_sync_lock = threading.Lock()


def _cuchillas_normalize_source_metric(value, default=CUCHILLAS_SOURCE_DEFAULT):
    source = str(value or "").strip().upper()
    if source in CUCHILLAS_SOURCE_ALLOWED:
        return source
    return default


def _cuchillas_get_metric_value(plan_activo, source_metric):
    plan = plan_activo or {}
    normalized = _cuchillas_normalize_source_metric(source_metric)
    if normalized == "PLAN_COUNT":
        return _cuchillas_to_float(plan.get("plan_count"), 0.0) or 0.0
    return _cuchillas_to_float(plan.get("produced_count"), 0.0) or 0.0


def _cuchillas_bool_from_int(value):
    try:
        return int(value or 0) == 1
    except Exception:
        return False


def _cuchillas_to_float(value, default=None):
    try:
        if value is None:
            return default
        if isinstance(value, str):
            value = value.strip().replace(",", "")
            if value == "":
                return default
        return float(value)
    except Exception:
        return default


def _cuchillas_bool_param(value):
    return str(value or "").strip().lower() in ("1", "true", "yes", "si", "on")


def _cuchillas_row_to_json(row):
    if not row:
        return None
    if not isinstance(row, dict):
        return row
    parsed = {}
    for k, v in row.items():
        if isinstance(v, datetime):
            parsed[k] = v.strftime("%Y-%m-%d %H:%M:%S")
        elif isinstance(v, date):
            parsed[k] = v.strftime("%Y-%m-%d")
        elif isinstance(v, Decimal):
            parsed[k] = float(v)
        else:
            parsed[k] = v
    return parsed


def _cuchillas_rows_to_json(rows):
    return [_cuchillas_row_to_json(r) for r in (rows or [])]


def _cuchillas_execute_raw(query, params=None, fetch=None):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if conn is None:
            return execute_query(query, params, fetch=fetch)

        cursor = conn.cursor()
        if params is None:
            cursor.execute(query)
        else:
            cursor.execute(query, params)

        if fetch == "one":
            return cursor.fetchone()
        if fetch == "all":
            return cursor.fetchall()

        conn.commit()
        return cursor.rowcount
    finally:
        try:
            if cursor:
                cursor.close()
        except Exception:
            pass
        try:
            if conn:
                conn.close()
        except Exception:
            pass


def _cuchillas_usuario_actual():
    usuario = session.get("usuario") or session.get("username") or "sistema"
    usuario = str(usuario).strip() if usuario else "sistema"
    return usuario[:64] if usuario else "sistema"


def _cuchillas_get_plan_activo_por_linea(linea):
    if not linea:
        return None
    query = """
        SELECT
            id, lot_no, line, part_no, model_code, process, status,
            COALESCE(plan_count, 0) AS plan_count,
            COALESCE(produced_count, 0) AS produced_count,
            created_at, updated_at
        FROM plan_main
        WHERE line = %s
          AND status IN ('EN PROGRESO', 'PAUSADO', 'PLAN')
        ORDER BY
            CASE status
                WHEN 'EN PROGRESO' THEN 1
                WHEN 'PAUSADO' THEN 2
                WHEN 'PLAN' THEN 3
                ELSE 9
            END,
            COALESCE(updated_at, created_at) DESC,
            created_at DESC,
            id DESC
        LIMIT 1
    """
    row = execute_query(query, (linea,), fetch="one")
    return _cuchillas_row_to_json(row)


def _cuchillas_get_config_por_linea(linea):
    if not linea:
        return None
    query = """
        SELECT
            id, linea, pcb_qty, cut_qty, prealert_pct, source_metric, activo, updated_at
        FROM cuchillas_corte_config_linea
        WHERE linea = %s
        LIMIT 1
    """
    row = execute_query(query, (linea,), fetch="one")
    parsed = _cuchillas_row_to_json(row)
    if not parsed:
        return None
    parsed["source_metric"] = _cuchillas_normalize_source_metric(
        parsed.get("source_metric"), CUCHILLAS_SOURCE_DEFAULT
    )
    parsed["activo"] = 1 if _cuchillas_bool_from_int(parsed.get("activo")) else 0
    return parsed


def _cuchillas_get_config_por_modelo(linea, model_code):
    if not linea or not model_code:
        return None
    row = execute_query(
        """
        SELECT id, linea, model_code, pcb_qty, cut_qty, activo, updated_at
        FROM cuchillas_corte_config_modelo
        WHERE linea = %s AND model_code = %s AND activo = 1
        LIMIT 1
        """,
        (str(linea).strip(), str(model_code).strip()),
        fetch="one",
    )
    return _cuchillas_row_to_json(row)


def _cuchillas_get_configs_modelo_por_linea(linea):
    if not linea:
        return {}
    rows = (
        execute_query(
            """
        SELECT model_code, pcb_qty, cut_qty
        FROM cuchillas_corte_config_modelo
        WHERE linea = %s AND activo = 1
        """,
            (str(linea).strip(),),
            fetch="all",
        )
        or []
    )
    config_map = {}
    for r in rows:
        rd = _cuchillas_row_to_json(r)
        mc = str(rd.get("model_code", "")).strip()
        if mc:
            config_map[mc] = rd
    return config_map


def _cuchillas_get_effective_config(linea, model_code):
    model_cfg = (
        _cuchillas_get_config_por_modelo(linea, model_code) if model_code else None
    )
    if model_cfg:
        return {
            "pcb_qty": model_cfg.get("pcb_qty"),
            "cut_qty": model_cfg.get("cut_qty"),
            "config_tipo": "MODELO",
            "config_model_code": model_code,
        }
    line_cfg = _cuchillas_get_config_por_linea(linea)
    if line_cfg and _cuchillas_bool_from_int(line_cfg.get("activo")):
        return {
            "pcb_qty": line_cfg.get("pcb_qty"),
            "cut_qty": line_cfg.get("cut_qty"),
            "config_tipo": "LINEA",
            "config_model_code": None,
        }
    return None


def _cuchillas_get_sesion_por_linea(linea):
    if not linea:
        return None
    query = """
        SELECT
            s.id, s.linea, s.blade_code, s.max_cortes, s.consumo_cortes,
            s.last_lot_no, s.last_input_snapshot, s.estado,
            s.prealert_emitida, s.vencida_emitida,
            s.started_at, s.expired_at, s.ended_at, s.last_hourly_sync_at, s.created_by, s.updated_at,
            c.pcb_qty, c.cut_qty, c.prealert_pct, c.source_metric, c.activo AS config_activo
        FROM cuchillas_corte_sesiones s
        LEFT JOIN cuchillas_corte_config_linea c
            ON c.linea = s.linea
        WHERE s.linea = %s
        ORDER BY
            CASE s.estado
                WHEN 'ACTIVA' THEN 1
                WHEN 'VENCIDA' THEN 2
                WHEN 'REEMPLAZADA' THEN 3
                ELSE 9
            END,
            s.started_at DESC,
            s.id DESC
        LIMIT 1
    """
    row = execute_query(query, (linea,), fetch="one")
    parsed = _cuchillas_row_to_json(row)
    if not parsed:
        return None

    consumo = _cuchillas_to_float(parsed.get("consumo_cortes"), 0.0) or 0.0
    max_cortes = _cuchillas_to_float(parsed.get("max_cortes"), 0.0) or 0.0
    restante = max(0.0, max_cortes - consumo)
    pct_uso = round((consumo / max_cortes) * 100.0, 2) if max_cortes > 0 else 0.0
    pcb_qty = _cuchillas_to_float(parsed.get("pcb_qty"), 0.0) or 0.0
    cut_qty = _cuchillas_to_float(parsed.get("cut_qty"), 0.0) or 0.0
    factor_corte = round((cut_qty / pcb_qty), 6) if pcb_qty > 0 else None
    config_activo = 1 if _cuchillas_bool_from_int(parsed.get("config_activo")) else 0
    source_metric = _cuchillas_normalize_source_metric(
        parsed.get("source_metric"), CUCHILLAS_SOURCE_DEFAULT
    )

    parsed["consumo_cortes"] = consumo
    parsed["max_cortes"] = max_cortes
    parsed["restante_cortes"] = restante
    parsed["porcentaje_uso"] = pct_uso
    parsed["factor_corte"] = factor_corte
    parsed["config_activo"] = config_activo
    parsed["source_metric"] = source_metric
    return parsed


def _cuchillas_get_historial_sesiones(linea=None, limit=100):
    try:
        limit_num = int(limit or 100)
    except Exception:
        limit_num = 100
    limit_num = max(1, min(limit_num, 500))

    where = []
    params = []
    linea_norm = str(linea or "").strip()
    if linea_norm:
        where.append("s.linea = %s")
        params.append(linea_norm)

    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    query = f"""
        SELECT
            s.id, s.linea, s.blade_code, s.max_cortes, s.consumo_cortes,
            s.last_lot_no, s.last_input_snapshot, s.estado,
            s.prealert_emitida, s.vencida_emitida,
            s.started_at, s.expired_at, s.ended_at, s.last_hourly_sync_at, s.created_by, s.updated_at,
            c.pcb_qty, c.cut_qty, c.prealert_pct, c.source_metric, c.activo AS config_activo
        FROM cuchillas_corte_sesiones s
        LEFT JOIN cuchillas_corte_config_linea c
            ON c.linea = s.linea
        {where_sql}
        ORDER BY s.started_at DESC, s.id DESC
        LIMIT %s
    """
    params.append(limit_num)
    rows = execute_query(query, tuple(params), fetch="all") or []

    historial = []
    for row in rows:
        parsed = _cuchillas_row_to_json(row)
        if not parsed:
            continue

        consumo = _cuchillas_to_float(parsed.get("consumo_cortes"), 0.0) or 0.0
        max_cortes = _cuchillas_to_float(parsed.get("max_cortes"), 0.0) or 0.0
        restante = max(0.0, max_cortes - consumo)
        pct_uso = round((consumo / max_cortes) * 100.0, 2) if max_cortes > 0 else 0.0
        pcb_qty = _cuchillas_to_float(parsed.get("pcb_qty"), 0.0) or 0.0
        cut_qty = _cuchillas_to_float(parsed.get("cut_qty"), 0.0) or 0.0
        factor_corte = round((cut_qty / pcb_qty), 6) if pcb_qty > 0 else None

        parsed["consumo_cortes"] = consumo
        parsed["max_cortes"] = max_cortes
        parsed["restante_cortes"] = restante
        parsed["porcentaje_uso"] = pct_uso
        parsed["factor_corte"] = factor_corte
        parsed["source_metric"] = _cuchillas_normalize_source_metric(
            parsed.get("source_metric"), CUCHILLAS_SOURCE_DEFAULT
        )
        parsed["config_activo"] = (
            1 if _cuchillas_bool_from_int(parsed.get("config_activo")) else 0
        )
        historial.append(parsed)

    return historial


def _cuchillas_crear_sesion(linea, blade_code, max_cortes, created_by, config=None):
    cfg = config or _cuchillas_get_config_por_linea(linea) or {}
    source_metric = _cuchillas_normalize_source_metric(
        cfg.get("source_metric"), CUCHILLAS_SOURCE_DEFAULT
    )
    plan_activo = _cuchillas_get_plan_activo_por_linea(linea)
    baseline_lot = plan_activo.get("lot_no") if plan_activo else None
    baseline_input = _cuchillas_get_metric_value(plan_activo, source_metric)

    insert_sql = """
        INSERT INTO cuchillas_corte_sesiones (
            linea, blade_code, max_cortes, consumo_cortes,
            last_lot_no, last_input_snapshot,
            estado, prealert_emitida, vencida_emitida,
            started_at, created_by, updated_at
        )
        VALUES (
            %s, %s, %s, 0,
            %s, %s,
            'ACTIVA', 0, 0,
            %s, %s, %s
        )
    """
    mexico_now = AuthSystem.get_mexico_time_mysql()
    execute_query(
        insert_sql,
        (
            linea,
            blade_code,
            max_cortes,
            baseline_lot,
            baseline_input,
            mexico_now,
            created_by,
            mexico_now,
        ),
    )

    sesion_row = execute_query(
        """
        SELECT
            id, linea, blade_code, max_cortes, consumo_cortes,
            last_lot_no, last_input_snapshot, estado,
            prealert_emitida, vencida_emitida,
            started_at, expired_at, ended_at, last_hourly_sync_at, created_by, updated_at
        FROM cuchillas_corte_sesiones
        WHERE linea = %s
          AND blade_code = %s
        ORDER BY id DESC
        LIMIT 1
        """,
        (linea, blade_code),
        fetch="one",
    )
    sesion = _cuchillas_row_to_json(sesion_row)

    if sesion and sesion.get("id"):
        evento_sql = """
            INSERT INTO cuchillas_corte_eventos (
                sesion_id, linea, lot_no, event_type,
                consumo_cortes, max_cortes, porcentaje_uso, mensaje,
                pendiente_externo, created_at
            )
            VALUES (
                %s, %s, %s, 'INFO',
                0, %s, 0,
                %s, 0, %s
            )
        """
        mensaje = (
            f"Sesion iniciada para cuchilla {blade_code} (fuente: {source_metric})"
        )
        execute_query(
            evento_sql,
            (sesion["id"], linea, baseline_lot, max_cortes, mensaje, mexico_now),
        )

    return sesion


def _cuchillas_insert_evento(
    sesion_id,
    linea,
    lot_no,
    event_type,
    consumo_cortes,
    max_cortes,
    porcentaje_uso,
    mensaje,
    pendiente_externo=1,
):
    execute_query(
        """
        INSERT INTO cuchillas_corte_eventos (
            sesion_id, linea, lot_no, event_type,
            consumo_cortes, max_cortes, porcentaje_uso, mensaje,
            pendiente_externo, created_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            sesion_id,
            linea,
            lot_no,
            event_type,
            consumo_cortes,
            max_cortes,
            porcentaje_uso,
            mensaje,
            1 if _cuchillas_bool_from_int(pendiente_externo) else 0,
            AuthSystem.get_mexico_time_mysql(),
        ),
    )


def _cuchillas_source_sum_since_session(linea, started_at, source_metric):
    if not linea:
        return 0.0

    metric = _cuchillas_normalize_source_metric(source_metric, CUCHILLAS_SOURCE_DEFAULT)
    metric_col = "plan_count" if metric == "PLAN_COUNT" else "produced_count"

    started_ref = started_at
    if isinstance(started_ref, datetime):
        started_ref = started_ref.strftime("%Y-%m-%d %H:%M:%S")
    elif isinstance(started_ref, date):
        started_ref = started_ref.strftime("%Y-%m-%d")
    elif started_ref is None:
        started_ref = AuthSystem.get_mexico_time_mysql()
    else:
        started_ref = str(started_ref)

    mexico_today = AuthSystem.get_mexico_time().strftime("%Y-%m-%d")
    row = (
        execute_query(
            f"""
        SELECT COALESCE(SUM(COALESCE({metric_col}, 0)), 0) AS total_metric
        FROM plan_main
        WHERE line = %s
          AND COALESCE(DATE(working_date), DATE(created_at), %s) >= DATE(%s)
          AND COALESCE(DATE(working_date), DATE(created_at), %s) <= %s
          AND COALESCE(status, '') <> 'CANCELADO'
        """,
            (linea, mexico_today, started_ref, mexico_today, mexico_today),
            fetch="one",
        )
        or {}
    )
    return _cuchillas_to_float((row or {}).get("total_metric"), 0.0) or 0.0


def _cuchillas_consumo_ponderado_since_session(
    linea, started_at, source_metric, default_pcb_qty, default_cut_qty
):
    if not linea:
        return 0.0

    metric = _cuchillas_normalize_source_metric(source_metric, CUCHILLAS_SOURCE_DEFAULT)
    metric_col = "plan_count" if metric == "PLAN_COUNT" else "produced_count"

    started_ref = started_at
    if isinstance(started_ref, datetime):
        started_ref = started_ref.strftime("%Y-%m-%d %H:%M:%S")
    elif isinstance(started_ref, date):
        started_ref = started_ref.strftime("%Y-%m-%d")
    elif started_ref is None:
        started_ref = AuthSystem.get_mexico_time_mysql()
    else:
        started_ref = str(started_ref)

    mexico_today = AuthSystem.get_mexico_time().strftime("%Y-%m-%d")

    rows = (
        execute_query(
            f"""
        SELECT COALESCE(model_code, '') AS model_code,
               COALESCE(SUM(COALESCE({metric_col}, 0)), 0) AS total_metric
        FROM plan_main
        WHERE line = %s
          AND COALESCE(DATE(working_date), DATE(created_at), %s) >= DATE(%s)
          AND COALESCE(DATE(working_date), DATE(created_at), %s) <= %s
          AND COALESCE(status, '') <> 'CANCELADO'
        GROUP BY COALESCE(model_code, '')
        """,
            (linea, mexico_today, started_ref, mexico_today, mexico_today),
            fetch="all",
        )
        or []
    )

    config_map = _cuchillas_get_configs_modelo_por_linea(linea)

    total_consumo = 0.0
    for row_data in rows:
        r = _cuchillas_row_to_json(row_data)
        mc = str(r.get("model_code", "")).strip()
        metric_val = _cuchillas_to_float(r.get("total_metric"), 0.0) or 0.0

        if mc and mc in config_map:
            pcb = _cuchillas_to_float(config_map[mc].get("pcb_qty"), 0.0) or 0.0
            cut = _cuchillas_to_float(config_map[mc].get("cut_qty"), 0.0)
            if cut is None:
                cut = 0.0
        else:
            pcb = default_pcb_qty
            cut = default_cut_qty

        if cut <= 0 or pcb <= 0:
            continue

        factor = cut / pcb
        total_consumo += metric_val * factor

    return max(total_consumo, 0.0)


def _cuchillas_sync_linea_consumo(linea, force=False, reason="hourly"):
    linea_norm = str(linea or "").strip()
    if not linea_norm:
        return {"linea": linea_norm, "status": "LINEA_INVALIDA"}

    sesion_row = execute_query(
        """
        SELECT
            s.id, s.linea, s.blade_code, s.max_cortes, s.consumo_cortes,
            s.last_lot_no, s.last_input_snapshot, s.estado,
            s.prealert_emitida, s.vencida_emitida,
            s.started_at, s.expired_at, s.ended_at, s.last_hourly_sync_at, s.created_by, s.updated_at,
            c.pcb_qty, c.cut_qty, c.prealert_pct, c.source_metric, c.activo AS config_activo
        FROM cuchillas_corte_sesiones s
        LEFT JOIN cuchillas_corte_config_linea c
            ON c.linea = s.linea
        WHERE s.linea = %s
          AND s.estado = 'ACTIVA'
        ORDER BY s.started_at DESC, s.id DESC
        LIMIT 1
        """,
        (linea_norm,),
        fetch="one",
    )
    sesion = _cuchillas_row_to_json(sesion_row)
    if not sesion:
        return {"linea": linea_norm, "status": "SIN_SESION_ACTIVA"}

    if not _cuchillas_bool_from_int(sesion.get("config_activo")):
        return {
            "linea": linea_norm,
            "status": "CONFIG_INACTIVA",
            "sesion_id": sesion.get("id"),
        }

    now_dt = AuthSystem.get_mexico_time()
    last_sync = sesion.get("last_hourly_sync_at")
    if not force and isinstance(last_sync, str):
        try:
            last_sync = datetime.strptime(last_sync, "%Y-%m-%d %H:%M:%S")
        except Exception:
            last_sync = None
    if not force and isinstance(last_sync, datetime):
        if last_sync.tzinfo is None:
            elapsed = (now_dt.replace(tzinfo=None) - last_sync).total_seconds()
        else:
            elapsed = (now_dt - last_sync).total_seconds()
        if elapsed < CUCHILLAS_HOURLY_SYNC_SECONDS:
            return {
                "linea": linea_norm,
                "status": "SKIPPED_INTERVAL",
                "sesion_id": sesion.get("id"),
                "elapsed_seconds": elapsed,
            }

    source_metric = _cuchillas_normalize_source_metric(
        sesion.get("source_metric"), CUCHILLAS_SOURCE_DEFAULT
    )
    source_total = _cuchillas_source_sum_since_session(
        linea=linea_norm,
        started_at=sesion.get("started_at"),
        source_metric=source_metric,
    )

    pcb_qty = _cuchillas_to_float(sesion.get("pcb_qty"), 0.0) or 0.0
    cut_qty = _cuchillas_to_float(sesion.get("cut_qty"), 0.0) or 0.0
    max_cortes = _cuchillas_to_float(sesion.get("max_cortes"), 0.0) or 0.0
    if pcb_qty <= 0 or cut_qty <= 0 or max_cortes <= 0:
        return {
            "linea": linea_norm,
            "status": "CONFIG_INVALIDA",
            "sesion_id": sesion.get("id"),
        }

    nuevo_consumo = _cuchillas_consumo_ponderado_since_session(
        linea=linea_norm,
        started_at=sesion.get("started_at"),
        source_metric=source_metric,
        default_pcb_qty=pcb_qty,
        default_cut_qty=cut_qty,
    )
    consumo_prev = _cuchillas_to_float(sesion.get("consumo_cortes"), 0.0) or 0.0
    consumo_changed = abs(nuevo_consumo - consumo_prev) > 0.0001
    porcentaje_uso = (
        round((nuevo_consumo / max_cortes) * 100.0, 2) if max_cortes > 0 else 0.0
    )
    plan_activo = _cuchillas_get_plan_activo_por_linea(linea_norm)
    lot_no = (plan_activo or {}).get("lot_no") or sesion.get("last_lot_no")
    mexico_now = AuthSystem.get_mexico_time_mysql()

    execute_query(
        """
        UPDATE cuchillas_corte_sesiones
        SET consumo_cortes = %s,
            last_input_snapshot = %s,
            last_lot_no = %s,
            last_hourly_sync_at = %s,
            updated_at = %s
        WHERE id = %s
          AND estado = 'ACTIVA'
        """,
        (nuevo_consumo, source_total, lot_no, mexico_now, mexico_now, sesion.get("id")),
    )

    prealert_pct = _cuchillas_to_float(sesion.get("prealert_pct"), 90.0) or 90.0
    prealert_threshold = max_cortes * (prealert_pct / 100.0)
    prealert_emitida = _cuchillas_bool_from_int(sesion.get("prealert_emitida"))
    vencida_emitida = _cuchillas_bool_from_int(sesion.get("vencida_emitida"))

    if not prealert_emitida and nuevo_consumo >= prealert_threshold:
        _cuchillas_insert_evento(
            sesion_id=sesion.get("id"),
            linea=linea_norm,
            lot_no=lot_no,
            event_type="PREALERTA",
            consumo_cortes=nuevo_consumo,
            max_cortes=max_cortes,
            porcentaje_uso=porcentaje_uso,
            mensaje=f"Prealerta de cuchilla en linea {linea_norm} ({porcentaje_uso}% de uso)",
            pendiente_externo=1,
        )
        execute_query(
            """
            UPDATE cuchillas_corte_sesiones
            SET prealert_emitida = 1, updated_at = %s
            WHERE id = %s
            """,
            (mexico_now, sesion.get("id")),
        )

    if not vencida_emitida and nuevo_consumo >= max_cortes:
        _cuchillas_insert_evento(
            sesion_id=sesion.get("id"),
            linea=linea_norm,
            lot_no=lot_no,
            event_type="VENCIDA",
            consumo_cortes=nuevo_consumo,
            max_cortes=max_cortes,
            porcentaje_uso=porcentaje_uso,
            mensaje=f"Cuchilla vencida en linea {linea_norm} ({porcentaje_uso}% de uso)",
            pendiente_externo=1,
        )
        execute_query(
            """
            UPDATE cuchillas_corte_sesiones
            SET estado = 'VENCIDA',
                vencida_emitida = 1,
                expired_at = %s,
                ended_at = COALESCE(ended_at, %s),
                updated_at = %s
            WHERE id = %s
            """,
            (mexico_now, mexico_now, mexico_now, sesion.get("id")),
        )

    if reason == "manual" and consumo_changed:
        _cuchillas_insert_evento(
            sesion_id=sesion.get("id"),
            linea=linea_norm,
            lot_no=lot_no,
            event_type="INFO",
            consumo_cortes=nuevo_consumo,
            max_cortes=max_cortes,
            porcentaje_uso=porcentaje_uso,
            mensaje=(
                f"Recalculo manual ({source_metric}): "
                f"{round(consumo_prev, 4)} -> {round(nuevo_consumo, 4)}"
            ),
            pendiente_externo=0,
        )

    return {
        "linea": linea_norm,
        "status": "UPDATED" if consumo_changed else "NO_CHANGE",
        "sesion_id": sesion.get("id"),
        "source_metric": source_metric,
        "source_total": source_total,
        "consumo_anterior": consumo_prev,
        "consumo_nuevo": nuevo_consumo,
    }


def _cuchillas_sync_all_active_lines(force=False, reason="hourly"):
    rows = (
        execute_query(
            """
        SELECT DISTINCT linea
        FROM cuchillas_corte_sesiones
        WHERE estado = 'ACTIVA'
          AND linea IS NOT NULL
          AND TRIM(linea) <> ''
        ORDER BY linea
        """,
            fetch="all",
        )
        or []
    )
    results = []
    for row in rows:
        linea = str((row or {}).get("linea") or "").strip()
        if not linea:
            continue
        try:
            results.append(
                _cuchillas_sync_linea_consumo(linea, force=force, reason=reason)
            )
        except Exception as sync_error:
            results.append(
                {"linea": linea, "status": "ERROR", "error": str(sync_error)}
            )
    return results


def _cuchillas_hourly_sync_loop():
    while True:
        started = time.time()
        try:
            results = _cuchillas_sync_all_active_lines(force=False, reason="hourly")
            print(f"[cuchillas-hourly] sync completado: {len(results)} lineas")
        except Exception as e:
            print(f"[cuchillas-hourly] error: {e}")

        elapsed = time.time() - started
        sleep_seconds = max(5, CUCHILLAS_HOURLY_SYNC_SECONDS - int(elapsed))
        time.sleep(sleep_seconds)


def iniciar_cuchillas_hourly_sync_worker():
    global _cuchillas_sync_thread
    if _env_flag("CUCHILLAS_DISABLE_HOURLY_SYNC", False):
        print("[cuchillas-hourly] deshabilitado por CUCHILLAS_DISABLE_HOURLY_SYNC")
        return

    with _cuchillas_sync_lock:
        if _cuchillas_sync_thread and _cuchillas_sync_thread.is_alive():
            return
        _cuchillas_sync_thread = threading.Thread(
            target=_cuchillas_hourly_sync_loop,
            name="cuchillas-hourly-sync",
            daemon=True,
        )
        _cuchillas_sync_thread.start()
        print(f"[cuchillas-hourly] worker iniciado ({CUCHILLAS_HOURLY_SYNC_SECONDS}s)")


def _cuchillas_build_diagnostico(linea, plan_activo=None, config=None, sesion=None):
    plan = (
        plan_activo
        if plan_activo is not None
        else _cuchillas_get_plan_activo_por_linea(linea)
    )
    cfg = config if config is not None else _cuchillas_get_config_por_linea(linea)
    ssn = sesion if sesion is not None else _cuchillas_get_sesion_por_linea(linea)

    source_metric = _cuchillas_normalize_source_metric(
        (cfg or {}).get("source_metric"), CUCHILLAS_SOURCE_DEFAULT
    )
    if ssn:
        source_actual = _cuchillas_source_sum_since_session(
            linea=linea, started_at=ssn.get("started_at"), source_metric=source_metric
        )
    else:
        source_actual = _cuchillas_get_metric_value(plan, source_metric)
    snapshot = _cuchillas_to_float((ssn or {}).get("last_input_snapshot"), 0.0) or 0.0
    same_lot = bool(
        ssn
        and plan
        and str(ssn.get("last_lot_no") or "") == str(plan.get("lot_no") or "")
    )
    delta_estimado = max(source_actual - snapshot, 0.0) if ssn else 0.0

    consumo_habilitado = True
    motivo = "Consumo habilitado"

    if not cfg or not _cuchillas_bool_from_int((cfg or {}).get("activo")):
        consumo_habilitado = False
        motivo = "Linea sin configuracion activa"
    elif not ssn:
        consumo_habilitado = False
        motivo = "No hay sesion activa de cuchilla"
    elif str((ssn or {}).get("estado") or "").upper() != "ACTIVA":
        consumo_habilitado = False
        motivo = "La sesion actual no esta ACTIVA"
    elif not plan:
        consumo_habilitado = False
        motivo = "No hay plan activo para la linea"
    else:
        pcb_qty = _cuchillas_to_float((cfg or {}).get("pcb_qty"), 0.0) or 0.0
        cut_qty = _cuchillas_to_float((cfg or {}).get("cut_qty"), 0.0) or 0.0
        max_cortes = _cuchillas_to_float((ssn or {}).get("max_cortes"), 0.0) or 0.0
        if pcb_qty <= 0 or cut_qty <= 0:
            consumo_habilitado = False
            motivo = "Configuracion invalida de factor PCB/Corte"
        elif max_cortes <= 0:
            consumo_habilitado = False
            motivo = "Max cortes invalido en sesion"
        elif source_actual <= snapshot:
            consumo_habilitado = False
            motivo = f"No hay incremento en {source_metric}"

    plan_seleccionado = None
    if plan:
        plan_seleccionado = {
            "id": plan.get("id"),
            "lot_no": plan.get("lot_no"),
            "status": plan.get("status"),
            "line": plan.get("line"),
        }

    return {
        "linea": linea,
        "source_metric": source_metric,
        "source_actual": source_actual,
        "last_input_snapshot": snapshot,
        "delta_estimado": delta_estimado,
        "same_lot": same_lot,
        "plan_seleccionado": plan_seleccionado,
        "sesion_activa": bool(ssn and str(ssn.get("estado") or "").upper() == "ACTIVA"),
        "motivo_no_descuento": motivo if not consumo_habilitado else "",
        "consumo_habilitado": consumo_habilitado,
    }


def crear_tablas_cuchillas_corte():
    try:
        _cuchillas_execute_raw("""
            CREATE TABLE IF NOT EXISTS cuchillas_corte_config_linea (
                id INT AUTO_INCREMENT PRIMARY KEY,
                linea VARCHAR(32) NOT NULL,
                pcb_qty DECIMAL(10,4) NOT NULL,
                cut_qty DECIMAL(10,4) NOT NULL,
                prealert_pct DECIMAL(5,2) NOT NULL DEFAULT 90.00,
                source_metric ENUM('PRODUCED_COUNT','PLAN_COUNT') NOT NULL DEFAULT 'PRODUCED_COUNT',
                activo TINYINT(1) NOT NULL DEFAULT 1,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY uk_cuchillas_linea (linea)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        try:
            _cuchillas_execute_raw("""
                ALTER TABLE cuchillas_corte_config_linea
                ADD COLUMN source_metric ENUM('PRODUCED_COUNT','PLAN_COUNT') NOT NULL DEFAULT 'PRODUCED_COUNT'
                AFTER prealert_pct
            """)
        except Exception as alter_error:
            print(f"(info) columna source_metric ya existe o no aplica: {alter_error}")

        _cuchillas_execute_raw("""
            CREATE TABLE IF NOT EXISTS cuchillas_corte_sesiones (
                id INT AUTO_INCREMENT PRIMARY KEY,
                linea VARCHAR(32) NOT NULL,
                blade_code VARCHAR(64) NOT NULL,
                max_cortes DECIMAL(12,4) NOT NULL,
                consumo_cortes DECIMAL(12,4) NOT NULL DEFAULT 0,
                last_lot_no VARCHAR(64) NULL,
                last_input_snapshot DECIMAL(12,4) NOT NULL DEFAULT 0,
                estado ENUM('ACTIVA','VENCIDA','REEMPLAZADA') NOT NULL DEFAULT 'ACTIVA',
                prealert_emitida TINYINT(1) NOT NULL DEFAULT 0,
                vencida_emitida TINYINT(1) NOT NULL DEFAULT 0,
                started_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                expired_at DATETIME NULL,
                ended_at DATETIME NULL,
                last_hourly_sync_at DATETIME NULL,
                created_by VARCHAR(64) NULL,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        try:
            _cuchillas_execute_raw("""
                ALTER TABLE cuchillas_corte_sesiones
                ADD COLUMN last_hourly_sync_at DATETIME NULL
                AFTER ended_at
            """)
        except Exception as alter_sesion_error:
            print(
                f"(info) columna last_hourly_sync_at ya existe o no aplica: {alter_sesion_error}"
            )

        _cuchillas_execute_raw("""
            CREATE TABLE IF NOT EXISTS cuchillas_corte_eventos (
                id INT AUTO_INCREMENT PRIMARY KEY,
                sesion_id INT NOT NULL,
                linea VARCHAR(32) NOT NULL,
                lot_no VARCHAR(64) NULL,
                event_type ENUM('PREALERTA','VENCIDA','INFO') NOT NULL,
                consumo_cortes DECIMAL(12,4) NOT NULL,
                max_cortes DECIMAL(12,4) NOT NULL,
                porcentaje_uso DECIMAL(6,2) NOT NULL,
                mensaje VARCHAR(255) NOT NULL,
                pendiente_externo TINYINT(1) NOT NULL DEFAULT 1,
                consumido_externo_at DATETIME NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        # Corregir/asegurar ENUM exacto (sin conversion automatica REAL->DECIMAL)
        _cuchillas_execute_raw("""
            ALTER TABLE cuchillas_corte_eventos
            MODIFY event_type ENUM('PREALERTA','VENCIDA','INFO') NOT NULL
        """)

        try:
            _cuchillas_execute_raw("""
                UPDATE cuchillas_corte_config_linea
                SET source_metric = 'PRODUCED_COUNT'
                WHERE source_metric IS NULL
                   OR source_metric NOT IN ('PRODUCED_COUNT', 'PLAN_COUNT')
            """)
        except Exception as source_fix_error:
            print(f"(info) no fue posible normalizar source_metric: {source_fix_error}")

        _cuchillas_execute_raw("""
            CREATE TABLE IF NOT EXISTS cuchillas_corte_config_modelo (
                id INT AUTO_INCREMENT PRIMARY KEY,
                linea VARCHAR(32) NOT NULL,
                model_code VARCHAR(64) NOT NULL,
                pcb_qty DECIMAL(10,4) NOT NULL,
                cut_qty DECIMAL(10,4) NOT NULL DEFAULT 0,
                activo TINYINT(1) NOT NULL DEFAULT 1,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY uk_cuchillas_modelo (linea, model_code)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        index_queries = [
            "CREATE INDEX idx_sesion_linea_estado ON cuchillas_corte_sesiones(linea, estado, started_at)",
            "CREATE INDEX idx_eventos_linea_tipo ON cuchillas_corte_eventos(linea, event_type, created_at)",
            "CREATE INDEX idx_eventos_pendiente ON cuchillas_corte_eventos(pendiente_externo, event_type, created_at)",
            "CREATE INDEX idx_config_modelo_linea ON cuchillas_corte_config_modelo(linea, activo)",
        ]
        for q in index_queries:
            try:
                _cuchillas_execute_raw(q)
            except Exception as index_error:
                print(f"(info) indice cuchillas ya existe o no aplica: {index_error}")

        print("Tablas de cuchillas de corte creadas/verificadas")
    except Exception as e:
        print(f"Error creando tablas de cuchillas de corte: {e}")


def crear_trigger_cuchillas_corte_plan_main():
    trigger_name = "trg_plan_main_cuchillas_after_update"
    try:
        existing = _cuchillas_execute_raw(
            """
            SELECT TRIGGER_NAME
            FROM information_schema.TRIGGERS
            WHERE TRIGGER_SCHEMA = DATABASE()
              AND TRIGGER_NAME = %s
            """,
            (trigger_name,),
            fetch="one",
        )

        if existing:
            _cuchillas_execute_raw(f"DROP TRIGGER IF EXISTS {trigger_name}")

        trigger_sql = f"""
        CREATE TRIGGER {trigger_name}
        AFTER UPDATE ON plan_main
        FOR EACH ROW
        cuchillas_trigger: BEGIN
            DECLARE v_plan_id BIGINT DEFAULT NULL;
            DECLARE v_sesion_id INT DEFAULT NULL;
            DECLARE v_last_lot_no VARCHAR(64) DEFAULT NULL;
            DECLARE v_last_input_snapshot DECIMAL(12,4) DEFAULT 0;
            DECLARE v_consumo_cortes DECIMAL(12,4) DEFAULT 0;
            DECLARE v_max_cortes DECIMAL(12,4) DEFAULT 0;
            DECLARE v_prealert_emitida TINYINT DEFAULT 0;
            DECLARE v_vencida_emitida TINYINT DEFAULT 0;
            DECLARE v_pcb_qty DECIMAL(10,4) DEFAULT 0;
            DECLARE v_cut_qty DECIMAL(10,4) DEFAULT 0;
            DECLARE v_prealert_pct DECIMAL(5,2) DEFAULT 90.00;
            DECLARE v_config_activa TINYINT DEFAULT 0;
            DECLARE v_source_metric VARCHAR(20) DEFAULT 'PRODUCED_COUNT';
            DECLARE v_current_input DECIMAL(12,4) DEFAULT 0;
            DECLARE v_old_input DECIMAL(12,4) DEFAULT 0;
            DECLARE v_delta_input DECIMAL(12,4) DEFAULT 0;
            DECLARE v_delta_cortes DECIMAL(12,4) DEFAULT 0;
            DECLARE v_nuevo_consumo DECIMAL(12,4) DEFAULT 0;
            DECLARE v_new_snapshot DECIMAL(12,4) DEFAULT 0;
            DECLARE v_pct_uso DECIMAL(7,2) DEFAULT 0;
            DECLARE v_prealert_threshold DECIMAL(12,4) DEFAULT 0;
            DECLARE v_model_pcb_qty DECIMAL(10,4) DEFAULT NULL;
            DECLARE v_model_cut_qty DECIMAL(10,4) DEFAULT NULL;
            DECLARE v_model_found TINYINT DEFAULT 0;
            DECLARE CONTINUE HANDLER FOR NOT FOUND BEGIN END;

            IF NEW.line IS NULL OR TRIM(NEW.line) = '' THEN
                LEAVE cuchillas_trigger;
            END IF;

            SELECT p.id
              INTO v_plan_id
            FROM plan_main p
            WHERE p.line = NEW.line
              AND p.status IN ('EN PROGRESO', 'PAUSADO', 'PLAN')
            ORDER BY
                CASE p.status
                    WHEN 'EN PROGRESO' THEN 1
                    WHEN 'PAUSADO' THEN 2
                    WHEN 'PLAN' THEN 3
                    ELSE 9
                END,
                COALESCE(p.updated_at, p.created_at) DESC,
                p.created_at DESC,
                p.id DESC
            LIMIT 1;

            IF v_plan_id IS NULL OR v_plan_id <> NEW.id THEN
                LEAVE cuchillas_trigger;
            END IF;

            SELECT
                s.id,
                s.last_lot_no,
                COALESCE(s.last_input_snapshot, 0),
                COALESCE(s.consumo_cortes, 0),
                COALESCE(s.max_cortes, 0),
                COALESCE(s.prealert_emitida, 0),
                COALESCE(s.vencida_emitida, 0),
                COALESCE(c.pcb_qty, 0),
                COALESCE(c.cut_qty, 0),
                COALESCE(c.prealert_pct, 90.00),
                COALESCE(c.activo, 0),
                COALESCE(c.source_metric, 'PRODUCED_COUNT')
            INTO
                v_sesion_id,
                v_last_lot_no,
                v_last_input_snapshot,
                v_consumo_cortes,
                v_max_cortes,
                v_prealert_emitida,
                v_vencida_emitida,
                v_pcb_qty,
                v_cut_qty,
                v_prealert_pct,
                v_config_activa,
                v_source_metric
            FROM cuchillas_corte_sesiones s
            LEFT JOIN cuchillas_corte_config_linea c
                ON c.linea = s.linea
            WHERE s.linea = NEW.line
              AND s.estado = 'ACTIVA'
            ORDER BY s.started_at DESC, s.id DESC
            LIMIT 1;

            IF v_sesion_id IS NULL THEN
                LEAVE cuchillas_trigger;
            END IF;

            IF COALESCE(v_config_activa, 0) <> 1 THEN
                LEAVE cuchillas_trigger;
            END IF;

            -- Buscar config por modelo, si existe sobreescribe pcb_qty y cut_qty de linea
            SELECT pcb_qty, cut_qty
            INTO v_model_pcb_qty, v_model_cut_qty
            FROM cuchillas_corte_config_modelo
            WHERE linea = NEW.line
              AND model_code = COALESCE(NEW.model_code, '')
              AND activo = 1
            LIMIT 1;

            IF v_model_pcb_qty IS NOT NULL THEN
                SET v_pcb_qty = v_model_pcb_qty;
                SET v_cut_qty = v_model_cut_qty;
                SET v_model_found = 1;
            END IF;

            -- Si cut_qty = 0 para este modelo, no consume cuchilla
            IF COALESCE(v_cut_qty, 0) <= 0 THEN
                LEAVE cuchillas_trigger;
            END IF;

            IF v_source_metric IS NULL OR v_source_metric NOT IN ('PRODUCED_COUNT', 'PLAN_COUNT') THEN
                SET v_source_metric = 'PRODUCED_COUNT';
            END IF;

            IF v_source_metric = 'PLAN_COUNT' THEN
                LEAVE cuchillas_trigger;
            END IF;

            SET v_current_input = GREATEST(COALESCE(NEW.produced_count, 0), 0);
            SET v_old_input = GREATEST(COALESCE(OLD.produced_count, 0), 0);

            IF v_current_input = v_old_input THEN
                LEAVE cuchillas_trigger;
            END IF;

            IF COALESCE(v_pcb_qty, 0) <= 0
               OR COALESCE(v_max_cortes, 0) <= 0 THEN
                LEAVE cuchillas_trigger;
            END IF;

            IF COALESCE(v_last_lot_no, '') = COALESCE(NEW.lot_no, '') THEN
                SET v_delta_input = GREATEST(v_current_input - COALESCE(v_last_input_snapshot, 0), 0);
                SET v_new_snapshot = GREATEST(v_current_input, COALESCE(v_last_input_snapshot, 0));
            ELSE
                SET v_delta_input = GREATEST(v_current_input, 0);
                SET v_new_snapshot = v_current_input;
            END IF;

            SET v_delta_cortes = v_delta_input * (v_cut_qty / v_pcb_qty);
            SET v_nuevo_consumo = COALESCE(v_consumo_cortes, 0) + COALESCE(v_delta_cortes, 0);
            IF v_nuevo_consumo < 0 THEN
                SET v_nuevo_consumo = 0;
            END IF;

            SET v_pct_uso = IF(v_max_cortes > 0, ROUND((v_nuevo_consumo / v_max_cortes) * 100, 2), 0);

            SET @mexico_now = CONVERT_TZ(NOW(), @@global.time_zone, '-06:00');

            UPDATE cuchillas_corte_sesiones
               SET consumo_cortes = v_nuevo_consumo,
                   last_input_snapshot = v_new_snapshot,
                   last_lot_no = NEW.lot_no,
                   updated_at = @mexico_now
             WHERE id = v_sesion_id
               AND estado = 'ACTIVA';

            SET v_prealert_threshold = v_max_cortes * (COALESCE(v_prealert_pct, 90.00) / 100.00);

            IF v_prealert_emitida = 0 AND v_nuevo_consumo >= v_prealert_threshold THEN
                INSERT INTO cuchillas_corte_eventos (
                    sesion_id, linea, lot_no, event_type,
                    consumo_cortes, max_cortes, porcentaje_uso, mensaje,
                    pendiente_externo, created_at
                )
                VALUES (
                    v_sesion_id, NEW.line, NEW.lot_no, 'PREALERTA',
                    v_nuevo_consumo, v_max_cortes, v_pct_uso,
                    CONCAT('Prealerta de cuchilla en linea ', NEW.line, ' (', ROUND(v_pct_uso, 2), '% de uso)'),
                    1, @mexico_now
                );

                UPDATE cuchillas_corte_sesiones
                   SET prealert_emitida = 1,
                       updated_at = @mexico_now
                 WHERE id = v_sesion_id;
            END IF;

            IF v_vencida_emitida = 0 AND v_nuevo_consumo >= v_max_cortes THEN
                INSERT INTO cuchillas_corte_eventos (
                    sesion_id, linea, lot_no, event_type,
                    consumo_cortes, max_cortes, porcentaje_uso, mensaje,
                    pendiente_externo, created_at
                )
                VALUES (
                    v_sesion_id, NEW.line, NEW.lot_no, 'VENCIDA',
                    v_nuevo_consumo, v_max_cortes, v_pct_uso,
                    CONCAT('Cuchilla vencida en linea ', NEW.line, ' (', ROUND(v_pct_uso, 2), '% de uso)'),
                    1, @mexico_now
                );

                UPDATE cuchillas_corte_sesiones
                   SET estado = 'VENCIDA',
                       vencida_emitida = 1,
                       expired_at = @mexico_now,
                       ended_at = COALESCE(ended_at, @mexico_now),
                       updated_at = @mexico_now
                 WHERE id = v_sesion_id;
            END IF;
        END
        """
        _cuchillas_execute_raw(trigger_sql)
        print("Trigger de cuchillas de corte creado/actualizado")
    except Exception as e:
        print(f"Error creando trigger de cuchillas de corte: {e}")

@bp.route("/control-cuchillas-corte-ajax")
@login_requerido
@requiere_permiso_dropdown(
    CUCHILLAS_PERMISO_PAGINA, CUCHILLAS_PERMISO_SECCION, CUCHILLAS_PERMISO_BOTON
)
def control_cuchillas_corte_ajax():
    try:
        return render_template("Control de produccion/control_cuchillas_corte_ajax.html")
    except Exception as e:
        print(f"Error al cargar control_cuchillas_corte_ajax: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@bp.route("/api/cuchillas-corte/lineas", methods=["GET"])
@login_requerido
@requiere_permiso_dropdown(
    CUCHILLAS_PERMISO_PAGINA, CUCHILLAS_PERMISO_SECCION, CUCHILLAS_PERMISO_BOTON
)
def api_cuchillas_corte_lineas():
    try:
        include_all = _cuchillas_bool_param(request.args.get("include_all"))
        if include_all:
            rows = (
                execute_query(
                    """
                SELECT DISTINCT line AS linea
                FROM plan_main
                WHERE line IS NOT NULL
                  AND TRIM(line) <> ''
                ORDER BY line
                """,
                    fetch="all",
                )
                or []
            )
        else:
            rows = (
                execute_query(
                    """
                SELECT linea
                FROM cuchillas_corte_config_linea
                WHERE activo = 1
                  AND linea IS NOT NULL
                  AND TRIM(linea) <> ''
                ORDER BY linea
                """,
                    fetch="all",
                )
                or []
            )

        lineas = [str((r or {}).get("linea") or "").strip() for r in rows]
        lineas = [l for l in lineas if l]
        return jsonify({"success": True, "lineas": lineas, "include_all": include_all})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/api/cuchillas-corte/dashboard", methods=["GET"])
@login_requerido
@requiere_permiso_dropdown(
    CUCHILLAS_PERMISO_PAGINA, CUCHILLAS_PERMISO_SECCION, CUCHILLAS_PERMISO_BOTON
)
def api_cuchillas_corte_dashboard():
    try:
        include_inactive = _cuchillas_bool_param(request.args.get("include_inactive"))
        if include_inactive:
            rows = (
                execute_query(
                    """
                SELECT linea
                FROM cuchillas_corte_config_linea
                WHERE linea IS NOT NULL
                  AND TRIM(linea) <> ''
                ORDER BY linea
                """,
                    fetch="all",
                )
                or []
            )
        else:
            rows = (
                execute_query(
                    """
                SELECT linea
                FROM cuchillas_corte_config_linea
                WHERE activo = 1
                  AND linea IS NOT NULL
                  AND TRIM(linea) <> ''
                ORDER BY linea
                """,
                    fetch="all",
                )
                or []
            )

        items = []
        for row in rows:
            linea = str((row or {}).get("linea") or "").strip()
            if not linea:
                continue

            _cuchillas_sync_linea_consumo(linea, force=False, reason="dashboard")
            config = _cuchillas_get_config_por_linea(linea)
            plan_activo = _cuchillas_get_plan_activo_por_linea(linea)
            sesion = _cuchillas_get_sesion_por_linea(linea)
            diagnostico = _cuchillas_build_diagnostico(
                linea=linea, plan_activo=plan_activo, config=config, sesion=sesion
            )
            pendiente_row = (
                execute_query(
                    """
                SELECT COUNT(*) AS total
                FROM cuchillas_corte_eventos
                WHERE linea = %s
                  AND pendiente_externo = 1
                  AND event_type = 'VENCIDA'
                """,
                    (linea,),
                    fetch="one",
                )
                or {}
            )

            model_code = (plan_activo or {}).get("model_code", "")
            effective = _cuchillas_get_effective_config(linea, model_code)
            items.append(
                {
                    "linea": linea,
                    "config": config,
                    "plan_activo": plan_activo,
                    "sesion": sesion,
                    "diagnostico": diagnostico,
                    "config_efectiva": effective,
                    "eventos_vencida_pendientes": int(
                        (pendiente_row or {}).get("total") or 0
                    ),
                }
            )

        return jsonify(
            {"success": True, "items": items, "include_inactive": include_inactive}
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/api/cuchillas-corte/config", methods=["GET"])
@login_requerido
@requiere_permiso_dropdown(
    CUCHILLAS_PERMISO_PAGINA, CUCHILLAS_PERMISO_SECCION, CUCHILLAS_PERMISO_BOTON
)
def api_cuchillas_corte_get_config():
    try:
        linea = (request.args.get("linea") or "").strip()
        if not linea:
            return jsonify(
                {"success": False, "error": "Parametro linea requerido"}
            ), 400

        config = _cuchillas_get_config_por_linea(linea)
        if not config:
            config = {
                "linea": linea,
                "pcb_qty": 1.0,
                "cut_qty": 1.0,
                "prealert_pct": 90.0,
                "source_metric": CUCHILLAS_SOURCE_DEFAULT,
                "activo": 0,
            }
        return jsonify({"success": True, "config": config})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/api/cuchillas-corte/config", methods=["POST"])
@login_requerido
@requiere_permiso_dropdown(
    CUCHILLAS_PERMISO_PAGINA, CUCHILLAS_PERMISO_SECCION, CUCHILLAS_PERMISO_BOTON
)
def api_cuchillas_corte_save_config():
    try:
        data = request.get_json() or {}
        linea = (data.get("linea") or "").strip()
        pcb_qty = _cuchillas_to_float(data.get("pcb_qty"))
        cut_qty = _cuchillas_to_float(data.get("cut_qty"))
        prealert_pct = _cuchillas_to_float(data.get("prealert_pct"), 90.0)
        source_metric = _cuchillas_normalize_source_metric(
            data.get("source_metric"), CUCHILLAS_SOURCE_DEFAULT
        )
        activo = 1 if _cuchillas_bool_param(data.get("activo", 1)) else 0

        if not linea:
            return jsonify({"success": False, "error": "linea requerida"}), 400
        if pcb_qty is None or pcb_qty <= 0:
            return jsonify(
                {"success": False, "error": "pcb_qty debe ser mayor a 0"}
            ), 400
        if cut_qty is None or cut_qty <= 0:
            return jsonify(
                {"success": False, "error": "cut_qty debe ser mayor a 0"}
            ), 400
        if prealert_pct is None or prealert_pct <= 0 or prealert_pct > 100:
            return jsonify(
                {"success": False, "error": "prealert_pct debe estar entre 0 y 100"}
            ), 400

        upsert_sql = """
            INSERT INTO cuchillas_corte_config_linea (
                linea, pcb_qty, cut_qty, prealert_pct, source_metric, activo, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                pcb_qty = VALUES(pcb_qty),
                cut_qty = VALUES(cut_qty),
                prealert_pct = VALUES(prealert_pct),
                source_metric = VALUES(source_metric),
                activo = VALUES(activo),
                updated_at = %s
        """
        mexico_now = AuthSystem.get_mexico_time_mysql()
        execute_query(
            upsert_sql,
            (
                linea,
                pcb_qty,
                cut_qty,
                prealert_pct,
                source_metric,
                activo,
                mexico_now,
                mexico_now,
            ),
        )
        config = _cuchillas_get_config_por_linea(linea)
        return jsonify({"success": True, "config": config})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/api/cuchillas-corte/config-modelo", methods=["GET"])
@login_requerido
@requiere_permiso_dropdown(
    CUCHILLAS_PERMISO_PAGINA, CUCHILLAS_PERMISO_SECCION, CUCHILLAS_PERMISO_BOTON
)
def api_cuchillas_corte_get_config_modelos():
    try:
        linea = (request.args.get("linea") or "").strip()
        if not linea:
            return jsonify({"success": False, "error": "linea requerida"}), 400
        rows = (
            execute_query(
                "SELECT id, linea, model_code, pcb_qty, cut_qty, activo, updated_at FROM cuchillas_corte_config_modelo WHERE linea = %s ORDER BY model_code",
                (linea,),
                fetch="all",
            )
            or []
        )
        modelos = [_cuchillas_row_to_json(r) for r in rows]
        return jsonify({"success": True, "modelos": modelos})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/api/cuchillas-corte/config-modelo", methods=["POST"])
@login_requerido
@requiere_permiso_dropdown(
    CUCHILLAS_PERMISO_PAGINA, CUCHILLAS_PERMISO_SECCION, CUCHILLAS_PERMISO_BOTON
)
def api_cuchillas_corte_save_config_modelo():
    try:
        data = request.get_json() or {}
        linea = (data.get("linea") or "").strip()
        model_code = (data.get("model_code") or "").strip()
        pcb_qty = _cuchillas_to_float(data.get("pcb_qty"))
        cut_qty = _cuchillas_to_float(data.get("cut_qty"), 0.0)
        activo = 1 if _cuchillas_bool_param(data.get("activo", 1)) else 0

        if not linea or not model_code:
            return jsonify(
                {"success": False, "error": "linea y model_code requeridos"}
            ), 400
        if pcb_qty is None or pcb_qty <= 0:
            return jsonify(
                {"success": False, "error": "pcb_qty debe ser mayor a 0"}
            ), 400
        if cut_qty is None or cut_qty < 0:
            return jsonify(
                {"success": False, "error": "cut_qty no puede ser negativo"}
            ), 400

        mexico_now = AuthSystem.get_mexico_time_mysql()
        execute_query(
            """
            INSERT INTO cuchillas_corte_config_modelo (linea, model_code, pcb_qty, cut_qty, activo, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                pcb_qty = VALUES(pcb_qty),
                cut_qty = VALUES(cut_qty),
                activo = VALUES(activo),
                updated_at = %s
            """,
            (linea, model_code, pcb_qty, cut_qty, activo, mexico_now, mexico_now),
        )
        modelos_rows = (
            execute_query(
                "SELECT id, linea, model_code, pcb_qty, cut_qty, activo, updated_at FROM cuchillas_corte_config_modelo WHERE linea = %s ORDER BY model_code",
                (linea,),
                fetch="all",
            )
            or []
        )
        modelos = [_cuchillas_row_to_json(r) for r in modelos_rows]
        return jsonify({"success": True, "modelos": modelos})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/api/cuchillas-corte/config-modelo/eliminar", methods=["POST"])
@login_requerido
@requiere_permiso_dropdown(
    CUCHILLAS_PERMISO_PAGINA, CUCHILLAS_PERMISO_SECCION, CUCHILLAS_PERMISO_BOTON
)
def api_cuchillas_corte_delete_config_modelo():
    try:
        data = request.get_json() or {}
        linea = (data.get("linea") or "").strip()
        model_code = (data.get("model_code") or "").strip()
        if not linea or not model_code:
            return jsonify(
                {"success": False, "error": "linea y model_code requeridos"}
            ), 400
        execute_query(
            "DELETE FROM cuchillas_corte_config_modelo WHERE linea = %s AND model_code = %s",
            (linea, model_code),
        )
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/api/cuchillas-corte/modelos-linea", methods=["GET"])
@login_requerido
@requiere_permiso_dropdown(
    CUCHILLAS_PERMISO_PAGINA, CUCHILLAS_PERMISO_SECCION, CUCHILLAS_PERMISO_BOTON
)
def api_cuchillas_corte_modelos_linea():
    try:
        linea = (request.args.get("linea") or "").strip()
        if not linea:
            return jsonify({"success": False, "error": "linea requerida"}), 400
        rows = (
            execute_query(
                """SELECT DISTINCT model_code FROM plan_main
               WHERE line = %s AND model_code IS NOT NULL AND model_code <> ''
               ORDER BY model_code""",
                (linea,),
                fetch="all",
            )
            or []
        )
        modelos = []
        for r in rows:
            rd = _cuchillas_row_to_json(r)
            mc = str(rd.get("model_code", "") if rd else "").strip()
            if mc:
                modelos.append(mc)
        return jsonify({"success": True, "modelos": modelos})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/api/cuchillas-corte/sesion/iniciar", methods=["POST"])
@login_requerido
@requiere_permiso_dropdown(
    CUCHILLAS_PERMISO_PAGINA, CUCHILLAS_PERMISO_SECCION, CUCHILLAS_PERMISO_BOTON
)
def api_cuchillas_corte_sesion_iniciar():
    try:
        data = request.get_json() or {}
        linea = (data.get("linea") or "").strip()
        blade_code = (data.get("blade_code") or "").strip()
        max_cortes = _cuchillas_to_float(data.get("max_cortes"))

        if not linea:
            return jsonify({"success": False, "error": "linea requerida"}), 400
        if not blade_code:
            return jsonify({"success": False, "error": "blade_code requerido"}), 400
        if max_cortes is None or max_cortes <= 0:
            return jsonify(
                {"success": False, "error": "max_cortes debe ser mayor a 0"}
            ), 400

        config = _cuchillas_get_config_por_linea(linea)
        if not config or not int(config.get("activo") or 0):
            return jsonify(
                {
                    "success": False,
                    "error": f"No hay configuracion activa para la linea {linea}. Guarda primero la equivalencia PCB/Corte.",
                }
            ), 400

        activa = execute_query(
            """
            SELECT id, blade_code
            FROM cuchillas_corte_sesiones
            WHERE linea = %s
              AND estado = 'ACTIVA'
            ORDER BY started_at DESC, id DESC
            LIMIT 1
            """,
            (linea,),
            fetch="one",
        )
        if activa:
            return jsonify(
                {
                    "success": False,
                    "error": f"Ya existe una sesion activa para la linea {linea} (ID {activa.get('id')}). Usa reemplazar.",
                }
            ), 409

        sesion = _cuchillas_crear_sesion(
            linea=linea,
            blade_code=blade_code,
            max_cortes=max_cortes,
            created_by=_cuchillas_usuario_actual(),
            config=config,
        )
        return jsonify({"success": True, "sesion": sesion})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/api/cuchillas-corte/sesion/reemplazar", methods=["POST"])
@login_requerido
@requiere_permiso_dropdown(
    CUCHILLAS_PERMISO_PAGINA, CUCHILLAS_PERMISO_SECCION, CUCHILLAS_PERMISO_BOTON
)
def api_cuchillas_corte_sesion_reemplazar():
    try:
        data = request.get_json() or {}
        linea = (data.get("linea") or "").strip()
        blade_code = (data.get("blade_code") or "").strip()
        max_cortes = _cuchillas_to_float(data.get("max_cortes"))

        if not linea:
            return jsonify({"success": False, "error": "linea requerida"}), 400
        if not blade_code:
            return jsonify({"success": False, "error": "blade_code requerido"}), 400
        if max_cortes is None or max_cortes <= 0:
            return jsonify(
                {"success": False, "error": "max_cortes debe ser mayor a 0"}
            ), 400

        config = _cuchillas_get_config_por_linea(linea)
        if not config or not int(config.get("activo") or 0):
            return jsonify(
                {
                    "success": False,
                    "error": f"No hay configuracion activa para la linea {linea}. Guarda primero la equivalencia PCB/Corte.",
                }
            ), 400

        activa = execute_query(
            """
            SELECT id, blade_code, max_cortes, consumo_cortes
            FROM cuchillas_corte_sesiones
            WHERE linea = %s
              AND estado = 'ACTIVA'
            ORDER BY started_at DESC, id DESC
            LIMIT 1
            """,
            (linea,),
            fetch="one",
        )

        mexico_now_reemplazo = AuthSystem.get_mexico_time_mysql()
        if activa:
            execute_query(
                """
                UPDATE cuchillas_corte_sesiones
                SET estado = 'REEMPLAZADA',
                    ended_at = %s,
                    updated_at = %s
                WHERE id = %s
                  AND estado = 'ACTIVA'
                """,
                (mexico_now_reemplazo, mexico_now_reemplazo, activa.get("id")),
            )

            mensaje = (
                f"Cuchilla {activa.get('blade_code')} reemplazada por {blade_code}. "
                f"Consumo final: {activa.get('consumo_cortes')}/{activa.get('max_cortes')}"
            )
            execute_query(
                """
                INSERT INTO cuchillas_corte_eventos (
                    sesion_id, linea, lot_no, event_type,
                    consumo_cortes, max_cortes, porcentaje_uso, mensaje,
                    pendiente_externo, created_at
                )
                VALUES (%s, %s, NULL, 'INFO', %s, %s, 0, %s, 0, %s)
                """,
                (
                    activa.get("id"),
                    linea,
                    _cuchillas_to_float(activa.get("consumo_cortes"), 0.0) or 0.0,
                    _cuchillas_to_float(activa.get("max_cortes"), 0.0) or 0.0,
                    mensaje,
                    mexico_now_reemplazo,
                ),
            )

        nueva_sesion = _cuchillas_crear_sesion(
            linea=linea,
            blade_code=blade_code,
            max_cortes=max_cortes,
            created_by=_cuchillas_usuario_actual(),
            config=config,
        )
        return jsonify(
            {
                "success": True,
                "sesion": nueva_sesion,
                "reemplazo_realizado": bool(activa),
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/api/cuchillas-corte/sesiones", methods=["GET"])
@login_requerido
@requiere_permiso_dropdown(
    CUCHILLAS_PERMISO_PAGINA, CUCHILLAS_PERMISO_SECCION, CUCHILLAS_PERMISO_BOTON
)
def api_cuchillas_corte_sesiones():
    try:
        linea = (request.args.get("linea") or "").strip()
        limit = request.args.get("limit") or 100
        sesiones = _cuchillas_get_historial_sesiones(linea=linea or None, limit=limit)
        return jsonify(
            {
                "success": True,
                "linea": linea or None,
                "total": len(sesiones),
                "sesiones": sesiones,
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/api/cuchillas-corte/sesion/eliminar", methods=["POST"])
@login_requerido
@requiere_permiso_dropdown(
    CUCHILLAS_PERMISO_PAGINA, CUCHILLAS_PERMISO_SECCION, CUCHILLAS_PERMISO_BOTON
)
def api_cuchillas_corte_sesion_eliminar():
    try:
        data = request.get_json() or {}
        linea = (data.get("linea") or request.args.get("linea") or "").strip()
        sesion_id_raw = data.get("sesion_id")
        if sesion_id_raw is None:
            sesion_id_raw = request.args.get("sesion_id")

        sesion_id = None
        if sesion_id_raw is not None and str(sesion_id_raw).strip() != "":
            try:
                sesion_id = int(sesion_id_raw)
            except Exception:
                return jsonify({"success": False, "error": "sesion_id invalido"}), 400
            if sesion_id <= 0:
                return jsonify({"success": False, "error": "sesion_id invalido"}), 400

        if sesion_id is None and not linea:
            return jsonify(
                {"success": False, "error": "linea o sesion_id requerido"}
            ), 400

        target = None
        if sesion_id is not None:
            target = execute_query(
                """
                SELECT id, linea, blade_code, estado
                FROM cuchillas_corte_sesiones
                WHERE id = %s
                LIMIT 1
                """,
                (sesion_id,),
                fetch="one",
            )
            if target and linea and str(target.get("linea") or "").strip() != linea:
                return jsonify(
                    {
                        "success": False,
                        "error": f"La sesion {sesion_id} no pertenece a la linea {linea}",
                    }
                ), 400
        else:
            target = execute_query(
                """
                SELECT id, linea, blade_code, estado
                FROM cuchillas_corte_sesiones
                WHERE linea = %s
                ORDER BY
                    CASE estado
                        WHEN 'ACTIVA' THEN 1
                        WHEN 'VENCIDA' THEN 2
                        WHEN 'REEMPLAZADA' THEN 3
                        ELSE 9
                    END,
                    started_at DESC,
                    id DESC
                LIMIT 1
                """,
                (linea,),
                fetch="one",
            )

        if not target:
            return jsonify(
                {"success": False, "error": "No se encontro sesion para eliminar"}
            ), 404

        target_id = int(target.get("id"))
        target_linea = str(target.get("linea") or "").strip()
        target_blade = str(target.get("blade_code") or "").strip()
        target_estado = str(target.get("estado") or "").strip().upper()

        eventos_borrados = (
            execute_query(
                "DELETE FROM cuchillas_corte_eventos WHERE sesion_id = %s", (target_id,)
            )
            or 0
        )
        sesiones_borradas = (
            execute_query(
                "DELETE FROM cuchillas_corte_sesiones WHERE id = %s", (target_id,)
            )
            or 0
        )

        if int(sesiones_borradas) <= 0:
            return jsonify(
                {"success": False, "error": "No se pudo eliminar la sesion"}
            ), 409

        return jsonify(
            {
                "success": True,
                "eliminada": {
                    "id": target_id,
                    "linea": target_linea,
                    "blade_code": target_blade,
                    "estado": target_estado,
                },
                "eventos_borrados": int(eventos_borrados),
                "sesiones_borradas": int(sesiones_borradas),
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/api/cuchillas-corte/estado", methods=["GET"])
@login_requerido
@requiere_permiso_dropdown(
    CUCHILLAS_PERMISO_PAGINA, CUCHILLAS_PERMISO_SECCION, CUCHILLAS_PERMISO_BOTON
)
def api_cuchillas_corte_estado():
    try:
        linea = (request.args.get("linea") or "").strip()
        if not linea:
            return jsonify(
                {"success": False, "error": "Parametro linea requerido"}
            ), 400

        _cuchillas_sync_linea_consumo(linea, force=False, reason="estado")
        plan_activo = _cuchillas_get_plan_activo_por_linea(linea)
        config = _cuchillas_get_config_por_linea(linea)
        sesion = _cuchillas_get_sesion_por_linea(linea)
        diagnostico = _cuchillas_build_diagnostico(
            linea=linea, plan_activo=plan_activo, config=config, sesion=sesion
        )

        eventos = (
            execute_query(
                """
            SELECT
                id, sesion_id, linea, lot_no, event_type,
                consumo_cortes, max_cortes, porcentaje_uso, mensaje,
                pendiente_externo, consumido_externo_at, created_at
            FROM cuchillas_corte_eventos
            WHERE linea = %s
            ORDER BY created_at DESC, id DESC
            LIMIT 20
            """,
                (linea,),
                fetch="all",
            )
            or []
        )

        model_code = (plan_activo or {}).get("model_code", "")
        effective = _cuchillas_get_effective_config(linea, model_code)
        return jsonify(
            {
                "success": True,
                "linea": linea,
                "plan_activo": plan_activo,
                "config": config,
                "sesion": sesion,
                "diagnostico": diagnostico,
                "config_efectiva": effective,
                "eventos_recentes": _cuchillas_rows_to_json(eventos),
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/api/cuchillas-corte/diagnostico", methods=["GET"])
@login_requerido
@requiere_permiso_dropdown(
    CUCHILLAS_PERMISO_PAGINA, CUCHILLAS_PERMISO_SECCION, CUCHILLAS_PERMISO_BOTON
)
def api_cuchillas_corte_diagnostico():
    try:
        linea = (request.args.get("linea") or "").strip()
        if not linea:
            return jsonify(
                {"success": False, "error": "Parametro linea requerido"}
            ), 400

        _cuchillas_sync_linea_consumo(linea, force=False, reason="diagnostico")
        plan_activo = _cuchillas_get_plan_activo_por_linea(linea)
        config = _cuchillas_get_config_por_linea(linea)
        sesion = _cuchillas_get_sesion_por_linea(linea)
        diagnostico = _cuchillas_build_diagnostico(
            linea=linea, plan_activo=plan_activo, config=config, sesion=sesion
        )

        return jsonify(
            {
                "success": True,
                "linea": linea,
                "plan_activo": plan_activo,
                "config": config,
                "sesion": sesion,
                "diagnostico": diagnostico,
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/api/cuchillas-corte/recalcular", methods=["POST"])
@login_requerido
@requiere_permiso_dropdown(
    CUCHILLAS_PERMISO_PAGINA, CUCHILLAS_PERMISO_SECCION, CUCHILLAS_PERMISO_BOTON
)
def api_cuchillas_corte_recalcular():
    try:
        data = request.get_json() or {}
        linea = (data.get("linea") or request.args.get("linea") or "").strip()
        if not linea:
            return jsonify({"success": False, "error": "linea requerida"}), 400

        sync_result = _cuchillas_sync_linea_consumo(linea, force=True, reason="manual")
        status = str((sync_result or {}).get("status") or "").upper()
        if status in (
            "SIN_SESION_ACTIVA",
            "CONFIG_INACTIVA",
            "CONFIG_INVALIDA",
            "LINEA_INVALIDA",
        ):
            mensajes = {
                "SIN_SESION_ACTIVA": f"No hay sesion ACTIVA para la linea {linea}",
                "CONFIG_INACTIVA": f"La configuracion de la linea {linea} esta inactiva",
                "CONFIG_INVALIDA": f"Configuracion invalida para la linea {linea}",
                "LINEA_INVALIDA": "Linea invalida",
            }
            return jsonify(
                {
                    "success": False,
                    "linea": linea,
                    "error": mensajes.get(status, status),
                    "detalle": sync_result,
                }
            ), 400

        plan_activo = _cuchillas_get_plan_activo_por_linea(linea)
        config = _cuchillas_get_config_por_linea(linea)
        sesion_actualizada = _cuchillas_get_sesion_por_linea(linea)
        diagnostico_actualizado = _cuchillas_build_diagnostico(
            linea=linea,
            plan_activo=plan_activo,
            config=config,
            sesion=sesion_actualizada,
        )
        return jsonify(
            {
                "success": True,
                "linea": linea,
                "aplico_cambios": status == "UPDATED",
                "mensaje": "Recalculo aplicado"
                if status == "UPDATED"
                else "Sin cambios en consumo",
                "sync_result": sync_result,
                "sesion": sesion_actualizada,
                "diagnostico": diagnostico_actualizado,
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/api/cuchillas-corte/eventos", methods=["GET"])
@login_requerido
@requiere_permiso_dropdown(
    CUCHILLAS_PERMISO_PAGINA, CUCHILLAS_PERMISO_SECCION, CUCHILLAS_PERMISO_BOTON
)
def api_cuchillas_corte_eventos():
    try:
        linea = (request.args.get("linea") or "").strip()
        if not linea:
            return jsonify(
                {"success": False, "error": "Parametro linea requerido"}
            ), 400

        solo_pendientes = _cuchillas_bool_param(request.args.get("solo_pendientes"))
        where = ["linea = %s"]
        params = [linea]
        if solo_pendientes:
            where.append("pendiente_externo = 1")

        query = f"""
            SELECT
                id, sesion_id, linea, lot_no, event_type,
                consumo_cortes, max_cortes, porcentaje_uso, mensaje,
                pendiente_externo, consumido_externo_at, created_at
            FROM cuchillas_corte_eventos
            WHERE {" AND ".join(where)}
            ORDER BY created_at DESC, id DESC
            LIMIT 300
        """
        eventos = execute_query(query, tuple(params), fetch="all") or []
        return jsonify(
            {
                "success": True,
                "linea": linea,
                "solo_pendientes": solo_pendientes,
                "eventos": _cuchillas_rows_to_json(eventos),
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

