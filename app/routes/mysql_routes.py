# -*- coding: utf-8 -*-
"""
MySQL Routes - Rutas para el visor MySQL y operaciones directas de base de datos
"""

from flask import Blueprint, request, jsonify, render_template, session
from functools import wraps
import re
import traceback
from ..database.db_mysql import execute_query

mysql_bp = Blueprint('mysql', __name__)

# ============================================================================
# DECORADOR DE AUTENTICACIÓN
# ============================================================================

def login_requerido(f):
    """Decorador para verificar que el usuario está autenticado"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session:
            return jsonify({'error': 'No autorizado', 'redirect': '/login'}), 401
        return f(*args, **kwargs)
    return decorated_function


# ============================================================================
# PÁGINA DEL VISOR MySQL
# ============================================================================

@mysql_bp.route('/visor-mysql')
@login_requerido
def visor_mysql():
    """Página del visor MySQL"""
    try:
        return render_template('visor_mysql.html')
    except Exception as e:
        print(f"Error al renderizar visor MySQL: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


# ============================================================================
# API: TABLAS DISPONIBLES
# ============================================================================

@mysql_bp.route('/api/mysql/tables')
def api_mysql_tables():
    """API para obtener lista de tablas de la base de datos"""
    try:
        query = """
        SELECT TABLE_NAME 
        FROM INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_SCHEMA=DATABASE() AND TABLE_TYPE='BASE TABLE'
        ORDER BY TABLE_NAME
        """
        
        result = execute_query(query, fetch='all')
        if result is not None:
            tables = [row["TABLE_NAME"] for row in result]
            return jsonify({"tables": tables})
        else:
            return jsonify({"tables": []})
            
    except Exception as e:
        print(f"❌ Error en api_mysql_tables: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================================================
# API: COLUMNAS DE UNA TABLA
# ============================================================================

@mysql_bp.route('/api/mysql/columns')
def api_mysql_columns():
    """API para obtener columnas de una tabla específica"""
    try:
        table = request.args.get("table", "raw")
        if not re.match(r"^[A-Za-z0-9_]+$", table):
            return jsonify({"error": "Nombre de tabla inválido"}), 400
            
        query = """
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=%s
        ORDER BY ORDINAL_POSITION
        """
        
        result = execute_query(query, (table,), fetch='all')
        if result is not None:
            columns = [row["COLUMN_NAME"] for row in result]
            return jsonify({"table": table, "columns": columns})
        else:
            return jsonify({"table": table, "columns": []})
            
    except Exception as e:
        print(f"❌ Error en api_mysql_columns: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================================================
# API: DATOS DE UNA TABLA
# ============================================================================

@mysql_bp.route('/api/mysql/data')
def api_mysql_data():
    """API para obtener datos de una tabla con filtros y ordenamiento inteligente"""
    try:
        table = request.args.get("table", "raw")
        if not re.match(r"^[A-Za-z0-9_]+$", table):
            return jsonify({"error": "Nombre de tabla inválido"}), 400
            
        limit = min(max(int(request.args.get("limit", 200)), 1), 2000)
        offset = max(int(request.args.get("offset", 0)), 0)
        search = (request.args.get("search") or "").strip()
        
        # Obtener columnas primero
        cols_query = """
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=%s
        ORDER BY ORDINAL_POSITION
        """
        cols_result = execute_query(cols_query, (table,), fetch='all')
        if not cols_result:
            return jsonify({"table": table, "columns": [], "rows": [], "total": 0})
            
        columns = [row["COLUMN_NAME"] for row in cols_result]
        
        # Construir consulta base con ordenamiento inteligente
        base_sql = f"SELECT * FROM `{table}`"
        where = ""
        params = []
        
        # Agregar filtro de búsqueda si existe
        if search:
            like_conditions = []
            for col in columns:
                like_conditions.append(f"CAST(`{col}` AS CHAR) LIKE %s")
            where = f" WHERE ({' OR '.join(like_conditions)})"
            params = [f"%{search}%"] * len(columns)
        
        # Ordenamiento inteligente para agrupar modelos similares
        # Buscar columnas que podrían contener códigos de modelo
        model_columns = []
        for col in columns:
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in ['modelo', 'model', 'codigo', 'parte', 'part', 'ebr', 'product']):
                model_columns.append(col)
        
        # Construir ORDER BY inteligente
        order_by = ""
        main_col = None
        if model_columns:
            # Usar la primera columna que parece ser de modelo/código
            main_col = model_columns[0]
            # Ordenar por la parte base del código (sin números finales) y luego por el código completo
            order_by = f" ORDER BY REGEXP_REPLACE(`{main_col}`, '[0-9]+$', ''), `{main_col}`"
        else:
            # Si no hay columnas obvias de modelo, ordenar por la primera columna
            if columns:
                main_col = columns[0]
                order_by = f" ORDER BY `{columns[0]}`"
        
        # Consulta para contar total
        count_sql = f"SELECT COUNT(*) as total FROM `{table}`{where}"
        count_result = execute_query(count_sql, params, fetch='one')
        total = count_result["total"] if count_result else 0
        
        # Consulta para obtener datos paginados con ordenamiento
        data_sql = f"{base_sql}{where}{order_by} LIMIT %s OFFSET %s"
        data_params = params + [limit, offset]
        data_result = execute_query(data_sql, data_params, fetch='all')
        
        rows = data_result if data_result else []
        
        return jsonify({
            "table": table,
            "columns": columns,
            "rows": rows,
            "total": total,
            "limit": limit,
            "offset": offset,
            "search": search,
            "ordering": f"Ordenado por: {main_col if main_col else 'N/A'}"
        })
        
    except Exception as e:
        print(f"❌ Error en api_mysql_data: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================================================
# API: ACTUALIZAR REGISTRO
# ============================================================================

@mysql_bp.route('/api/mysql/update', methods=['POST'])
def api_mysql_update():
    """API para actualizar registros en tabla raw"""
    
    def clean_column_value(column_name, value):
        """Limpiar y validar valores según el tipo de columna"""
        if value is None or value == '':
            return None
        
        value = str(value).strip()
        
        # Columnas numéricas que pueden tener formato con comas
        numeric_columns = ['hora_dia', 'c_t', 'uph', 'price', 'st', 'neck_st', 'l_b', 'input', 'output']
        
        if column_name in numeric_columns:
            # Remover comas y convertir a formato numérico válido
            cleaned = value.replace(',', '').replace(' ', '')
            
            # Si está vacío después de limpiar, devolver None
            if not cleaned:
                return None
                
            try:
                # Intentar convertir a float para validar
                float(cleaned)
                return cleaned
            except ValueError:
                print(f"⚠️ Valor no numérico para columna {column_name}: {value}, usando NULL")
                return None
        
        # Para otras columnas, devolver el valor limpio
        return value if value != '' else None
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No se recibieron datos"}), 400
            
        # Por seguridad, solo permitir actualizar tabla raw
        table = "raw"
        
        # Obtener datos originales y nuevos
        original_data = data.get('original', {})
        new_data = data.get('new', {})
        
        if not original_data or not new_data:
            return jsonify({"error": "Faltan datos originales o nuevos"}), 400
        
        # Construir la cláusula WHERE basada en los datos originales
        # Usar solo campos clave para identificar el registro, no los campos que se están modificando
        
        # Definir campos clave que normalmente no cambian (identificadores únicos)
        key_fields = ['part_no', 'model', 'project', 'main_display', 'linea']
        
        where_conditions = []
        where_params = []
        
        # Usar solo los campos clave disponibles
        for key in key_fields:
            if key in original_data:
                value = original_data[key]
                if value is None or value == '' or value == 'NULL':
                    where_conditions.append(f"(`{key}` IS NULL OR `{key}` = '' OR `{key}` = 'NULL')")
                else:
                    where_conditions.append(f"`{key}` = %s")
                    where_params.append(value)
        
        # Si no hay suficientes campos clave, usar los primeros 5 campos no modificados
        if len(where_conditions) < 3:
            used_fields = set(key_fields)
            for key, value in original_data.items():
                if key not in used_fields and len(where_conditions) < 5:
                    # Solo usar si no es un campo que se está modificando
                    if key not in new_data or new_data[key] == value:
                        if value is None or value == '' or value == 'NULL':
                            where_conditions.append(f"(`{key}` IS NULL OR `{key}` = '' OR `{key}` = 'NULL')")
                        else:
                            where_conditions.append(f"`{key}` = %s")
                            where_params.append(value)
                        used_fields.add(key)
        
        if not where_conditions:
            return jsonify({"error": "No se pueden identificar los datos originales"}), 400
        
        # Construir la cláusula SET para los nuevos datos
        # Excluir columnas generadas y de solo lectura
        readonly_columns = ['Usuario', 'crea', 'upt']  # Columnas que no se pueden actualizar
        
        set_conditions = []
        set_params = []
        
        for key, value in new_data.items():
            # Saltar columnas de solo lectura/generadas
            if key in readonly_columns:
                print(f"⚠️ Saltando columna de solo lectura: {key}")
                continue
            
            # Limpiar y validar valores según el tipo de columna
            cleaned_value = clean_column_value(key, value)
            
            set_conditions.append(f"`{key}` = %s")
            set_params.append(cleaned_value)
        
        if not set_conditions:
            return jsonify({"error": "No hay datos válidos para actualizar (todas las columnas son de solo lectura)"}), 400
        
        # Construir y ejecutar la consulta UPDATE
        update_sql = f"""
            UPDATE `{table}` 
            SET {', '.join(set_conditions)}
            WHERE {' AND '.join(where_conditions)}
            LIMIT 1
        """
        
        params = set_params + where_params
        
        # Ejecutar la actualización
        result = execute_query(update_sql, params, fetch='none')
        
        # Verificar si se actualizó algún registro
        if result is not False:
            return jsonify({
                "success": True,
                "message": "Registro actualizado exitosamente"
            })
        else:
            return jsonify({"error": "No se pudo actualizar el registro"}), 500
            
    except Exception as e:
        print(f"❌ Error en api_mysql_update: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ============================================================================
# API: CREAR REGISTRO
# ============================================================================

@mysql_bp.route('/api/mysql/create', methods=['POST'])
def api_mysql_create():
    """Crear nuevo registro en tabla raw"""
    try:
        # Obtener datos del request
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No se enviaron datos"}), 400
        
        new_data = data.get('data', {})
        
        if not new_data:
            return jsonify({"error": "No se enviaron datos para crear"}), 400
        
        # Tabla fija para este visor
        table = 'raw'
        
        # Función para limpiar valores de columnas
        def clean_column_value(column_name, value):
            if value is None:
                return None
            
            # Si es string vacío, convertir a None para enviar NULL
            if isinstance(value, str) and value.strip() == '':
                return None
                
            # Limpiar campos numéricos (remover comas)
            numeric_fields = ['hora_dia', 'c_t', 'uph', 'price', 'st', 'neck_st', 'l_b', 'input', 'output']
            if column_name in numeric_fields and isinstance(value, str):
                cleaned = value.replace(',', '').strip()
                if cleaned == '':
                    return None
                return cleaned
            
            return value
        
        # Preparar datos para inserción (excluir campos de solo lectura)
        readonly_fields = ['crea', 'upt', 'raw']  # Usuario ya no es columna generada
        insert_data = {}
        
        # Agregar usuario logueado si no está en los datos
        if 'Usuario' not in new_data:
            new_data['Usuario'] = session.get('nombre_completo', session.get('usuario', 'Sistema')).strip()
        
        for key, value in new_data.items():
            if key not in readonly_fields:
                cleaned_value = clean_column_value(key, value)
                # Incluir todos los campos, incluso si son NULL
                insert_data[key] = cleaned_value
        
        if not insert_data:
            return jsonify({"error": "No hay datos válidos para insertar"}), 400
        
        # Construir consulta INSERT
        columns = list(insert_data.keys())
        placeholders = ', '.join(['%s'] * len(columns))
        columns_str = ', '.join([f'`{col}`' for col in columns])
        
        insert_sql = f"""
            INSERT INTO `{table}` ({columns_str})
            VALUES ({placeholders})
        """
        
        values = list(insert_data.values())
        
        # Ejecutar la inserción
        result = execute_query(insert_sql, values, fetch='none')
        
        # Verificar si se insertó el registro
        if result is not False:
            return jsonify({
                "success": True,
                "message": "Registro creado exitosamente"
            })
        else:
            return jsonify({"error": "No se pudo crear el registro"}), 500
            
    except Exception as e:
        print(f"❌ Error en api_mysql_create: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ============================================================================
# API: USUARIO ACTUAL
# ============================================================================

@mysql_bp.route('/api/mysql/usuario-actual', methods=['GET'])
@login_requerido
def api_mysql_usuario_actual():
    """Obtener el usuario actualmente logueado"""
    try:
        usuario_id = session.get('usuario', 'Sistema')
        nombre_completo = session.get('nombre_completo', usuario_id).strip()
        return jsonify({
            "success": True,
            "usuario": usuario_id,
            "nombre_completo": nombre_completo,
            "usuario_display": nombre_completo  # El nombre que se mostrará en la UI
        })
    except Exception as e:
        print(f"❌ Error en api_mysql_usuario_actual: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================================================
# API: ELIMINAR REGISTRO
# ============================================================================

@mysql_bp.route('/api/mysql/delete', methods=['POST'])
@login_requerido
def api_mysql_delete():
    """API para eliminar un registro de una tabla MySQL"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Datos no válidos"}), 400
            
        table = data.get("table", "raw")
        if not re.match(r"^[A-Za-z0-9_]+$", table):
            return jsonify({"error": "Nombre de tabla inválido"}), 400
        
        # Obtener el ID o identificador único del registro
        record_id = data.get("id")
        if not record_id:
            return jsonify({"error": "ID del registro requerido"}), 400
        
        # Verificar que la tabla tenga una columna 'id'
        cols_query = """
        SELECT COLUMN_NAME, COLUMN_KEY
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=%s
        ORDER BY ORDINAL_POSITION
        """
        cols_result = execute_query(cols_query, (table,), fetch='all')
        if not cols_result:
            return jsonify({"error": "Tabla no encontrada"}), 404
        
        # Buscar columna de clave primaria o 'id'
        id_column = None
        for col in cols_result:
            if col["COLUMN_KEY"] == "PRI" or col["COLUMN_NAME"].lower() == "id":
                id_column = col["COLUMN_NAME"]
                break
        
        if not id_column:
            return jsonify({"error": "No se encontró columna ID en la tabla"}), 400
        
        # Verificar que el registro existe antes de eliminar
        check_sql = f"SELECT COUNT(*) as count FROM `{table}` WHERE `{id_column}` = %s"
        check_result = execute_query(check_sql, (record_id,), fetch='one')
        
        if not check_result or check_result["count"] == 0:
            return jsonify({"error": "Registro no encontrado"}), 404
        
        # Ejecutar eliminación
        delete_sql = f"DELETE FROM `{table}` WHERE `{id_column}` = %s"
        result = execute_query(delete_sql, (record_id,), fetch=None)
        
        if result is not False:
            return jsonify({
                "success": True,
                "message": "Registro eliminado exitosamente",
                "deleted_id": record_id
            })
        else:
            return jsonify({"error": "No se pudo eliminar el registro"}), 500
            
    except Exception as e:
        print(f"❌ Error en api_mysql_delete: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
