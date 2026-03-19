#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Shipping Entries API - Sistema de Registro de Entradas de Embarques
Endpoints REST para la app móvil PDA Zebra TC15

Autor: ILSAN MES Team
Fecha: Marzo 2026
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta, timezone
import hashlib
import logging
import functools
import os
import traceback

# Intentar importar MySQLdb/pymysql
try:
    import pymysql
    pymysql.install_as_MySQLdb()
    import MySQLdb
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False
    print("⚠️ MySQLdb no disponible para shipping_api")

# Configurar logging
logger = logging.getLogger(__name__)

# Crear Blueprint
shipping_api = Blueprint('shipping_api', __name__, url_prefix='/api/shipping')


# ═══════════════════════════════════════════════════════════════════════════════
# UTILIDADES
# ═══════════════════════════════════════════════════════════════════════════════

def get_mexico_time():
    """Obtener la hora actual de México (GMT-6)"""
    mexico_tz = timezone(timedelta(hours=-6))
    return datetime.now(mexico_tz).replace(tzinfo=None)


def get_db_connection():
    """Crear conexión a la base de datos MySQL"""
    if not MYSQL_AVAILABLE:
        raise RuntimeError("MySQL no está disponible")

    return MySQLdb.connect(
        host=os.getenv('MYSQL_HOST', 'localhost'),
        port=int(os.getenv('MYSQL_PORT', 3306)),
        user=os.getenv('MYSQL_USER') or os.getenv('MYSQL_USERNAME', ''),
        passwd=os.getenv('MYSQL_PASSWORD', ''),
        db=os.getenv('MYSQL_DATABASE', ''),
        charset='utf8mb4',
        autocommit=True
    )


def hash_shipping_password(password):
    """Generar hash SHA-256 para credenciales del módulo de embarques."""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def verify_shipping_password(stored_hash, password):
    """Verificar contraseñas soportando hash SHA-256 y valores legacy."""
    if not stored_hash:
        return False

    password_hash = hash_shipping_password(password)
    return stored_hash == password_hash or stored_hash == password


