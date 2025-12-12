# -*- coding: utf-8 -*-
"""
Servicio de Work Orders (Órdenes de Trabajo)
Lógica de negocio para gestión de órdenes de trabajo
"""

from app.database.db_mysql import get_mysql_connection
from app.utils.timezone import get_mexico_time_str
from app.utils.responses import success_response, error_response, paginated_response
import traceback


def obtener_work_orders(filtros: dict) -> dict:
    """
    Obtiene lista de work orders con filtros opcionales
    
    Args:
        filtros: dict con campos opcionales:
            - q: búsqueda general (work_order, modelo, descripcion)
            - estado: filtrar por estado
            - desde: fecha inicio (YYYY-MM-DD)
            - hasta: fecha fin (YYYY-MM-DD)
            - pagina: número de página (default 1)
            - porPagina: registros por página (default 50)
    
    Returns:
        dict con respuesta estandarizada
    """
    conn = None
    try:
        conn = get_mysql_connection()
        if not conn:
            return error_response("No se pudo conectar a la base de datos", 503)
        
        cursor = conn.cursor()
        
        # Extraer filtros
        busqueda = filtros.get('q', '').strip()
        estado = filtros.get('estado', '').strip()
        fecha_desde = filtros.get('desde', '').strip()
        fecha_hasta = filtros.get('hasta', '').strip()
        pagina = int(filtros.get('pagina', 1))
        por_pagina = int(filtros.get('porPagina', 50))
        
        # Validar paginación
        if pagina < 1:
            pagina = 1
        if por_pagina < 1 or por_pagina > 500:
            por_pagina = 50
        
        offset = (pagina - 1) * por_pagina
        
        # Construir query
        where_clauses = []
        params = []
        
        if busqueda:
            where_clauses.append("""
                (work_order LIKE %s OR modelo LIKE %s OR descripcion LIKE %s)
            """)
            like_pattern = f"%{busqueda}%"
            params.extend([like_pattern, like_pattern, like_pattern])
        
        if estado:
            where_clauses.append("estado = %s")
            params.append(estado)
        
        if fecha_desde:
            where_clauses.append("fecha_creacion >= %s")
            params.append(fecha_desde)
        
        if fecha_hasta:
            where_clauses.append("fecha_creacion <= %s")
            params.append(f"{fecha_hasta} 23:59:59")
        
        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)
        
        # Query de conteo
        count_query = f"""
            SELECT COUNT(*) FROM work_orders {where_sql}
        """
        cursor.execute(count_query, params)
        total_registros = cursor.fetchone()[0]
        
        # Query principal con LEFT JOIN a plan_main para verificar si ya fue importado
        query = f"""
            SELECT 
                wo.id,
                wo.work_order,
                wo.modelo,
                wo.descripcion,
                wo.cantidad,
                wo.estado,
                wo.fecha_creacion,
                wo.fecha_actualizacion,
                wo.cliente,
                wo.prioridad,
                CASE 
                    WHEN pm.work_order IS NOT NULL THEN 1 
                    ELSE 0 
                END as ya_importado
            FROM work_orders wo
            LEFT JOIN plan_main pm ON wo.work_order = pm.work_order
            {where_sql}
            ORDER BY wo.fecha_creacion DESC
            LIMIT %s OFFSET %s
        """
        params.extend([por_pagina, offset])
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        work_orders = []
        for row in rows:
            work_orders.append({
                'id': row[0],
                'workOrder': row[1],
                'modelo': row[2],
                'descripcion': row[3],
                'cantidad': int(row[4]) if row[4] else 0,
                'estado': row[5],
                'fechaCreacion': row[6].strftime('%Y-%m-%d %H:%M:%S') if row[6] else None,
                'fechaActualizacion': row[7].strftime('%Y-%m-%d %H:%M:%S') if row[7] else None,
                'cliente': row[8],
                'prioridad': row[9],
                'yaImportado': bool(row[10])
            })
        
        total_paginas = (total_registros + por_pagina - 1) // por_pagina
        
        return paginated_response(
            data=work_orders,
            total=total_registros,
            pagina=pagina,
            por_pagina=por_pagina,
            total_paginas=total_paginas,
            mensaje=f"Se encontraron {total_registros} work orders"
        )
        
    except Exception as e:
        print(f"❌ Error en obtener_work_orders: {e}")
        traceback.print_exc()
        return error_response(f"Error al obtener work orders: {str(e)}", 500)
    finally:
        if conn:
            conn.close()


