"""
BOM Service - Lógica de negocio para gestión de BOM (Bill of Materials)
"""

from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from ..database.db_mysql import execute_query


class BomService:
    """Servicio para gestión de BOM (Bill of Materials)"""
    
    @staticmethod
    def get_bom_by_model(model_code: str) -> Tuple[List[Dict], Optional[str]]:
        """
        Obtener BOM de un modelo específico
        
        Args:
            model_code: Código del modelo
            
        Returns:
            Tuple (lista_componentes, error)
        """
        if not model_code:
            return [], 'Código de modelo requerido'
        
        try:
            sql = """
                SELECT id, model_code, item_no, part_no, description, 
                       quantity, unit, reference, category, supplier,
                       created_at, updated_at
                FROM bom_items
                WHERE model_code = %s
                ORDER BY item_no ASC
            """
            
            results = execute_query(sql, (model_code,), fetch='all')
            return results or [], None
            
        except Exception as e:
            return [], str(e)
    
    @staticmethod
    def get_models_list() -> List[Dict]:
        """
        Obtener lista de modelos con BOM
        
        Returns:
            Lista de modelos
        """
        try:
            sql = """
                SELECT DISTINCT model_code, 
                       COUNT(*) as items_count,
                       MAX(created_at) as last_updated
                FROM bom_items
                GROUP BY model_code
                ORDER BY model_code ASC
            """
            
            results = execute_query(sql, fetch='all')
            return results or []
            
        except Exception:
            return []
    
    @staticmethod
    def add_bom_item(data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """
        Agregar item a BOM
        
        Args:
            data: Datos del item
            
        Returns:
            Tuple (success, result_or_error)
        """
        try:
            model_code = data.get('model_code', '').strip()
            part_no = data.get('part_no', '').strip()
            
            if not model_code:
                return False, {'error': 'Código de modelo requerido'}
            
            if not part_no:
                return False, {'error': 'Número de parte requerido'}
            
            # Verificar si ya existe
            existing = execute_query(
                "SELECT id FROM bom_items WHERE model_code = %s AND part_no = %s",
                (model_code, part_no),
                fetch='one'
            )
            
            if existing:
                return False, {'error': f'El componente {part_no} ya existe en el BOM de {model_code}'}
            
            # Obtener siguiente item_no
            max_item = execute_query(
                "SELECT MAX(item_no) as max_no FROM bom_items WHERE model_code = %s",
                (model_code,),
                fetch='one'
            )
            
            next_item_no = 1
            if max_item and max_item.get('max_no'):
                next_item_no = int(max_item['max_no']) + 1
            
            sql = """
                INSERT INTO bom_items 
                (model_code, item_no, part_no, description, quantity, unit,
                 reference, category, supplier, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """
            
            params = (
                model_code,
                next_item_no,
                part_no,
                data.get('description', ''),
                float(data.get('quantity', 1)),
                data.get('unit', 'PZ'),
                data.get('reference', ''),
                data.get('category', ''),
                data.get('supplier', '')
            )
            
            execute_query(sql, params)
            
            return True, {
                'model_code': model_code,
                'item_no': next_item_no,
                'part_no': part_no,
                'message': 'Item agregado exitosamente'
            }
            
        except Exception as e:
            return False, {'error': str(e)}
    
    @staticmethod
    def update_bom_item(item_id: int, data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Actualizar item de BOM
        
        Args:
            item_id: ID del item
            data: Datos a actualizar
            
        Returns:
            Tuple (success, error_message)
        """
        if not item_id:
            return False, 'ID de item requerido'
        
        try:
            # Verificar que existe
            existing = execute_query(
                "SELECT id FROM bom_items WHERE id = %s",
                (item_id,),
                fetch='one'
            )
            
            if not existing:
                return False, f'Item {item_id} no encontrado'
            
            fields = []
            vals = []
            
            updatable = ['description', 'quantity', 'unit', 'reference', 'category', 'supplier']
            for field in updatable:
                if field in data:
                    fields.append(f'{field} = %s')
                    vals.append(data[field])
            
            if not fields:
                return False, 'Sin cambios'
            
            fields.append('updated_at = NOW()')
            
            sql = f"UPDATE bom_items SET {', '.join(fields)} WHERE id = %s"
            vals.append(item_id)
            
            execute_query(sql, tuple(vals))
            
            return True, None
            
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def delete_bom_item(item_id: int) -> Tuple[bool, Optional[str]]:
        """
        Eliminar item de BOM
        
        Args:
            item_id: ID del item
            
        Returns:
            Tuple (success, error_message)
        """
        if not item_id:
            return False, 'ID de item requerido'
        
        try:
            execute_query("DELETE FROM bom_items WHERE id = %s", (item_id,))
            return True, None
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def import_bom_from_excel(model_code: str, items: List[Dict]) -> Tuple[bool, Dict[str, Any]]:
        """
        Importar BOM desde lista de items (Excel/CSV)
        
        Args:
            model_code: Código del modelo
            items: Lista de items a importar
            
        Returns:
            Tuple (success, result_or_error)
        """
        if not model_code:
            return False, {'error': 'Código de modelo requerido'}
        
        if not items:
            return False, {'error': 'Lista de items vacía'}
        
        try:
            imported = 0
            skipped = 0
            errors = []
            
            for idx, item in enumerate(items):
                try:
                    part_no = str(item.get('part_no', '')).strip()
                    if not part_no:
                        skipped += 1
                        continue
                    
                    # Verificar si ya existe
                    existing = execute_query(
                        "SELECT id FROM bom_items WHERE model_code = %s AND part_no = %s",
                        (model_code, part_no),
                        fetch='one'
                    )
                    
                    if existing:
                        # Actualizar existente
                        execute_query(
                            """UPDATE bom_items SET 
                               description = %s, quantity = %s, unit = %s,
                               reference = %s, category = %s, supplier = %s,
                               updated_at = NOW()
                               WHERE id = %s""",
                            (
                                str(item.get('description', '')),
                                float(item.get('quantity', 1)),
                                str(item.get('unit', 'PZ')),
                                str(item.get('reference', '')),
                                str(item.get('category', '')),
                                str(item.get('supplier', '')),
                                existing.get('id')
                            )
                        )
                    else:
                        # Insertar nuevo
                        execute_query(
                            """INSERT INTO bom_items 
                               (model_code, item_no, part_no, description, quantity, unit,
                                reference, category, supplier, created_at)
                               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())""",
                            (
                                model_code,
                                idx + 1,
                                part_no,
                                str(item.get('description', '')),
                                float(item.get('quantity', 1)),
                                str(item.get('unit', 'PZ')),
                                str(item.get('reference', '')),
                                str(item.get('category', '')),
                                str(item.get('supplier', ''))
                            )
                        )
                    
                    imported += 1
                    
                except Exception as item_error:
                    errors.append(f"Item {idx + 1}: {str(item_error)}")
                    skipped += 1
            
            return True, {
                'model_code': model_code,
                'imported': imported,
                'skipped': skipped,
                'errors': errors if errors else None
            }
            
        except Exception as e:
            return False, {'error': str(e)}
    
    @staticmethod
    def calculate_material_requirements(
        model_code: str, 
        quantity: int
    ) -> Tuple[List[Dict], Optional[str]]:
        """
        Calcular requerimientos de material para producción
        
        Args:
            model_code: Código del modelo
            quantity: Cantidad a producir
            
        Returns:
            Tuple (lista_requerimientos, error)
        """
        if not model_code:
            return [], 'Código de modelo requerido'
        
        if quantity <= 0:
            return [], 'Cantidad debe ser mayor a 0'
        
        try:
            # Obtener BOM
            bom_items, error = BomService.get_bom_by_model(model_code)
            
            if error:
                return [], error
            
            if not bom_items:
                return [], f'No se encontró BOM para el modelo {model_code}'
            
            requirements = []
            for item in bom_items:
                required_qty = float(item.get('quantity', 1)) * quantity
                
                # Buscar stock actual si existe en materiales
                stock_info = execute_query(
                    "SELECT stock_actual FROM materiales WHERE codigo = %s",
                    (item.get('part_no'),),
                    fetch='one'
                )
                
                stock_actual = stock_info.get('stock_actual', 0) if stock_info else 0
                shortage = max(0, required_qty - stock_actual)
                
                requirements.append({
                    'part_no': item.get('part_no'),
                    'description': item.get('description'),
                    'unit': item.get('unit'),
                    'quantity_per_unit': item.get('quantity'),
                    'required_quantity': required_qty,
                    'stock_actual': stock_actual,
                    'shortage': shortage,
                    'status': 'OK' if shortage == 0 else 'FALTA'
                })
            
            return requirements, None
            
        except Exception as e:
            return [], str(e)
    
    @staticmethod
    def search_component(search: str) -> List[Dict]:
        """
        Buscar componente en todos los BOMs
        
        Args:
            search: Término de búsqueda
            
        Returns:
            Lista de resultados
        """
        if not search or len(search) < 2:
            return []
        
        try:
            sql = """
                SELECT model_code, item_no, part_no, description, quantity, unit
                FROM bom_items
                WHERE part_no LIKE %s OR description LIKE %s
                ORDER BY model_code, item_no
                LIMIT 100
            """
            
            search_term = f'%{search}%'
            results = execute_query(sql, (search_term, search_term), fetch='all')
            
            return results or []
            
        except Exception:
            return []
