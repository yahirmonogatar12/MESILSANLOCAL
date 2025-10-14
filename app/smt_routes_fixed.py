#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SMT Routes - API endpoints para historial de cambio de material SMT
Actualizado para usar la nueva estructura de tabla historial_cambio_material_smt
"""

from flask import Blueprint, request, jsonify, render_template
import mysql.connector
import logging
import os

# Configurar logging
logger = logging.getLogger(__name__)

# Configuración MySQL
DB_CONFIG = {
    'host': os.getenv('MYSQL_HOST', 'up-de-fra1-mysql-1.db.run-on-seenode.com'),
    'port': int(os.getenv('MYSQL_PORT', 11550)),
    'user': os.getenv('MYSQL_USER', 'db_rrpq0erbdujn'),
    'password': os.getenv('MYSQL_PASSWORD', ''),
    'database': os.getenv('MYSQL_DATABASE', 'db_rrpq0erbdujn'),
    'charset': 'utf8mb4'
}

# Crear Blueprint
smt_api = Blueprint('smt_api', __name__)

def get_db_connection():
    """Crear conexión a la base de datos"""
    return mysql.connector.connect(**DB_CONFIG)

@smt_api.route('/api/smt/filtros/opciones', methods=['GET'])
def get_filtros_opciones():
    """
    Obtener opciones disponibles para los filtros (líneas, máquinas)
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Obtener líneas únicas
        cursor.execute("""
            SELECT DISTINCT linea 
            FROM historial_cambio_material_smt 
            WHERE linea IS NOT NULL AND linea != '' 
            ORDER BY linea
        """)
        lineas = [row['linea'] for row in cursor.fetchall()]
        
        # Obtener máquinas únicas
        cursor.execute("""
            SELECT DISTINCT maquina 
            FROM historial_cambio_material_smt 
            WHERE maquina IS NOT NULL AND maquina != '' 
            ORDER BY maquina
        """)
        maquinas = [row['maquina'] for row in cursor.fetchall()]
        
        # Obtener combinaciones línea/máquina
        cursor.execute("""
            SELECT DISTINCT linea, maquina 
            FROM historial_cambio_material_smt 
            WHERE linea IS NOT NULL AND maquina IS NOT NULL 
            AND linea != '' AND maquina != ''
            ORDER BY linea, maquina
        """)
        combinaciones = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'lineas': lineas,
            'maquinas': maquinas,
            'combinaciones': combinaciones
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo opciones de filtros: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@smt_api.route('/smt/historial', methods=['GET'])
def historial_smt():
    """
    Ruta para mostrar el historial SMT con filtros optimizados
    """
    return render_template('Control de calidad/historial_cambio_material_smt_ajax.html')

