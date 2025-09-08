# -*- coding: utf-8 -*-
import json
import hashlib
from typing import List, Dict, Any
from decimal import Decimal
import datetime

from flask import Blueprint, render_template, request, jsonify, session

from ..config_mysql import execute_query
from .settings import TABLE_NAME, SAFETY_LIMIT, USER_NAME

EXCLUDE_COLS = {"id", "created_at", "updated_at"}
MANDATORY_EXTRA_COL = "usuario"


def init_control_modelos_table():
    """Verifica que la tabla raw_smd exista y tiene la estructura necesaria"""
    try:
        # Verificar si la tabla existe
        result = execute_query(
            "SHOW TABLES LIKE %s",
            (TABLE_NAME,),
            fetch='one'
        )
        
        if result:
            print(f"Tabla {TABLE_NAME} encontrada")
            # Solo verificar/agregar la columna usuario
            ensure_usuario_column()
        else:
            print(f"ADVERTENCIA: La tabla {TABLE_NAME} no existe en la base de datos")
            
    except Exception as e:
        print(f"Error verificando tabla: {e}")


def insert_sample_data():
    """Esta función ya no se usa ya que la tabla tiene datos reales"""
    pass


def get_current_user():
    """Obtiene el usuario actual de la sesión"""
    try:
        # Primero intentar obtener el nombre completo
        nombre_completo = session.get('nombre_completo', '')
        if nombre_completo:
            return nombre_completo
        
        # Si no hay nombre completo, usar el usuario
        usuario = session.get('usuario', '')
        if usuario:
            return usuario
            
        # Fallback al valor por defecto
        return USER_NAME
    except Exception as e:
        print(f"Error obteniendo usuario de sesión: {e}")
        return USER_NAME


def ensure_usuario_column():
    """Asegura que la columna 'usuario' exista en la tabla"""
    try:
        # Verificar si la columna existe
        result = execute_query(
            f"SHOW COLUMNS FROM `{TABLE_NAME}` LIKE %s",
            (MANDATORY_EXTRA_COL,),
            fetch='one'
        )
        
        if not result:
            # Agregar la columna si no existe
            execute_query(
                f"ALTER TABLE `{TABLE_NAME}` ADD COLUMN `{MANDATORY_EXTRA_COL}` varchar(128) NULL"
            )
    except Exception as e:
        print(f"Error verificando/agregando columna usuario: {e}")


def get_columns_excluding() -> List[str]:
    """Obtiene las columnas de la tabla excluyendo las especificadas"""
    try:
        result = execute_query(f"SHOW COLUMNS FROM `{TABLE_NAME}`", fetch='all')
        cols = [row['Field'] for row in result if row['Field'] not in EXCLUDE_COLS]
        
        if MANDATORY_EXTRA_COL not in cols:
            cols.append(MANDATORY_EXTRA_COL)
        return cols
    except Exception as e:
        print(f"Error obteniendo columnas: {e}")
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


def control_modelos_smt_index():
    """Función principal que muestra la tabla de modelos SMT"""
    ensure_usuario_column()
    columns = get_columns_excluding()

    try:
        select_cols = ", ".join([f"`{c}`" for c in columns]) if columns else "*"
        limit_clause = f" LIMIT {SAFETY_LIMIT}" if SAFETY_LIMIT and SAFETY_LIMIT > 0 else ""
        
        # Ordenar por ID descendente para mostrar los más nuevos primero
        query = f"SELECT {select_cols} FROM `{TABLE_NAME}` ORDER BY id DESC{limit_clause}"
        result = execute_query(query, fetch='all')
        rows = result if result else []

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
            user_name=USER_NAME,
        )
    except Exception as e:
        print(f"Error en control_modelos_smt_index: {e}")
        return render_template(
            "INFORMACION BASICA/Control_modelos_SMT.html",
            columns=[],
            rows=[],
            table_name=TABLE_NAME,
            total=0,
            user_name=USER_NAME,
        )


