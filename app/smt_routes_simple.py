#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SMT Routes Simple - Sin filtros complicados
"""

from flask import Blueprint, request, jsonify
import mysql.connector
from datetime import datetime, timedelta
import os

# Configuración MySQL (variables de entorno obligatorias - sin fallback)
DB_CONFIG = {
    'host': os.getenv('MYSQL_HOST'),
    'port': int(os.getenv('MYSQL_PORT', 3306)),
    'user': os.getenv('MYSQL_USER'),
    'password': os.getenv('MYSQL_PASSWORD'),
    'database': os.getenv('MYSQL_DATABASE'),
    'charset': 'utf8mb4'
}

smt_bp = Blueprint('smt', __name__)

def get_db_connection():
    """Conexión MySQL simple"""
    return mysql.connector.connect(**DB_CONFIG)

@smt_bp.route('/api/historial_smt_data', methods=['GET'])
def get_historial_smt_data():
    """Obtener datos SMT - Simple y sin filtros complicados"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Query simple - Sin filtros complicados usando columnas reales
        query = """
            SELECT 
                ScanDate,
                ScanTime,
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
                linea,
                maquina,
                archivo
            FROM historial_cambio_material_smt
            ORDER BY id DESC
            LIMIT 1000
        """
        
        print(f"🔍 Query: {query}")
        
        cursor.execute(query)
        records = cursor.fetchall()
        
        print(f"📊 Registros encontrados: {len(records)}")
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'status': 'success',
            'data': records,
            'total': len(records),
            'message': f'Se encontraron {len(records)} registros'
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
        
        # Últimas 24 horas
        cursor.execute("""
            SELECT COUNT(*) FROM historial_cambio_material_smt 
            WHERE ScanDate >= CURDATE()
        """)
        today = cursor.fetchone()[0]
        
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
                'hoy': today,
                'por_resultado': por_resultado
            }
        })
        
    except Exception as e:
        print(f"❌ Error stats: {e}")
        return jsonify({
            'status': 'error',
            'stats': {}
        }), 500
