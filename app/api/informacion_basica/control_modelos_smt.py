"""Endpoints HTTP del modulo Control de modelos SMT.

Forma parte de Informacion Basica (LISTA_INFORMACIONBASICA). Gestiona la
tabla `raw_smd` que es el catalogo maestro de modelos para SMT.

Rutas:
  GET    /control-modelos-smt-ajax       -> render del template AJAX (fragment)
  GET    /control-modelos/               -> render del template standalone (legacy)
  GET    /control-modelos/api/data       -> JSON con columnas + filas
  POST   /control-modelos/api/rows       -> crear fila
  PUT    /control-modelos/api/rows/<rowhash>    -> actualizar fila (con check de hash)
  DELETE /control-modelos/api/rows/<rowhash>    -> borrar fila (con check de hash)

Migrado desde `app/py/control_modelos_smt.py` (2026-05-22). Cambios:
  - Se INLINE las 3 constantes que estaban en `app/py/settings.py`
    (TABLE_NAME, SAFETY_LIMIT, USER_NAME) — no vale la pena un settings.py
    aparte para 3 constantes especificas del modulo.
  - Se integra la ruta huerfana `/control-modelos-smt-ajax` que vivia en
    `app/routes.py:24354` (solo renderizaba el template; sin razon para
    estar separada).
  - Mismo blueprint name 'control_modelos' y mismas rutas: frontend y JS
    no requieren cambios.

NOTA WF_003: usa `execute_query()` correctamente — el modulo ya cumplia
WF_003 desde antes de la migracion.
"""

import datetime
import hashlib
import json
from decimal import Decimal
from typing import Any, Dict, List

from flask import Blueprint, jsonify, render_template, request, session

from app.api.shared import execute_query

import logging
logger = logging.getLogger(__name__)


# Constantes del modulo (ex `app/py/settings.py`)
TABLE_NAME = "raw_smd"
SAFETY_LIMIT = 2000
USER_NAME = "sistema"

EXCLUDE_COLS = {"id", "created_at", "updated_at"}
MANDATORY_EXTRA_COL = "usuario"


bp = Blueprint('control_modelos', __name__, url_prefix='/control-modelos')


# ============================================================
# Helpers de tabla y normalizacion
# ============================================================

def init_control_modelos_table():
    """Verifica que la tabla raw_smd exista y tiene la estructura necesaria."""
    try:
        result = execute_query(
            "SHOW TABLES LIKE %s",
            (TABLE_NAME,),
            fetch='one'
        )

        if result:
            logger.info(f"Tabla {TABLE_NAME} encontrada")
            ensure_usuario_column()
        else:
            logger.warning(f"ADVERTENCIA: La tabla {TABLE_NAME} no existe en la base de datos")

    except Exception as e:
        logger.error(f"Error verificando tabla: {e}")


def get_current_user():
    """Obtiene el usuario actual de la sesion."""
    try:
        nombre_completo = session.get('nombre_completo', '')
        if nombre_completo:
            return nombre_completo

        usuario = session.get('usuario', '')
        if usuario:
            return usuario

        return USER_NAME
    except Exception as e:
        logger.error(f"Error obteniendo usuario de sesion: {e}")
        return USER_NAME


def ensure_usuario_column():
    """Asegura que la columna 'usuario' exista en la tabla."""
    try:
        result = execute_query(
            f"SHOW COLUMNS FROM `{TABLE_NAME}` LIKE %s",
            (MANDATORY_EXTRA_COL,),
            fetch='one'
        )

        if not result:
            execute_query(
                f"ALTER TABLE `{TABLE_NAME}` ADD COLUMN `{MANDATORY_EXTRA_COL}` varchar(128) NULL"
            )
    except Exception as e:
        logger.error(f"Error verificando/agregando columna usuario: {e}")