def obtener_work_order_detalle(work_order: str) -> dict:
    """
    Obtiene detalle completo de un work order
    
    Args:
        work_order: número de work order
    
    Returns:
        dict con respuesta estandarizada
    """
    conn = None
    try:
        if not work_order:
            return error_response("Work order requerido", 400)
        
        conn = get_mysql_connection()
        if not conn:
            return error_response("No se pudo conectar a la base de datos", 503)
        
        cursor = conn.cursor()
        
        # Query principal
        query = """
            SELECT 
                id, work_order, modelo, descripcion, cantidad,
                estado, fecha_creacion, fecha_actualizacion,
                cliente, prioridad, linea, observaciones
            FROM work_orders
            WHERE work_order = %s
        """
        cursor.execute(query, (work_order,))
        row = cursor.fetchone()
        
        if not row:
            return error_response(f"Work order {work_order} no encontrado", 404)
        
        # Verificar si ya fue importado a plan
        cursor.execute("""
            SELECT id, fecha_importacion 
            FROM plan_main 
            WHERE work_order = %s 
            LIMIT 1
        """, (work_order,))
        plan_row = cursor.fetchone()
        
        detalle = {
            'id': row[0],
            'workOrder': row[1],
            'modelo': row[2],
            'descripcion': row[3],
            'cantidad': int(row[4]) if row[4] else 0,
            'estado': row[5],
            'fechaCreacion': row[6].strftime('%Y-%m-%d %H:%M:%S') if row[6] else None,
            'fechaActualizacion': row[7].strftime('%Y-%m-%d %H:%M:%S') if row[7] else None,
            'cliente': row[8],
            'prioridad': row[9],
            'linea': row[10],
            'observaciones': row[11],
            'yaImportado': plan_row is not None,
            'planId': plan_row[0] if plan_row else None,
            'fechaImportacion': plan_row[1].strftime('%Y-%m-%d %H:%M:%S') if plan_row and plan_row[1] else None
        }
        
        return success_response(detalle, f"Detalle de work order {work_order}")
        
    except Exception as e:
        print(f"❌ Error en obtener_work_order_detalle: {e}")
        traceback.print_exc()
        return error_response(f"Error al obtener detalle: {str(e)}", 500)
    finally:
        if conn:
            conn.close()


def crear_work_order(datos: dict, usuario: str) -> dict:
    """
    Crea un nuevo work order
    
    Args:
        datos: dict con campos:
            - workOrder: número de work order (requerido)
            - modelo: modelo del producto (requerido)
            - descripcion: descripción
            - cantidad: cantidad a producir (requerido)
            - cliente: nombre del cliente
            - prioridad: 'ALTA', 'MEDIA', 'BAJA'
            - linea: línea de producción
            - observaciones: notas adicionales
        usuario: usuario que crea el registro
    
    Returns:
        dict con respuesta estandarizada
    """
    conn = None
    try:
        # Validaciones
        work_order = datos.get('workOrder', '').strip()
        modelo = datos.get('modelo', '').strip()
        cantidad = datos.get('cantidad')
        
        if not work_order:
            return error_response("Work order es requerido", 400)
        if not modelo:
            return error_response("Modelo es requerido", 400)
        if not cantidad or int(cantidad) <= 0:
            return error_response("Cantidad debe ser mayor a 0", 400)
        
        conn = get_mysql_connection()
        if not conn:
            return error_response("No se pudo conectar a la base de datos", 503)
        
        cursor = conn.cursor()
        
        # Verificar si ya existe
        cursor.execute("SELECT id FROM work_orders WHERE work_order = %s", (work_order,))
        if cursor.fetchone():
            return error_response(f"Work order {work_order} ya existe", 409)
        
        # Insertar
        query = """
            INSERT INTO work_orders 
            (work_order, modelo, descripcion, cantidad, estado, cliente, 
             prioridad, linea, observaciones, fecha_creacion, creado_por)
            VALUES (%s, %s, %s, %s, 'PENDIENTE', %s, %s, %s, %s, NOW(), %s)
        """
        params = (
            work_order,
            modelo,
            datos.get('descripcion', ''),
            int(cantidad),
            datos.get('cliente', ''),
            datos.get('prioridad', 'MEDIA'),
            datos.get('linea', ''),
            datos.get('observaciones', ''),
            usuario
        )
        
        cursor.execute(query, params)
        nuevo_id = cursor.lastrowid
        conn.commit()
        
        return success_response({
            'id': nuevo_id,
            'workOrder': work_order,
            'modelo': modelo,
            'cantidad': int(cantidad),
            'estado': 'PENDIENTE',
            'creadoPor': usuario,
            'fechaCreacion': get_mexico_time_str()
        }, f"Work order {work_order} creado correctamente", 201)
        
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ Error en crear_work_order: {e}")
        traceback.print_exc()
        return error_response(f"Error al crear work order: {str(e)}", 500)
    finally:
        if conn:
            conn.close()


