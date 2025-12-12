"""
Plan Service - Lógica de negocio para gestión de planes de producción
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from ..database.db_mysql import execute_query
from ..utils.responses import ApiResponse
from ..utils.timezone import get_mexico_time, get_shift_routing


class PlanService:
    """Servicio para gestión de planes de producción"""
    
    # Estados válidos para un plan
    VALID_STATUSES = ['PENDIENTE', 'EN PROGRESO', 'PAUSADO', 'TERMINADO', 'CANCELADO', 'PLAN']
    
    # Mapeo de turnos a routing
    SHIFT_ROUTING = {
        'DIA': 1,
        'TIEMPO EXTRA': 2,
        'NOCHE': 3
    }
    
    @staticmethod
    def generate_lot_number(fecha: datetime, prefix: str = 'ASSYLINE') -> str:
        """
        Generar número de lote único basado en fecha
        
        Args:
            fecha: Fecha para generar el lote
            prefix: Prefijo del lote
            
        Returns:
            Código de lote único
        """
        try:
            fecha_str = fecha.strftime('%y%m%d')
            lot_prefix = f'{prefix}-{fecha_str}'
            
            row = execute_query(
                "SELECT COUNT(*) AS c FROM plan_main WHERE lot_no LIKE %s", 
                (f"{lot_prefix}%",), 
                fetch='one'
            )
            
            count = 0
            if row:
                if isinstance(row, dict):
                    count = list(row.values())[0] if len(row.values()) == 1 else (row.get('c') or row.get('COUNT(*)') or 0)
                else:
                    count = row[0]
            
            return f"{lot_prefix}-{int(count)+1:03d}"
        except Exception:
            # Fallback
            return f"{prefix}-{fecha.strftime('%y%m%d')}-001"
    
    @staticmethod
    def get_raw_data(part_no: str) -> Optional[Dict[str, Any]]:
        """
        Obtener datos de la tabla RAW por part_no
        
        Args:
            part_no: Número de parte a buscar
            
        Returns:
            Diccionario con datos del modelo o None
        """
        query = """
            SELECT part_no, model, project, c_t as ct, uph
            FROM raw
            WHERE TRIM(model) = %s 
               OR TRIM(part_no) = %s 
               OR TRIM(part_no) LIKE %s
               OR UPPER(TRIM(part_no)) = UPPER(%s)
            LIMIT 1
        """
        params = (part_no, part_no, f'%{part_no}%', part_no)
        
        result = execute_query(query, params, fetch='one')
        
        if result:
            return {
                'part_no': result.get('part_no', ''),
                'model': result.get('model', ''),
                'model_code': result.get('model', ''),
                'project': result.get('project', ''),
                'ct': float(result.get('ct') or 0),
                'uph': int(float(result.get('uph') or 0))
            }
        return None
    
    @staticmethod
    def list_plans(
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        line: Optional[str] = None,
        status: Optional[str] = None
    ) -> Tuple[List[Dict], Optional[str]]:
        """
        Listar planes con filtros opcionales
        
        Args:
            start_date: Fecha inicial (YYYY-MM-DD)
            end_date: Fecha final (YYYY-MM-DD)
            line: Filtrar por línea
            status: Filtrar por estado
            
        Returns:
            Tuple (lista_de_planes, error_message)
        """
        try:
            conditions = []
            params = []
            
            if start_date:
                if not end_date:
                    conditions.append('DATE(working_date) = %s')
                    params.append(start_date)
                else:
                    conditions.append('DATE(working_date) >= %s')
                    params.append(start_date)
            
            if end_date:
                conditions.append('DATE(working_date) <= %s')
                params.append(end_date)
            
            if line:
                conditions.append('line = %s')
                params.append(line)
            
            if status:
                conditions.append('status = %s')
                params.append(status.upper())
            
            sql = """
                SELECT id, lot_no, wo_code, po_code, working_date, line, routing, 
                       model_code, part_no, project, process,
                       COALESCE(ct,0) AS ct, COALESCE(uph,0) AS uph, 
                       COALESCE(plan_count,0) AS plan_count,
                       COALESCE(produced_count,0) AS input, 0 AS output, 
                       COALESCE(entregadas_main,0) AS entregadas_main,
                       COALESCE(produced_count,0) AS produced, status, 
                       group_no, sequence 
                FROM plan_main
            """
            
            if conditions:
                sql += ' WHERE ' + ' AND '.join(conditions)
            
            sql += ' ORDER BY COALESCE(group_no,999), COALESCE(sequence,999), working_date, created_at'
            
            rows = execute_query(sql, tuple(params) if params else None, fetch='all')
            
            # Normalizar datos
            plans = []
            for r in rows:
                plans.append({
                    'lot_no': r.get('lot_no'),
                    'wo_code': r.get('wo_code'),
                    'po_code': r.get('po_code'),
                    'working_date': str(r.get('working_date') or '')[:10],
                    'line': r.get('line'),
                    'routing': r.get('routing'),
                    'model_code': r.get('model_code'),
                    'part_no': r.get('part_no'),
                    'project': r.get('project'),
                    'process': r.get('process'),
                    'ct': r.get('ct'),
                    'uph': r.get('uph'),
                    'plan_count': r.get('plan_count'),
                    'input': r.get('input'),
                    'output': r.get('output'),
                    'entregadas_main': r.get('entregadas_main'),
                    'produced': r.get('produced'),
                    'status': r.get('status'),
                    'group_no': r.get('group_no'),
                    'sequence': r.get('sequence'),
                })
            
            return plans, None
            
        except Exception as e:
            return [], str(e)
    
    @staticmethod
    def create_plan(data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """
        Crear un nuevo plan de producción
        
        Args:
            data: Datos del plan
            
        Returns:
            Tuple (success, result_or_error)
        """
        try:
            working_date = data.get('working_date')
            part_no = data.get('part_no')
            line = data.get('line')
            turno = (data.get('turno') or 'DIA').strip().upper()
            plan_count = int(data.get('plan_count') or 0)
            
            # Valores por defecto para WO/PO
            wo_code = data.get('wo_code') or 'SIN-WO'
            po_code = data.get('po_code') or 'SIN-PO'
            
            if not (working_date and part_no and line):
                return False, {'error': 'Parámetros requeridos: working_date, part_no, line'}
            
            # Parsear fecha
            try:
                fecha = datetime.strptime(working_date[:10], '%Y-%m-%d').date()
            except ValueError:
                fecha = datetime.utcnow().date()
            
            # Obtener routing por turno
            routing = PlanService.SHIFT_ROUTING.get(turno, 1)
            
            # Generar lote
            lot_no = PlanService.generate_lot_number(datetime.combine(fecha, datetime.min.time()))
            
            # Buscar datos adicionales en RAW
            raw_data = PlanService.get_raw_data(part_no)
            
            if raw_data:
                model_code = raw_data['model'] or part_no
                project = raw_data['project'] or ''
                ct = raw_data['ct']
                uph = raw_data['uph']
            else:
                model_code = part_no
                project = ''
                ct = 0.0
                uph = 0
            
            # Manejo de grupo
            group_no = data.get('group_no')
            sequence = None
            
            if group_no is not None:
                seq_result = execute_query(
                    "SELECT MAX(sequence) as max_seq FROM plan_main WHERE group_no = %s",
                    (int(group_no),),
                    fetch='one'
                )
                max_seq = seq_result.get('max_seq') if seq_result else None
                sequence = (max_seq + 1) if max_seq is not None else 1
            
            # Insertar plan
            if group_no is not None and sequence is not None:
                sql = """
                    INSERT INTO plan_main 
                    (lot_no, wo_code, po_code, working_date, line, model_code, part_no, 
                     project, process, plan_count, ct, uph, routing, status, group_no, sequence, created_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'PLAN',%s,%s,NOW())
                """
                params = (lot_no, wo_code, po_code, fecha, line, model_code, part_no, 
                         project, 'MAIN', plan_count, ct, uph, routing, int(group_no), sequence)
            else:
                sql = """
                    INSERT INTO plan_main 
                    (lot_no, wo_code, po_code, working_date, line, model_code, part_no,
                     project, process, plan_count, ct, uph, routing, status, created_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'PLAN',NOW())
                """
                params = (lot_no, wo_code, po_code, fecha, line, model_code, part_no,
                         project, 'MAIN', plan_count, ct, uph, routing)
            
            execute_query(sql, params)
            
            return True, {
                'lot_no': lot_no,
                'model_code': model_code,
                'ct': ct,
                'uph': uph,
                'project': project
            }
            
        except Exception as e:
            return False, {'error': str(e)}
    
    @staticmethod
    def update_plan(lot_no: str, data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Actualizar un plan existente
        
        Args:
            lot_no: Número de lote a actualizar
            data: Datos a actualizar
            
        Returns:
            Tuple (success, error_message)
        """
        if not lot_no:
            return False, 'lot_no requerido'
        
        try:
            fields = []
            vals = []
            
            # Campos actualizables
            updatable_fields = {
                'plan_count': lambda v: int(v or 0),
                'status': lambda v: str(v),
                'line': lambda v: str(v),
                'wo_code': lambda v: str(v),
                'po_code': lambda v: str(v),
                'uph': lambda v: str(v),
                'ct': lambda v: str(v),
                'project': lambda v: str(v),
                'model_code': lambda v: str(v),
            }
            
            for field, converter in updatable_fields.items():
                if field in data:
                    fields.append(f'{field} = %s')
                    vals.append(converter(data[field]))
            
            # Turno especial
            if 'turno' in data:
                routing = PlanService.SHIFT_ROUTING.get(
                    str(data['turno']).strip().upper(), 1
                )
                fields.append('routing = %s')
                vals.append(routing)
            
            if not fields:
                return False, 'Sin cambios'
            
            fields.append('updated_at = NOW()')
            
            sql = f"UPDATE plan_main SET {', '.join(fields)} WHERE lot_no = %s"
            vals.append(lot_no)
            
            execute_query(sql, tuple(vals))
            return True, None
            
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def change_status(
        lot_no: str, 
        new_status: str,
        reason: Optional[str] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Cambiar estado de un plan con validaciones
        
        Args:
            lot_no: Número de lote
            new_status: Nuevo estado
            reason: Motivo del cambio (para PAUSADO/CANCELADO)
            
        Returns:
            Tuple (success, result_or_error)
        """
        if not lot_no:
            return False, {'error': 'lot_no requerido', 'error_code': 'MISSING_LOT_NO'}
        
        if not new_status:
            return False, {'error': 'status requerido', 'error_code': 'MISSING_STATUS'}
        
        new_status = new_status.strip().upper()
        
        if new_status not in PlanService.VALID_STATUSES:
            return False, {
                'error': f'Status inválido: {new_status}',
                'error_code': 'INVALID_STATUS'
            }
        
        try:
            # Obtener plan actual
            plan = execute_query(
                """SELECT line, status, plan_count, produced_count, 
                          started_at, pause_started_at, paused_at 
                   FROM plan_main WHERE lot_no = %s""",
                (lot_no,),
                fetch='one'
            )
            
            if not plan:
                return False, {'error': 'Plan no encontrado', 'error_code': 'NOT_FOUND'}
            
            current_line = plan.get('line')
            current_status = (plan.get('status') or '').strip().upper()
            
            # Validar: No puede haber dos planes EN PROGRESO en la misma línea
            if new_status == 'EN PROGRESO' and current_status != 'EN PROGRESO':
                conflict = execute_query(
                    """SELECT lot_no FROM plan_main 
                       WHERE line = %s AND status = 'EN PROGRESO' AND lot_no != %s 
                       LIMIT 1""",
                    (current_line, lot_no),
                    fetch='one'
                )
                
                if conflict:
                    return False, {
                        'error': 'Ya existe un plan EN PROGRESO en esta línea',
                        'error_code': 'LINE_CONFLICT',
                        'line': current_line,
                        'lot_no_en_progreso': conflict.get('lot_no')
                    }
            
            # Construir actualización según el nuevo estado
            fields = ['status = %s']
            vals = [new_status]
            
            if new_status == 'EN PROGRESO' and current_status != 'EN PROGRESO':
                # Iniciar producción
                if not plan.get('started_at'):
                    fields.append('started_at = NOW()')
            
            elif new_status == 'PAUSADO':
                # Registrar inicio de pausa
                fields.append('pause_started_at = NOW()')
                if reason:
                    fields.append('pause_reason = %s')
                    vals.append(reason)
            
            elif new_status == 'TERMINADO':
                # Marcar tiempo de finalización
                fields.append('finished_at = NOW()')
            
            fields.append('updated_at = NOW()')
            
            sql = f"UPDATE plan_main SET {', '.join(fields)} WHERE lot_no = %s"
            vals.append(lot_no)
            
            execute_query(sql, tuple(vals))
            
            return True, {
                'lot_no': lot_no,
                'status': new_status,
                'previous_status': current_status
            }
            
        except Exception as e:
            return False, {'error': str(e), 'error_code': 'INTERNAL_ERROR'}
    
    @staticmethod
    def delete_plan(lot_no: str) -> Tuple[bool, Optional[str]]:
        """
        Eliminar un plan (solo si no está EN PROGRESO o TERMINADO)
        
        Args:
            lot_no: Número de lote a eliminar
            
        Returns:
            Tuple (success, error_message)
        """
        if not lot_no:
            return False, 'lot_no requerido'
        
        try:
            # Verificar estado actual
            plan = execute_query(
                "SELECT status FROM plan_main WHERE lot_no = %s",
                (lot_no,),
                fetch='one'
            )
            
            if not plan:
                return False, 'Plan no encontrado'
            
            status = (plan.get('status') or '').upper()
            
            if status in ['EN PROGRESO', 'TERMINADO']:
                return False, f'No se puede eliminar un plan con estado {status}'
            
            execute_query("DELETE FROM plan_main WHERE lot_no = %s", (lot_no,))
            
            return True, None
            
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def get_plan_by_lot(lot_no: str) -> Optional[Dict[str, Any]]:
        """
        Obtener un plan específico por su lote
        
        Args:
            lot_no: Número de lote
            
        Returns:
            Diccionario con datos del plan o None
        """
        if not lot_no:
            return None
        
        try:
            result = execute_query(
                """SELECT id, lot_no, wo_code, po_code, working_date, line, routing,
                          model_code, part_no, project, process, ct, uph, plan_count,
                          produced_count, entregadas_main, status, group_no, sequence,
                          started_at, finished_at, created_at, updated_at
                   FROM plan_main WHERE lot_no = %s""",
                (lot_no,),
                fetch='one'
            )
            
            return result
            
        except Exception:
            return None
    
    @staticmethod
    def get_lines_summary(working_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Obtener resumen de producción por línea
        
        Args:
            working_date: Fecha a consultar (default: hoy)
            
        Returns:
            Lista con resumen por línea
        """
        try:
            if not working_date:
                working_date = get_mexico_time().strftime('%Y-%m-%d')
            
            sql = """
                SELECT line, 
                       COUNT(*) as total_plans,
                       SUM(plan_count) as total_planned,
                       SUM(produced_count) as total_produced,
                       SUM(CASE WHEN status = 'EN PROGRESO' THEN 1 ELSE 0 END) as in_progress,
                       SUM(CASE WHEN status = 'TERMINADO' THEN 1 ELSE 0 END) as completed
                FROM plan_main
                WHERE DATE(working_date) = %s
                GROUP BY line
                ORDER BY line
            """
            
            results = execute_query(sql, (working_date,), fetch='all')
            
            return results or []
            
        except Exception:
            return []
