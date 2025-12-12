# -*- coding: utf-8 -*-
"""
Rutas de SMT (Surface Mount Technology)
APIs para gestión de datos SMT, historial de cambio de material, logs de máquina
"""

import os
import traceback
from datetime import datetime
import mysql.connector
from flask import Blueprint, request, jsonify, session, render_template

from .utils import login_requerido, obtener_fecha_hora_mexico
from ..database.db_mysql import execute_query, get_connection

smt_bp = Blueprint('smt_modular', __name__)


# ============== VISTAS SMT ==============

@smt_bp.route('/csv-viewer')
@login_requerido
def csv_viewer():
    """Página principal del visor de CSV"""
    try:
        return render_template('csv-viewer.html')
    except Exception as e:
        print(f"Error al cargar CSV viewer: {e}")
        return f"Error al cargar la página: {str(e)}", 500


@smt_bp.route('/historial-cambio-material-smt')
@login_requerido
def historial_cambio_material_smt():
    """Página del historial de cambio de material de SMT"""
    try:
        return render_template('Control de calidad/historial_cambio_material_smt.html')
    except Exception as e:
        print(f"Error al cargar historial de cambio de material SMT: {e}")
        return f"Error al cargar la página: {str(e)}", 500


@smt_bp.route('/historial-cambio-material-smt-ajax')
@login_requerido
def historial_cambio_material_smt_ajax():
    """Ruta AJAX para historial de cambio de material SMT"""
    try:
        return render_template('Control de calidad/historial_cambio_material_smt_ajax.html')
    except Exception as e:
        print(f"Error en historial_cambio_material_smt_ajax: {e}")
        return f"Error interno del servidor: {e}", 500


# ============== API DATOS CSV/SMT ==============

@smt_bp.route('/api/csv_data')
@login_requerido
def get_csv_data():
    """API para obtener datos SMT desde MySQL"""
    try:
        folder = request.args.get('folder', '')
        print(f"🔍 Solicitud recibida para carpeta: '{folder}'")
        
        if not folder:
            return jsonify({'success': False, 'error': 'Folder parameter required'}), 400
        
        mysql_config = {
            'host': os.getenv('MYSQL_HOST'),
            'port': int(os.getenv('MYSQL_PORT', 3306)),
            'user': os.getenv('MYSQL_USER'),
            'password': os.getenv('MYSQL_PASSWORD'),
            'database': os.getenv('MYSQL_DATABASE'),
            'charset': 'utf8mb4'
        }
        
        conn = mysql.connector.connect(**mysql_config)
        cursor = conn.cursor(dictionary=True)
        
        query = """
            SELECT ScanDate, ScanTime, SlotNo, Result, PreviousBarcode,
                   Productdate, PartName, Quantity, SEQ, Vendor, LOTNO,
                   Barcode, FeederBase, archivo, linea, maquina, fecha_subida
            FROM logs_maquina
            WHERE archivo LIKE %s OR linea LIKE %s OR maquina LIKE %s
            ORDER BY ScanDate DESC, ScanTime DESC
            LIMIT 1000
        """
        
        cursor.execute(query, (f"%{folder}%", f"%{folder}%", f"%{folder}%"))
        resultados = cursor.fetchall()
        
        print(f"✓ Encontrados {len(resultados)} registros en MySQL")
        
        all_data = []
        for resultado in resultados:
            cleaned_record = {}
            for key, value in resultado.items():
                if hasattr(value, 'isoformat'):
                    cleaned_record[key] = value.isoformat()
                elif value is None:
                    cleaned_record[key] = None
                else:
                    cleaned_record[key] = str(value)
            
            cleaned_record['SourceFile'] = cleaned_record.get('archivo', '')
            all_data.append(cleaned_record)
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'data': all_data,
            'message': f'Datos MySQL cargados para {folder}: {len(all_data)} registros',
            'files_processed': len(set([d.get('SourceFile', '') for d in all_data])),
            'source': 'mysql_logs_maquina'
        })
        
    except Exception as e:
        print(f"❌ Error obteniendo datos desde MySQL: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False, 
            'error': f'Error al consultar base de datos MySQL: {str(e)}'
        }), 500


