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


MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15
SESSION_DURATION_HOURS = 24
FULL_ACCESS_DEPARTMENTS = {'Sistemas', 'Gerencia', 'Administración'}
SHIPPING_PERMISSION_PANEL_PAGE = 'APP_REGISTRO_EMBARQUES'
AVAILABLE_DEPARTMENTS = [
    'Almacén de Embarques',
    'Calidad',
    'Sistemas',
    'Gerencia',
    'Administración',
]
AVAILABLE_CARGOS = [
    'Operador de Embarques',
    'Supervisor de Embarques',
    'Inspector de Calidad',
    'Administrador',
]
SHIPPING_PERMISSION_DEFINITIONS = [
    {
        'key': 'view_warehousing',
        'name': 'Ver entradas',
        'description': 'Permite consultar el módulo de entradas de material.',
        'section': 'Operación',
    },
    {
        'key': 'write_warehousing',
        'name': 'Registrar entradas',
        'description': 'Permite capturar y editar entradas de material.',
        'section': 'Operación',
    },
    {
        'key': 'multi_edit_warehousing',
        'name': 'Edición múltiple de entradas',
        'description': 'Permite editar varias entradas de material al mismo tiempo.',
        'section': 'Operación',
    },
    {
        'key': 'view_outgoing',
        'name': 'Ver salidas',
        'description': 'Permite consultar el módulo de salidas.',
        'section': 'Operación',
    },
    {
        'key': 'write_outgoing',
        'name': 'Registrar salidas',
        'description': 'Permite capturar y editar salidas de material.',
        'section': 'Operación',
    },
    {
        'key': 'view_inventory',
        'name': 'Ver inventario',
        'description': 'Permite consultar el inventario.',
        'section': 'Inventario',
    },
    {
        'key': 'view_iqc',
        'name': 'Ver IQC',
        'description': 'Permite consultar la inspección de calidad.',
        'section': 'Calidad',
    },
    {
        'key': 'write_iqc',
        'name': 'Registrar IQC',
        'description': 'Permite capturar resultados de inspección de calidad.',
        'section': 'Calidad',
    },
    {
        'key': 'view_quarantine',
        'name': 'Ver cuarentena',
        'description': 'Permite consultar el módulo de cuarentena.',
        'section': 'Calidad',
    },
    {
        'key': 'send_quarantine',
        'name': 'Enviar a cuarentena',
        'description': 'Permite enviar material a cuarentena.',
        'section': 'Calidad',
    },
    {
        'key': 'release_quarantine',
        'name': 'Liberar cuarentena',
        'description': 'Permite liberar o modificar material en cuarentena.',
        'section': 'Calidad',
    },
    {
        'key': 'view_blacklist',
        'name': 'Ver lista negra',
        'description': 'Permite consultar la lista negra.',
        'section': 'Calidad',
    },
    {
        'key': 'write_blacklist',
        'name': 'Editar lista negra',
        'description': 'Permite crear y actualizar registros en lista negra.',
        'section': 'Calidad',
    },
    {
        'key': 'manage_users',
        'name': 'Administrar usuarios',
        'description': 'Permite gestionar usuarios y sus permisos.',
        'section': 'Administración',
    },
    {
        'key': 'view_reports',
        'name': 'Ver reportes',
        'description': 'Permite consultar reportes operativos.',
        'section': 'Auditoría y reportes',
    },
    {
        'key': 'export_data',
        'name': 'Exportar datos',
        'description': 'Permite exportar información del sistema.',
        'section': 'Auditoría y reportes',
    },
    {
        'key': 'approve_cancellation',
        'name': 'Aprobar cancelaciones',
        'description': 'Permite aprobar cancelaciones de registros.',
        'section': 'Auditoría y reportes',
    },
    {
        'key': 'view_material_return',
        'name': 'Ver devoluciones de material',
        'description': 'Permite consultar devoluciones de material.',
        'section': 'Retornos y requerimientos',
    },
    {
        'key': 'write_material_return',
        'name': 'Registrar devoluciones de material',
        'description': 'Permite crear devoluciones de material.',
        'section': 'Retornos y requerimientos',
    },
    {
        'key': 'view_requirements',
        'name': 'Ver requerimientos',
        'description': 'Permite consultar requerimientos de material.',
        'section': 'Retornos y requerimientos',
    },
    {
        'key': 'write_requirements',
        'name': 'Registrar requerimientos',
        'description': 'Permite crear o editar requerimientos de material.',
        'section': 'Retornos y requerimientos',
    },
    {
        'key': 'approve_requirements',
        'name': 'Aprobar requerimientos',
        'description': 'Permite aprobar requerimientos de material.',
        'section': 'Retornos y requerimientos',
    },
    {
        'key': 'view_reentry',
        'name': 'Ver reingresos',
        'description': 'Permite consultar reingresos o reubicaciones.',
        'section': 'Inventario',
    },
    {
        'key': 'write_reentry',
        'name': 'Registrar reingresos',
        'description': 'Permite registrar reingresos o reubicaciones.',
        'section': 'Inventario',
    },
    {
        'key': 'view_pending_exits',
        'name': 'Ver pendientes de salida',
        'description': 'Permite consultar salidas pendientes.',
        'section': 'Inventario',
    },
    {
        'key': 'write_pending_exits',
        'name': 'Registrar pendientes de salida',
        'description': 'Permite procesar salidas pendientes.',
        'section': 'Inventario',
    },
    {
        'key': 'view_audit',
        'name': 'Ver auditoría',
        'description': 'Permite consultar auditorías de inventario.',
        'section': 'Auditoría y reportes',
    },
    {
        'key': 'start_audit',
        'name': 'Gestionar auditoría',
        'description': 'Permite iniciar y cerrar auditorías.',
        'section': 'Auditoría y reportes',
    },
    {
        'key': 'scan_audit',
        'name': 'Escanear auditoría',
        'description': 'Permite capturar lecturas durante auditorías.',
        'section': 'Auditoría y reportes',
    },
    {
        'key': 'view_master_labels',
        'name': 'Ver etiquetas master',
        'description': 'Permite consultar etiquetas master.',
        'section': 'Inventario',
    },
    {
        'key': 'write_master_labels',
        'name': 'Gestionar etiquetas master',
        'description': 'Permite crear o eliminar etiquetas master.',
        'section': 'Inventario',
    },
    {
        'key': 'view_warehouse_map',
        'name': 'Ver mapa de almacén',
        'description': 'Permite consultar el mapa del almacén.',
        'section': 'Layout',
    },
    {
        'key': 'create_warehouse_zones',
        'name': 'Crear zonas de almacén',
        'description': 'Permite crear zonas y editar datos de zona.',
        'section': 'Layout',
    },
    {
        'key': 'edit_warehouse_locations',
        'name': 'Editar ubicaciones de almacén',
        'description': 'Permite editar ubicaciones, racks y movimientos.',
        'section': 'Layout',
    },
    {
        'key': 'manage_warehouse_layout',
        'name': 'Gestionar layout de almacén',
        'description': 'Permite administrar el layout completo del almacén.',
        'section': 'Layout',
    },
]

