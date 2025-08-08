#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rutas SMT corregidas - API endpoints para historial de cambio de material SMT
"""

from flask import Blueprint, request, jsonify, render_template
import mysql.connector
import logging

# Configurar logging
logger = logging.getLogger(__name__)

# Configuración MySQL
DB_CONFIG = {
    'host': 'up-de-fra1-mysql-1.db.run-on-seenode.com',
    'port': 11550,
    'user': 'db_rrpq0erbdujn',
    'password': '5fUNbSRcPP3LN9K2I33Pr0ge',
    'database': 'db_rrpq0erbdujn',
    'charset': 'utf8mb4'
}

# Crear Blueprint
smt_api = Blueprint('smt_api', __name__)

def get_db_connection():
    """Crear conexión a la base de datos"""
    return mysql.connector.connect(**DB_CONFIG)

@smt_api.route('/smt/historial', methods=['GET'])
def smt_historial():
    """
    Página HTML para visualizar historial SMT con filtros optimizados
    """
    try:
        return render_template('Control de calidad/historial_cambio_material_smt_ajax.html')
    except Exception as e:
        logger.error(f"Error en /smt/historial: {e}")
        return f"Error cargando template: {e}", 500

@smt_api.route('/api/historial_smt_data', methods=['GET'])
def api_historial_smt_data():
    """
    API optimizada para cargar datos SMT con filtros
    Filtros optimizados para cargar solo datos del día actual por defecto
    """
    try:
        # Obtener parámetros de filtro
        folder = request.args.get('folder', '')
        part_name = request.args.get('part_name', '')
        result = request.args.get('result', '')
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        linea = request.args.get('linea', '')
        maquina = request.args.get('maquina', '')

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Construir filtros dinámicamente
        filters = []
        params = []

        # Filtro por fecha (opcional para no limitar resultados por defecto)
        if date_from or date_to:
            if date_from:
                date_from_formatted = date_from.replace('-', '')
                filters.append('ScanDate >= %s')
                params.append(date_from_formatted)
            if date_to:
                date_to_formatted = date_to.replace('-', '')
                filters.append('ScanDate <= %s')
                params.append(date_to_formatted)
        # Si no hay filtros de fecha, mostrar datos recientes (últimos 30 días por defecto)
        elif not filters:  # Solo si no hay otros filtros
            from datetime import datetime, timedelta
            thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
            filters.append('ScanDate >= %s')
            params.append(thirty_days_ago)

        # Filtro por línea
        if linea:
            filters.append('linea = %s')
            params.append(linea)

        # Filtro por máquina
        if maquina:
            filters.append('maquina = %s')
            params.append(maquina)

        # Filtro por carpeta/archivo (compatible con versión anterior)
        if folder:
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

        # Construir cláusula WHERE
        where_clause = 'WHERE ' + ' AND '.join(filters) if filters else ''
        
        query = f"""
            SELECT
                ScanDate, ScanTime, SlotNo, Result,
                LOTNO, Barcode, archivo, linea, maquina,
                PartName, Quantity, SEQ, Vendor,
                PreviousBarcode, Productdate, FeederBase
            FROM historial_cambio_material_smt
            {where_clause}
            ORDER BY id DESC
            LIMIT 1000
        """

        cursor.execute(query, params)
        results = cursor.fetchall()

        # Formatear resultados con todas las columnas
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

        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'lineas': lineas,
            'maquinas': maquinas
        })

    except Exception as e:
        logger.error(f"Error en filtros opciones: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@smt_api.route('/smt/debug', methods=['GET'])
def debug_smt():
    """
    Ruta de debug para diagnosticar problemas con datos SMT
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Query básica para obtener datos
        if request.args.get('folder'):
            folder = request.args.get('folder')
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
        unique_files = len(set(r['archivo'] for r in registros if r['archivo']))

        # Obtener valores únicos para filtros
        cursor.execute("SELECT DISTINCT linea FROM historial_cambio_material_smt WHERE linea IS NOT NULL ORDER BY linea")
        lineas = [r['linea'] for r in cursor.fetchall()]
        
        cursor.execute("SELECT DISTINCT maquina FROM historial_cambio_material_smt WHERE maquina IS NOT NULL ORDER BY maquina")
        maquinas = [r['maquina'] for r in cursor.fetchall()]

        cursor.close()
        conn.close()

        debug_info = {
            'total_registros': total_registros,
            'ok_count': ok_count,
            'ng_count': ng_count,
            'unique_files': unique_files,
            'lineas_disponibles': lineas,
            'maquinas_disponibles': maquinas,
            'registros_muestra': registros[:10]  # Solo mostrar 10 para debug
        }

        return jsonify({
            'success': True,
            'debug_info': debug_info
        })

    except Exception as e:
        logger.error(f"Error en debug SMT: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@smt_api.route('/api/smt/historial/data', methods=['GET'])
def get_smt_historial_data():
    """
    API endpoint para obtener datos del historial SMT (compatibilidad)
    """
    try:
        folder = request.args.get('folder', '')

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        if folder:
            cursor.execute("""
                SELECT
                    ScanDate, ScanTime, SlotNo, Result,
                    LOTNO, Barcode, archivo, linea, maquina,
                    PartName, Quantity, SEQ, Vendor,
                    PreviousBarcode, Productdate, FeederBase
                FROM historial_cambio_material_smt
                WHERE (archivo LIKE %s OR linea LIKE %s OR maquina LIKE %s)
                ORDER BY ScanDate DESC, ScanTime DESC
                LIMIT 1000
            """, (f"%{folder}%", f"%{folder}%", f"%{folder}%"))
        else:
            cursor.execute("""
                SELECT
                    ScanDate, ScanTime, SlotNo, Result,
                    LOTNO, Barcode, archivo, linea, maquina,
                    PartName, Quantity, SEQ, Vendor,
                    PreviousBarcode, Productdate, FeederBase
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
                'slot_no': row['SlotNo'],
                'result': row['Result'],
                'lot_no': row['LOTNO'],
                'barcode': row['Barcode'],
                'source_file': row['archivo'],
                'linea': row['linea'],
                'maquina': row['maquina'],
                'part_name': row['PartName'],
                'quantity': row['Quantity'],
                'seq': row['SEQ'],
                'vendor': row['Vendor'],
                'previousbarcode': row.get('PreviousBarcode', '') or '',
                'productdate': row.get('Productdate', row['ScanDate']) or row['ScanDate'],
                'feederbase': row.get('FeederBase', '') or ''
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
            'error': str(e),
            'data': [],
            'stats': {'total': 0, 'ok': 0, 'ng': 0},
            'total': 0
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
