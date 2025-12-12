# -*- coding: utf-8 -*-
"""
Metal Mask Routes - Rutas para control de máscaras metálicas y cajas de almacenamiento
"""

from flask import Blueprint, request, jsonify, render_template, session
from functools import wraps
from ..database.db_mysql import execute_query

metal_mask_bp = Blueprint('metal_mask', __name__)

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
# INICIALIZACIÓN DE TABLAS METAL MASK
# ============================================================================

def init_metal_mask_tables():
    """Crea/ajusta tablas usadas por Metal Mask si no existen."""
    try:
        # Tabla principal de masks con nombres de columnas en inglés (usadas por el frontend)
        execute_query(
            """
            CREATE TABLE IF NOT EXISTS masks (
                id INT AUTO_INCREMENT PRIMARY KEY,
                management_no VARCHAR(64) UNIQUE,
                storage_box VARCHAR(64),
                pcb_code VARCHAR(64),
                side VARCHAR(16),
                production_date DATE,
                used_count INT DEFAULT 0,
                max_count INT DEFAULT 0,
                allowance INT DEFAULT 0,
                model_name VARCHAR(255),
                tension_min DECIMAL(6,2),
                tension_max DECIMAL(6,2),
                thickness DECIMAL(6,2),
                supplier VARCHAR(128),
                registration_date VARCHAR(64),
                disuse ENUM('Uso','Desuso','Scrap') DEFAULT 'Uso',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )

        # Asegurar valores del ENUM en caso de historiales previos (migración suave)
        try:
            execute_query("ALTER TABLE masks MODIFY COLUMN disuse ENUM('Use','Disuse','Uso','Desuso','Scrap') DEFAULT 'Uso'")
            execute_query("UPDATE masks SET disuse='Uso' WHERE disuse='Use'")
            execute_query("UPDATE masks SET disuse='Desuso' WHERE disuse='Disuse'")
            execute_query("ALTER TABLE masks MODIFY COLUMN disuse ENUM('Uso','Desuso','Scrap') DEFAULT 'Uso'")
        except Exception as _:
            pass

        # Tabla de cajas de almacenamiento
        execute_query(
            """
            CREATE TABLE IF NOT EXISTS storage_boxes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                management_no VARCHAR(64) UNIQUE,
                code VARCHAR(64),
                name VARCHAR(64),
                location VARCHAR(64),
                storage_status ENUM('Disponible','Ocupado','Mantenimiento') DEFAULT 'Disponible',
                used_status ENUM('Usado','No Usado') DEFAULT 'Usado',
                note TEXT,
                registration_date VARCHAR(64),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )
        print("✅ Tablas Metal Mask creadas/verificadas")
    except Exception as e:
        print(f"Error creando/verificando tablas Metal Mask: {e}")


# ============================================================================
# PÁGINAS HTML
# ============================================================================