def manejo_errores(func):
    """Decorator para manejo centralizado de errores"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except MySQLdb.Error as e:
            logger.error(f"Error MySQL en {func.__name__}: {e}")
            return jsonify({
                "success": False,
                "error": "Error de base de datos",
                "message": str(e)
            }), 500
        except Exception as e:
            logger.error(f"Error en {func.__name__}: {e}\n{traceback.format_exc()}")
            return jsonify({
                "success": False,
                "error": "Error interno del servidor",
                "message": str(e)
            }), 500
    return wrapper


# ═══════════════════════════════════════════════════════════════════════════════
# AUTENTICACIÓN
# ═══════════════════════════════════════════════════════════════════════════════

@shipping_api.route('/auth/login', methods=['POST'])
@manejo_errores
def login():
    """
    POST /api/shipping/auth/login
    Autenticar operador de embarques
    
    Body:
    {
        "username": "1247",
        "password": "contraseña"
    }
    
    Response:
    {
        "success": true,
        "token": "...",
        "user": { id, username, full_name, department, shift }
    }
    """
    data = request.get_json(force=True)
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    if not username or not password:
        return jsonify({
            "success": False,
            "message": "Usuario y contraseña son requeridos"
        }), 400
    
    conn = get_db_connection()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)
    
    try:
        # Buscar operador en la tabla dedicada de operadores de embarques
        cursor.execute("""
            SELECT id, full_name, department, shift, password_hash
            FROM operators_shipping
            WHERE id = %s AND is_active = TRUE
        """, (username,))
        
        operator = cursor.fetchone()
        
        if not operator:
            return jsonify({
                "success": False,
                "message": "Usuario o contraseña incorrectos"
            }), 401
        
        # Verificar contraseña usando hash propio y compatibilidad legacy.
        password_valid = verify_shipping_password(operator['password_hash'], password)
        
        if not password_valid:
            return jsonify({
                "success": False,
                "message": "Usuario o contraseña incorrectos"
            }), 401
        
        # Actualizar último acceso
        cursor.execute("""
            UPDATE operators_shipping SET last_login = %s WHERE id = %s
        """, (get_mexico_time(), username))
        
        # Generar token simple (en producción usar JWT)
        import secrets
        token_data = f"{username}:{secrets.token_hex(16)}:{datetime.now().isoformat()}"
        token = hashlib.sha256(token_data.encode()).hexdigest()
        
        return jsonify({
            "success": True,
            "token": token,
            "user": {
                "id": operator['id'],
                "username": operator['id'],
                "full_name": operator['full_name'],
                "department": operator['department'],
                "shift": operator['shift']
            }
        })
        
    finally:
        cursor.close()
        conn.close()


@shipping_api.route('/auth/logout', methods=['POST'])
@manejo_errores
def logout():
    """
    POST /api/shipping/auth/logout
    Cerrar sesión del operador
    """
    # En una implementación con JWT, aquí invalidaríamos el token
    return jsonify({
        "success": True,
        "message": "Sesión cerrada correctamente"
    })


# ═══════════════════════════════════════════════════════════════════════════════
# CONSULTA DE CALIDAD
# ═══════════════════════════════════════════════════════════════════════════════

@shipping_api.route('/quality/<box_id>', methods=['GET'])
@manejo_errores
def get_quality_status(box_id):
    """
    GET /api/shipping/quality/{box_id}
    Consultar el estatus de calidad de un Box ID
    
    Response:
    {
        "box_id": "BOX-2026-001847",
        "product_name": "Componente electrónico A",
        "lot_number": "LOT-2026-0218A",
        "quality_status": "released",
        "validated_by": "1249",
        "validated_at": "2026-03-12T10:30:00",
        "rejection_reason": null
    }
    """
    if not box_id or len(box_id) < 3:
        return jsonify({
            "success": False,
            "message": "Box ID inválido"
        }), 400
    
    conn = get_db_connection()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)
    
    try:
        cursor.execute("""
            SELECT box_id, product_name, lot_number, quality_status,
                   validated_by, validated_at, rejection_reason
            FROM quality_validations
            WHERE box_id = %s
        """, (box_id,))
        
        result = cursor.fetchone()
        
        if not result:
            return jsonify({
                "success": False,
                "message": "Box ID no encontrado en el sistema"
            }), 404
        
        # Convertir datetime a string
        if result.get('validated_at'):
            result['validated_at'] = result['validated_at'].strftime('%Y-%m-%dT%H:%M:%S')
        
        return jsonify(result)
        
    finally:
        cursor.close()
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# REGISTRO DE EMBARQUES
# ═══════════════════════════════════════════════════════════════════════════════

@shipping_api.route('/entries', methods=['POST'])
@manejo_errores
def create_entry():
    """
    POST /api/shipping/entries
    Registrar una nueva entrada de embarque
    
    Body:
    {
        "box_id": "BOX-2026-001850",
        "quality_status": "released",
        "scanned_by": "1247",
        "product_name": "Componente A",
        "lot_number": "LOT-2026-0218A",
        "warehouse_zone": "A1",
        "notes": "Sin observaciones",
        "device_id": "PDA-TC15-001",
        "scanned_at": "2026-03-12T14:32:00"
    }
    """
    data = request.get_json(force=True)
    
    # Validaciones
    box_id = data.get('box_id', '').strip()
    scanned_by = data.get('scanned_by', '').strip()
    
    if not box_id:
        return jsonify({
            "success": False,
            "message": "El campo box_id es requerido"
        }), 400
    
    if not scanned_by:
        return jsonify({
            "success": False,
            "message": "El campo scanned_by es requerido"
        }), 400
    
    # Parsear fecha de escaneo o usar actual
    scanned_at_str = data.get('scanned_at')
    if scanned_at_str:
        try:
            scanned_at = datetime.fromisoformat(scanned_at_str.replace('Z', '+00:00'))
            scanned_at = scanned_at.replace(tzinfo=None)
        except ValueError:
            scanned_at = get_mexico_time()
    else:
        scanned_at = get_mexico_time()
    
    # Obtener estatus de calidad (de la petición o consultar BD)
    quality_status = data.get('quality_status', 'pending')
    product_name = data.get('product_name')
    lot_number = data.get('lot_number')
    
    conn = get_db_connection()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)
    
    try:
        # Si no se proporcionó info del producto, intentar obtenerla de quality_validations
        if not product_name or not lot_number:
            cursor.execute("""
                SELECT product_name, lot_number, quality_status
                FROM quality_validations
                WHERE box_id = %s
            """, (box_id,))
            
            quality_info = cursor.fetchone()
            if quality_info:
                product_name = product_name or quality_info.get('product_name')
                lot_number = lot_number or quality_info.get('lot_number')
                quality_status = quality_info.get('quality_status', quality_status)
        
        # Insertar registro de entrada
        cursor.execute("""
            INSERT INTO shipping_entries 
                (box_id, quality_status, scanned_at, scanned_by, product_name, 
                 lot_number, warehouse_zone, notes, device_id, synced_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            box_id,
            quality_status,
            scanned_at,
            scanned_by,
            product_name,
            lot_number,
            data.get('warehouse_zone'),
            data.get('notes'),
            data.get('device_id'),
            get_mexico_time()
        ))
        
        entry_id = cursor.lastrowid
        
        return jsonify({
            "success": True,
            "id": entry_id,
            "message": "Entrada registrada correctamente"
        }), 201
        
    finally:
        cursor.close()
        conn.close()