@smt_bp.route('/api/csv_stats')
@login_requerido
def get_csv_stats():
    """API para obtener estadísticas SMT desde MySQL"""
    try:
        folder = request.args.get('folder', '')
        
        if not folder:
            return jsonify({'success': False, 'error': 'Folder parameter required'}), 400
        
        mysql_config = {
            'host': os.getenv('MYSQL_HOST'),
            'port': int(os.getenv('MYSQL_PORT', 3306)),
            'user': os.getenv('MYSQL_USER'),
            'password': os.getenv('MYSQL_PASSWORD'),
            'database': os.getenv('MYSQL_DATABASE'),
            'charset': 'utf8mb4'
        }
        
        conn = mysql.connector.connect(**mysql_config)
        cursor = conn.cursor(dictionary=True)
        
        query = """
            SELECT COUNT(*) as total_records,
                   COUNT(DISTINCT archivo) as total_files,
                   COUNT(DISTINCT ScanDate) as total_days,
                   COUNT(CASE WHEN Result = 'OK' THEN 1 END) as ok_count,
                   COUNT(CASE WHEN Result = 'NG' THEN 1 END) as ng_count,
                   MIN(ScanDate) as first_date,
                   MAX(ScanDate) as last_date
            FROM logs_maquina
            WHERE archivo LIKE %s OR linea LIKE %s OR maquina LIKE %s
        """
        
        cursor.execute(query, (f"%{folder}%", f"%{folder}%", f"%{folder}%"))
        stats = cursor.fetchone()
        
        files_query = """
            SELECT DISTINCT archivo, COUNT(*) as records
            FROM logs_maquina
            WHERE archivo LIKE %s OR linea LIKE %s OR maquina LIKE %s
            GROUP BY archivo
            ORDER BY archivo
        """
        
        cursor.execute(files_query, (f"%{folder}%", f"%{folder}%", f"%{folder}%"))
        files_info = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_records': stats['total_records'] or 0,
                'total_files': stats['total_files'] or 0,
                'total_days': stats['total_days'] or 0,
                'ok_count': stats['ok_count'] or 0,
                'ng_count': stats['ng_count'] or 0,
                'first_date': stats['first_date'].isoformat() if stats['first_date'] else None,
                'last_date': stats['last_date'].isoformat() if stats['last_date'] else None
            },
            'files': [{'name': f['archivo'], 'records': f['records']} for f in files_info],
            'source': 'mysql'
        })
        
    except Exception as e:
        print(f"❌ Error obteniendo estadísticas desde MySQL: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False, 
            'error': f'Error al consultar estadísticas MySQL: {str(e)}'
        }), 500


