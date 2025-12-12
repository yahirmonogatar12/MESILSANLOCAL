# -*- coding: utf-8 -*-
"""
API v2 de Work Orders (Órdenes de Trabajo)
Endpoints REST para gestión de órdenes de trabajo
"""

from flask import Blueprint, request, jsonify, session
from functools import wraps
from app.services import work_orders_service
from app.utils.responses import error_response

# Crear Blueprint
work_orders_bp = Blueprint('work_orders_api_v2', __name__, url_prefix='/api/v2/work-orders')


# ============================================================================
# DECORADORES
# ============================================================================

def login_requerido(f):
    """Decorador para verificar autenticación"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session:
            response = error_response("No autenticado. Inicie sesión para continuar.", 401)
            return jsonify(response), 401
        return f(*args, **kwargs)
    return decorated_function


def obtener_usuario_actual():
    """Obtiene el usuario actual de la sesión"""
    return session.get('usuario', 'sistema')


# ============================================================================
# ENDPOINTS PÚBLICOS
# ============================================================================

@work_orders_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check del módulo de work orders
    
    GET /api/v2/work-orders/health
    
    Returns:
        JSON con estado del servicio
    """
    return jsonify({
        'success': True,
        'service': 'work-orders-api',
        'version': '2.0.0',
        'status': 'healthy',
        'endpoints': [
            'GET /api/v2/work-orders/health',
            'GET /api/v2/work-orders',
            'GET /api/v2/work-orders/<work_order>',
            'POST /api/v2/work-orders',
            'PUT /api/v2/work-orders/<work_order>/estado',
            'POST /api/v2/work-orders/<work_order>/importar',
            'GET /api/v2/work-orders/estadisticas'
        ]
    })


# ============================================================================
# ENDPOINTS DE CONSULTA
# ============================================================================

@work_orders_bp.route('', methods=['GET'])
@work_orders_bp.route('/', methods=['GET'])
@login_requerido
def listar_work_orders():
    """
    Lista work orders con filtros opcionales
    
    GET /api/v2/work-orders
    
    Query params:
        q: búsqueda general (work_order, modelo, descripcion)
        estado: PENDIENTE|EN_PROCESO|COMPLETADO|CANCELADO
        desde: YYYY-MM-DD (fecha inicio)
        hasta: YYYY-MM-DD (fecha fin)
        pagina: número de página (default 1)
        porPagina: registros por página (default 50)
    
    Returns:
        JSON con lista paginada de work orders
    """
    try:
        filtros = {
            'q': request.args.get('q', ''),
            'estado': request.args.get('estado', ''),
            'desde': request.args.get('desde', ''),
            'hasta': request.args.get('hasta', ''),
            'pagina': request.args.get('pagina', 1),
            'porPagina': request.args.get('porPagina', 50)
        }
        
        resultado = work_orders_service.obtener_work_orders(filtros)
        status_code = resultado.get('statusCode', 200)
        
        return jsonify(resultado), status_code
        
    except Exception as e:
        response = error_response(f"Error al listar work orders: {str(e)}", 500)
        return jsonify(response), 500


@work_orders_bp.route('/<work_order>', methods=['GET'])
@login_requerido
def obtener_work_order(work_order):
    """
    Obtiene detalle de un work order específico
    
    GET /api/v2/work-orders/<work_order>
    
    Path params:
        work_order: número de work order
    
    Returns:
        JSON con detalle completo del work order
    """
    try:
        resultado = work_orders_service.obtener_work_order_detalle(work_order)
        status_code = resultado.get('statusCode', 200)
        
        return jsonify(resultado), status_code
        
    except Exception as e:
        response = error_response(f"Error al obtener work order: {str(e)}", 500)
        return jsonify(response), 500


@work_orders_bp.route('/estadisticas', methods=['GET'])
@login_requerido
def obtener_estadisticas():
    """
    Obtiene estadísticas generales de work orders
    
    GET /api/v2/work-orders/estadisticas
    
    Returns:
        JSON con estadísticas (total, por estado, creados hoy, etc.)
    """
    try:
        resultado = work_orders_service.obtener_estadisticas_work_orders()
        status_code = resultado.get('statusCode', 200)
        
        return jsonify(resultado), status_code
        
    except Exception as e:
        response = error_response(f"Error al obtener estadísticas: {str(e)}", 500)
        return jsonify(response), 500


# ============================================================================
# ENDPOINTS DE CREACIÓN/MODIFICACIÓN
# ============================================================================

@work_orders_bp.route('', methods=['POST'])
@work_orders_bp.route('/', methods=['POST'])
@login_requerido
def crear_work_order():
    """
    Crea un nuevo work order
    
    POST /api/v2/work-orders
    
    Body JSON:
        {
            "workOrder": "string (requerido)",
            "modelo": "string (requerido)",
            "descripcion": "string (opcional)",
            "cantidad": number (requerido),
            "cliente": "string (opcional)",
            "prioridad": "ALTA|MEDIA|BAJA (default MEDIA)",
            "linea": "string (opcional)",
            "observaciones": "string (opcional)"
        }
    
    Returns:
        JSON con datos del work order creado
    """
    try:
        datos = request.get_json()
        
        if not datos:
            response = error_response("Datos requeridos en formato JSON", 400)
            return jsonify(response), 400
        
        # Validar campos requeridos
        if not datos.get('workOrder'):
            response = error_response("Campo 'workOrder' es requerido", 400)
            return jsonify(response), 400
        if not datos.get('modelo'):
            response = error_response("Campo 'modelo' es requerido", 400)
            return jsonify(response), 400
        if not datos.get('cantidad'):
            response = error_response("Campo 'cantidad' es requerido", 400)
            return jsonify(response), 400
        
        usuario = obtener_usuario_actual()
        
        resultado = work_orders_service.crear_work_order(datos, usuario)
        status_code = resultado.get('statusCode', 200)
        
        return jsonify(resultado), status_code
        
    except Exception as e:
        response = error_response(f"Error al crear work order: {str(e)}", 500)
        return jsonify(response), 500