@smt_api.route('/api/historial_smt_data', methods=['GET'])
def get_historial_smt_data():
    """
    API endpoint específico para el template historial_cambio_material_smt_ajax.html
    Filtros optimizados para cargar solo datos del día actual por defecto
    """
    try:
        # Obtener parámetros de filtro
        folder = request.args.get('folder', '')
        part_name = request.args.get('part_name', '')
        result = request.args.get('result', '')
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Construir filtros dinámicamente
        filters = []
        params = []
        
        # Filtro por fecha (obligatorio para limitar resultados)
        if not date_from and not date_to:
            # Si no se especifica fecha, usar fecha actual
            from datetime import datetime
            today = datetime.now().strftime('%Y%m%d')
            filters.append('ScanDate = %s')
            params.append(today)
        else:
            if date_from:
                date_from_formatted = date_from.replace('-', '')
                filters.append('ScanDate >= %s')
                params.append(date_from_formatted)
            if date_to:
                date_to_formatted = date_to.replace('-', '')
                filters.append('ScanDate <= %s')
                params.append(date_to_formatted)
        
        # Filtro por línea/mounter
        if folder:
            if 'line/' in folder:
                # Formato "1line/L1 m1" o "1line/ALL"
                parts = folder.split('/')
                line_part = parts[0]  # "1line"
                mounter_part = parts[1] if len(parts) > 1 else ''
                
                if 'line' in line_part:
                    line_number = line_part.replace('line', '')
                    filters.append('linea LIKE %s')
                    params.append(f"%{line_number}line%")
                    
                    if mounter_part and mounter_part != 'ALL':
                        # "L1 m1" -> buscar máquina específica
                        filters.append('maquina LIKE %s')
                        params.append(f"%{mounter_part}%")
            else:
                # Búsqueda genérica en archivo, línea o máquina
                filters.append('(archivo LIKE %s OR linea LIKE %s OR maquina LIKE %s)')
                params.extend([f"%{folder}%", f"%{folder}%", f"%{folder}%"])
        
        # Filtro por nombre de parte
        if part_name:
            filters.append('PartName LIKE %s')
            params.append(f"%{part_name}%")
        
        # Filtro por resultado
        if result:
            filters.append('Result = %s')
            params.append(result)
        
        # Construir consulta
        where_clause = 'WHERE ' + ' AND '.join(filters) if filters else ''
        
        query = f"""
            SELECT 
                ScanDate, ScanTime, SlotNo, Result, 
                LOTNO, Barcode, archivo, linea, maquina,
                PartName, Quantity, SEQ, Vendor,
                PreviousBarcode, Productdate, FeederBase
            FROM historial_cambio_material_smt 
            {where_clause}
            ORDER BY ScanDate DESC, ScanTime DESC 
            LIMIT 1000
        """
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        # Formatear resultados
        data = []
        for i, row in enumerate(results, 1):
            data.append({
                'index': i,
                'scan_date': row['ScanDate'],
                'scan_time': row['ScanTime'],
                'slotno': row['SlotNo'],
                'result': row['Result'],
                'lotno': row['LOTNO'],
                'serial': row['Barcode'],  # Para compatibilidad
                'barcode': row['Barcode'],
                'source_file': row['archivo'],
                'linea': row['linea'],
                'maquina': row['maquina'],
                'part_name': row['PartName'],
                'quantity': row['Quantity'],
                'seq': row['SEQ'],
                'vendor': row['Vendor'],
                # Campos adicionales que SÍ están disponibles en la tabla
                'previousbarcode': row.get('PreviousBarcode', '') or '',
                'productdate': row.get('Productdate', row['ScanDate']) or row['ScanDate'],
                'feederbase': row.get('FeederBase', '') or '',
                # Campos que no están en la tabla
                'l_position': '',  # No disponible en esta tabla
                'm_position': ''   # No disponible en esta tabla
            })
        
        # Calcular estadísticas
        total_records = len(data)
        ok_count = sum(1 for row in data if row['result'] == 'OK')
        ng_count = sum(1 for row in data if row['result'] == 'NG')
        
        stats = {
            'total': total_records,
            'ok': ok_count,
            'ng': ng_count
        }
        
        response_data = {
            'success': True,
            'data': data,
            'stats': stats,
            'total': total_records,
            'message': f'Encontrados {total_records} registros'
        }
        
        cursor.close()
        conn.close()
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error en /api/historial_smt_data: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': [],
            'stats': {'total': 0, 'ok': 0, 'ng': 0},
            'total': 0
        }), 500

@smt_api.route('/smt/debug', methods=['GET'])
def debug_smt():
    """
    Ruta de debug para diagnosticar problemas con datos SMT
    """
    try:
        from datetime import datetime
        
        folder = request.args.get('folder', '')
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Query básica para obtener datos
        if folder:
            query = """
                SELECT ScanDate, ScanTime, SlotNo, Result, LOTNO, Barcode,
                       archivo, linea, maquina, PartName, Quantity, SEQ, Vendor,
                       PreviousBarcode, Productdate, FeederBase
                FROM historial_cambio_material_smt
                WHERE (archivo LIKE %s OR linea LIKE %s OR maquina LIKE %s)
                ORDER BY ScanDate DESC, ScanTime DESC
                LIMIT 50
            """
            cursor.execute(query, (f"%{folder}%", f"%{folder}%", f"%{folder}%"))
        else:
            query = """
                SELECT ScanDate, ScanTime, SlotNo, Result, LOTNO, Barcode, 
                       archivo, linea, maquina, PartName, Quantity, SEQ, Vendor,
                       PreviousBarcode, Productdate, FeederBase
                FROM historial_cambio_material_smt 
                ORDER BY ScanDate DESC, ScanTime DESC 
                LIMIT 50
            """
            cursor.execute(query)
        
        registros = cursor.fetchall()
        
        # Calcular estadísticas
        total_registros = len(registros)
        ok_count = sum(1 for r in registros if r['Result'] == 'OK')
        ng_count = sum(1 for r in registros if r['Result'] == 'NG')
        
        cursor.close()
        conn.close()
        
        return render_template('debug_smt.html',
                             registros=registros,
                             total_registros=total_registros,
                             ok_count=ok_count,
                             ng_count=ng_count,
                             timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                             error=None)
                             
    except Exception as e:
        logger.error(f"Error en debug SMT: {e}")
        return render_template('debug_smt.html',
                             registros=[],
                             total_registros=0,
                             ok_count=0,
                             ng_count=0,
                             timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                             error=str(e))