def get_columns_excluding() -> List[str]:
    """Obtiene las columnas de la tabla excluyendo las especificadas."""
    try:
        result = execute_query(f"SHOW COLUMNS FROM `{TABLE_NAME}`", fetch='all')
        cols = [row['Field'] for row in result if row['Field'] not in EXCLUDE_COLS]

        if MANDATORY_EXTRA_COL not in cols:
            cols.append(MANDATORY_EXTRA_COL)
        return cols
    except Exception as e:
        logger.error(f"Error obteniendo columnas: {e}")
        return []


def normalize_value(v):
    if isinstance(v, Decimal):
        return str(v)
    if isinstance(v, (datetime.datetime, datetime.date)):
        return v.isoformat()
    return v


def normalize_row(row: Dict[str, Any], columns: List[str]) -> Dict[str, Any]:
    return {c: normalize_value(row.get(c)) for c in columns}


def compute_rowhash(row: Dict[str, Any], columns: List[str]) -> str:
    payload = json.dumps(
        [normalize_value(row.get(c)) for c in columns],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


# ============================================================
# Rutas: vistas HTML
# ============================================================

@bp.route("/", methods=["GET"])
def index():
    """Pagina standalone del control de modelos SMT (legacy / acceso directo)."""
    init_control_modelos_table()
    ensure_usuario_column()
    columns = get_columns_excluding()

    current_user = get_current_user()

    if not columns:
        return render_template(
            "INFORMACION BASICA/Control_modelos_SMT.html",
            columns=[],
            rows=[],
            table_name=TABLE_NAME,
            total=0,
            user_name=current_user,
        )

    try:
        select_cols = ", ".join([f"`{c}`" for c in columns])
        limit_clause = f" LIMIT {SAFETY_LIMIT}" if SAFETY_LIMIT and SAFETY_LIMIT > 0 else ""

        query = f"SELECT {select_cols} FROM `{TABLE_NAME}`{limit_clause}"
        rows = execute_query(query, fetch='all')

        norm_rows = []
        for r in rows:
            n = normalize_row(r, columns)
            n["__rowhash"] = compute_rowhash(n, columns)
            norm_rows.append(n)

        return render_template(
            "INFORMACION BASICA/Control_modelos_SMT.html",
            columns=columns,
            rows=norm_rows,
            table_name=TABLE_NAME,
            total=len(norm_rows),
            user_name=current_user,
        )
    except Exception as e:
        logger.error(f"Error cargando datos: {e}")
        return render_template(
            "INFORMACION BASICA/Control_modelos_SMT.html",
            columns=columns,
            rows=[],
            table_name=TABLE_NAME,
            total=0,
            user_name=current_user,
            error=str(e)
        )


# Segundo blueprint SIN url_prefix para la ruta huerfana
# `/control-modelos-smt-ajax` (era una ruta absoluta en routes.py que solo
# renderizaba el template AJAX). Se expone como `bp_ajax` y se registra
# junto con `bp` desde app/api/__init__.py.
bp_ajax = Blueprint('control_modelos_smt_ajax', __name__)


@bp_ajax.route("/control-modelos-smt-ajax", methods=["GET"])
def control_modelos_smt_ajax():
    """Ruta AJAX para cargar dinamicamente el contenido (fragment HTML)."""
    try:
        usuario_actual = session.get(
            "nombre_completo", session.get("usuario", "Usuario no identificado")
        ).strip()
        return render_template(
            "INFORMACION BASICA/control_modelos_smt_ajax.html", usuario=usuario_actual
        )
    except Exception as e:
        logger.error(f"Error al cargar template Control de Modelos SMT AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


# ============================================================
# Rutas: APIs JSON
# ============================================================

@bp.route("/api/data", methods=["GET"])
def api_get_data():
    """API para obtener datos actualizados sin recargar la pagina."""
    ensure_usuario_column()
    columns = get_columns_excluding()

    try:
        select_cols = ", ".join([f"`{c}`" for c in columns]) if columns else "*"
        limit_clause = f" LIMIT {SAFETY_LIMIT}" if SAFETY_LIMIT and SAFETY_LIMIT > 0 else ""

        query = f"SELECT {select_cols} FROM `{TABLE_NAME}` ORDER BY id DESC{limit_clause}"
        result = execute_query(query, fetch='all')
        rows = result if result else []

        norm_rows = []
        for r in rows:
            n = normalize_row(r, columns)
            n["__rowhash"] = compute_rowhash(n, columns)
            norm_rows.append(n)

        return jsonify({
            "ok": True,
            "columns": columns,
            "rows": norm_rows,
            "total": len(norm_rows)
        })
    except Exception as e:
        logger.error(f"Error obteniendo datos actualizados: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


@bp.route("/api/rows", methods=["POST"])
def api_create():
    """API para crear un nuevo registro."""
    ensure_usuario_column()
    payload = request.get_json(force=True) or {}
    columns = get_columns_excluding()

    current_user = get_current_user()

    if (MANDATORY_EXTRA_COL in columns) and (not payload.get(MANDATORY_EXTRA_COL)):
        payload[MANDATORY_EXTRA_COL] = current_user

    insert_cols = [c for c in columns if c in payload]
    if not insert_cols:
        return jsonify({"ok": False, "error": "No hay campos validos para insertar."}), 400

    try:
        values = [payload.get(c) for c in insert_cols]
        placeholders = ", ".join(["%s"] * len(insert_cols))
        colnames = ", ".join([f"`{c}`" for c in insert_cols])

        query = f"INSERT INTO `{TABLE_NAME}` ({colnames}) VALUES ({placeholders})"
        execute_query(query, values)

        logger.info(f"Registro creado por usuario: {current_user}")
        return jsonify({"ok": True})
    except Exception as e:
        logger.error(f"Error creando registro: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


@bp.route("/api/rows/<rowhash>", methods=["PUT"])
def api_update(rowhash: str):
    """API para actualizar un registro (con check de rowhash para concurrencia)."""
    ensure_usuario_column()
    data = request.get_json(force=True) or {}
    original = data.get("original") or {}
    changes = data.get("changes") or {}

    columns = get_columns_excluding()
    original_norm = normalize_row(original, columns)

    if compute_rowhash(original_norm, columns) != rowhash:
        return jsonify({"ok": False, "error": "Rowhash no coincide con los datos originales."}), 409

    set_cols = [c for c in changes.keys() if c in columns]
    if not set_cols:
        return jsonify({"ok": False, "error": "Sin cambios validos."}), 400

    try:
        set_expr = ", ".join([f"`{c}` = %s" for c in set_cols])
        values = [changes[c] for c in set_cols]

        where_parts = []
        for c in columns:
            if original_norm.get(c) is None:
                where_parts.append(f"`{c}` IS NULL")
            else:
                where_parts.append(f"`{c}` = %s")
                values.append(original_norm.get(c))

        query = f"UPDATE `{TABLE_NAME}` SET {set_expr} WHERE " + " AND ".join(where_parts) + " LIMIT 1"
        execute_query(query, values)

        return jsonify({"ok": True})
    except Exception as e:
        logger.error(f"Error actualizando registro: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


@bp.route("/api/rows/<rowhash>", methods=["DELETE"])
def api_delete(rowhash: str):
    """API para eliminar un registro (con check de rowhash)."""
    data = request.get_json(force=True) or {}
    original = data.get("original") or {}
    columns = get_columns_excluding()

    original_norm = normalize_row(original, columns)

    if compute_rowhash(original_norm, columns) != rowhash:
        return jsonify({"ok": False, "error": "Rowhash no coincide."}), 409

    try:
        values = []
        where_parts = []
        for c in columns:
            if original_norm.get(c) is None:
                where_parts.append(f"`{c}` IS NULL")
            else:
                where_parts.append(f"`{c}` = %s")
                values.append(original_norm.get(c))

        query = f"DELETE FROM `{TABLE_NAME}` WHERE " + " AND ".join(where_parts) + " LIMIT 1"
        execute_query(query, values)

        return jsonify({"ok": True})
    except Exception as e:
        logger.error(f"Error eliminando registro: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


# Alias publico para mantener compatibilidad con el nombre anterior.
control_modelos_bp = bp
