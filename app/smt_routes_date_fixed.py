#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SMT Routes Simple - Con formato correcto de fechas y horas
"""

from flask import Blueprint, request, jsonify
import mysql.connector
from datetime import datetime, timedelta

# Configuración MySQL
DB_CONFIG = {
    'host': 'up-de-fra1-mysql-1.db.run-on-seenode.com',
    'port': 11550,
    'user': 'db_rrpq0erbdujn',
    'password': '5fUNbSRcPP3LN9K2I33Pr0ge',
    'database': 'db_rrpq0erbdujn',
    'charset': 'utf8mb4'
}

smt_bp = Blueprint('smt', __name__)

def get_db_connection():
    """Conexión MySQL simple"""
    return mysql.connector.connect(**DB_CONFIG)

def format_scan_date(scan_date):
    """Convertir ScanDate de YYYYMMDD a YYYY-MM-DD"""
    if scan_date and len(str(scan_date)) == 8:
        date_str = str(scan_date)
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
    return scan_date

def format_scan_time(scan_time):
    """Convertir ScanTime de HHMMSS a HH:MM:SS"""
    if scan_time:
        time_str = str(scan_time).zfill(6)  # Asegurar 6 dígitos
        return f"{time_str[:2]}:{time_str[2:4]}:{time_str[4:6]}"
    return scan_time

@smt_bp.route('/api/historial_smt_data', methods=['GET'])
def get_historial_smt_data():
    """Obtener datos SMT - Simple y sin filtros complicados"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Obtener parámetros de filtro opcionales
        fecha_desde = request.args.get('fecha_desde')
        fecha_hasta = request.args.get('fecha_hasta')
        limit = request.args.get('limit', 1000)
        
        # Query base
        query = """
            SELECT 
                SlotNo,
                Result,
                LOTNO,
                Barcode,
                PreviousBarcode,
                Productdate,
                PartName,
                Quantity,
                SEQ,
                Vendor,
                FeederBase,
                ScanDate,
                ScanTime,
                linea,
                maquina,
                archivo
            FROM historial_cambio_material_smt
        """
        
        # Agregar filtros de fecha si se proporcionan
        where_conditions = []
        params = []
        
        if fecha_desde:
            # Convertir fecha YYYY-MM-DD a YYYYMMDD
            fecha_desde_formatted = fecha_desde.replace('-', '')
            where_conditions.append("ScanDate >= %s")
            params.append(fecha_desde_formatted)
        
        if fecha_hasta:
            # Convertir fecha YYYY-MM-DD a YYYYMMDD
            fecha_hasta_formatted = fecha_hasta.replace('-', '')
            where_conditions.append("ScanDate <= %s")
            params.append(fecha_hasta_formatted)
        
        if where_conditions:
            query += " WHERE " + " AND ".join(where_conditions)
        
        query += f" ORDER BY ScanDate DESC, ScanTime DESC LIMIT {limit}"
        
        print(f"🔍 Query: {query}")
        print(f"📋 Params: {params}")
        
        cursor.execute(query, params)
        records = cursor.fetchall()
        
        # Formatear fechas y horas en los resultados
        for record in records:
            if 'ScanDate' in record:
                record['fecha_formateada'] = format_scan_date(record['ScanDate'])
            if 'ScanTime' in record:
                record['hora_formateada'] = format_scan_time(record['ScanTime'])
        
        print(f"📊 Registros encontrados: {len(records)}")
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'status': 'success',
            'data': records,
            'total': len(records),
            'message': f'Se encontraron {len(records)} registros',
            'filters': {
                'fecha_desde': fecha_desde,
                'fecha_hasta': fecha_hasta
            }
        })
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            'status': 'error',
            'data': [],
            'total': 0,
            'message': f'Error: {str(e)}'
        }), 500

@smt_bp.route('/api/smt_stats', methods=['GET'])
def get_smt_stats():
    """Estadísticas básicas"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Total de registros
        cursor.execute("SELECT COUNT(*) FROM historial_cambio_material_smt")
        total = cursor.fetchone()[0]
        
        # Últimas 24 horas (usando ScanDate)
        today = datetime.now().strftime('%Y%m%d')
        cursor.execute("""
            SELECT COUNT(*) FROM historial_cambio_material_smt 
            WHERE ScanDate = %s
        """, (today,))
        today_count = cursor.fetchone()[0]
        
        # Por resultado
        cursor.execute("""
            SELECT Result, COUNT(*) 
            FROM historial_cambio_material_smt 
            GROUP BY Result
        """)
        por_resultado = dict(cursor.fetchall())
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'status': 'success',
            'stats': {
                'total': total,
                'hoy': today_count,
                'por_resultado': por_resultado
            }
        })
        
    except Exception as e:
        print(f"❌ Error stats: {e}")
        return jsonify({
            'status': 'error',
            'stats': {}
        }), 500
