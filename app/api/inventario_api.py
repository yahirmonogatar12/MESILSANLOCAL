# -*- coding: utf-8 -*-
"""
API v2 de Inventario
Endpoints REST para gestión de inventario consolidado
"""

from flask import Blueprint, request, jsonify, session
from functools import wraps
from app.services import inventario_service
from app.utils.responses import error_response

# Crear Blueprint
inventario_bp = Blueprint('inventario_api_v2', __name__, url_prefix='/api/v2/inventario')


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

@inventario_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check del módulo de inventario
    
    GET /api/v2/inventario/health
    
    Returns:
        JSON con estado del servicio
    """
    return jsonify({
        'success': True,
        'service': 'inventario-api',
        'version': '2.0.0',
        'status': 'healthy',
        'endpoints': [
            'GET /api/v2/inventario/health',
            'POST /api/v2/inventario/consultar',
            'GET /api/v2/inventario/detalle/<numero_parte>',
            'GET /api/v2/inventario/historial',
            'POST /api/v2/inventario/ajuste',
            'GET /api/v2/inventario/resumen'
        ]
    })


# ============================================================================
# ENDPOINTS DE CONSULTA
# ============================================================================

@inventario_bp.route('/consultar', methods=['POST'])
@login_requerido
def consultar_inventario():
    """
    Consulta inventario consolidado con filtros
    
    POST /api/v2/inventario/consultar
    
    Body JSON:
        {
            "numeroParte": "string (opcional)",
            "propiedad": "SANMINA|CLIENTE (opcional)",
            "cantidadMinima": number (opcional),
            "pagina": number (default 1),
            "porPagina": number (default 50)
        }
    
    Returns:
        JSON con lista paginada de inventario
    """
    try:
        datos = request.get_json() or {}
        usuario = obtener_usuario_actual()
        
        resultado = inventario_service.consultar_inventario(datos, usuario)
        status_code = resultado.get('statusCode', 200)
        
        return jsonify(resultado), status_code
        
    except Exception as e:
        response = error_response(f"Error al consultar inventario: {str(e)}", 500)
        return jsonify(response), 500


@inventario_bp.route('/detalle/<numero_parte>', methods=['GET'])
@login_requerido
def obtener_detalle(numero_parte):
    """
    Obtiene detalle completo de un número de parte
    
    GET /api/v2/inventario/detalle/<numero_parte>
    
    Path params:
        numero_parte: Número de parte a consultar
    
    Returns:
        JSON con detalle del inventario incluyendo todos los lotes
    """
    try:
        resultado = inventario_service.obtener_detalle_inventario(numero_parte)
        status_code = resultado.get('statusCode', 200)
        
        return jsonify(resultado), status_code
        
    except Exception as e:
        response = error_response(f"Error al obtener detalle: {str(e)}", 500)
        return jsonify(response), 500


@inventario_bp.route('/historial', methods=['GET'])
@login_requerido
def obtener_historial():
    """
    Obtiene historial de movimientos de inventario
    
    GET /api/v2/inventario/historial
    
    Query params:
        numeroParte: string (opcional)
        lote: string (opcional)
        desde: YYYY-MM-DD (opcional)
        hasta: YYYY-MM-DD (opcional)
        limite: number (default 100)
    
    Returns:
        JSON con lista de movimientos
    """
    try:
        numero_parte = request.args.get('numeroParte', '')
        lote = request.args.get('lote', '')
        fecha_desde = request.args.get('desde', '')
        fecha_hasta = request.args.get('hasta', '')
        limite = int(request.args.get('limite', 100))
        
        resultado = inventario_service.obtener_historial_movimientos(
            numero_parte=numero_parte if numero_parte else None,
            lote=lote if lote else None,
            fecha_desde=fecha_desde if fecha_desde else None,
            fecha_hasta=fecha_hasta if fecha_hasta else None,
            limite=limite
        )
        status_code = resultado.get('statusCode', 200)
        
        return jsonify(resultado), status_code
        
    except Exception as e:
        response = error_response(f"Error al obtener historial: {str(e)}", 500)
        return jsonify(response), 500


@inventario_bp.route('/resumen', methods=['GET'])
@login_requerido
def obtener_resumen():
    """
    Obtiene resumen general del inventario
    
    GET /api/v2/inventario/resumen
    
    Returns:
        JSON con estadísticas generales
    """
    try:
        resultado = inventario_service.obtener_resumen_inventario()
        status_code = resultado.get('statusCode', 200)
        
        return jsonify(resultado), status_code
        
    except Exception as e:
        response = error_response(f"Error al obtener resumen: {str(e)}", 500)
        return jsonify(response), 500


# ============================================================================
# ENDPOINTS DE MODIFICACIÓN
# ============================================================================

@inventario_bp.route('/ajuste', methods=['POST'])
@login_requerido
def registrar_ajuste():
    """
    Registra un ajuste de inventario
    
    POST /api/v2/inventario/ajuste
    
    Body JSON:
        {
            "numeroParte": "string (requerido)",
            "lote": "string (requerido)",
            "cantidadAjuste": number (requerido),
            "tipoAjuste": "ENTRADA|SALIDA|AJUSTE (requerido)",
            "motivo": "string (requerido)"
        }
    
    Returns:
        JSON con resultado del ajuste
    """
    try:
        datos = request.get_json()
        
        if not datos:
            response = error_response("Datos requeridos en formato JSON", 400)
            return jsonify(response), 400
        
        # Validar campos requeridos
        campos_requeridos = ['numeroParte', 'lote', 'cantidadAjuste', 'tipoAjuste', 'motivo']
        for campo in campos_requeridos:
            if campo not in datos or not datos[campo]:
                response = error_response(f"Campo '{campo}' es requerido", 400)
                return jsonify(response), 400
        
        usuario = obtener_usuario_actual()
        
        resultado = inventario_service.registrar_ajuste_inventario(
            numero_parte=datos['numeroParte'],
            lote=datos['lote'],
            cantidad_ajuste=float(datos['cantidadAjuste']),
            tipo_ajuste=datos['tipoAjuste'].upper(),
            motivo=datos['motivo'],
            usuario=usuario
        )
        status_code = resultado.get('statusCode', 200)
        
        return jsonify(resultado), status_code
        
    except ValueError as e:
        response = error_response(f"Valor inválido: {str(e)}", 400)
        return jsonify(response), 400
    except Exception as e:
        response = error_response(f"Error al registrar ajuste: {str(e)}", 500)
        return jsonify(response), 500


# ============================================================================
# ENDPOINTS DE BÚSQUEDA RÁPIDA
# ============================================================================

@inventario_bp.route('/buscar', methods=['GET'])
@login_requerido
def buscar_rapido():
    """
    Búsqueda rápida de inventario por número de parte
    
    GET /api/v2/inventario/buscar?q=<termino>
    
    Query params:
        q: término de búsqueda (mínimo 3 caracteres)
        limite: número máximo de resultados (default 20)
    
    Returns:
        JSON con lista de coincidencias
    """
    try:
        termino = request.args.get('q', '').strip()
        limite = int(request.args.get('limite', 20))
        
        if len(termino) < 3:
            response = error_response("El término de búsqueda debe tener al menos 3 caracteres", 400)
            return jsonify(response), 400
        
        # Usar el servicio con filtro simple
        resultado = inventario_service.consultar_inventario({
            'numeroParte': termino,
            'porPagina': limite
        })
        
        status_code = resultado.get('statusCode', 200)
        return jsonify(resultado), status_code
        
    except Exception as e:
        response = error_response(f"Error en búsqueda: {str(e)}", 500)
        return jsonify(response), 500
