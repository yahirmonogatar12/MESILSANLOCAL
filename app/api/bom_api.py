"""
BOM API - Endpoints para gestión de BOM (Bill of Materials)
Blueprint modular con respuestas estandarizadas
"""

from flask import Blueprint, request, session
from functools import wraps

from ..services.bom_service import BomService
from ..utils.responses import ApiResponse, handle_exceptions
from ..utils.validators import Validator

# Blueprint para API de BOM
bom_api = Blueprint('bom_api', __name__, url_prefix='/api/v2')


def login_required(f):
    """Decorador para verificar autenticación"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'usuario' not in session:
            return ApiResponse.error('Usuario no autenticado', status_code=401)
        return f(*args, **kwargs)
    return decorated


@bom_api.route('/bom/models', methods=['GET'])
@login_required
@handle_exceptions
def list_models():
    """Listar modelos con BOM"""
    models = BomService.get_models_list()
    
    return ApiResponse.success(
        data=models,
        message=f'{len(models)} modelos encontrados'
    )


@bom_api.route('/bom/<model_code>', methods=['GET'])
@login_required
@handle_exceptions
def get_bom(model_code):
    """Obtener BOM de un modelo específico"""
    items, error = BomService.get_bom_by_model(model_code)
    
    if error:
        return ApiResponse.error(error)
    
    if not items:
        return ApiResponse.not_found(f'No se encontró BOM para el modelo {model_code}')
    
    return ApiResponse.success(
        data={
            'model_code': model_code,
            'items': items,
            'total_items': len(items)
        }
    )


@bom_api.route('/bom/<model_code>/items', methods=['POST'])
@login_required
@handle_exceptions
def add_bom_item(model_code):
    """
    Agregar item a BOM
    
    Body JSON:
        - part_no: Número de parte (requerido)
        - description: Descripción (opcional)
        - quantity: Cantidad por unidad (opcional, default: 1)
        - unit: Unidad (opcional, default: PZ)
        - reference: Referencia (opcional)
        - category: Categoría (opcional)
        - supplier: Proveedor (opcional)
    """
    data = request.get_json() or {}
    data['model_code'] = model_code
    
    validator = Validator(data)
    validator.required('part_no')
    
    if not validator.is_valid():
        return ApiResponse.validation_error(
            validator.get_first_error(),
            errors=validator.get_errors()
        )
    
    success, result = BomService.add_bom_item(data)
    
    if not success:
        return ApiResponse.error(result.get('error', 'Error al agregar item'))
    
    return ApiResponse.success(
        data=result,
        message='Item agregado exitosamente',
        status_code=201
    )


@bom_api.route('/bom/items/<int:item_id>', methods=['PUT', 'PATCH'])
@login_required
@handle_exceptions
def update_bom_item(item_id):
    """
    Actualizar item de BOM
    
    Body JSON (campos opcionales):
        - description, quantity, unit, reference, category, supplier
    """
    data = request.get_json() or {}
    
    success, error = BomService.update_bom_item(item_id, data)
    
    if not success:
        return ApiResponse.error(error)
    
    return ApiResponse.success(
        data={'item_id': item_id},
        message='Item actualizado exitosamente'
    )


@bom_api.route('/bom/items/<int:item_id>', methods=['DELETE'])
@login_required
@handle_exceptions
def delete_bom_item(item_id):
    """Eliminar item de BOM"""
    success, error = BomService.delete_bom_item(item_id)
    
    if not success:
        return ApiResponse.error(error)
    
    return ApiResponse.success(
        data={'item_id': item_id},
        message='Item eliminado exitosamente'
    )


@bom_api.route('/bom/<model_code>/import', methods=['POST'])
@login_required
@handle_exceptions
def import_bom(model_code):
    """
    Importar BOM desde lista de items
    
    Body JSON:
        - items: Lista de items a importar
            - part_no (requerido)
            - description, quantity, unit, reference, category, supplier (opcionales)
    """
    data = request.get_json() or {}
    items = data.get('items', [])
    
    if not items:
        return ApiResponse.validation_error('Lista de items vacía')
    
    success, result = BomService.import_bom_from_excel(model_code, items)
    
    if not success:
        return ApiResponse.error(result.get('error', 'Error al importar BOM'))
    
    return ApiResponse.success(
        data=result,
        message=f"Importación completada: {result.get('imported')} items importados, {result.get('skipped')} omitidos"
    )


@bom_api.route('/bom/<model_code>/requirements', methods=['GET'])
@login_required
@handle_exceptions
def calculate_requirements(model_code):
    """
    Calcular requerimientos de material para producción
    
    Query params:
        - quantity: Cantidad a producir (requerido)
    """
    quantity = request.args.get('quantity', type=int)
    
    if not quantity or quantity <= 0:
        return ApiResponse.validation_error('quantity debe ser un número mayor a 0')
    
    requirements, error = BomService.calculate_material_requirements(model_code, quantity)
    
    if error:
        return ApiResponse.error(error)
    
    # Calcular resumen
    total_items = len(requirements)
    items_ok = sum(1 for r in requirements if r.get('status') == 'OK')
    items_falta = total_items - items_ok
    
    return ApiResponse.success(
        data={
            'model_code': model_code,
            'quantity': quantity,
            'requirements': requirements,
            'summary': {
                'total_items': total_items,
                'items_ok': items_ok,
                'items_falta': items_falta
            }
        }
    )


@bom_api.route('/bom/search', methods=['GET'])
@login_required
@handle_exceptions
def search_component():
    """
    Buscar componente en todos los BOMs
    
    Query params:
        - q: Término de búsqueda (mínimo 2 caracteres)
    """
    search = request.args.get('q', '').strip()
    
    if len(search) < 2:
        return ApiResponse.validation_error('El término de búsqueda debe tener al menos 2 caracteres')
    
    results = BomService.search_component(search)
    
    return ApiResponse.success(
        data=results,
        message=f'{len(results)} resultados encontrados'
    )
