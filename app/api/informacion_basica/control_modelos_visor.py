"""Endpoints HTTP del modulo Control de modelos (visor MySQL).

Forma parte de Informacion Basica (LISTA_INFORMACIONBASICA). Es un visor/editor
generico de tablas MySQL — el frontend pasa el nombre de tabla y la API
devuelve columnas + datos paginados con filtros y ordenamiento inteligente.

Rutas (HTML):
  GET    /visor-mysql                       -> render standalone (legacy)
  GET    /control-modelos-visor-ajax        -> render fragment para AJAX

Rutas (API JSON):
  GET    /api/mysql                         -> consulta SQL directa (CORS, sin auth, para Android)
  GET    /api/mysql/columns                 -> lista columnas de una tabla
  GET    /api/mysql/data                    -> datos paginados con filtros
  POST   /api/mysql/update                  -> actualizar registro (tabla 'raw' hardcoded)
  POST   /api/mysql/create                  -> crear registro (tabla 'raw' hardcoded)
  GET    /api/mysql/usuario-actual          -> devolver usuario logueado
  POST   /api/mysql/delete                  -> eliminar registro por id

Migrado desde `app/routes.py:22819-23520` (2026-05-22). Mismas URLs y
mismo formato de respuesta para que JS y consumidores externos (Android
que usa /api/mysql) sigan funcionando.

NOTA WF_003: usa `execute_query()` correctamente (ya cumplia desde antes).

Se exponen DOS blueprints porque las rutas tienen url_prefix distintos:
  - `bp`       -> sin prefix (las URLs son absolutas: /visor-mysql, /api/mysql, etc.)
  - bp_ajax    -> sin prefix tambien (la URL absoluta /control-modelos-visor-ajax)

Para simplificar se usa un solo blueprint sin prefix para todas las rutas.
"""

import re
import traceback

from flask import Blueprint, jsonify, render_template, request, session

from app.api.shared import execute_query, login_requerido


bp = Blueprint('control_modelos_visor', __name__)


# ============================================================
# Rutas: vistas HTML
# ============================================================

@bp.route("/visor-mysql")
def visor_mysql():
    """Visor de tablas MySQL standalone (legacy / acceso directo)."""
    table = request.args.get("table", "raw")
    if not re.match(r"^[A-Za-z0-9_]+$", table):
        table = "raw"
    return render_template("visor_mysql.html", table=table)