@metal_mask_bp.route('/control/metal-mask')
@login_requerido
def pagina_control_metal_mask():
    """Página de control de máscaras metálicas"""
    try:
        return render_template('Control de produccion/control_mask_metal_ajax.html')
    except Exception as e:
        print(f"Error al renderizar Control de metal mask: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@metal_mask_bp.route('/control/metal-mask/caja')
@login_requerido
def pagina_control_caja_metal_mask():
    """Página de control de cajas de almacenamiento"""
    try:
        return render_template('Control de produccion/control_caja_mask_metal_ajax.html')
    except Exception as e:
        print(f"Error al renderizar Control de caja de metal mask: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


# ============================================================================
# API: MASKS (MÁSCARAS METÁLICAS)
# ============================================================================

@metal_mask_bp.route('/api/masks', methods=['GET'])
@login_requerido
def api_list_masks():
    """Listar todas las máscaras metálicas"""
    try:
        disuse = request.args.get('disuse', 'ALL')
        sql = (
            "SELECT id, management_no, storage_box, pcb_code, side, "
            "COALESCE(DATE_FORMAT(production_date, '%Y-%m-%d'), '') AS production_date, "
            "used_count, max_count, allowance, model_name, tension_min, tension_max, thickness, "
            "supplier, registration_date, disuse FROM masks"
        )
        params = []
        if disuse and disuse != 'ALL':
            sql += " WHERE disuse=%s"
            params.append(disuse)
        sql += " ORDER BY id DESC"
        rows = execute_query(sql, tuple(params) if params else None, fetch='all') or []

        # Normalización ligera de tipos para JSON
        out = []
        for r in rows:
            r = dict(r)
            for k in ('used_count', 'max_count', 'allowance'):
                try:
                    r[k] = int(r.get(k) or 0)
                except Exception:
                    pass
            for k in ('tension_min', 'tension_max', 'thickness'):
                v = r.get(k)
                try:
                    r[k] = float(v) if v is not None else None
                except Exception:
                    pass
            out.append(r)
        return jsonify(out)
    except Exception as e:
        print(f"Error en api_list_masks: {e}")
        return jsonify({'error': str(e)}), 500


@metal_mask_bp.route('/api/masks', methods=['POST'])
@login_requerido
def api_create_mask():
    """Crear nueva máscara metálica"""
    try:
        data = request.get_json(force=True) or {}
        data.setdefault('used_count', 0)
        data.setdefault('max_count', 0)
        data.setdefault('allowance', 0)
        data.setdefault('disuse', 'Uso')

        pd = data.get('production_date')
        if isinstance(pd, str) and len(pd) >= 10:
            data['production_date'] = pd[:10]
        else:
            data['production_date'] = None

        cols = (
            'management_no','storage_box','pcb_code','side','production_date',
            'used_count','max_count','allowance','model_name','tension_min',
            'tension_max','thickness','supplier','registration_date','disuse'
        )
        placeholders = ','.join(['%s']*len(cols))
        values = [data.get(c) for c in cols]
        sql = f"INSERT INTO masks ({','.join(cols)}) VALUES ({placeholders})"
        execute_query(sql, tuple(values))
        return jsonify({'success': True, 'message': 'Registrado', 'data': data}), 201
    except Exception as e:
        msg = str(e)
        if 'Duplicate entry' in msg:
            return jsonify({'error': 'El Número de Gestión ya existe'}), 400
        print(f"Error en api_create_mask: {e}")
        return jsonify({'error': msg}), 500


@metal_mask_bp.route('/api/masks/<int:mask_id>', methods=['PUT'])
@login_requerido
def api_update_mask(mask_id: int):
    """Actualizar máscara metálica existente"""
    try:
        p = request.get_json(force=True) or {}
        required = p.get('management_no', '').strip()
        if not required:
            return jsonify({'error': 'Número de Gestión es requerido'}), 400

        sql = (
            "UPDATE masks SET management_no=%s, storage_box=%s, pcb_code=%s, side=%s, "
            "production_date=%s, used_count=%s, max_count=%s, allowance=%s, "
            "model_name=%s, tension_min=%s, tension_max=%s, thickness=%s, "
            "supplier=%s, registration_date=%s, disuse=%s WHERE id=%s"
        )
        params = (
            p.get('management_no','').strip(),
            p.get('storage_box','').strip(),
            p.get('pcb_code','').strip(),
            p.get('side','').strip(),
            (p.get('production_date') or None),
            p.get('used_count',0),
            p.get('max_count',0),
            p.get('allowance',0),
            p.get('model_name','').strip(),
            p.get('tension_min',0),
            p.get('tension_max',0),
            p.get('thickness',0),
            p.get('supplier','').strip(),
            p.get('registration_date','').strip(),
            p.get('disuse','Uso'),
            mask_id
        )
        affected = execute_query(sql, params)
        if affected == 0:
            return jsonify({'error': 'Máscara no encontrada'}), 404
        return jsonify({'success': True, 'message': 'Actualizado'})
    except Exception as e:
        msg = str(e)
        if 'Duplicate entry' in msg:
            return jsonify({'error': 'El Número de Gestión ya existe'}), 400
        print(f"Error en api_update_mask: {e}")
        return jsonify({'error': msg}), 500


# ============================================================================
# API: STORAGE BOXES (CAJAS DE ALMACENAMIENTO)
# ============================================================================

@metal_mask_bp.route('/api/storage', methods=['GET'])
@login_requerido
def api_get_storage():
    """Obtener lista de cajas de almacenamiento"""
    try:
        offset = int(request.args.get('offset', 0))
        limit = int(request.args.get('limit', 100))
        search = (request.args.get('search', '') or '').strip()
        filter_storage_status = (request.args.get('filter_storage_status', '') or '').strip()
        filter_used_status = (request.args.get('filter_used_status', '') or '').strip()

        clauses = []
        params = []
        if search:
            like = f"%{search}%"
            clauses.append("(management_no LIKE %s OR code LIKE %s OR name LIKE %s OR location LIKE %s OR note LIKE %s)")
            params += [like, like, like, like, like]
        if filter_storage_status:
            clauses.append("storage_status=%s")
            params.append(filter_storage_status)
        if filter_used_status:
            clauses.append("used_status=%s")
            params.append(filter_used_status)
        where = ' AND '.join(clauses) if clauses else '1=1'

        total_row = execute_query(f"SELECT COUNT(*) AS total FROM storage_boxes WHERE {where}", tuple(params) if params else None, fetch='one') or {'total': 0}
        data = execute_query(
            f"""
            SELECT id, management_no, code, name, location, storage_status, used_status, note, registration_date
            FROM storage_boxes WHERE {where}
            ORDER BY id DESC
            LIMIT %s OFFSET %s
            """,
            tuple(params + [limit, offset]) if params else (limit, offset),
            fetch='all'
        ) or []
        return jsonify({'data': data, 'total': total_row.get('total', 0)})
    except Exception as e:
        print(f"Error en api_get_storage: {e}")
        return jsonify({'error': str(e)}), 500


@metal_mask_bp.route('/api/storage', methods=['POST'])
@login_requerido
def api_add_storage():
    """Agregar nueva caja de almacenamiento"""
    try:
        p = request.get_json(force=True) or {}
        management_no = (p.get('management_no','') or '').strip()
        if not management_no:
            return jsonify({'error': 'Número de Gestión es requerido'}), 400
        sql = (
            "INSERT INTO storage_boxes (management_no, code, name, location, storage_status, used_status, note, registration_date) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)"
        )
        params = (
            management_no,
            (p.get('code','') or '').strip(),
            (p.get('name','') or '').strip(),
            (p.get('location','') or '').strip(),
            (p.get('storage_status','Disponible') or 'Disponible'),
            (p.get('used_status','Usado') or 'Usado'),
            (p.get('note','') or '').strip(),
            (p.get('registration_date','') or '').strip(),
        )
        execute_query(sql, params)
        return jsonify({'success': True, 'message': 'Caja de almacenamiento registrada exitosamente'})
    except Exception as e:
        msg = str(e)
        if 'Duplicate entry' in msg:
            return jsonify({'error': f'El Número de Gestión "{management_no}" ya existe. Por favor use un código/ubicación diferente.'}), 400
        print(f"Error en api_add_storage: {e}")
        return jsonify({'error': msg}), 500


@metal_mask_bp.route('/api/storage/<int:storage_id>', methods=['PUT'])
@login_requerido
def api_update_storage(storage_id: int):
    """Actualizar caja de almacenamiento existente"""
    try:
        p = request.get_json(force=True) or {}
        management_no = (p.get('management_no','') or '').strip()
        if not management_no:
            return jsonify({'error': 'Número de Gestión es requerido'}), 400
        sql = (
            "UPDATE storage_boxes SET management_no=%s, code=%s, name=%s, location=%s, "
            "storage_status=%s, used_status=%s, note=%s, registration_date=%s WHERE id=%s"
        )
        params = (
            management_no,
            (p.get('code','') or '').strip(),
            (p.get('name','') or '').strip(),
            (p.get('location','') or '').strip(),
            (p.get('storage_status','Disponible') or 'Disponible'),
            (p.get('used_status','Usado') or 'Usado'),
            (p.get('note','') or '').strip(),
            (p.get('registration_date','') or '').strip(),
            storage_id,
        )
        affected = execute_query(sql, params)
        if affected == 0:
            return jsonify({'error': 'Caja de almacenamiento no encontrada'}), 404
        return jsonify({'success': True, 'message': 'Caja de almacenamiento actualizada exitosamente'})
    except Exception as e:
        msg = str(e)
        if 'Duplicate entry' in msg:
            return jsonify({'error': 'El Número de Gestión ya existe'}), 400
        print(f"Error en api_update_storage: {e}")
        return jsonify({'error': msg}), 500


# ============================================================================
# API: BOM SMT DATA (para Metal Mask)
# ============================================================================

@metal_mask_bp.route('/api/bom-smt-data', methods=['GET'])
@login_requerido
def api_bom_smt_data():
    """API para obtener datos del BOM SMT basado en línea y modelo"""
    try:
        from ..database.db_mysql import get_connection
        
        # Obtener parámetros
        linea = request.args.get('linea', '')
        model_code = request.args.get('model_code', '')
        
        if not linea or not model_code:
            return jsonify({'success': False, 'error': 'Línea y modelo son requeridos'}), 400
            
        print(f"API BOM SMT - Filtros:")
        print(f"  Linea: {linea}")
        print(f"  Modelo: {model_code}")
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Mapear línea SMT a número de línea
        mapeo_lineas = {
            'SMT A': '2',
            'SMT B': '2', 
            'SMT C': '3',
            'SMT D': '4',
            '1LINE': '2',
            '2LINE': '2',
            '3LINE': '3',
            '4LINE': '4'
        }
        
        linea_numero = mapeo_lineas.get(linea, '2')
        
        # Consultar ambas tablas (bom_smt_f y bom_smt_r) - solo elementos con cantidad > 0
        query_f = """
            SELECT 
                id, linea, model_code, mounter, slot, material_code, 
                description, feeder_info, qty, raw_filename, 
                created_at, updated_at, 'FRONT' as tabla_tipo
            FROM bom_smt_f 
            WHERE linea = %s AND model_code LIKE %s AND qty > 0
            ORDER BY mounter, slot
        """
        
        query_r = """
            SELECT 
                id, linea, model_code, mounter, slot, material_code, 
                description, feeder_info, qty, raw_filename, 
                created_at, updated_at, 'REAR' as tabla_tipo
            FROM bom_smt_r 
            WHERE linea = %s AND model_code LIKE %s AND qty > 0
            ORDER BY mounter, slot
        """
        
        # Buscar por modelo (puede contener EBR)
        model_pattern = f'%{model_code}%'
        
        # Ejecutar consultas
        cursor.execute(query_f, [linea_numero, model_pattern])
        resultados_f = cursor.fetchall()
        
        cursor.execute(query_r, [linea_numero, model_pattern])
        resultados_r = cursor.fetchall()
        
        # Combinar resultados
        todos_resultados = list(resultados_f) + list(resultados_r)
        
        print(f"Encontrados {len(todos_resultados)} registros BOM ({len(resultados_f)} F + {len(resultados_r)} R)")
        print(f"Parametros de busqueda - Linea numero: {linea_numero}, Patron modelo: {model_pattern}")
        
        # Formatear datos - solo incluir elementos con cantidad > 0
        formatted_data = []
        for row in todos_resultados:
            try:
                qty_value = row[8] if len(row) > 8 else 0
                
                # Solo incluir si qty > 0
                if qty_value <= 0:
                    continue
                    
                formatted_row = {
                    'id': row[0] if len(row) > 0 else '',
                    'linea': row[1] if len(row) > 1 else '',
                    'model_code': row[2] if len(row) > 2 else '',
                    'mounter': row[3] if len(row) > 3 else '',
                    'slot': row[4] if len(row) > 4 else '',
                    'material_code': row[5] if len(row) > 5 else '',
                    'description': row[6] if len(row) > 6 else '',
                    'feeder_info': row[7] if len(row) > 7 else '',
                    'qty': qty_value,
                    'raw_filename': row[9] if len(row) > 9 else '',
                    'created_at': str(row[10]) if len(row) > 10 and row[10] else '',
                    'updated_at': str(row[11]) if len(row) > 11 and row[11] else '',
                    'tabla_tipo': row[12] if len(row) > 12 else '',
                    'status': 'pending'  # Por defecto pendiente
                }
                formatted_data.append(formatted_row)
                
            except Exception as row_error:
                print(f"Error procesando fila BOM: {row_error}")
                continue
        
        cursor.close()
        conn.close()
        
        print(f"BOM filtrado: {len(formatted_data)} elementos con qty > 0")
        
        return jsonify({
            'success': True,
            'data': formatted_data,
            'total': len(formatted_data),
            'linea': linea,
            'model_code': model_code,
            'total_raw': len(todos_resultados),
            'total_filtered': len(formatted_data)
        })
        
    except Exception as e:
        print(f"Error en api_bom_smt_data: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
