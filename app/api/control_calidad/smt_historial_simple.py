"""Version simple del historial SMT con formato correcto de fechas y horas.

Consumido por 'Historial de cambio de material de SMT' en
LISTA_CONTROL_DE_CALIDAD.

Rutas:
  GET /api/historial_smt_data  -> JSON (ESTA implementacion es la que responde
                                  en runtime; ver nota en smt_historial.py)
  GET /api/smt_stats           -> JSON estadisticas basicas

Migrado desde `app/smt_routes_date_fixed.py` (2026-05-22). Mismo blueprint
name ('smt') y mismas rutas; el frontend no requiere cambios.

NOTA: comparte la ruta /api/historial_smt_data con `smt_historial.py`.
Este blueprint se registra primero (orden de _MODULOS_REGISTRADOS) y por
tanto gana en el routing de Flask. Mantener ese orden si se reordena la lista.

NOTA WF_003: conserva `get_db_connection()` directo con mysql.connector.
"""

import os
from datetime import datetime, timedelta

import mysql.connector
from flask import Blueprint, jsonify, request


DB_CONFIG = {
    'host': os.getenv('MYSQL_HOST'),
    'port': int(os.getenv('MYSQL_PORT', 3306)),
    'user': os.getenv('MYSQL_USER'),
    'password': os.getenv('MYSQL_PASSWORD'),
    'database': os.getenv('MYSQL_DATABASE'),
    'charset': 'utf8mb4'
}


bp = Blueprint('smt', __name__)


def get_db_connection():
    """Conexion MySQL simple"""
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
        time_str = str(scan_time).zfill(6)
        return f"{time_str[:2]}:{time_str[2:4]}:{time_str[4:6]}"
    return scan_time


@bp.route('/api/historial_smt_data', methods=['GET'])
def get_historial_smt_data():
    """Obtener datos SMT - Simple y sin filtros complicados"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        fecha_desde = request.args.get('fecha_desde')
        fecha_hasta = request.args.get('fecha_hasta')
        limit = request.args.get('limit', 1000)

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

        where_conditions = []
        params = []

        if fecha_desde:
            fecha_desde_formatted = fecha_desde.replace('-', '')
            where_conditions.append("ScanDate >= %s")
            params.append(fecha_desde_formatted)

        if fecha_hasta:
            fecha_hasta_formatted = fecha_hasta.replace('-', '')
            where_conditions.append("ScanDate <= %s")
            params.append(fecha_hasta_formatted)

        if where_conditions:
            query += " WHERE " + " AND ".join(where_conditions)

        query += f" ORDER BY ScanDate DESC, ScanTime DESC LIMIT {limit}"

        print(f"Query: {query}")
        print(f"Params: {params}")

        cursor.execute(query, params)
        records = cursor.fetchall()

        for record in records:
            if 'ScanDate' in record:
                record['fecha_formateada'] = format_scan_date(record['ScanDate'])
            if 'ScanTime' in record:
                record['hora_formateada'] = format_scan_time(record['ScanTime'])

        print(f"Registros encontrados: {len(records)}")

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
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

        return jsonify({
            'status': 'error',
            'data': [],
            'total': 0,
            'message': f'Error: {str(e)}'
        }), 500


@bp.route('/api/smt_stats', methods=['GET'])
def get_smt_stats():
    """Estadisticas basicas"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM historial_cambio_material_smt")
        total = cursor.fetchone()[0]

        today = datetime.now().strftime('%Y%m%d')
        cursor.execute("""
            SELECT COUNT(*) FROM historial_cambio_material_smt
            WHERE ScanDate = %s
        """, (today,))
        today_count = cursor.fetchone()[0]

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
        print(f"Error stats: {e}")
        return jsonify({
            'status': 'error',
            'stats': {}
        }), 500