@bp.route("/control-modelos-visor-ajax")
@login_requerido
def control_modelos_visor_ajax():
    """Ruta AJAX para cargar dinamicamente el visor MySQL para Control de modelos."""
    try:
        table = request.args.get("table", "raw")
        if not re.match(r"^[A-Za-z0-9_]+$", table):
            table = "raw"

        usuario_actual = session.get(
            "nombre_completo", session.get("usuario", "Usuario no identificado")
        ).strip()

        return render_template(
            "INFORMACION BASICA/control_modelos_visor_ajax.html",
            table=table,
            usuario=usuario_actual,
        )
    except Exception as e:
        print(f"Error al cargar template de visor MySQL: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


# ============================================================
# API generica para Android (sin auth, con CORS)
# ============================================================

@bp.route("/api/mysql", methods=["POST", "GET", "OPTIONS"])
def api_mysql_simple():
    """Ruta API simple para consultas MySQL desde Android (sin autenticacion)."""
    try:
        if request.method == "OPTIONS":
            response = jsonify({"status": "ok"})
            response.headers.add("Access-Control-Allow-Origin", "*")
            response.headers.add("Access-Control-Allow-Headers", "Content-Type")
            response.headers.add("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
            return response

        if request.method == "POST":
            data = request.get_json()
            if not data:
                return jsonify({"success": False, "error": "No se recibio JSON"}), 400
            sql_query = data.get("sql", "").strip()
        else:
            sql_query = request.args.get("sql", "").strip()

        if not sql_query:
            sql_query = "SELECT COUNT(*) as total_materiales FROM materiales"
            print(f"No se proporciono SQL, usando consulta por defecto: {sql_query}")

        print(f"Ejecutando consulta API simple: {sql_query}")

        sql_upper = sql_query.upper()
        if not sql_upper.startswith("SELECT") and not sql_upper.startswith("SHOW"):
            return jsonify(
                {"success": False, "error": "Solo se permiten consultas SELECT y SHOW"}
            ), 403

        result = execute_query(sql_query, fetch="all")

        response_data = {
            "success": True,
            "data": result if result else [],
            "count": len(result) if result else 0,
        }

        response = jsonify(response_data)
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type")
        response.headers.add("Access-Control-Allow-Methods", "GET,POST,OPTIONS")

        print(f"API Simple - Consulta exitosa: {len(result) if result else 0} registros")
        return response

    except Exception as e:
        print(f"Error en API MySQL Simple: {e}")
        error_response = jsonify({"success": False, "error": str(e)})
        error_response.headers.add("Access-Control-Allow-Origin", "*")
        return error_response, 500


# ============================================================
# APIs de visor: columnas, data, CRUD
# ============================================================

@bp.route("/api/mysql/columns")
def api_mysql_columns():
    """API para obtener columnas de una tabla."""
    try:
        table = request.args.get("table", "raw")
        if not re.match(r"^[A-Za-z0-9_]+$", table):
            return jsonify({"error": "Nombre de tabla invalido"}), 400

        query = """
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=%s
        ORDER BY ORDINAL_POSITION
        """

        result = execute_query(query, (table,), fetch="all")
        if result is not None:
            columns = [row["COLUMN_NAME"] for row in result]
            return jsonify({"table": table, "columns": columns})
        else:
            return jsonify({"table": table, "columns": []})

    except Exception as e:
        print(f"Error en api_mysql_columns: {e}")
        return jsonify({"error": str(e)}), 500


@bp.route("/api/mysql/data")
def api_mysql_data():
    """API para obtener datos de una tabla con filtros y ordenamiento inteligente."""
    try:
        table = request.args.get("table", "raw")
        if not re.match(r"^[A-Za-z0-9_]+$", table):
            return jsonify({"error": "Nombre de tabla invalido"}), 400

        limit = min(max(int(request.args.get("limit", 200)), 1), 2000)
        offset = max(int(request.args.get("offset", 0)), 0)
        search = (request.args.get("search") or "").strip()

        cols_query = """
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=%s
        ORDER BY ORDINAL_POSITION
        """
        cols_result = execute_query(cols_query, (table,), fetch="all")
        if not cols_result:
            return jsonify({"table": table, "columns": [], "rows": [], "total": 0})

        columns = [row["COLUMN_NAME"] for row in cols_result]

        base_sql = f"SELECT * FROM `{table}`"
        where = ""
        params = []

        if search:
            like_conditions = []
            for col in columns:
                like_conditions.append(f"CAST(`{col}` AS CHAR) LIKE %s")
            where = f" WHERE ({' OR '.join(like_conditions)})"
            params = [f"%{search}%"] * len(columns)

        # Ordenamiento inteligente para agrupar modelos similares.
        model_columns = []
        for col in columns:
            col_lower = col.lower()
            if any(
                keyword in col_lower
                for keyword in ["modelo", "model", "codigo", "parte", "part", "ebr", "product"]
            ):
                model_columns.append(col)

        order_by = ""
        if model_columns:
            main_col = model_columns[0]
            order_by = (
                f" ORDER BY REGEXP_REPLACE(`{main_col}`, '[0-9]+$', ''), `{main_col}`"
            )
        else:
            if columns:
                order_by = f" ORDER BY `{columns[0]}`"

        count_sql = f"SELECT COUNT(*) as total FROM `{table}`{where}"
        count_result = execute_query(count_sql, params, fetch="one")
        total = count_result["total"] if count_result else 0

        data_sql = f"{base_sql}{where}{order_by} LIMIT %s OFFSET %s"
        data_params = params + [limit, offset]
        data_result = execute_query(data_sql, data_params, fetch="all")

        rows = data_result if data_result else []

        return jsonify(
            {
                "table": table,
                "columns": columns,
                "rows": rows,
                "total": total,
                "limit": limit,
                "offset": offset,
                "search": search,
                "ordering": f"Ordenado por: {main_col if model_columns else columns[0] if columns else 'N/A'}",
            }
        )

    except Exception as e:
        print(f"Error en api_mysql_data: {e}")
        return jsonify({"error": str(e)}), 500


@bp.route("/api/mysql/update", methods=["POST"])
def api_mysql_update():
    """API para actualizar registros en tabla raw."""

    def clean_column_value(column_name, value):
        """Limpiar y validar valores segun el tipo de columna."""
        if value is None or value == "":
            return None

        value = str(value).strip()

        numeric_columns = [
            "hora_dia", "c_t", "uph", "price", "st", "neck_st", "l_b", "input", "output",
        ]

        if column_name in numeric_columns:
            cleaned = value.replace(",", "").replace(" ", "")

            if not cleaned:
                return None

            try:
                float(cleaned)
                return cleaned
            except ValueError:
                print(f"Valor no numerico para columna {column_name}: {value}, usando NULL")
                return None

        return value if value != "" else None

    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No se recibieron datos"}), 400

        # Por seguridad, solo permitir actualizar tabla raw
        table = "raw"

        original_data = data.get("original", {})
        new_data = data.get("new", {})

        if not original_data or not new_data:
            return jsonify({"error": "Faltan datos originales o nuevos"}), 400

        # Campos clave que normalmente no cambian (identificadores unicos).
        key_fields = ["part_no", "model", "project", "main_display", "linea"]

        where_conditions = []
        where_params = []

        for key in key_fields:
            if key in original_data:
                value = original_data[key]
                if value is None or value == "" or value == "NULL":
                    where_conditions.append(
                        f"(`{key}` IS NULL OR `{key}` = '' OR `{key}` = 'NULL')"
                    )
                else:
                    where_conditions.append(f"`{key}` = %s")
                    where_params.append(value)

        # Si no hay suficientes campos clave, usar los primeros 5 campos no modificados.
        if len(where_conditions) < 3:
            used_fields = set(key_fields)
            for key, value in original_data.items():
                if key not in used_fields and len(where_conditions) < 5:
                    if key not in new_data or new_data[key] == value:
                        if value is None or value == "" or value == "NULL":
                            where_conditions.append(
                                f"(`{key}` IS NULL OR `{key}` = '' OR `{key}` = 'NULL')"
                            )
                        else:
                            where_conditions.append(f"`{key}` = %s")
                            where_params.append(value)
                        used_fields.add(key)

        if not where_conditions:
            return jsonify(
                {"error": "No se pueden identificar los datos originales"}
            ), 400

        # Excluir columnas generadas y de solo lectura.
        readonly_columns = ["Usuario", "crea", "upt"]

        set_conditions = []
        set_params = []

        for key, value in new_data.items():
            if key in readonly_columns:
                print(f"Saltando columna de solo lectura: {key}")
                continue

            cleaned_value = clean_column_value(key, value)

            set_conditions.append(f"`{key}` = %s")
            set_params.append(cleaned_value)

        if not set_conditions:
            return jsonify(
                {
                    "error": "No hay datos validos para actualizar (todas las columnas son de solo lectura)"
                }
            ), 400

        update_sql = f"""
            UPDATE `{table}`
            SET {", ".join(set_conditions)}
            WHERE {" AND ".join(where_conditions)}
            LIMIT 1
        """

        params = set_params + where_params

        result = execute_query(update_sql, params, fetch="none")

        if result is not False:
            return jsonify(
                {"success": True, "message": "Registro actualizado exitosamente"}
            )
        else:
            return jsonify({"error": "No se pudo actualizar el registro"}), 500

    except Exception as e:
        print(f"Error en api_mysql_update: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@bp.route("/api/mysql/create", methods=["POST"])
def api_mysql_create():
    """Crear nuevo registro en tabla raw."""
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No se enviaron datos"}), 400

        new_data = data.get("data", {})

        if not new_data:
            return jsonify({"error": "No se enviaron datos para crear"}), 400

        table = "raw"

        def clean_column_value(column_name, value):
            if value is None:
                return None

            if isinstance(value, str) and value.strip() == "":
                return None

            numeric_fields = [
                "hora_dia", "c_t", "uph", "price", "st", "neck_st", "l_b", "input", "output",
            ]
            if column_name in numeric_fields and isinstance(value, str):
                cleaned = value.replace(",", "").strip()
                if cleaned == "":
                    return None
                return cleaned

            return value

        readonly_fields = ["crea", "upt", "raw"]
        insert_data = {}

        if "Usuario" not in new_data:
            new_data["Usuario"] = session.get(
                "nombre_completo", session.get("usuario", "Sistema")
            ).strip()

        for key, value in new_data.items():
            if key not in readonly_fields:
                cleaned_value = clean_column_value(key, value)
                insert_data[key] = cleaned_value

        if not insert_data:
            return jsonify({"error": "No hay datos validos para insertar"}), 400

        columns = list(insert_data.keys())
        placeholders = ", ".join(["%s"] * len(columns))
        columns_str = ", ".join([f"`{col}`" for col in columns])

        insert_sql = f"""
            INSERT INTO `{table}` ({columns_str})
            VALUES ({placeholders})
        """

        values = list(insert_data.values())

        result = execute_query(insert_sql, values, fetch="none")

        if result is not False:
            return jsonify({"success": True, "message": "Registro creado exitosamente"})
        else:
            return jsonify({"error": "No se pudo crear el registro"}), 500

    except Exception as e:
        print(f"Error en api_mysql_create: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@bp.route("/api/mysql/usuario-actual", methods=["GET"])
@login_requerido
def api_mysql_usuario_actual():
    """Obtener el usuario actualmente logueado."""
    try:
        usuario_id = session.get("usuario", "Sistema")
        nombre_completo = session.get("nombre_completo", usuario_id).strip()
        return jsonify(
            {
                "success": True,
                "usuario": usuario_id,
                "nombre_completo": nombre_completo,
                "usuario_display": nombre_completo,
            }
        )
    except Exception as e:
        print(f"Error en api_mysql_usuario_actual: {e}")
        return jsonify({"error": str(e)}), 500


@bp.route("/api/mysql/delete", methods=["POST"])
@login_requerido
def api_mysql_delete():
    """API para eliminar un registro de una tabla MySQL."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Datos no validos"}), 400

        table = data.get("table", "raw")
        if not re.match(r"^[A-Za-z0-9_]+$", table):
            return jsonify({"error": "Nombre de tabla invalido"}), 400

        record_id = data.get("id")
        if not record_id:
            return jsonify({"error": "ID del registro requerido"}), 400

        cols_query = """
        SELECT COLUMN_NAME, COLUMN_KEY
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=%s
        ORDER BY ORDINAL_POSITION
        """
        cols_result = execute_query(cols_query, (table,), fetch="all")
        if not cols_result:
            return jsonify({"error": "Tabla no encontrada"}), 404

        id_column = None
        for col in cols_result:
            if col["COLUMN_KEY"] == "PRI" or col["COLUMN_NAME"].lower() == "id":
                id_column = col["COLUMN_NAME"]
                break

        if not id_column:
            return jsonify({"error": "No se encontro columna ID en la tabla"}), 400

        check_sql = f"SELECT COUNT(*) as count FROM `{table}` WHERE `{id_column}` = %s"
        check_result = execute_query(check_sql, (record_id,), fetch="one")

        if not check_result or check_result["count"] == 0:
            return jsonify({"error": "Registro no encontrado"}), 404

        delete_sql = f"DELETE FROM `{table}` WHERE `{id_column}` = %s"
        result = execute_query(delete_sql, (record_id,), fetch=None)

        if result is not False:
            return jsonify(
                {
                    "success": True,
                    "message": "Registro eliminado exitosamente",
                    "deleted_id": record_id,
                }
            )
        else:
            return jsonify({"error": "No se pudo eliminar el registro"}), 500

    except Exception as e:
        print(f"Error en api_mysql_delete: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