@smt_api.route('/smt/tabla', methods=['GET'])
def tabla_smt():
    """
    Ruta para visualizar la tabla SMT con filtros HTML
    """
    try:
        # Obtener parámetros de filtro del formulario
        filters = []
        params = []
        
        linea = request.values.get('linea', '')
        maquina = request.values.get('maquina', '')
        fecha_ini = request.values.get('fecha_ini', '')
        fecha_fin = request.values.get('fecha_fin', '')
        result = request.values.get('result', '')

        # Construir filtros dinámicamente
        if linea:
            filters.append('linea = %s')
            params.append(linea)
        if maquina:
            filters.append('maquina = %s')
            params.append(maquina)
        if fecha_ini:
            filters.append('ScanDate >= %s')
            params.append(fecha_ini)
        if fecha_fin:
            filters.append('ScanDate <= %s')
            params.append(fecha_fin)
        if result:
            filters.append('Result = %s')
            params.append(result)

        # Construir consulta
        where_clause = (' WHERE ' + ' AND '.join(filters)) if filters else ''
        query = f"""
            SELECT ScanDate, ScanTime, SlotNo, Result, LOTNO, Barcode, 
                   archivo, linea, maquina, PartName, Quantity, SEQ, Vendor,
                   PreviousBarcode, Productdate, FeederBase
            FROM historial_cambio_material_smt 
            {where_clause} 
            ORDER BY ScanDate DESC, ScanTime DESC 
            LIMIT 1000
        """

        # Ejecutar consulta principal
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # Calcular estadísticas
        ok_count = sum(1 for r in rows if r['Result'] == 'OK')
        ng_count = sum(1 for r in rows if r['Result'] == 'NG')
        unique_files = len(set(r['archivo'] for r in rows if r['archivo']))
        
        # Obtener valores únicos para los selects
        cursor.execute("SELECT DISTINCT linea FROM historial_cambio_material_smt WHERE linea IS NOT NULL ORDER BY linea")
        lineas = [r['linea'] for r in cursor.fetchall()]
        
        cursor.execute("SELECT DISTINCT maquina FROM historial_cambio_material_smt WHERE maquina IS NOT NULL ORDER BY maquina")
        maquinas = [r['maquina'] for r in cursor.fetchall()]
        
        cursor.close()
        conn.close()

        return render_template('tabla_smt.html', 
                             rows=rows, 
                             lineas=lineas, 
                             maquinas=maquinas,
                             linea_selected=linea, 
                             maquina_selected=maquina, 
                             fecha_ini=fecha_ini, 
                             fecha_fin=fecha_fin,
                             result_selected=result,
                             ok_count=ok_count,
                             ng_count=ng_count,
                             unique_files=unique_files)
                             
    except Exception as e:
        logger.error(f"Error en tabla SMT: {e}")
        return f"Error: {e}", 500