def api_create_row():
    """API para crear un nuevo registro"""
    ensure_usuario_column()
    payload = request.get_json(force=True) or {}
    columns = get_columns_excluding()

    # Obtener el usuario actual de la sesión
    current_user = get_current_user()
    
    if (MANDATORY_EXTRA_COL in columns) and (not payload.get(MANDATORY_EXTRA_COL)):
        payload[MANDATORY_EXTRA_COL] = current_user

    insert_cols = [c for c in columns if c in payload]
    if not insert_cols:
        return jsonify({"ok": False, "error": "No hay campos válidos para insertar."}), 400

    try:
        values = [payload.get(c) for c in insert_cols]
        placeholders = ", ".join(["%s"] * len(insert_cols))
        colnames = ", ".join([f"`{c}`" for c in insert_cols])
        
        query = f"INSERT INTO `{TABLE_NAME}` ({colnames}) VALUES ({placeholders})"
        execute_query(query, values)
        
        print(f"✅ Registro creado por usuario: {current_user}")
        return jsonify({"ok": True})
    except Exception as e:
        print(f"Error creando registro: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


def api_update_row(rowhash: str):
    """API para actualizar un registro existente"""
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
        return jsonify({"ok": False, "error": "Sin cambios válidos."}), 400

    try:
        # Construir la consulta UPDATE
        set_expr = ", ".join([f"`{c}` = %s" for c in set_cols])
        values = [changes[c] for c in set_cols]
        
        # Construir las condiciones WHERE
        where_parts = []
        for c in columns:
            if original_norm.get(c) is None:
                where_parts.append(f"`{c}` IS NULL")
            else:
                where_parts.append(f"`{c}` = %s")
                values.append(original_norm.get(c))
        
        query = f"UPDATE `{TABLE_NAME}` SET {set_expr} WHERE " + " AND ".join(where_parts) + " LIMIT 1"
        result = execute_query(query, values)
        
        # Verificar que se actualizó al menos una fila
        if result is None:  # Si no hay información de filas afectadas, asumimos éxito
            return jsonify({"ok": True})
        
        return jsonify({"ok": True})
    except Exception as e:
        print(f"Error actualizando registro: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


def api_delete_row(rowhash: str):
    """API para eliminar un registro"""
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
        result = execute_query(query, values)
        
        return jsonify({"ok": True})
    except Exception as e:
        print(f"Error eliminando registro: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


# Crear el blueprint
control_modelos_bp = Blueprint('control_modelos', __name__, url_prefix='/control-modelos')

@control_modelos_bp.route("/", methods=["GET"])
def index():
    """Página principal del control de modelos SMT"""
    init_control_modelos_table()
    ensure_usuario_column()
    columns = get_columns_excluding()

    # Obtener el usuario actual de la sesión
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
        print(f"Error cargando datos: {e}")
        return render_template(
            "INFORMACION BASICA/Control_modelos_SMT.html",
            columns=columns,
            rows=[],
            table_name=TABLE_NAME,
            total=0,
            user_name=current_user,
            error=str(e)
        )


@control_modelos_bp.route("/api/rows", methods=["POST"])
def api_create():
    """API para crear un nuevo registro"""
    return api_create_row()


@control_modelos_bp.route("/api/rows/<rowhash>", methods=["PUT"])
def api_update(rowhash: str):
    """API para actualizar un registro"""
    return api_update_row(rowhash)


@control_modelos_bp.route("/api/rows/<rowhash>", methods=["DELETE"])
def api_delete(rowhash: str):
    """API para eliminar un registro"""
    return api_delete_row(rowhash)


@control_modelos_bp.route("/api/data", methods=["GET"])
def api_get_data():
    """API para obtener datos actualizados sin recargar la página"""
    ensure_usuario_column()
    columns = get_columns_excluding()

    try:
        select_cols = ", ".join([f"`{c}`" for c in columns]) if columns else "*"
        limit_clause = f" LIMIT {SAFETY_LIMIT}" if SAFETY_LIMIT and SAFETY_LIMIT > 0 else ""
        
        # Ordenar por ID descendente para mostrar los más nuevos primero
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
        print(f"Error obteniendo datos actualizados: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500
