"""Endpoints HTTP + infraestructura para snapshots de inventario IMD/SMD.

Servicio compartido (no pertenece a un solo modulo de UI): captura
periodicamente el estado del inventario para auditoria historica.
Consumido indirectamente por "IMD-SMD TERMINADO" (vista historica)
pero el snapshot se toma en background via worker daemon iniciado al
startup de la app.

Contenido:
  - Constantes de zona horaria y horario diario
  - DDL `crear_tablas_snapshot_inventario()` (idempotente)
  - Captura `_snapshot_inv_tomar(fecha_override=None)`
  - Worker daemon `_snapshot_inv_daily_loop()` + `iniciar_snapshot_inv_worker()`
  - 4 rutas HTTP (`/api/snapshot_inventario/*`)

Rutas HTTP:
  GET  /api/snapshot_inventario/fechas     -> listar fechas disponibles
  GET  /api/snapshot_inventario/general    -> snapshot inventario general por fecha
  GET  /api/snapshot_inventario/ubicacion  -> snapshot ubicacion por fecha
  POST /api/snapshot_inventario/trigger    -> tomar snapshot manualmente (admin)

Migrado desde app/routes.py el 2026-05-27 (rutas) y 2026-05-27 (DDL +
worker). El worker se arranca desde app/startup_init.py.

WF_003: las 3 GETs reciben @login_requerido (antes eran publicas: cualquier
visitante sin sesion podia leer snapshots historicos de inventario).
"""

import os
import threading
import time
from datetime import date, datetime, timedelta

import pytz
from flask import Blueprint, jsonify, request

from app.api.shared import execute_query, login_requerido


bp = Blueprint("shared_snapshot_inventario", __name__)


# ---------------------------------------------------------------------------
# Constantes y estado de modulo
# ---------------------------------------------------------------------------

_SNAPSHOT_INV_TZ = pytz.timezone("America/Monterrey")
_SNAPSHOT_INV_TARGET_HOUR = 7
_SNAPSHOT_INV_TARGET_MINUTE = 30
_snapshot_inv_thread = None
_snapshot_inv_lock = threading.Lock()


def _env_flag(name, default=False):
    val = os.getenv(name)
    if val is None:
        return default
    return str(val).strip().lower() in ("1", "true", "yes", "on", "si")


# ---------------------------------------------------------------------------
# DDL idempotente (llamado desde startup_init.py)
# ---------------------------------------------------------------------------