@shipping_api.route('/entries', methods=['GET'])
@manejo_errores
def list_entries():
    """
    GET /api/shipping/entries
    Listar historial de escaneos con filtros
    
    Query params:
    - limit: int (default 50)
    - offset: int (default 0)
    - status: released|pending|rejected|in_process
    - search: string (busca en box_id, product_name)
    - from_date: ISO8601
    - to_date: ISO8601
    - scanned_by: ID del operador
    """
    # Parámetros de paginación
    limit = min(int(request.args.get('limit', 50)), 200)  # Máximo 200
    offset = int(request.args.get('offset', 0))
    
    # Filtros
    status_filter = request.args.get('status', '').strip()
    search_query = request.args.get('search', '').strip()
    from_date = request.args.get('from_date', '').strip()
    to_date = request.args.get('to_date', '').strip()
    scanned_by = request.args.get('scanned_by', '').strip()
    
    conn = get_db_connection()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)
    
    try:
        # Construir query con filtros
        where_clauses = []
        params = []
        
        if status_filter:
            where_clauses.append("quality_status = %s")
            params.append(status_filter)
        
        if search_query:
            where_clauses.append("(box_id LIKE %s OR product_name LIKE %s)")
            params.extend([f"%{search_query}%", f"%{search_query}%"])
        
        if from_date:
            where_clauses.append("scanned_at >= %s")
            params.append(from_date)
        
        if to_date:
            where_clauses.append("scanned_at <= %s")
            params.append(to_date + ' 23:59:59')
        
        if scanned_by:
            where_clauses.append("scanned_by = %s")
            params.append(scanned_by)
        
        where_sql = 'WHERE ' + ' AND '.join(where_clauses) if where_clauses else ''
        
        # Obtener total
        cursor.execute(f"SELECT COUNT(*) as total FROM shipping_entries {where_sql}", params)
        total = cursor.fetchone()['total']
        
        # Obtener registros
        query = f"""
            SELECT id, box_id, quality_status, scanned_at, scanned_by,
                   product_name, lot_number, warehouse_zone
            FROM shipping_entries
            {where_sql}
            ORDER BY scanned_at DESC
            LIMIT %s OFFSET %s
        """
        
        cursor.execute(query, params + [limit, offset])
        entries = cursor.fetchall()
        
        # Convertir datetime a string
        for entry in entries:
            if entry.get('scanned_at'):
                entry['scanned_at'] = entry['scanned_at'].strftime('%Y-%m-%dT%H:%M:%S')
        
        return jsonify({
            "success": True,
            "total": total,
            "limit": limit,
            "offset": offset,
            "entries": entries
        })
        
    finally:
        cursor.close()
        conn.close()