@smt_api.route('/api/smt/historial/data', methods=['GET'])
def get_smt_historial_data():
    """
    API endpoint para obtener datos del historial SMT
    Actualizado para usar la nueva estructura de tabla
    """
    try:
        folder = request.args.get('folder', '')
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        if folder:
            # Buscar por archivo, línea o máquina
            cursor.execute("""
                SELECT 
                    ScanDate, ScanTime, SlotNo, Result, 
                    PartName, Quantity, SEQ, Vendor,
                    PreviousBarcode, Productdate, FeederBase
                    PartName, Quantity, SEQ, Vendor
                FROM historial_cambio_material_smt 
                WHERE (archivo LIKE %s OR linea LIKE %s OR maquina LIKE %s)
                ORDER BY ScanDate DESC, ScanTime DESC 
                LIMIT 1000
            """, (f"%{folder}%", f"%{folder}%", f"%{folder}%"))
        else:
            # Sin filtro, obtener todos los datos recientes
            cursor.execute("""
                SELECT 
                    ScanDate, ScanTime, SlotNo, Result, 
                    PartName, Quantity, SEQ, Vendor,
                    PreviousBarcode, Productdate, FeederBase
                    PartName, Quantity, SEQ, Vendor
                FROM historial_cambio_material_smt 
                ORDER BY ScanDate DESC, ScanTime DESC 
                LIMIT 1000
            """)
        
        results = cursor.fetchall()
        
        # Formatear resultados para compatibilidad con frontend
        data = []
        for row in results:
            data.append({
                'scan_date': row['ScanDate'],
                'scan_time': row['ScanTime'],
                'slotno': row['SlotNo'],
                'result': row['Result'],
                'lotno': row['LOTNO'],
                'serial': row['Barcode'],
                'source_file': row['archivo'],
                'linea': row['linea'],
                'maquina': row['maquina'],
                'part_name': row['PartName'],
                'quantity': row['Quantity'],
                'seq': row['SEQ'],
                'vendor': row['Vendor']
            })
        
        # Calcular estadísticas básicas
        total_records = len(data)
        ok_count = sum(1 for row in data if row['result'] == 'OK')
        ng_count = sum(1 for row in data if row['result'] == 'NG')
        
        stats = {
            'total': total_records,
            'ok': ok_count,
            'ng': ng_count
        }
        
        return jsonify({
            'success': True,
            'data': data,
            'stats': stats,
            'total': total_records
        })
        
    except Exception as e:
        logger.error(f"Error en /api/smt/historial/data: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@smt_api.route('/api/smt/historial/stats', methods=['GET'])
def get_smt_historial_stats():
    """
    API endpoint para obtener estadísticas del historial SMT
    """
    try:
        folder = request.args.get('folder', '')
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        if folder:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_records,
                    COUNT(DISTINCT archivo) as total_files,
                    COUNT(CASE WHEN Result = 'OK' THEN 1 END) as ok_count,
                    COUNT(CASE WHEN Result = 'NG' THEN 1 END) as ng_count,
                    COUNT(DISTINCT linea) as total_lines,
                    COUNT(DISTINCT maquina) as total_machines
                FROM historial_cambio_material_smt 
                WHERE (archivo LIKE %s OR linea LIKE %s OR maquina LIKE %s)
            """, (f"%{folder}%", f"%{folder}%", f"%{folder}%"))
        else:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_records,
                    COUNT(DISTINCT archivo) as total_files,
                    COUNT(CASE WHEN Result = 'OK' THEN 1 END) as ok_count,
                    COUNT(CASE WHEN Result = 'NG' THEN 1 END) as ng_count,
                    COUNT(DISTINCT linea) as total_lines,
                    COUNT(DISTINCT maquina) as total_machines
                FROM historial_cambio_material_smt
            """)
        
        stats = cursor.fetchone()
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        logger.error(f"Error en /api/smt/historial/stats: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@smt_api.route('/api/smt/historial/filter', methods=['GET'])
def filter_smt_historial():
    """
    API endpoint para filtrar datos del historial SMT
    """
    try:
        # Obtener parámetros de filtro
        folder = request.args.get('folder', '')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        result_filter = request.args.get('result')
        part_name = request.args.get('part_name')
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Construir query dinámico
        where_conditions = []
        params = []
        
        if folder:
            where_conditions.append("(archivo LIKE %s OR linea LIKE %s OR maquina LIKE %s)")
            params.extend([f"%{folder}%", f"%{folder}%", f"%{folder}%"])
        
        if date_from:
            where_conditions.append("ScanDate >= %s")
            params.append(date_from)
        
        if date_to:
            where_conditions.append("ScanDate <= %s")
            params.append(date_to)
        
        if result_filter:
            where_conditions.append("Result = %s")
            params.append(result_filter)
        
        if part_name:
            where_conditions.append("PartName LIKE %s")
            params.append(f"%{part_name}%")
        
        where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        
        query = f"""
            SELECT 
                ScanDate, ScanTime, SlotNo, Result, 
                PartName, Quantity, SEQ, Vendor,
                PreviousBarcode, Productdate, FeederBase
                PartName, Quantity, SEQ, Vendor
            FROM historial_cambio_material_smt 
            {where_clause}
            ORDER BY ScanDate DESC, ScanTime DESC 
            LIMIT 1000
        """
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        # Formatear resultados
        data = []
        for row in results:
            data.append({
                'scan_date': row['ScanDate'],
                'scan_time': row['ScanTime'],
                'slotno': row['SlotNo'],
                'result': row['Result'],
                'lotno': row['LOTNO'],
                'serial': row['Barcode'],
                'source_file': row['archivo'],
                'linea': row['linea'],
                'maquina': row['maquina'],
                'part_name': row['PartName'],
                'quantity': row['Quantity'],
                'seq': row['SEQ'],
                'vendor': row['Vendor']
            })
        
        # Calcular estadísticas básicas
        total_records = len(data)
        ok_count = sum(1 for row in data if row['result'] == 'OK')
        ng_count = sum(1 for row in data if row['result'] == 'NG')
        
        stats = {
            'total': total_records,
            'ok': ok_count,
            'ng': ng_count
        }
        
        return jsonify({
            'success': True,
            'data': data,
            'stats': stats,
            'total': total_records
        })
        
    except Exception as e:
        logger.error(f"Error en /api/smt/historial/filter: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

def register_smt_routes(app):
    """Registrar las rutas SMT en la aplicación Flask"""
    app.register_blueprint(smt_api)
    logger.info("SMT routes registradas exitosamente")
