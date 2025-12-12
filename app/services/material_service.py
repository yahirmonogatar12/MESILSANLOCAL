"""
Material Service - Lógica de negocio para gestión de materiales
"""

from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from ..database.db_mysql import execute_query
from ..utils.timezone import get_mexico_time


class MaterialService:
    """Servicio para gestión de materiales e inventario"""
    
    @staticmethod
    def get_materials(
        search: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[Dict], int, Optional[str]]:
        """
        Obtener lista de materiales con filtros
        
        Args:
            search: Búsqueda por código o descripción
            category: Filtrar por categoría
            limit: Límite de resultados
            offset: Desplazamiento para paginación
            
        Returns:
            Tuple (lista_materiales, total, error)
        """
        try:
            conditions = []
            params = []
            
            if search:
                conditions.append("(codigo LIKE %s OR descripcion LIKE %s)")
                params.extend([f'%{search}%', f'%{search}%'])
            
            if category:
                conditions.append("categoria = %s")
                params.append(category)
            
            where_clause = ' AND '.join(conditions) if conditions else '1=1'
            
            # Contar total
            count_sql = f"SELECT COUNT(*) as total FROM materiales WHERE {where_clause}"
            count_result = execute_query(count_sql, tuple(params) if params else None, fetch='one')
            total = count_result.get('total', 0) if count_result else 0
            
            # Obtener materiales
            sql = f"""
                SELECT id, codigo, descripcion, categoria, unidad, 
                       stock_actual, stock_minimo, ubicacion, activo,
                       created_at, updated_at
                FROM materiales 
                WHERE {where_clause}
                ORDER BY codigo ASC
                LIMIT %s OFFSET %s
            """
            params.extend([limit, offset])
            
            results = execute_query(sql, tuple(params), fetch='all')
            
            return results or [], total, None
            
        except Exception as e:
            return [], 0, str(e)
    
    @staticmethod
    def get_material_by_code(codigo: str) -> Optional[Dict[str, Any]]:
        """
        Obtener material por código
        
        Args:
            codigo: Código del material
            
        Returns:
            Diccionario con datos del material o None
        """
        if not codigo:
            return None
        
        try:
            result = execute_query(
                "SELECT * FROM materiales WHERE codigo = %s",
                (codigo,),
                fetch='one'
            )
            return result
        except Exception:
            return None
    
    @staticmethod
    def create_material(data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """
        Crear nuevo material
        
        Args:
            data: Datos del material
            
        Returns:
            Tuple (success, result_or_error)
        """
        try:
            codigo = data.get('codigo', '').strip()
            descripcion = data.get('descripcion', '').strip()
            
            if not codigo:
                return False, {'error': 'Código es requerido'}
            
            if not descripcion:
                return False, {'error': 'Descripción es requerida'}
            
            # Verificar que no exista
            existing = MaterialService.get_material_by_code(codigo)
            if existing:
                return False, {'error': f'Ya existe un material con código {codigo}'}
            
            sql = """
                INSERT INTO materiales 
                (codigo, descripcion, categoria, unidad, stock_actual, 
                 stock_minimo, ubicacion, activo, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 1, NOW())
            """
            params = (
                codigo,
                descripcion,
                data.get('categoria', ''),
                data.get('unidad', 'PZ'),
                int(data.get('stock_actual', 0)),
                int(data.get('stock_minimo', 0)),
                data.get('ubicacion', '')
            )
            
            execute_query(sql, params)
            
            return True, {'codigo': codigo, 'message': 'Material creado exitosamente'}
            
        except Exception as e:
            return False, {'error': str(e)}
    
    @staticmethod
    def update_material(codigo: str, data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Actualizar material existente
        
        Args:
            codigo: Código del material
            data: Datos a actualizar
            
        Returns:
            Tuple (success, error_message)
        """
        if not codigo:
            return False, 'Código es requerido'
        
        try:
            # Verificar que exista
            existing = MaterialService.get_material_by_code(codigo)
            if not existing:
                return False, f'Material {codigo} no encontrado'
            
            fields = []
            vals = []
            
            updatable = ['descripcion', 'categoria', 'unidad', 'stock_minimo', 'ubicacion']
            for field in updatable:
                if field in data:
                    fields.append(f'{field} = %s')
                    vals.append(data[field])
            
            if not fields:
                return False, 'Sin cambios'
            
            fields.append('updated_at = NOW()')
            
            sql = f"UPDATE materiales SET {', '.join(fields)} WHERE codigo = %s"
            vals.append(codigo)
            
            execute_query(sql, tuple(vals))
            
            return True, None
            
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def update_stock(
        codigo: str, 
        cantidad: int, 
        tipo: str = 'ENTRADA',
        motivo: str = '',
        usuario: str = ''
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Actualizar stock de un material
        
        Args:
            codigo: Código del material
            cantidad: Cantidad a modificar (positivo)
            tipo: 'ENTRADA' o 'SALIDA'
            motivo: Motivo del movimiento
            usuario: Usuario que realiza el movimiento
            
        Returns:
            Tuple (success, result_or_error)
        """
        if not codigo:
            return False, {'error': 'Código es requerido'}
        
        if cantidad <= 0:
            return False, {'error': 'Cantidad debe ser mayor a 0'}
        
        tipo = tipo.upper()
        if tipo not in ['ENTRADA', 'SALIDA']:
            return False, {'error': 'Tipo debe ser ENTRADA o SALIDA'}
        
        try:
            # Obtener stock actual
            material = MaterialService.get_material_by_code(codigo)
            if not material:
                return False, {'error': f'Material {codigo} no encontrado'}
            
            stock_actual = int(material.get('stock_actual', 0))
            
            # Calcular nuevo stock
            if tipo == 'ENTRADA':
                nuevo_stock = stock_actual + cantidad
            else:
                if cantidad > stock_actual:
                    return False, {
                        'error': f'Stock insuficiente. Disponible: {stock_actual}',
                        'stock_actual': stock_actual
                    }
                nuevo_stock = stock_actual - cantidad
            
            # Actualizar stock
            execute_query(
                "UPDATE materiales SET stock_actual = %s, updated_at = NOW() WHERE codigo = %s",
                (nuevo_stock, codigo)
            )
            
            # Registrar movimiento
            execute_query(
                """INSERT INTO movimientos_material 
                   (codigo_material, tipo, cantidad, stock_anterior, stock_nuevo, 
                    motivo, usuario, fecha)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())""",
                (codigo, tipo, cantidad, stock_actual, nuevo_stock, motivo, usuario)
            )
            
            return True, {
                'codigo': codigo,
                'tipo': tipo,
                'cantidad': cantidad,
                'stock_anterior': stock_actual,
                'stock_nuevo': nuevo_stock
            }
            
        except Exception as e:
            return False, {'error': str(e)}
    
    @staticmethod
    def get_inventory_summary() -> Dict[str, Any]:
        """
        Obtener resumen de inventario
        
        Returns:
            Diccionario con resumen
        """
        try:
            result = execute_query(
                """SELECT 
                    COUNT(*) as total_materiales,
                    SUM(CASE WHEN stock_actual <= stock_minimo THEN 1 ELSE 0 END) as bajo_minimo,
                    SUM(CASE WHEN stock_actual = 0 THEN 1 ELSE 0 END) as sin_stock
                   FROM materiales WHERE activo = 1""",
                fetch='one'
            )
            
            return result or {
                'total_materiales': 0,
                'bajo_minimo': 0,
                'sin_stock': 0
            }
            
        except Exception:
            return {
                'total_materiales': 0,
                'bajo_minimo': 0,
                'sin_stock': 0
            }
    
    @staticmethod
    def get_low_stock_materials() -> List[Dict[str, Any]]:
        """
        Obtener materiales con stock bajo (igual o menor al mínimo)
        
        Returns:
            Lista de materiales con stock bajo
        """
        try:
            results = execute_query(
                """SELECT codigo, descripcion, stock_actual, stock_minimo, ubicacion
                   FROM materiales 
                   WHERE activo = 1 AND stock_actual <= stock_minimo
                   ORDER BY (stock_actual - stock_minimo) ASC""",
                fetch='all'
            )
            return results or []
        except Exception:
            return []
    
    @staticmethod
    def get_movement_history(
        codigo: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Obtener historial de movimientos
        
        Args:
            codigo: Filtrar por código de material
            start_date: Fecha inicial
            end_date: Fecha final
            limit: Límite de resultados
            
        Returns:
            Lista de movimientos
        """
        try:
            conditions = []
            params = []
            
            if codigo:
                conditions.append("codigo_material = %s")
                params.append(codigo)
            
            if start_date:
                conditions.append("DATE(fecha) >= %s")
                params.append(start_date)
            
            if end_date:
                conditions.append("DATE(fecha) <= %s")
                params.append(end_date)
            
            where_clause = ' AND '.join(conditions) if conditions else '1=1'
            
            sql = f"""
                SELECT id, codigo_material, tipo, cantidad, 
                       stock_anterior, stock_nuevo, motivo, usuario, fecha
                FROM movimientos_material
                WHERE {where_clause}
                ORDER BY fecha DESC
                LIMIT %s
            """
            params.append(limit)
            
            results = execute_query(sql, tuple(params), fetch='all')
            return results or []
            
        except Exception:
            return []