@shipping_api.route('/entries/<int:entry_id>', methods=['GET'])
@manejo_errores
def get_entry(entry_id):
    """
    GET /api/shipping/entries/{id}
    Obtener detalle de una entrada específica
    """
    conn = get_db_connection()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)
    
    try:
        cursor.execute("""
            SELECT se.*, o.full_name as operator_name
            FROM shipping_entries se
            LEFT JOIN operators o ON se.scanned_by = o.id
            WHERE se.id = %s
        """, (entry_id,))
        
        entry = cursor.fetchone()
        
        if not entry:
            return jsonify({
                "success": False,
                "message": "Entrada no encontrada"
            }), 404
        
        # Convertir datetime a string
        for key in ['scanned_at', 'synced_at', 'created_at', 'updated_at']:
            if entry.get(key):
                entry[key] = entry[key].strftime('%Y-%m-%dT%H:%M:%S')
        
        return jsonify({
            "success": True,
            "entry": entry
        })
        
    finally:
        cursor.close()
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# ESTADÍSTICAS
# ═══════════════════════════════════════════════════════════════════════════════

@shipping_api.route('/stats/today', methods=['GET'])
@manejo_errores
def get_today_stats():
    """
    GET /api/shipping/stats/today
    Obtener estadísticas del día actual
    
    Query params:
    - date: YYYY-MM-DD (default: hoy)
    - scanned_by: filtrar por operador
    """
    date_param = request.args.get('date', '').strip()
    scanned_by = request.args.get('scanned_by', '').strip()
    
    # Usar fecha proporcionada o fecha actual de México
    if date_param:
        try:
            target_date = datetime.strptime(date_param, '%Y-%m-%d').date()
        except ValueError:
            target_date = get_mexico_time().date()
    else:
        target_date = get_mexico_time().date()
    
    conn = get_db_connection()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)
    
    try:
        # Construir filtro de operador si se proporciona
        operator_filter = ""
        params = [target_date]
        
        if scanned_by:
            operator_filter = "AND scanned_by = %s"
            params.append(scanned_by)
        
        cursor.execute(f"""
            SELECT 
                COUNT(*) AS total,
                SUM(CASE WHEN quality_status = 'released' THEN 1 ELSE 0 END) AS released,
                SUM(CASE WHEN quality_status = 'pending' THEN 1 ELSE 0 END) AS pending,
                SUM(CASE WHEN quality_status = 'rejected' THEN 1 ELSE 0 END) AS rejected,
                SUM(CASE WHEN quality_status = 'in_process' THEN 1 ELSE 0 END) AS in_process
            FROM shipping_entries
            WHERE DATE(scanned_at) = %s {operator_filter}
        """, params)
        
        stats = cursor.fetchone()
        
        # Asegurar valores no nulos
        for key in ['total', 'released', 'pending', 'rejected', 'in_process']:
            stats[key] = int(stats.get(key) or 0)
        
        stats['date'] = target_date.strftime('%Y-%m-%d')
        
        return jsonify(stats)
        
    finally:
        cursor.close()
        conn.close()