def actualizar_estado_work_order(work_order: str, nuevo_estado: str, usuario: str) -> dict:
    """
    Actualiza el estado de un work order
    
    Args:
        work_order: número de work order
        nuevo_estado: nuevo estado ('PENDIENTE', 'EN_PROCESO', 'COMPLETADO', 'CANCELADO')
        usuario: usuario que realiza el cambio
    
    Returns:
        dict con respuesta estandarizada
    """
    conn = None
    try:
        estados_validos = ['PENDIENTE', 'EN_PROCESO', 'COMPLETADO', 'CANCELADO']
        
        if not work_order:
            return error_response("Work order requerido", 400)
        if nuevo_estado not in estados_validos:
            return error_response(f"Estado inválido. Valores permitidos: {estados_validos}", 400)
        
        conn = get_mysql_connection()
        if not conn:
            return error_response("No se pudo conectar a la base de datos", 503)
        
        cursor = conn.cursor()
        
        # Obtener estado actual
        cursor.execute("""
            SELECT id, estado FROM work_orders WHERE work_order = %s
        """, (work_order,))
        row = cursor.fetchone()
        
        if not row:
            return error_response(f"Work order {work_order} no encontrado", 404)
        
        id_wo = row[0]
        estado_anterior = row[1]
        
        if estado_anterior == nuevo_estado:
            return success_response({
                'workOrder': work_order,
                'estado': nuevo_estado,
                'mensaje': 'Estado sin cambios'
            }, "El work order ya tiene ese estado")
        
        # Actualizar estado
        cursor.execute("""
            UPDATE work_orders 
            SET estado = %s, fecha_actualizacion = NOW(), actualizado_por = %s
            WHERE id = %s
        """, (nuevo_estado, usuario, id_wo))
        
        conn.commit()
        
        return success_response({
            'workOrder': work_order,
            'estadoAnterior': estado_anterior,
            'estadoNuevo': nuevo_estado,
            'actualizadoPor': usuario,
            'fechaActualizacion': get_mexico_time_str()
        }, f"Estado de {work_order} actualizado a {nuevo_estado}")
        
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ Error en actualizar_estado_work_order: {e}")
        traceback.print_exc()
        return error_response(f"Error al actualizar estado: {str(e)}", 500)
    finally:
        if conn:
            conn.close()


