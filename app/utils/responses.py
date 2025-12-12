"""
Módulo de Respuestas API Estandarizadas
Proporciona formato consistente para todas las respuestas JSON del sistema
"""

from flask import jsonify
from typing import Any, Optional, Dict, List, Union
from functools import wraps
import traceback


class ApiResponse:
    """Clase para generar respuestas API estandarizadas"""
    
    @staticmethod
    def success(
        data: Any = None,
        message: str = "Operación exitosa",
        code: str = "SUCCESS",
        meta: Optional[Dict] = None,
        status_code: int = 200
    ) -> tuple:
        """
        Genera respuesta de éxito estandarizada
        
        Args:
            data: Datos a devolver
            message: Mensaje descriptivo
            code: Código de operación
            meta: Metadatos adicionales (paginación, totales, etc.)
            status_code: Código HTTP
        
        Returns:
            Tuple (response_json, status_code)
        """
        response = {
            "success": True,
            "code": code,
            "message": message,
            "data": data,
            "error": None
        }
        
        if meta:
            response["meta"] = meta
            
        return jsonify(response), status_code
    
    @staticmethod
    def error(
        message: str = "Error en la operación",
        code: str = "ERROR",
        errors: Optional[Union[str, List, Dict]] = None,
        status_code: int = 400,
        data: Any = None
    ) -> tuple:
        """
        Genera respuesta de error estandarizada
        
        Args:
            message: Mensaje de error principal
            code: Código de error
            errors: Detalles adicionales del error
            status_code: Código HTTP
            data: Datos parciales si los hay
        
        Returns:
            Tuple (response_json, status_code)
        """
        response = {
            "success": False,
            "code": code,
            "message": message,
            "data": data,
            "error": errors if errors else message
        }
        
        return jsonify(response), status_code
    
    @staticmethod
    def not_found(
        message: str = "Recurso no encontrado",
        resource: Optional[str] = None
    ) -> tuple:
        """Respuesta para recurso no encontrado"""
        if resource:
            message = f"{resource} no encontrado"
        return ApiResponse.error(
            message=message,
            code="NOT_FOUND",
            status_code=404
        )
    
    @staticmethod
    def validation_error(
        message: str = "Error de validación",
        errors: Optional[Dict] = None,
        field: Optional[str] = None
    ) -> tuple:
        """Respuesta para error de validación"""
        error_detail = errors
        if field and not errors:
            error_detail = {field: message}
        return ApiResponse.error(
            message=message,
            code="VALIDATION_ERROR",
            errors=error_detail,
            status_code=400
        )
    
    @staticmethod
    def unauthorized(message: str = "No autorizado") -> tuple:
        """Respuesta para usuario no autorizado"""
        return ApiResponse.error(
            message=message,
            code="UNAUTHORIZED",
            status_code=401
        )
    
    @staticmethod
    def forbidden(message: str = "Acceso denegado") -> tuple:
        """Respuesta para acceso prohibido"""
        return ApiResponse.error(
            message=message,
            code="FORBIDDEN",
            status_code=403
        )
    
    @staticmethod
    def conflict(message: str = "Conflicto con recurso existente") -> tuple:
        """Respuesta para conflicto (ej: duplicado)"""
        return ApiResponse.error(
            message=message,
            code="CONFLICT",
            status_code=409
        )
    
    @staticmethod
    def server_error(
        message: str = "Error interno del servidor",
        exception: Optional[Exception] = None
    ) -> tuple:
        """Respuesta para error del servidor"""
        error_detail = None
        if exception:
            # En desarrollo mostrar detalles, en producción ocultar
            error_detail = str(exception)
            print(f"❌ Server Error: {exception}")
            traceback.print_exc()
            
        return ApiResponse.error(
            message=message,
            code="INTERNAL_ERROR",
            errors=error_detail,
            status_code=500
        )
    
    @staticmethod
    def created(
        data: Any = None,
        message: str = "Recurso creado exitosamente"
    ) -> tuple:
        """Respuesta para recurso creado"""
        return ApiResponse.success(
            data=data,
            message=message,
            code="CREATED",
            status_code=201
        )
    
    @staticmethod
    def paginated(
        data: List,
        total: int,
        page: int = 1,
        per_page: int = 50,
        message: str = "Datos obtenidos exitosamente"
    ) -> tuple:
        """Respuesta paginada"""
        total_pages = (total + per_page - 1) // per_page
        return ApiResponse.success(
            data=data,
            message=message,
            meta={
                "pagination": {
                    "total": total,
                    "page": page,
                    "per_page": per_page,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_prev": page > 1
                }
            }
        )