def crear_tablas_snapshot_inventario():
    """Crear tablas para almacenar snapshots diarios de inventario"""
    try:
        execute_query("""
            CREATE TABLE IF NOT EXISTS snapshot_inventario_general (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                fecha_snapshot DATE NOT NULL,
                modelo VARCHAR(100),
                nparte VARCHAR(100),
                stock_total INT DEFAULT 0,
                ubicaciones TEXT,
                ultima_entrada DATETIME,
                ultima_salida DATETIME,
                tipo_inventario VARCHAR(50),
                created_at DATETIME DEFAULT NOW(),
                INDEX idx_snap_ig_fecha (fecha_snapshot),
                INDEX idx_snap_ig_fecha_nparte (fecha_snapshot, nparte)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        print("[snapshot-inv] Tabla snapshot_inventario_general OK")
    except Exception as e:
        print(f"[snapshot-inv] Error creando snapshot_inventario_general: {e}")

    try:
        execute_query("""
            CREATE TABLE IF NOT EXISTS snapshot_ubicacion (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                fecha_snapshot DATE NOT NULL,
                modelo VARCHAR(100),
                nparte VARCHAR(100),
                fecha VARCHAR(50),
                ubicacion VARCHAR(100),
                cantidad INT DEFAULT 0,
                tipo_inventario VARCHAR(50),
                comentario TEXT,
                carro VARCHAR(100),
                created_at DATETIME DEFAULT NOW(),
                INDEX idx_snap_ub_fecha (fecha_snapshot),
                INDEX idx_snap_ub_fecha_modelo (fecha_snapshot, modelo)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        print("[snapshot-inv] Tabla snapshot_ubicacion OK")
    except Exception as e:
        print(f"[snapshot-inv] Error creando snapshot_ubicacion: {e}")


# ---------------------------------------------------------------------------
# Captura de snapshot
# ---------------------------------------------------------------------------


def _snapshot_inv_tomar(fecha_override=None):
    """Tomar snapshot de inventario general y ubicacion para una fecha.
    Idempotente: si ya existe snapshot para esa fecha, no inserta."""
    fecha = fecha_override or datetime.now(_SNAPSHOT_INV_TZ).date()
    fecha_str = str(fecha)

    # Verificar si ya existe snapshot para esta fecha
    existing = execute_query(
        "SELECT COUNT(*) AS cnt FROM snapshot_inventario_general WHERE fecha_snapshot = %s",
        [fecha_str], fetch="one"
    )
    if existing and existing.get("cnt", 0) > 0:
        print(f"[snapshot-inv] Ya existe snapshot para {fecha_str}, omitiendo")
        return {"fecha": fecha_str, "inventario_general": 0, "ubicacion": 0, "skipped": True}

    # Snapshot de inventario general (inv_resumen_modelo)
    rows_ig = execute_query("""
        INSERT INTO snapshot_inventario_general
            (fecha_snapshot, modelo, nparte, stock_total, ubicaciones, ultima_entrada, ultima_salida, tipo_inventario)
        SELECT
            %s, modelo, nparte, stock_total, ubicaciones, ultima_entrada, ultima_salida, tipo_inventario
        FROM inv_resumen_modelo
    """, [fecha_str])

    # Snapshot de ubicacion (ubicacionimdinv)
    rows_ub = execute_query("""
        INSERT INTO snapshot_ubicacion
            (fecha_snapshot, modelo, nparte, fecha, ubicacion, cantidad, tipo_inventario, comentario, carro)
        SELECT
            %s, modelo, nparte, fecha, ubicacion, cantidad, tipo_inventario, comentario, carro
        FROM ubicacionimdinv
    """, [fecha_str])

    result = {
        "fecha": fecha_str,
        "inventario_general": rows_ig if isinstance(rows_ig, int) else 0,
        "ubicacion": rows_ub if isinstance(rows_ub, int) else 0,
        "skipped": False
    }
    print(f"[snapshot-inv] Snapshot completado: {result}")
    return result


# ---------------------------------------------------------------------------
# Worker daemon (arrancado desde startup_init.py)
# ---------------------------------------------------------------------------


def _snapshot_inv_daily_loop():
    """Loop background que duerme hasta las 7:30 AM Monterrey, toma snapshot, repite."""
    while True:
        try:
            now = datetime.now(_SNAPSHOT_INV_TZ)
            target_today = now.replace(
                hour=_SNAPSHOT_INV_TARGET_HOUR,
                minute=_SNAPSHOT_INV_TARGET_MINUTE,
                second=0, microsecond=0
            )
            if now >= target_today:
                target = target_today + timedelta(days=1)
            else:
                target = target_today

            sleep_seconds = max(60, (target - now).total_seconds())
            print(f"[snapshot-inv] Durmiendo {sleep_seconds:.0f}s hasta {target.strftime('%Y-%m-%d %H:%M')}")
            time.sleep(sleep_seconds)

            result = _snapshot_inv_tomar()
            print(f"[snapshot-inv] Resultado: {result}")
        except Exception as e:
            print(f"[snapshot-inv] Error: {e}")
            time.sleep(300)


def iniciar_snapshot_inv_worker():
    """Iniciar thread daemon para snapshot diario de inventario"""
    global _snapshot_inv_thread
    if _env_flag("SNAPSHOT_INV_DISABLE", False):
        print("[snapshot-inv] Deshabilitado por SNAPSHOT_INV_DISABLE")
        return

    with _snapshot_inv_lock:
        if _snapshot_inv_thread and _snapshot_inv_thread.is_alive():
            return
        _snapshot_inv_thread = threading.Thread(
            target=_snapshot_inv_daily_loop,
            name="snapshot-inv-daily",
            daemon=True,
        )
        _snapshot_inv_thread.start()
        print("[snapshot-inv] Worker iniciado (target 07:30 America/Monterrey)")


# ---------------------------------------------------------------------------
# Endpoints HTTP
# ---------------------------------------------------------------------------


@bp.route("/api/snapshot_inventario/fechas", methods=["GET"])
@login_requerido
def api_snapshot_inv_fechas():
    """Listar fechas disponibles de snapshots de inventario con hora"""
    try:
        sql = """
            SELECT fecha_snapshot,
                   DATE_FORMAT(DATE_SUB(MIN(created_at), INTERVAL 6 HOUR), '%H:%i') AS hora_snapshot
            FROM snapshot_inventario_general
            GROUP BY fecha_snapshot
            ORDER BY fecha_snapshot DESC
            LIMIT 365
        """
        rows = execute_query(sql, fetch="all")
        fechas = []
        for r in (rows or []):
            fechas.append({
                "fecha": str(r["fecha_snapshot"]),
                "hora": r.get("hora_snapshot") or ""
            })
        return jsonify({"status": "success", "fechas": fechas})
    except Exception as e:
        print(f"Error en api_snapshot_inv_fechas: {e}")
        return jsonify({"status": "error", "message": str(e), "fechas": []}), 500


@bp.route("/api/snapshot_inventario/general", methods=["GET"])
@login_requerido
def api_snapshot_inv_general():
    """Consultar snapshot de inventario general por fecha"""
    try:
        fecha = request.args.get("fecha", "", type=str).strip()
        if not fecha:
            return jsonify({"status": "error", "message": "Parametro 'fecha' requerido"}), 400

        q = request.args.get("q", "", type=str).strip()
        where = ["fecha_snapshot = %s"]
        params = [fecha]

        if q:
            where.append("(modelo LIKE %s OR nparte LIKE %s)")
            params.extend([f"%{q}%", f"%{q}%"])

        where_sql = ' AND '.join(where)
        sql = (
            "SELECT modelo, nparte, stock_total, ubicaciones,"
            " DATE_FORMAT(ultima_entrada, '%%Y-%%m-%%d %%H:%%i:%%s') AS ultima_entrada,"
            " DATE_FORMAT(ultima_salida,  '%%Y-%%m-%%d %%H:%%i:%%s') AS ultima_salida,"
            " tipo_inventario"
            " FROM snapshot_inventario_general"
            f" WHERE {where_sql}"
            " ORDER BY modelo, nparte"
            " LIMIT 2000"
        )
        results = execute_query(sql, params, fetch="all")
        return jsonify({"status": "success", "fecha": fecha, "items": results or []})

    except Exception as e:
        print(f"Error en api_snapshot_inv_general: {e}")
        return jsonify({"status": "error", "message": str(e), "items": []}), 500


@bp.route("/api/snapshot_inventario/ubicacion", methods=["GET"])
@login_requerido
def api_snapshot_inv_ubicacion():
    """Consultar snapshot de ubicacion por fecha"""
    try:
        fecha = request.args.get("fecha", "", type=str).strip()
        if not fecha:
            return jsonify({"status": "error", "message": "Parametro 'fecha' requerido"}), 400

        q = request.args.get("q", "", type=str).strip()
        where = ["fecha_snapshot = %s"]
        params = [fecha]

        if q:
            where.append("(modelo LIKE %s OR nparte LIKE %s OR ubicacion LIKE %s)")
            params.extend([f"%{q}%", f"%{q}%", f"%{q}%"])

        sql = f"""
            SELECT modelo, nparte, fecha, ubicacion, cantidad,
                   tipo_inventario, comentario, carro
            FROM snapshot_ubicacion
            WHERE {' AND '.join(where)}
            ORDER BY modelo, nparte
            LIMIT 5000
        """
        results = execute_query(sql, params, fetch="all")
        return jsonify({"status": "success", "fecha": fecha, "items": results or []})

    except Exception as e:
        print(f"Error en api_snapshot_inv_ubicacion: {e}")
        return jsonify({"status": "error", "message": str(e), "items": []}), 500


@bp.route("/api/snapshot_inventario/trigger", methods=["POST"])
@login_requerido
def api_snapshot_inv_trigger():
    """Trigger manual para tomar snapshot de inventario"""
    try:
        data = request.get_json(silent=True) or {}
        fecha_str = data.get("fecha", "").strip() if isinstance(data.get("fecha"), str) else ""

        fecha_override = None
        if fecha_str:
            try:
                fecha_override = date.fromisoformat(fecha_str)
            except ValueError:
                return jsonify({"status": "error", "message": "Formato de fecha invalido. Use YYYY-MM-DD"}), 400

        result = _snapshot_inv_tomar(fecha_override=fecha_override)
        return jsonify({"status": "success", "result": result})
    except Exception as e:
        print(f"Error en api_snapshot_inv_trigger: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