AVAILABLE_SHIPPING_PERMISSIONS = [
    {
        'key': permission['key'],
        'name': permission['name'],
        'description': permission['description'],
    }
    for permission in SHIPPING_PERMISSION_DEFINITIONS
]

SHIPPING_PERMISSION_DROPDOWN_CATALOG = [
    {
        'permission_key': permission['key'],
        'pagina': SHIPPING_PERMISSION_PANEL_PAGE,
        'seccion': permission['section'],
        'boton': permission['name'],
        'descripcion': permission['description'],
    }
    for permission in SHIPPING_PERMISSION_DEFINITIONS
]

SHIPPING_PERMISSION_LOOKUP_BY_DROPDOWN = {
    (permission['pagina'], permission['seccion'], permission['boton']): permission['permission_key']
    for permission in SHIPPING_PERMISSION_DROPDOWN_CATALOG
}


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


def normalize_db_datetime(value):
    """Normalizar valores datetime provenientes de MySQL o strings ISO."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    if isinstance(value, str):
        normalized = value.replace('Z', '+00:00')
        try:
            return datetime.fromisoformat(normalized).replace(tzinfo=None)
        except ValueError:
            return None
    return None


def build_user_payload(user_row):
    """Construir respuesta de usuario sin exponer campos sensibles."""
    active_value = user_row.get('activo', 0)
    if isinstance(active_value, str):
        is_active = active_value.strip().lower() in {'1', 'true'}
    else:
        is_active = bool(active_value)

    return {
        'id': user_row['id'],
        'username': user_row['username'],
        'email': user_row.get('email'),
        'full_name': user_row.get('nombre_completo') or user_row['username'],
        'department': user_row.get('departamento'),
        'cargo': user_row.get('cargo'),
        'active': is_active,
    }


def get_shipping_permission_dropdown_catalog():
    """Catálogo de permisos de embarques en formato del panel central."""
    return [dict(permission) for permission in SHIPPING_PERMISSION_DROPDOWN_CATALOG]


def user_has_superadmin_role(cursor, user_id):
    """Determinar si el usuario tiene el rol central de superadmin."""
    cursor.execute(
        """
        SELECT 1
        FROM usuario_roles ur
        JOIN roles r ON ur.rol_id = r.id
        WHERE ur.usuario_id = %s
          AND r.activo = 1
          AND r.nombre = 'superadmin'
        LIMIT 1
        """,
        (user_id,),
    )
    return cursor.fetchone() is not None


def get_role_based_shipping_permissions(cursor, user_id):
    """Resolver permisos de embarques heredados desde roles del panel central."""
    cursor.execute(
        """
        SELECT DISTINCT pb.pagina, pb.seccion, pb.boton
        FROM usuario_roles ur
        JOIN roles r ON ur.rol_id = r.id
        JOIN rol_permisos_botones rpb ON ur.rol_id = rpb.rol_id
        JOIN permisos_botones pb ON rpb.permiso_boton_id = pb.id
        WHERE ur.usuario_id = %s
          AND r.activo = 1
          AND pb.activo = 1
          AND pb.pagina = %s
        ORDER BY pb.seccion ASC, pb.boton ASC
        """,
        (user_id, SHIPPING_PERMISSION_PANEL_PAGE),
    )

    permissions = set()
    for row in cursor.fetchall():
        permission_key = SHIPPING_PERMISSION_LOOKUP_BY_DROPDOWN.get(
            (row['pagina'], row['seccion'], row['boton'])
        )
        if permission_key:
            permissions.add(permission_key)

    return sorted(permissions)


def get_legacy_user_shipping_permissions(cursor, user_id):
    """Resolver permisos legacy asignados directamente al usuario."""
    cursor.execute(
        """
        SELECT permission_key
        FROM user_permissions_materiales
        WHERE user_id = %s AND enabled = 1
        ORDER BY permission_key ASC
        """,
        (user_id,),
    )
    return [row['permission_key'] for row in cursor.fetchall()]


def get_enabled_permissions(cursor, user_id, department):
    """Obtener permisos efectivos del usuario para el módulo de embarques."""
    has_full_access = department in FULL_ACCESS_DEPARTMENTS or user_has_superadmin_role(
        cursor,
        user_id,
    )

    if has_full_access:
        return has_full_access, [permission['key'] for permission in AVAILABLE_SHIPPING_PERMISSIONS]

    role_permissions = set(get_role_based_shipping_permissions(cursor, user_id))
    legacy_permissions = set(get_legacy_user_shipping_permissions(cursor, user_id))
    permissions = sorted(role_permissions | legacy_permissions)
    return has_full_access, permissions


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
    Autenticar usuario del sistema para el módulo de embarques
    
    Body:
    {
        "username": "1247",
        "password": "contraseña"
    }
    
    Response:
    {
        "success": true,
        "user": { id, username, full_name, department, cargo }
    }
    """
    data = request.get_json(silent=True) or {}
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
        cursor.execute("""
            SELECT id, username, password_hash, email, nombre_completo,
                   departamento, cargo, activo, intentos_fallidos, bloqueado_hasta
            FROM usuarios_sistema
            WHERE username = %s
        """, (username,))
        
        user = cursor.fetchone()
        
        if not user:
            return jsonify({
                "success": False,
                "message": "Usuario o contraseña incorrectos"
            }), 401
        
        if int(user.get('activo') or 0) != 1:
            return jsonify({
                "success": False,
                "message": "El usuario está inactivo"
            }), 403

        bloqueado_hasta = normalize_db_datetime(user.get('bloqueado_hasta'))
        ahora = get_mexico_time()

        if bloqueado_hasta and ahora < bloqueado_hasta:
            return jsonify({
                "success": False,
                "message": "Usuario bloqueado temporalmente",
                "blockedUntil": bloqueado_hasta.isoformat(),
                "intentosRestantes": 0,
            }), 423

        if bloqueado_hasta and ahora >= bloqueado_hasta:
            cursor.execute("""
                UPDATE usuarios_sistema
                SET bloqueado_hasta = NULL, intentos_fallidos = 0
                WHERE id = %s
            """, (user['id'],))
            user['intentos_fallidos'] = 0
            user['bloqueado_hasta'] = None

        password_valid = verify_shipping_password(user['password_hash'], password)
        
        if not password_valid:
            intentos = int(user.get('intentos_fallidos') or 0) + 1
            intentos_restantes = max(0, MAX_FAILED_ATTEMPTS - intentos)

            if intentos >= MAX_FAILED_ATTEMPTS:
                bloqueado_hasta = get_mexico_time() + timedelta(minutes=LOCKOUT_MINUTES)
                cursor.execute("""
                    UPDATE usuarios_sistema
                    SET intentos_fallidos = %s, bloqueado_hasta = %s
                    WHERE id = %s
                """, (intentos, bloqueado_hasta, user['id']))

                return jsonify({
                    "success": False,
                    "message": f"Usuario bloqueado por {LOCKOUT_MINUTES} minutos",
                    "blockedUntil": bloqueado_hasta.isoformat(),
                    "intentosRestantes": 0,
                }), 401

            cursor.execute("""
                UPDATE usuarios_sistema
                SET intentos_fallidos = %s
                WHERE id = %s
            """, (intentos, user['id']))

            return jsonify({
                "success": False,
                "message": "Usuario o contraseña incorrectos",
                "intentosRestantes": intentos_restantes,
            }), 401
        
        cursor.execute("""
            UPDATE usuarios_sistema
            SET intentos_fallidos = 0,
                bloqueado_hasta = NULL,
                ultimo_acceso = %s
            WHERE id = %s
        """, (get_mexico_time(), user['id']))
        
        return jsonify({
            "success": True,
            "user": build_user_payload(user)
        })
        
    finally:
        cursor.close()
        conn.close()


