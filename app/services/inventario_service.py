# -*- coding: utf-8 -*-
"""
Servicio de Inventario
Lógica de negocio para consulta y gestión de inventario
"""

from app.database.db_mysql import get_mysql_connection
from app.utils.timezone import get_mexico_time_str
from app.utils.responses import success_response, error_response, paginated_response
from decimal import Decimal
import traceback


def consultar_inventario(filtros: dict, usuario: str = None) -> dict:
    """
    Consulta inventario consolidado con filtros opcionales
    
    Args:
        filtros: dict con campos opcionales:
            - numeroParte: filtro por número de parte (LIKE)
            - propiedad: 'SANMINA' o 'CLIENTE'
            - cantidadMinima: cantidad mínima en stock
            - pagina: número de página (default 1)
            - porPagina: registros por página (default 50)
        usuario: usuario que realiza la consulta (para auditoría)
    
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
        numero_parte = filtros.get('numeroParte', '').strip()
        propiedad = filtros.get('propiedad', '').strip()
        cantidad_minima = filtros.get('cantidadMinima')
        pagina = int(filtros.get('pagina', 1))
        por_pagina = int(filtros.get('porPagina', 50))
        
        # Validar paginación
        if pagina < 1:
            pagina = 1
        if por_pagina < 1 or por_pagina > 500:
            por_pagina = 50
        
        offset = (pagina - 1) * por_pagina
        
        # Construir query base
        where_clauses = []
        params = []
        
        if numero_parte:
            where_clauses.append("numero_parte LIKE %s")
            params.append(f"%{numero_parte}%")
        
        if propiedad and propiedad.upper() in ('SANMINA', 'CLIENTE'):
            where_clauses.append("propiedad = %s")
            params.append(propiedad.upper())
        
        if cantidad_minima is not None:
            try:
                cantidad_minima = float(cantidad_minima)
                where_clauses.append("cantidad_total >= %s")
                params.append(cantidad_minima)
            except (ValueError, TypeError):
                pass
        
        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)
        
        # Query de conteo total
        count_query = f"""
            SELECT COUNT(DISTINCT numero_parte) as total
            FROM inventario_consolidado
            {where_sql}
        """
        cursor.execute(count_query, params)
        total_registros = cursor.fetchone()[0]
        
        # Query principal con agrupación por número de parte
        query = f"""
            SELECT 
                numero_parte,
                SUM(cantidad_total) as cantidad_total,
                propiedad,
                MAX(fecha_actualizacion) as ultima_actualizacion,
                COUNT(*) as num_lotes
            FROM inventario_consolidado
            {where_sql}
            GROUP BY numero_parte, propiedad
            ORDER BY numero_parte ASC
            LIMIT %s OFFSET %s
        """
        params.extend([por_pagina, offset])
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # Formatear resultados
        inventario = []
        for row in rows:
            inventario.append({
                'numeroParte': row[0],
                'cantidadTotal': float(row[1]) if row[1] else 0,
                'propiedad': row[2],
                'ultimaActualizacion': row[3].strftime('%Y-%m-%d %H:%M:%S') if row[3] else None,
                'numLotes': row[4]
            })
        
        # Calcular paginación
        total_paginas = (total_registros + por_pagina - 1) // por_pagina
        
        return paginated_response(
            data=inventario,
            total=total_registros,
            pagina=pagina,
            por_pagina=por_pagina,
            total_paginas=total_paginas,
            mensaje=f"Se encontraron {total_registros} números de parte"
        )
        
    except Exception as e:
        print(f"❌ Error en consultar_inventario: {e}")
        traceback.print_exc()
        return error_response(f"Error al consultar inventario: {str(e)}", 500)
    finally:
        if conn:
            conn.close()


def obtener_detalle_inventario(numero_parte: str) -> dict:
    """
    Obtiene detalle completo de un número de parte incluyendo todos sus lotes
    
    Args:
        numero_parte: número de parte a consultar
    
    Returns:
        dict con respuesta estandarizada
    """
    conn = None
    try:
        if not numero_parte:
            return error_response("Número de parte requerido", 400)
        
        conn = get_mysql_connection()
        if not conn:
            return error_response("No se pudo conectar a la base de datos", 503)
        
        cursor = conn.cursor()
        
        # Query para obtener todos los lotes del número de parte
        query = """
            SELECT 
                id,
                numero_parte,
                lote,
                cantidad_total,
                propiedad,
                ubicacion,
                fecha_ingreso,
                fecha_actualizacion,
                observaciones
            FROM inventario_consolidado
            WHERE numero_parte = %s
            ORDER BY lote ASC
        """
        cursor.execute(query, (numero_parte,))
        rows = cursor.fetchall()
        
        if not rows:
            return error_response(f"No se encontró inventario para {numero_parte}", 404)
        
        # Calcular totales
        cantidad_total = 0
        lotes = []
        
        for row in rows:
            cantidad = float(row[3]) if row[3] else 0
            cantidad_total += cantidad
            
            lotes.append({
                'id': row[0],
                'numeroParte': row[1],
                'lote': row[2],
                'cantidad': cantidad,
                'propiedad': row[4],
                'ubicacion': row[5],
                'fechaIngreso': row[6].strftime('%Y-%m-%d %H:%M:%S') if row[6] else None,
                'fechaActualizacion': row[7].strftime('%Y-%m-%d %H:%M:%S') if row[7] else None,
                'observaciones': row[8]
            })
        
        return success_response({
            'numeroParte': numero_parte,
            'cantidadTotal': cantidad_total,
            'numLotes': len(lotes),
            'lotes': lotes
        }, f"Detalle de inventario para {numero_parte}")
        
    except Exception as e:
        print(f"❌ Error en obtener_detalle_inventario: {e}")
        traceback.print_exc()
        return error_response(f"Error al obtener detalle: {str(e)}", 500)
    finally:
        if conn:
            conn.close()


def obtener_historial_movimientos(numero_parte: str = None, lote: str = None, 
                                   fecha_desde: str = None, fecha_hasta: str = None,
                                   limite: int = 100) -> dict:
    """
    Obtiene historial de movimientos de inventario
    
    Args:
        numero_parte: filtrar por número de parte
        lote: filtrar por lote específico
        fecha_desde: fecha inicio (YYYY-MM-DD)
        fecha_hasta: fecha fin (YYYY-MM-DD)
        limite: máximo de registros a retornar
    
    Returns:
        dict con respuesta estandarizada
    """
    conn = None
    try:
        conn = get_mysql_connection()
        if not conn:
            return error_response("No se pudo conectar a la base de datos", 503)
        
        cursor = conn.cursor()
        
        # Construir query con filtros
        where_clauses = []
        params = []
        
        if numero_parte:
            where_clauses.append("numero_parte LIKE %s")
            params.append(f"%{numero_parte}%")
        
        if lote:
            where_clauses.append("lote = %s")
            params.append(lote)
        
        if fecha_desde:
            where_clauses.append("fecha_movimiento >= %s")
            params.append(fecha_desde)
        
        if fecha_hasta:
            where_clauses.append("fecha_movimiento <= %s")
            params.append(f"{fecha_hasta} 23:59:59")
        
        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)
        
        # Verificar si la tabla existe
        cursor.execute("SHOW TABLES LIKE 'historial_inventario'")
        if not cursor.fetchone():
            return success_response({
                'movimientos': [],
                'total': 0
            }, "Tabla de historial no disponible")
        
        query = f"""
            SELECT 
                id,
                numero_parte,
                lote,
                tipo_movimiento,
                cantidad,
                cantidad_anterior,
                cantidad_nueva,
                usuario,
                fecha_movimiento,
                observaciones
            FROM historial_inventario
            {where_sql}
            ORDER BY fecha_movimiento DESC
            LIMIT %s
        """
        params.append(limite)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        movimientos = []
        for row in rows:
            movimientos.append({
                'id': row[0],
                'numeroParte': row[1],
                'lote': row[2],
                'tipoMovimiento': row[3],
                'cantidad': float(row[4]) if row[4] else 0,
                'cantidadAnterior': float(row[5]) if row[5] else 0,
                'cantidadNueva': float(row[6]) if row[6] else 0,
                'usuario': row[7],
                'fechaMovimiento': row[8].strftime('%Y-%m-%d %H:%M:%S') if row[8] else None,
                'observaciones': row[9]
            })
        
        return success_response({
            'movimientos': movimientos,
            'total': len(movimientos)
        }, f"Se encontraron {len(movimientos)} movimientos")
        
    except Exception as e:
        print(f"❌ Error en obtener_historial_movimientos: {e}")
        traceback.print_exc()
        return error_response(f"Error al obtener historial: {str(e)}", 500)
    finally:
        if conn:
            conn.close()


def registrar_ajuste_inventario(numero_parte: str, lote: str, cantidad_ajuste: float,
                                 tipo_ajuste: str, motivo: str, usuario: str) -> dict:
    """
    Registra un ajuste de inventario (entrada, salida, ajuste)
    
    Args:
        numero_parte: número de parte
        lote: lote afectado
        cantidad_ajuste: cantidad a ajustar (positiva o negativa)
        tipo_ajuste: 'ENTRADA', 'SALIDA', 'AJUSTE'
        motivo: razón del ajuste
        usuario: usuario que realiza el ajuste
    
    Returns:
        dict con respuesta estandarizada
    """
    conn = None
    try:
        # Validaciones
        if not numero_parte or not lote:
            return error_response("Número de parte y lote son requeridos", 400)
        
        if tipo_ajuste not in ('ENTRADA', 'SALIDA', 'AJUSTE'):
            return error_response("Tipo de ajuste inválido", 400)
        
        conn = get_mysql_connection()
        if not conn:
            return error_response("No se pudo conectar a la base de datos", 503)
        
        cursor = conn.cursor()
        
        # Obtener cantidad actual
        cursor.execute("""
            SELECT id, cantidad_total 
            FROM inventario_consolidado 
            WHERE numero_parte = %s AND lote = %s
        """, (numero_parte, lote))
        
        row = cursor.fetchone()
        if not row:
            return error_response(f"No se encontró el lote {lote} para {numero_parte}", 404)
        
        id_registro = row[0]
        cantidad_anterior = float(row[1]) if row[1] else 0
        
        # Calcular nueva cantidad
        if tipo_ajuste == 'ENTRADA':
            cantidad_nueva = cantidad_anterior + abs(cantidad_ajuste)
        elif tipo_ajuste == 'SALIDA':
            cantidad_nueva = cantidad_anterior - abs(cantidad_ajuste)
            if cantidad_nueva < 0:
                return error_response("La cantidad resultante no puede ser negativa", 400)
        else:  # AJUSTE
            cantidad_nueva = cantidad_ajuste
        
        # Actualizar inventario
        cursor.execute("""
            UPDATE inventario_consolidado 
            SET cantidad_total = %s, fecha_actualizacion = NOW()
            WHERE id = %s
        """, (cantidad_nueva, id_registro))
        
        # Registrar en historial (si existe la tabla)
        try:
            cursor.execute("""
                INSERT INTO historial_inventario 
                (numero_parte, lote, tipo_movimiento, cantidad, cantidad_anterior, 
                 cantidad_nueva, usuario, fecha_movimiento, observaciones)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), %s)
            """, (numero_parte, lote, tipo_ajuste, cantidad_ajuste, 
                  cantidad_anterior, cantidad_nueva, usuario, motivo))
        except Exception as hist_error:
            print(f"⚠️ No se pudo registrar historial: {hist_error}")
        
        conn.commit()
        
        return success_response({
            'numeroParte': numero_parte,
            'lote': lote,
            'tipoAjuste': tipo_ajuste,
            'cantidadAnterior': cantidad_anterior,
            'cantidadAjuste': cantidad_ajuste,
            'cantidadNueva': cantidad_nueva,
            'usuario': usuario,
            'fechaAjuste': get_mexico_time_str()
        }, "Ajuste de inventario registrado correctamente")
        
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ Error en registrar_ajuste_inventario: {e}")
        traceback.print_exc()
        return error_response(f"Error al registrar ajuste: {str(e)}", 500)
    finally:
        if conn:
            conn.close()


def obtener_resumen_inventario() -> dict:
    """
    Obtiene resumen general del inventario
    
    Returns:
        dict con estadísticas generales
    """
    conn = None
    try:
        conn = get_mysql_connection()
        if not conn:
            return error_response("No se pudo conectar a la base de datos", 503)
        
        cursor = conn.cursor()
        
        # Estadísticas generales
        query = """
            SELECT 
                COUNT(DISTINCT numero_parte) as total_partes,
                COUNT(*) as total_lotes,
                SUM(cantidad_total) as cantidad_total,
                COUNT(CASE WHEN propiedad = 'SANMINA' THEN 1 END) as lotes_sanmina,
                COUNT(CASE WHEN propiedad = 'CLIENTE' THEN 1 END) as lotes_cliente
            FROM inventario_consolidado
        """
        cursor.execute(query)
        row = cursor.fetchone()
        
        if not row:
            return success_response({
                'totalPartes': 0,
                'totalLotes': 0,
                'cantidadTotal': 0,
                'lotesSanmina': 0,
                'lotesCliente': 0
            }, "Inventario vacío")
        
        return success_response({
            'totalPartes': row[0] or 0,
            'totalLotes': row[1] or 0,
            'cantidadTotal': float(row[2]) if row[2] else 0,
            'lotesSanmina': row[3] or 0,
            'lotesCliente': row[4] or 0,
            'fechaConsulta': get_mexico_time_str()
        }, "Resumen de inventario obtenido correctamente")
        
    except Exception as e:
        print(f"❌ Error en obtener_resumen_inventario: {e}")
        traceback.print_exc()
        return error_response(f"Error al obtener resumen: {str(e)}", 500)
    finally:
        if conn:
            conn.close()