@shipping_api.route('/stats/summary', methods=['GET'])
@manejo_errores
def get_stats_summary():
    """
    GET /api/shipping/stats/summary
    Obtener resumen de estadísticas por período
    
    Query params:
    - from_date: YYYY-MM-DD
    - to_date: YYYY-MM-DD  
    - group_by: day|week|month (default: day)
    """
    from_date = request.args.get('from_date', '').strip()
    to_date = request.args.get('to_date', '').strip()
    group_by = request.args.get('group_by', 'day').strip()
    
    # Valores por defecto: última semana
    if not to_date:
        to_date = get_mexico_time().strftime('%Y-%m-%d')
    if not from_date:
        from_date = (get_mexico_time() - timedelta(days=7)).strftime('%Y-%m-%d')
    
    conn = get_db_connection()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)
    
    try:
        # Determinar agrupación
        if group_by == 'week':
            date_format = '%Y-%u'  # Año-Semana
            date_label = "CONCAT(YEAR(scanned_at), '-W', LPAD(WEEK(scanned_at), 2, '0'))"
        elif group_by == 'month':
            date_format = '%Y-%m'
            date_label = "DATE_FORMAT(scanned_at, '%Y-%m')"
        else:
            date_format = '%Y-%m-%d'
            date_label = "DATE(scanned_at)"
        
        cursor.execute(f"""
            SELECT 
                {date_label} AS period,
                COUNT(*) AS total,
                SUM(CASE WHEN quality_status = 'released' THEN 1 ELSE 0 END) AS released,
                SUM(CASE WHEN quality_status = 'pending' THEN 1 ELSE 0 END) AS pending,
                SUM(CASE WHEN quality_status = 'rejected' THEN 1 ELSE 0 END) AS rejected,
                SUM(CASE WHEN quality_status = 'in_process' THEN 1 ELSE 0 END) AS in_process
            FROM shipping_entries
            WHERE DATE(scanned_at) BETWEEN %s AND %s
            GROUP BY {date_label}
            ORDER BY period DESC
        """, (from_date, to_date))
        
        results = cursor.fetchall()
        
        # Convertir a enteros
        for row in results:
            for key in ['total', 'released', 'pending', 'rejected', 'in_process']:
                row[key] = int(row.get(key) or 0)
        
        return jsonify({
            "success": True,
            "from_date": from_date,
            "to_date": to_date,
            "group_by": group_by,
            "data": results
        })
        
    finally:
        cursor.close()
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIÓN DE REGISTRO
# ═══════════════════════════════════════════════════════════════════════════════

def register_shipping_routes(app):
    """Registrar el blueprint de shipping en la aplicación Flask"""
    try:
        if 'shipping_api' not in app.blueprints:
            app.register_blueprint(shipping_api)
            print("✅ Shipping API registrada en /api/shipping")
        return True
    except Exception as e:
        print(f"❌ Error registrando Shipping API: {e}")
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# INICIALIZACIÓN DE TABLAS (ejecutar una vez)
# ═══════════════════════════════════════════════════════════════════════════════