# Funciones de conveniencia (shortcuts)
def api_response(success: bool, **kwargs) -> tuple:
    """
    Función genérica para crear respuestas API
    
    Args:
        success: Si la operación fue exitosa
        **kwargs: Argumentos adicionales según el tipo de respuesta
    
    Returns:
        Tuple (response_json, status_code)
    """
    if success:
        return ApiResponse.success(**kwargs)
    else:
        return ApiResponse.error(**kwargs)


def success_response(data: Any = None, message: str = "OK", status_code: int = 200, **kwargs) -> dict:
    """Atajo para respuesta de éxito - retorna diccionario para servicios"""
    response = {
        "success": True,
        "message": message,
        "data": data,
        "statusCode": status_code
    }
    response.update(kwargs)
    return response


def error_response(message: str, status_code: int = 400, code: str = "ERROR", **kwargs) -> dict:
    """Atajo para respuesta de error - retorna diccionario para servicios"""
    response = {
        "success": False,
        "message": message,
        "error": message,
        "code": code,
        "statusCode": status_code
    }
    response.update(kwargs)
    return response


def paginated_response(data: List, total: int, pagina: int = 1, 
                       por_pagina: int = 50, total_paginas: int = 0,
                       mensaje: str = "Datos obtenidos") -> dict:
    """Respuesta paginada - retorna diccionario para servicios"""
    if total_paginas == 0:
        total_paginas = (total + por_pagina - 1) // por_pagina
    
    return {
        "success": True,
        "message": mensaje,
        "data": data,
        "statusCode": 200,
        "pagination": {
            "total": total,
            "pagina": pagina,
            "porPagina": por_pagina,
            "totalPaginas": total_paginas,
            "hasNext": pagina < total_paginas,
            "hasPrev": pagina > 1
        }
    }


def handle_exceptions(func):
    """
    Decorador para manejo centralizado de excepciones en endpoints
    
    Usage:
        @app.route('/api/example')
        @handle_exceptions
        def my_endpoint():
            # código que puede lanzar excepciones
            pass
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValueError as e:
            return ApiResponse.validation_error(message=str(e))
        except PermissionError as e:
            return ApiResponse.forbidden(message=str(e))
        except FileNotFoundError as e:
            return ApiResponse.not_found(message=str(e))
        except Exception as e:
            return ApiResponse.server_error(exception=e)
    return wrapper


# Compatibilidad con formatos antiguos
def legacy_ok_response(data: Any = None, message: str = "OK", **extra) -> dict:
    """
    Formato legacy con 'ok' en lugar de 'success'
    Para mantener compatibilidad con código existente
    """
    response = {
        "ok": True,
        "message": message
    }
    if data is not None:
        if isinstance(data, dict):
            response.update(data)
        else:
            response["data"] = data
    response.update(extra)
    return jsonify(response)


def legacy_error_response(message: str, code: str = "ERROR", **extra) -> tuple:
    """
    Formato legacy con 'ok' en lugar de 'success'
    Para mantener compatibilidad con código existente
    """
    response = {
        "ok": False,
        "code": code,
        "message": message,
        "error": message
    }
    response.update(extra)
    return jsonify(response), 400
