"""
Material API - Endpoints para gestión de materiales
Blueprint modular con respuestas estandarizadas
"""

from flask import Blueprint, request, session
from functools import wraps

from ..services.material_service import MaterialService
from ..utils.responses import ApiResponse, handle_exceptions
from ..utils.validators import Validator

# Blueprint para API de Material
material_api = Blueprint('material_api', __name__, url_prefix='/api/v2')


def login_required(f):
    """Decorador para verificar autenticación"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'usuario' not in session:
            return ApiResponse.error('Usuario no autenticado', status_code=401)
        return f(*args, **kwargs)
    return decorated


@material_api.route('/materials', methods=['GET'])
@login_required
@handle_exceptions
def list_materials():
    """
    Listar materiales con filtros
    
    Query params:
        - search: Búsqueda por código o descripción
        - category: Filtrar por categoría
        - page: Número de página (default: 1)
        - per_page: Elementos por página (default: 50)
    """
    search = request.args.get('search', '').strip()
    category = request.args.get('category', '').strip()
    page = int(request.args.get('page', 1))
    per_page = min(int(request.args.get('per_page', 50)), 200)  # Máximo 200
    
    offset = (page - 1) * per_page
    
    materials, total, error = MaterialService.get_materials(
        search=search if search else None,
        category=category if category else None,
        limit=per_page,
        offset=offset
    )
    
    if error:
        return ApiResponse.error(error)
    
    return ApiResponse.success(
        data=materials,
        message=f'{len(materials)} materiales encontrados',
        meta={
            'page': page,
            'per_page': per_page,
            'total': total,
            'pages': (total + per_page - 1) // per_page if per_page > 0 else 0
        }
    )


@material_api.route('/materials/<codigo>', methods=['GET'])
@login_required
@handle_exceptions
def get_material(codigo):
    """Obtener material por código"""
    material = MaterialService.get_material_by_code(codigo)
    
    if not material:
        return ApiResponse.not_found(f'Material {codigo} no encontrado')
    
    return ApiResponse.success(data=material)


@material_api.route('/materials', methods=['POST'])
@login_required
@handle_exceptions
def create_material():
    """
    Crear nuevo material
    
    Body JSON:
        - codigo: Código del material (requerido)
        - descripcion: Descripción (requerido)
        - categoria: Categoría (opcional)
        - unidad: Unidad de medida (opcional, default: PZ)
        - stock_actual: Stock inicial (opcional, default: 0)
        - stock_minimo: Stock mínimo (opcional, default: 0)
        - ubicacion: Ubicación en almacén (opcional)
    """
    data = request.get_json() or {}
    
    validator = Validator(data)
    validator.required('codigo', 'descripcion')
    
    if not validator.is_valid():
        return ApiResponse.validation_error(
            validator.get_first_error(),
            errors=validator.get_errors()
        )
    
    success, result = MaterialService.create_material(data)
    
    if not success:
        return ApiResponse.error(result.get('error', 'Error al crear material'))
    
    return ApiResponse.success(
        data=result,
        message='Material creado exitosamente',
        status_code=201
    )


@material_api.route('/materials/<codigo>', methods=['PUT', 'PATCH'])
@login_required
@handle_exceptions
def update_material(codigo):
    """
    Actualizar material existente
    
    Body JSON (campos opcionales):
        - descripcion, categoria, unidad, stock_minimo, ubicacion
    """
    data = request.get_json() or {}
    
    success, error = MaterialService.update_material(codigo, data)
    
    if not success:
        return ApiResponse.error(error)
    
    return ApiResponse.success(
        data={'codigo': codigo},
        message='Material actualizado exitosamente'
    )


@material_api.route('/materials/<codigo>/stock', methods=['POST'])
@login_required
@handle_exceptions
def update_stock(codigo):
    """
    Actualizar stock de un material
    
    Body JSON:
        - cantidad: Cantidad a modificar (requerido, positivo)
        - tipo: 'ENTRADA' o 'SALIDA' (requerido)
        - motivo: Motivo del movimiento (opcional)
    """
    data = request.get_json() or {}
    
    validator = Validator(data)
    validator.required('cantidad', 'tipo')
    validator.positive_int('cantidad', required=True)
    validator.in_list('tipo', ['ENTRADA', 'SALIDA', 'entrada', 'salida'], required=True)
    
    if not validator.is_valid():
        return ApiResponse.validation_error(
            validator.get_first_error(),
            errors=validator.get_errors()
        )
    
    usuario = session.get('usuario', '')
    
    success, result = MaterialService.update_stock(
        codigo=codigo,
        cantidad=int(data.get('cantidad')),
        tipo=data.get('tipo', 'ENTRADA').upper(),
        motivo=data.get('motivo', ''),
        usuario=usuario
    )
    
    if not success:
        return ApiResponse.error(result.get('error', 'Error al actualizar stock'))
    
    return ApiResponse.success(
        data=result,
        message=f"Stock actualizado: {result.get('tipo')} de {result.get('cantidad')}"
    )


@material_api.route('/materials/summary', methods=['GET'])
@login_required
@handle_exceptions
def inventory_summary():
    """Obtener resumen de inventario"""
    summary = MaterialService.get_inventory_summary()
    
    return ApiResponse.success(
        data=summary,
        message='Resumen de inventario obtenido'
    )


@material_api.route('/materials/low-stock', methods=['GET'])
@login_required
@handle_exceptions
def low_stock_materials():
    """Obtener materiales con stock bajo"""
    materials = MaterialService.get_low_stock_materials()
    
    return ApiResponse.success(
        data=materials,
        message=f'{len(materials)} materiales con stock bajo'
    )


@material_api.route('/materials/movements', methods=['GET'])
@login_required
@handle_exceptions
def movement_history():
    """
    Obtener historial de movimientos
    
    Query params:
        - codigo: Filtrar por código de material
        - start: Fecha inicial (YYYY-MM-DD)
        - end: Fecha final (YYYY-MM-DD)
        - limit: Límite de resultados (default: 100)
    """
    codigo = request.args.get('codigo')
    start_date = request.args.get('start')
    end_date = request.args.get('end')
    limit = min(int(request.args.get('limit', 100)), 500)
    
    movements = MaterialService.get_movement_history(
        codigo=codigo,
        start_date=start_date,
        end_date=end_date,
        limit=limit
    )
    
    return ApiResponse.success(
        data=movements,
        message=f'{len(movements)} movimientos encontrados'
    )
