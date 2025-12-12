"""
Módulo de Validaciones
Funciones de validación centralizadas para el sistema
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


def validate_required(data: Dict[str, Any], required_fields: List[str]) -> Tuple[bool, Optional[str]]:
    """
    Validar que los campos requeridos estén presentes y no vacíos
    
    Args:
        data: Diccionario con los datos
        required_fields: Lista de campos requeridos
    
    Returns:
        Tuple (is_valid, error_message)
    """
    for field in required_fields:
        value = data.get(field)
        if value is None or (isinstance(value, str) and value.strip() == ''):
            return False, f"El campo '{field}' es requerido"
    return True, None


def validate_date_format(date_str: str, formato: str = '%Y-%m-%d') -> Tuple[bool, Optional[str]]:
    """
    Validar formato de fecha
    
    Args:
        date_str: String de fecha a validar
        formato: Formato esperado (default: YYYY-MM-DD)
    
    Returns:
        Tuple (is_valid, error_message)
    """
    if not date_str:
        return False, "La fecha es requerida"
    
    try:
        datetime.strptime(date_str[:10], formato)
        return True, None
    except ValueError:
        return False, f"Formato de fecha inválido. Esperado: {formato}"


def validate_code_format(code: str, prefix: str, pattern: str = None) -> Tuple[bool, Optional[str]]:
    """
    Validar formato de código (WO, PO, LOT, etc.)
    
    Args:
        code: Código a validar
        prefix: Prefijo esperado ('WO', 'PO', etc.)
        pattern: Patrón regex personalizado (opcional)
    
    Returns:
        Tuple (is_valid, error_message)
    """
    if not code:
        return False, f"El código {prefix} es requerido"
    
    if pattern:
        if not re.match(pattern, code):
            return False, f"Formato de código {prefix} inválido"
    else:
        # Patrón por defecto: PREFIX-YYMMDD-####
        default_pattern = rf'^{prefix}-\d{{6}}-\d{{4}}$'
        if not re.match(default_pattern, code):
            return False, f"Formato de código {prefix} inválido (esperado: {prefix}-YYMMDD-####)"
    
    return True, None


def validate_wo_code(code: str) -> Tuple[bool, Optional[str]]:
    """Validar código de Work Order (WO-YYMMDD-####)"""
    return validate_code_format(code, 'WO')


def validate_po_code(code: str) -> Tuple[bool, Optional[str]]:
    """Validar código de Purchase Order (PO-YYMMDD-####)"""
    return validate_code_format(code, 'PO')


def validate_positive_integer(value: Any, field_name: str = 'valor') -> Tuple[bool, Optional[str]]:
    """
    Validar que un valor sea entero positivo
    
    Args:
        value: Valor a validar
        field_name: Nombre del campo para mensaje de error
    
    Returns:
        Tuple (is_valid, error_message)
    """
    try:
        int_value = int(value)
        if int_value <= 0:
            return False, f"El {field_name} debe ser mayor a 0"
        return True, None
    except (ValueError, TypeError):
        return False, f"El {field_name} debe ser un número entero positivo"


def validate_email(email: str) -> Tuple[bool, Optional[str]]:
    """
    Validar formato de email
    
    Args:
        email: Email a validar
    
    Returns:
        Tuple (is_valid, error_message)
    """
    if not email:
        return True, None  # Email es opcional
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return False, "Formato de email inválido"
    return True, None


def validate_numeric_range(
    value: Any, 
    min_val: Optional[float] = None, 
    max_val: Optional[float] = None,
    field_name: str = 'valor'
) -> Tuple[bool, Optional[str]]:
    """
    Validar que un valor numérico esté dentro de un rango
    
    Args:
        value: Valor a validar
        min_val: Valor mínimo permitido
        max_val: Valor máximo permitido
        field_name: Nombre del campo
    
    Returns:
        Tuple (is_valid, error_message)
    """
    try:
        num_value = float(value)
        
        if min_val is not None and num_value < min_val:
            return False, f"El {field_name} debe ser mayor o igual a {min_val}"
        
        if max_val is not None and num_value > max_val:
            return False, f"El {field_name} debe ser menor o igual a {max_val}"
        
        return True, None
    except (ValueError, TypeError):
        return False, f"El {field_name} debe ser un valor numérico"


def validate_string_length(
    value: str,
    min_length: int = 0,
    max_length: int = 255,
    field_name: str = 'campo'
) -> Tuple[bool, Optional[str]]:
    """
    Validar longitud de string
    
    Args:
        value: String a validar
        min_length: Longitud mínima
        max_length: Longitud máxima
        field_name: Nombre del campo
    
    Returns:
        Tuple (is_valid, error_message)
    """
    if not value:
        if min_length > 0:
            return False, f"El {field_name} es requerido"
        return True, None
    
    length = len(value)
    
    if length < min_length:
        return False, f"El {field_name} debe tener al menos {min_length} caracteres"
    
    if length > max_length:
        return False, f"El {field_name} no puede exceder {max_length} caracteres"
    
    return True, None


def validate_in_list(value: Any, valid_values: List[Any], field_name: str = 'valor') -> Tuple[bool, Optional[str]]:
    """
    Validar que un valor esté en una lista de valores permitidos
    
    Args:
        value: Valor a validar
        valid_values: Lista de valores permitidos
        field_name: Nombre del campo
    
    Returns:
        Tuple (is_valid, error_message)
    """
    if value not in valid_values:
        return False, f"El {field_name} debe ser uno de: {', '.join(map(str, valid_values))}"
    return True, None


def validate_estado_wo(estado: str) -> Tuple[bool, Optional[str]]:
    """Validar estado de Work Order"""
    estados_validos = ['CREADA', 'PLANIFICADA', 'EN_PRODUCCION', 'CERRADA']
    return validate_in_list(estado.upper() if estado else '', estados_validos, 'estado')


def validate_estado_plan(estado: str) -> Tuple[bool, Optional[str]]:
    """Validar estado de Plan"""
    estados_validos = ['PENDIENTE', 'EN PROGRESO', 'PAUSADO', 'TERMINADO', 'CANCELADO', 'PLAN']
    return validate_in_list(estado.upper() if estado else '', estados_validos, 'estado')


class Validator:
    """Clase para encadenar validaciones"""
    
    def __init__(self, data: Dict[str, Any]):
        self.data = data
        self.errors = {}
        self._is_valid = True
    
    def required(self, *fields: str) -> 'Validator':
        """Validar campos requeridos"""
        for field in fields:
            is_valid, error = validate_required(self.data, [field])
            if not is_valid:
                self.errors[field] = error
                self._is_valid = False
        return self
    
    def date(self, field: str, required: bool = False) -> 'Validator':
        """Validar campo de fecha"""
        value = self.data.get(field)
        if not value:
            if required:
                self.errors[field] = f"El campo '{field}' es requerido"
                self._is_valid = False
            return self
        
        is_valid, error = validate_date_format(value)
        if not is_valid:
            self.errors[field] = error
            self._is_valid = False
        return self
    
    def positive_int(self, field: str, required: bool = False) -> 'Validator':
        """Validar entero positivo"""
        value = self.data.get(field)
        if value is None:
            if required:
                self.errors[field] = f"El campo '{field}' es requerido"
                self._is_valid = False
            return self
        
        is_valid, error = validate_positive_integer(value, field)
        if not is_valid:
            self.errors[field] = error
            self._is_valid = False
        return self
    
    def code(self, field: str, prefix: str, required: bool = True) -> 'Validator':
        """Validar código con prefijo"""
        value = self.data.get(field)
        if not value:
            if required:
                self.errors[field] = f"El código {prefix} es requerido"
                self._is_valid = False
            return self
        
        is_valid, error = validate_code_format(value, prefix)
        if not is_valid:
            self.errors[field] = error
            self._is_valid = False
        return self
    
    def in_list(self, field: str, valid_values: List[Any], required: bool = False) -> 'Validator':
        """Validar valor en lista"""
        value = self.data.get(field)
        if not value:
            if required:
                self.errors[field] = f"El campo '{field}' es requerido"
                self._is_valid = False
            return self
        
        is_valid, error = validate_in_list(value, valid_values, field)
        if not is_valid:
            self.errors[field] = error
            self._is_valid = False
        return self
    
    def is_valid(self) -> bool:
        """Retorna si todas las validaciones pasaron"""
        return self._is_valid
    
    def get_errors(self) -> Dict[str, str]:
        """Retorna diccionario de errores"""
        return self.errors
    
    def get_first_error(self) -> Optional[str]:
        """Retorna el primer mensaje de error o None"""
        if self.errors:
            return list(self.errors.values())[0]
        return None
