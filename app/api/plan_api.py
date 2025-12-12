"""
Plan API - Endpoints para gestión de planes de producción
Blueprint modular con respuestas estandarizadas
"""

from flask import Blueprint, request, jsonify, session
from functools import wraps

from ..services.plan_service import PlanService
from ..utils.responses import ApiResponse, handle_exceptions
from ..utils.validators import Validator

# Blueprint para API de Plan
plan_api = Blueprint('plan_api', __name__, url_prefix='/api/v2')


def login_required(f):
    """Decorador para verificar autenticación"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'usuario' not in session:
            return ApiResponse.error('Usuario no autenticado', status_code=401)
        return f(*args, **kwargs)
    return decorated


# ============== ENDPOINTS PÚBLICOS (Health Check) ==============

@plan_api.route('/health', methods=['GET'])
def health_check():
    """
    Health check público para verificar que la API está funcionando.
    No requiere autenticación.
    """
    return ApiResponse.success(
        data={
            'service': 'plan_api',
            'version': '2.0',
            'status': 'healthy',
            'endpoints': [
                'GET /api/v2/plan',
                'GET /api/v2/plan/<id>',
                'POST /api/v2/plan',
                'PUT /api/v2/plan/<id>',
                'DELETE /api/v2/plan/<id>',
                'GET /api/v2/health'
            ]
        },
        message='API v2 Plan funcionando correctamente'
    )


# ============== ENDPOINTS PROTEGIDOS ==============

@plan_api.route('/plan', methods=['GET'])
@login_required
@handle_exceptions
def list_plans():
    """
    Listar planes de producción
    
    Query params:
        - start: Fecha inicial (YYYY-MM-DD)
        - end: Fecha final (YYYY-MM-DD)
        - line: Filtrar por línea
        - status: Filtrar por estado
    """
    start_date = request.args.get('start')
    end_date = request.args.get('end')
    line = request.args.get('line')
    status = request.args.get('status')
    
    plans, error = PlanService.list_plans(
        start_date=start_date,
        end_date=end_date,
        line=line,
        status=status
    )
    
    if error:
        return ApiResponse.error(error)
    
    return ApiResponse.success(
        data=plans,
        message=f'{len(plans)} planes encontrados'
    )


@plan_api.route('/plan', methods=['POST'])
@login_required
@handle_exceptions
def create_plan():
    """
    Crear nuevo plan de producción
    
    Body JSON:
        - working_date: Fecha de trabajo (requerido)
        - part_no: Número de parte (requerido)
        - line: Línea de producción (requerido)
        - turno: DIA, TIEMPO EXTRA, NOCHE (opcional, default: DIA)
        - plan_count: Cantidad planificada (opcional)
        - wo_code: Código de WO (opcional)
        - po_code: Código de PO (opcional)
        - group_no: Número de grupo (opcional)
    """
    data = request.get_json() or {}
    
    # Validar campos requeridos
    validator = Validator(data)
    validator.required('working_date', 'part_no', 'line')
    validator.date('working_date', required=True)
    
    if not validator.is_valid():
        return ApiResponse.validation_error(
            validator.get_first_error(),
            errors=validator.get_errors()
        )
    
    success, result = PlanService.create_plan(data)
    
    if not success:
        return ApiResponse.error(result.get('error', 'Error al crear plan'))
    
    return ApiResponse.success(
        data=result,
        message='Plan creado exitosamente',
        status_code=201
    )


@plan_api.route('/plan/<lot_no>', methods=['GET'])
@login_required
@handle_exceptions
def get_plan(lot_no):
    """Obtener plan específico por lote"""
    plan = PlanService.get_plan_by_lot(lot_no)
    
    if not plan:
        return ApiResponse.not_found(f'Plan {lot_no} no encontrado')
    
    return ApiResponse.success(data=plan)


@plan_api.route('/plan/<lot_no>', methods=['PUT', 'PATCH'])
@login_required
@handle_exceptions
def update_plan(lot_no):
    """
    Actualizar plan existente
    
    Body JSON (campos opcionales):
        - plan_count: Nueva cantidad
        - status: Nuevo estado
        - line: Nueva línea
        - wo_code, po_code: Códigos
        - turno: Nuevo turno
        - ct, uph, project, model_code: Datos del modelo
    """
    data = request.get_json() or {}
    
    success, error = PlanService.update_plan(lot_no, data)
    
    if not success:
        return ApiResponse.error(error)
    
    return ApiResponse.success(
        data={'lot_no': lot_no},
        message='Plan actualizado exitosamente'
    )


@plan_api.route('/plan/<lot_no>', methods=['DELETE'])
@login_required
@handle_exceptions
def delete_plan(lot_no):
    """Eliminar plan (solo si no está EN PROGRESO o TERMINADO)"""
    success, error = PlanService.delete_plan(lot_no)
    
    if not success:
        return ApiResponse.error(error)
    
    return ApiResponse.success(
        data={'lot_no': lot_no},
        message='Plan eliminado exitosamente'
    )


@plan_api.route('/plan/<lot_no>/status', methods=['POST', 'PUT'])
@login_required
@handle_exceptions
def change_plan_status(lot_no):
    """
    Cambiar estado de un plan con validaciones
    
    Body JSON:
        - status: Nuevo estado (PENDIENTE, EN PROGRESO, PAUSADO, TERMINADO, CANCELADO)
        - reason: Motivo del cambio (opcional, para PAUSADO/CANCELADO)
    """
    data = request.get_json() or {}
    new_status = data.get('status', '').strip()
    reason = data.get('reason', '').strip()
    
    if not new_status:
        return ApiResponse.validation_error('status es requerido')
    
    success, result = PlanService.change_status(lot_no, new_status, reason)
    
    if not success:
        error_code = result.get('error_code', 'ERROR')
        error_msg = result.get('error', 'Error al cambiar estado')
        
        # Manejar conflicto de línea de manera especial
        if error_code == 'LINE_CONFLICT':
            return ApiResponse.error(
                message=error_msg,
                status_code=409,  # Conflict
                data={
                    'error_code': error_code,
                    'line': result.get('line'),
                    'lot_no_en_progreso': result.get('lot_no_en_progreso')
                }
            )
        
        return ApiResponse.error(error_msg, data={'error_code': error_code})
    
    return ApiResponse.success(
        data=result,
        message=f'Estado actualizado a {new_status}'
    )


@plan_api.route('/plan/lines-summary', methods=['GET'])
@login_required
@handle_exceptions
def lines_summary():
    """
    Obtener resumen de producción por línea
    
    Query params:
        - date: Fecha a consultar (YYYY-MM-DD, default: hoy)
    """
    working_date = request.args.get('date')
    
    summary = PlanService.get_lines_summary(working_date)
    
    return ApiResponse.success(
        data=summary,
        message='Resumen de líneas obtenido'
    )


@plan_api.route('/raw/search', methods=['GET'])
@login_required
@handle_exceptions
def search_raw():
    """
    Buscar datos en tabla RAW por part_no
    
    Query params:
        - part_no: Número de parte a buscar (requerido)
    """
    part_no = request.args.get('part_no', '').strip()
    
    if not part_no:
        return ApiResponse.validation_error('part_no es requerido')
    
    result = PlanService.get_raw_data(part_no)
    
    if not result:
        return ApiResponse.success(data=[], message='No se encontraron datos')
    
    return ApiResponse.success(data=[result])