@shipping_api.route('/auth/logout', methods=['POST'])
@manejo_errores
def logout():
    """
    POST /api/shipping/auth/logout
    Cerrar sesión del usuario y registrar su último acceso.
    """
    data = request.get_json(silent=True) or {}
    user_id = data.get('userId')

    if user_id:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE usuarios_sistema
                SET ultimo_acceso = %s
                WHERE id = %s
            """, (get_mexico_time(), user_id))
        finally:
            cursor.close()
            conn.close()

    return jsonify({
        "success": True,
        "message": "Sesión cerrada correctamente"
    })


@shipping_api.route('/auth/verify/<int:user_id>', methods=['GET'])
@manejo_errores
def verify_user(user_id):
    """
    GET /api/shipping/auth/verify/{user_id}
    Verificar que el usuario siga existiendo y permanezca activo.
    """
    conn = get_db_connection()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    try:
        cursor.execute("""
            SELECT id, username, email, nombre_completo, departamento, cargo, activo
            FROM usuarios_sistema
            WHERE id = %s
        """, (user_id,))
        user = cursor.fetchone()

        if not user:
            return jsonify({
                "success": False,
                "valid": False,
                "message": "Usuario no encontrado"
            }), 404

        if int(user.get('activo') or 0) != 1:
            return jsonify({
                "success": False,
                "valid": False,
                "message": "Usuario inactivo"
            }), 403

        return jsonify({
            "success": True,
            "valid": True,
            "user": build_user_payload(user),
        })
    finally:
        cursor.close()
        conn.close()


@shipping_api.route('/users/<int:user_id>/permissions', methods=['GET'])
@manejo_errores
def get_user_permissions(user_id):
    """
    GET /api/shipping/users/{user_id}/permissions
    Obtener permisos efectivos del catálogo compartido entre escritorio y móvil.
    """
    conn = get_db_connection()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    try:
        cursor.execute("""
            SELECT id, departamento, activo
            FROM usuarios_sistema
            WHERE id = %s
        """, (user_id,))
        user = cursor.fetchone()

        if not user:
            return jsonify({
                "success": False,
                "message": "Usuario no encontrado"
            }), 404

        if int(user.get('activo') or 0) != 1:
            return jsonify({
                "success": False,
                "message": "Usuario inactivo"
            }), 403

        has_full_access, permission_keys = get_enabled_permissions(
            cursor,
            user['id'],
            user.get('departamento'),
        )

        return jsonify({
            "success": True,
            "userId": user['id'],
            "department": user.get('departamento'),
            "hasFullAccess": has_full_access,
            "permissions": [
                {
                    "permission_key": permission_key,
                    "enabled": True,
                }
                for permission_key in permission_keys
            ],
            "enabledPermissions": permission_keys,
        })
    finally:
        cursor.close()
        conn.close()


@shipping_api.route('/permissions/available', methods=['GET'])
@manejo_errores
def get_available_permissions():
    """Catálogo hardcodeado de permisos compartidos entre escritorio y móvil."""
    return jsonify({
        "success": True,
        "permissions": AVAILABLE_SHIPPING_PERMISSIONS,
    })


@shipping_api.route('/departments', methods=['GET'])
@manejo_errores
def get_departments():
    """Catálogo hardcodeado de departamentos expuesto por API."""
    return jsonify({
        "success": True,
        "departments": AVAILABLE_DEPARTMENTS,
    })


@shipping_api.route('/cargos', methods=['GET'])
@manejo_errores
def get_cargos():
    """Catálogo hardcodeado de cargos expuesto por API."""
    return jsonify({
        "success": True,
        "cargos": AVAILABLE_CARGOS,
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
            SELECT se.*,
                   COALESCE(u.nombre_completo, u.username, se.scanned_by) AS operator_name
            FROM shipping_entries se
            LEFT JOIN usuarios_sistema u
                ON CAST(u.id AS CHAR) = se.scanned_by OR u.username = se.scanned_by
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

        # Tabla de permisos compartida por escritorio y app móvil.
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_permissions_materiales (
                    user_id INT NOT NULL,
                    permission_key VARCHAR(100) NOT NULL,
                    enabled BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, permission_key),
                    INDEX idx_user_permissions_enabled (user_id, enabled)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
        except Exception as e:
            print(f"Tabla user_permissions_materiales: {e}")
        
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