@work_orders_bp.route('/<work_order>/estado', methods=['PUT'])
@login_requerido
def actualizar_estado(work_order):
    """
    Actualiza el estado de un work order
    
    PUT /api/v2/work-orders/<work_order>/estado
    
    Body JSON:
        {
            "estado": "PENDIENTE|EN_PROCESO|COMPLETADO|CANCELADO"
        }
    
    Returns:
        JSON con resultado de la actualización
    """
    try:
        datos = request.get_json()
        
        if not datos or 'estado' not in datos:
            response = error_response("Campo 'estado' es requerido", 400)
            return jsonify(response), 400
        
        usuario = obtener_usuario_actual()
        
        resultado = work_orders_service.actualizar_estado_work_order(
            work_order=work_order,
            nuevo_estado=datos['estado'].upper(),
            usuario=usuario
        )
        status_code = resultado.get('statusCode', 200)
        
        return jsonify(resultado), status_code
        
    except Exception as e:
        response = error_response(f"Error al actualizar estado: {str(e)}", 500)
        return jsonify(response), 500


@work_orders_bp.route('/<work_order>/importar', methods=['POST'])
@login_requerido
def importar_a_plan(work_order):
    """
    Importa un work order al plan de producción
    
    POST /api/v2/work-orders/<work_order>/importar
    
    Body JSON:
        {
            "grupo": "string (opcional)",
            "linea": "string (opcional)",
            "fechaProgramada": "YYYY-MM-DD (opcional)",
            "turno": "string (opcional)"
        }
    
    Returns:
        JSON con datos de la importación
    """
    try:
        datos = request.get_json() or {}
        usuario = obtener_usuario_actual()
        
        resultado = work_orders_service.importar_work_order_a_plan(
            work_order=work_order,
            datos_plan=datos,
            usuario=usuario
        )
        status_code = resultado.get('statusCode', 200)
        
        return jsonify(resultado), status_code
        
    except Exception as e:
        response = error_response(f"Error al importar work order: {str(e)}", 500)
        return jsonify(response), 500


# ============================================================================
# ENDPOINTS DE BÚSQUEDA
# ============================================================================

@work_orders_bp.route('/buscar', methods=['GET'])
@login_requerido
def buscar_work_orders():
    """
    Búsqueda rápida de work orders
    
    GET /api/v2/work-orders/buscar?q=<termino>
    
    Query params:
        q: término de búsqueda (mínimo 2 caracteres)
        limite: máximo de resultados (default 20)
    
    Returns:
        JSON con lista de coincidencias
    """
    try:
        termino = request.args.get('q', '').strip()
        limite = int(request.args.get('limite', 20))
        
        if len(termino) < 2:
            response = error_response("El término de búsqueda debe tener al menos 2 caracteres", 400)
            return jsonify(response), 400
        
        resultado = work_orders_service.obtener_work_orders({
            'q': termino,
            'porPagina': limite
        })
        
        status_code = resultado.get('statusCode', 200)
        return jsonify(resultado), status_code
        
    except Exception as e:
        response = error_response(f"Error en búsqueda: {str(e)}", 500)
        return jsonify(response), 500


@work_orders_bp.route('/pendientes', methods=['GET'])
@login_requerido
def listar_pendientes():
    """
    Lista work orders pendientes (atajo para filtro por estado)
    
    GET /api/v2/work-orders/pendientes
    
    Query params:
        pagina: número de página (default 1)
        porPagina: registros por página (default 50)
    
    Returns:
        JSON con work orders en estado PENDIENTE
    """
    try:
        filtros = {
            'estado': 'PENDIENTE',
            'pagina': request.args.get('pagina', 1),
            'porPagina': request.args.get('porPagina', 50)
        }
        
        resultado = work_orders_service.obtener_work_orders(filtros)
        status_code = resultado.get('statusCode', 200)
        
        return jsonify(resultado), status_code
        
    except Exception as e:
        response = error_response(f"Error al listar pendientes: {str(e)}", 500)
        return jsonify(response), 500


@work_orders_bp.route('/no-importados', methods=['GET'])
@login_requerido
def listar_no_importados():
    """
    Lista work orders que aún no han sido importados al plan
    
    GET /api/v2/work-orders/no-importados
    
    Query params:
        pagina: número de página (default 1)
        porPagina: registros por página (default 50)
    
    Returns:
        JSON con work orders no importados
    """
    try:
        # Obtener todos los work orders y filtrar los no importados
        resultado = work_orders_service.obtener_work_orders({
            'pagina': request.args.get('pagina', 1),
            'porPagina': request.args.get('porPagina', 100)
        })
        
        if resultado.get('success'):
            # Filtrar solo los no importados
            data = resultado.get('data', [])
            no_importados = [wo for wo in data if not wo.get('yaImportado', False)]
            resultado['data'] = no_importados
            resultado['total'] = len(no_importados)
            resultado['message'] = f"Se encontraron {len(no_importados)} work orders no importados"
        
        status_code = resultado.get('statusCode', 200)
        return jsonify(resultado), status_code
        
    except Exception as e:
        response = error_response(f"Error al listar no importados: {str(e)}", 500)
        return jsonify(response), 500