def init_shipping_tables():
    """Crear las tablas necesarias para el módulo de embarques si no existen"""
    if not MYSQL_AVAILABLE:
        print("MySQL no disponible, no se pueden crear tablas de shipping")
        return False
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Limpiar tabla operators_shipping si tiene problemas de estructura
        try:
            cursor.execute("DROP TABLE IF EXISTS operators_shipping_old")
        except:
            pass
        
        # Verificar si operators_shipping ya existe
        cursor.execute("SHOW TABLES LIKE 'operators_shipping'")
        table_exists = cursor.fetchone() is not None
        
        if not table_exists:
            # Tabla dedicada de operadores para la app de embarques
            print("Creando tabla operators_shipping...")
            try:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS operators_shipping (
                        id VARCHAR(20) PRIMARY KEY COMMENT 'Número de empleado',
                        full_name VARCHAR(100) NOT NULL,
                        department VARCHAR(50) NULL,
                        shift ENUM('A', 'B', 'C', 'admin') DEFAULT 'A',
                        password_hash VARCHAR(255) NOT NULL,
                        is_active BOOLEAN DEFAULT TRUE,
                        last_login DATETIME NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        INDEX idx_is_active (is_active)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """)
                print("Tabla operators_shipping creada")
            except Exception as e:
                print(f"Error creando tabla operators_shipping: {e}")
                traceback.print_exc()
            
            # Migrar operadores legacy si la tabla anterior existe.
            try:
                cursor.execute("SHOW TABLES LIKE 'operators'")
                if cursor.fetchone():
                    cursor.execute("SHOW COLUMNS FROM operators")
                    legacy_columns = {row[0] for row in cursor.fetchall()}

                    if 'id' in legacy_columns:
                        full_name_expr = 'o.full_name' if 'full_name' in legacy_columns else 'o.id'
                        department_expr = 'o.department' if 'department' in legacy_columns else 'NULL'
                        shift_expr = 'o.shift' if 'shift' in legacy_columns else "'A'"
                        password_expr = (
                            'o.password_hash'
                            if 'password_hash' in legacy_columns
                            else 'SHA2(o.id, 256)'
                        )
                        is_active_expr = 'o.is_active' if 'is_active' in legacy_columns else 'TRUE'
                        last_login_expr = 'o.last_login' if 'last_login' in legacy_columns else 'NULL'
                        created_at_expr = 'o.created_at' if 'created_at' in legacy_columns else 'CURRENT_TIMESTAMP'
                        updated_at_expr = 'o.updated_at' if 'updated_at' in legacy_columns else 'CURRENT_TIMESTAMP'

                        cursor.execute(f"""
                            INSERT INTO operators_shipping (
                                id, full_name, department, shift, password_hash,
                                is_active, last_login, created_at, updated_at
                            )
                            SELECT
                                o.id, {full_name_expr}, {department_expr}, {shift_expr}, {password_expr},
                                {is_active_expr}, {last_login_expr}, {created_at_expr}, {updated_at_expr}
                            FROM operators o
                            LEFT JOIN operators_shipping os ON os.id = o.id
                            WHERE os.id IS NULL
                        """)
                        print("Operadores legacy migrados")
            except Exception as e:
                print(f"No se pudo migrar operadores legacy: {e}, continuando...")

            # Registrar admin por defecto para embarques si no existe.
            cursor.execute("""
                SELECT COUNT(*) FROM operators_shipping WHERE id = %s
            """, ('admin',))
            
            if cursor.fetchone()[0] == 0:
                try:
                    cursor.execute("""
                        INSERT INTO operators_shipping (
                            id, full_name, department, shift, password_hash, is_active
                        )
                        VALUES (%s, %s, %s, %s, %s, TRUE)
                    """, (
                        'admin',
                        'Administrador Embarques',
                        'Embarques',
                        'admin',
                        hash_shipping_password('admin123'),
                    ))
                    print("Admin de shipping creado")
                except Exception as e:
                    print(f"No se pudo insertar admin: {e}")
        else:
            print("Tabla operators_shipping ya existe, se omite creación")
        
        # Tabla de validaciones de calidad
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS quality_validations (
                    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                    box_id VARCHAR(50) NOT NULL,
                    product_name VARCHAR(150) NULL,
                    lot_number VARCHAR(50) NULL,
                    quality_status ENUM('released', 'pending', 'rejected', 'in_process') NOT NULL DEFAULT 'pending',
                    validated_by VARCHAR(20) NULL,
                    validated_at DATETIME NULL,
                    rejection_reason TEXT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE INDEX idx_box_id_unique (box_id),
                    INDEX idx_quality_status (quality_status)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
        except Exception as e:
            print(f"Tabla quality_validations: {e}")
        
        # Tabla de entradas de embarque
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS shipping_entries (
                    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                    box_id VARCHAR(50) NOT NULL,
                    quality_status ENUM('released', 'pending', 'rejected', 'in_process') NOT NULL,
                    scanned_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    scanned_by VARCHAR(20) NOT NULL,
                    product_name VARCHAR(150) NULL,
                    lot_number VARCHAR(50) NULL,
                    warehouse_zone VARCHAR(20) NULL,
                    notes TEXT NULL,
                    device_id VARCHAR(50) NULL,
                    synced_at DATETIME NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_box_id (box_id),
                    INDEX idx_scanned_at (scanned_at),
                    INDEX idx_scanned_by (scanned_by),
                    INDEX idx_quality_status (quality_status)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
        except Exception as e:
            print(f"Tabla shipping_entries: {e}")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("Tablas de shipping creadas/verificadas correctamente")
        return True
        
    except Exception as e:
        print(f"❌ Error creando tablas de shipping: {e}")
        import traceback
        traceback.print_exc()
        return False