@smt_bp.route('/api/filter_data', methods=['POST'])
@login_requerido
def filter_csv_data():
    """API para filtrar datos SMT desde MySQL"""
    try:
        filters = request.get_json()
        folder = filters.get('folder', '')
        part_name = filters.get('partName', '')
        result = filters.get('result', '')
        date_from = filters.get('dateFrom', '')
        date_to = filters.get('dateTo', '')
        
        if not folder:
            return jsonify({'success': False, 'error': 'Folder parameter required'}), 400
        
        mysql_config = {
            'host': os.getenv('MYSQL_HOST'),
            'port': int(os.getenv('MYSQL_PORT', 3306)),
            'user': os.getenv('MYSQL_USER'),
            'password': os.getenv('MYSQL_PASSWORD'),
            'database': os.getenv('MYSQL_DATABASE'),
            'charset': 'utf8mb4'
        }
        
        conn = mysql.connector.connect(**mysql_config)
        cursor = conn.cursor(dictionary=True)
        
        where_conditions = ["(archivo LIKE %s OR linea LIKE %s OR maquina LIKE %s)"]
        params = [f"%{folder}%", f"%{folder}%", f"%{folder}%"]
        
        if part_name:
            where_conditions.append("PartName LIKE %s")
            params.append(f"%{part_name}%")
        
        if result:
            where_conditions.append("Result = %s")
            params.append(result.upper())
        
        if date_from:
            where_conditions.append("ScanDate >= %s")
            params.append(date_from.replace('-', ''))
        
        if date_to:
            where_conditions.append("ScanDate <= %s")
            params.append(date_to.replace('-', ''))
        
        where_clause = " AND ".join(where_conditions)
        
        query = f"""
            SELECT ScanDate, ScanTime, SlotNo, Result, PreviousBarcode,
                   Productdate, PartName, Quantity, SEQ, Vendor, LOTNO,
                   Barcode, FeederBase, archivo, linea, maquina
            FROM logs_maquina
            WHERE {where_clause}
            ORDER BY ScanDate DESC, ScanTime DESC
            LIMIT 5000
        """
        
        cursor.execute(query, params)
        resultados = cursor.fetchall()
        
        filtered_data = []
        for resultado in resultados:
            cleaned_record = {}
            for key, value in resultado.items():
                if hasattr(value, 'isoformat'):
                    cleaned_record[key] = value.isoformat()
                elif value is None:
                    cleaned_record[key] = None
                else:
                    cleaned_record[key] = str(value)
            
            cleaned_record['SourceFile'] = cleaned_record.get('archivo', '')
            filtered_data.append(cleaned_record)
        
        stats = {
            'total_records': len(filtered_data),
            'ok_count': len([d for d in filtered_data if str(d.get('Result', '')).upper() == 'OK']),
            'ng_count': len([d for d in filtered_data if str(d.get('Result', '')).upper() == 'NG'])
        }
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'data': filtered_data,
            'stats': stats,
            'source': 'mysql'
        })
        
    except Exception as e:
        print(f"❌ Error filtrando datos desde MySQL: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Error al filtrar datos MySQL: {str(e)}'}), 500


# ============== RUTAS AJAX SMT ==============

@smt_bp.route('/control-produccion-smt-ajax')
@login_requerido
def control_produccion_smt_ajax():
    """Ruta AJAX para Control de produccion SMT"""
    try:
        return render_template('Control de proceso/control_produccion_smt_ajax.html')
    except Exception as e:
        print(f"Error al cargar template Control de produccion SMT AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@smt_bp.route('/control-operacion-linea-smt-ajax')
@login_requerido
def control_operacion_linea_smt_ajax():
    """Ruta AJAX para Control de operación de línea SMT"""
    try:
        fecha_hoy = obtener_fecha_hora_mexico().strftime('%d/%m/%Y')
        return render_template('Control de proceso/control_operacion_linea_smt_ajax.html', fecha_hoy=fecha_hoy)
    except Exception as e:
        print(f"Error al cargar template Control de operación de línea SMT AJAX: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@smt_bp.route('/control-impresion-identificacion-smt-ajax')
@login_requerido
def control_impresion_identificacion_smt_ajax():
    """Ruta AJAX para Control de impresión de identificación SMT"""
    try:
        return render_template('Control de proceso/control_impresion_identificacion_smt_ajax.html')
    except Exception as e:
        print(f"Error al cargar template: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@smt_bp.route('/control-registro-identificacion-smt-ajax')
@login_requerido
def control_registro_identificacion_smt_ajax():
    """Ruta AJAX para Control de registro de identificación SMT"""
    try:
        return render_template('Control de proceso/control_registro_identificacion_smt_ajax.html')
    except Exception as e:
        print(f"Error al cargar template: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@smt_bp.route('/reporte-diario-inspeccion-smt-ajax')
@login_requerido
def reporte_diario_inspeccion_smt_ajax():
    """Ruta AJAX para Reporte diario de inspección SMT"""
    try:
        return render_template('Control de proceso/reporte_diario_inspeccion_smt_ajax.html')
    except Exception as e:
        print(f"Error al cargar template: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500


@smt_bp.route('/control-diario-inspeccion-smt-ajax')
@login_requerido
def control_diario_inspeccion_smt_ajax():
    """Ruta AJAX para Control diario de inspección SMT"""
    try:
        return render_template('Control de proceso/control_diario_inspeccion_smt_ajax.html')
    except Exception as e:
        print(f"Error al cargar template: {e}")
        return f"Error al cargar el contenido: {str(e)}", 500