def importar_work_order_a_plan(work_order: str, datos_plan: dict, usuario: str) -> dict:
    """
    Importa un work order al plan de producción
    
    Args:
        work_order: número de work order a importar
        datos_plan: datos adicionales para el plan:
            - grupo: grupo de producción
            - linea: línea asignada
            - fechaProgramada: fecha programada
            - turno: turno asignado
        usuario: usuario que realiza la importación
    
    Returns:
        dict con respuesta estandarizada
    """
    conn = None
    try:
        if not work_order:
            return error_response("Work order requerido", 400)
        
        conn = get_mysql_connection()
        if not conn:
            return error_response("No se pudo conectar a la base de datos", 503)
        
        cursor = conn.cursor()
        
        # Obtener datos del work order
        cursor.execute("""
            SELECT id, work_order, modelo, descripcion, cantidad, cliente
            FROM work_orders 
            WHERE work_order = %s
        """, (work_order,))
        wo_row = cursor.fetchone()
        
        if not wo_row:
            return error_response(f"Work order {work_order} no encontrado", 404)
        
        # Verificar si ya existe en plan
        cursor.execute("""
            SELECT id FROM plan_main WHERE work_order = %s
        """, (work_order,))
        if cursor.fetchone():
            return error_response(f"Work order {work_order} ya está importado en el plan", 409)
        
        # Insertar en plan_main
        query = """
            INSERT INTO plan_main 
            (work_order, modelo, descripcion, cantidad_plan, cliente,
             grupo, linea, fecha_programada, turno, estado,
             fecha_importacion, importado_por)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'PROGRAMADO', NOW(), %s)
        """
        params = (
            wo_row[1],  # work_order
            wo_row[2],  # modelo
            wo_row[3],  # descripcion
            wo_row[4],  # cantidad
            wo_row[5],  # cliente
            datos_plan.get('grupo', ''),
            datos_plan.get('linea', ''),
            datos_plan.get('fechaProgramada'),
            datos_plan.get('turno', ''),
            usuario
        )
        
        cursor.execute(query, params)
        plan_id = cursor.lastrowid
        
        # Actualizar estado del work order
        cursor.execute("""
            UPDATE work_orders 
            SET estado = 'EN_PROCESO', fecha_actualizacion = NOW()
            WHERE id = %s
        """, (wo_row[0],))
        
        conn.commit()
        
        return success_response({
            'planId': plan_id,
            'workOrder': work_order,
            'modelo': wo_row[2],
            'cantidad': wo_row[4],
            'importadoPor': usuario,
            'fechaImportacion': get_mexico_time_str()
        }, f"Work order {work_order} importado al plan correctamente", 201)
        
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ Error en importar_work_order_a_plan: {e}")
        traceback.print_exc()
        return error_response(f"Error al importar work order: {str(e)}", 500)
    finally:
        if conn:
            conn.close()


def obtener_estadisticas_work_orders() -> dict:
    """
    Obtiene estadísticas generales de work orders
    
    Returns:
        dict con estadísticas
    """
    conn = None
    try:
        conn = get_mysql_connection()
        if not conn:
            return error_response("No se pudo conectar a la base de datos", 503)
        
        cursor = conn.cursor()
        
        query = """
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN estado = 'PENDIENTE' THEN 1 END) as pendientes,
                COUNT(CASE WHEN estado = 'EN_PROCESO' THEN 1 END) as en_proceso,
                COUNT(CASE WHEN estado = 'COMPLETADO' THEN 1 END) as completados,
                COUNT(CASE WHEN estado = 'CANCELADO' THEN 1 END) as cancelados,
                SUM(cantidad) as cantidad_total
            FROM work_orders
        """
        cursor.execute(query)
        row = cursor.fetchone()
        
        # Work orders creados hoy
        cursor.execute("""
            SELECT COUNT(*) FROM work_orders 
            WHERE DATE(fecha_creacion) = CURDATE()
        """)
        creados_hoy = cursor.fetchone()[0]
        
        return success_response({
            'total': row[0] or 0,
            'pendientes': row[1] or 0,
            'enProceso': row[2] or 0,
            'completados': row[3] or 0,
            'cancelados': row[4] or 0,
            'cantidadTotal': int(row[5]) if row[5] else 0,
            'creadosHoy': creados_hoy or 0,
            'fechaConsulta': get_mexico_time_str()
        }, "Estadísticas de work orders")
        
    except Exception as e:
        print(f"❌ Error en obtener_estadisticas_work_orders: {e}")
        traceback.print_exc()
        return error_response(f"Error al obtener estadísticas: {str(e)}", 500)
    finally:
        if conn:
            conn.close()
