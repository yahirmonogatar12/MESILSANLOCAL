#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import mysql.connector
import re

def test_and_fix():
    # Configuración de base de datos
    config = {
        'host': 'up-de-fra1-mysql-1.db.run-on-seenode.com',
        'port': 11550,
        'user': 'db_rrpq0erbdujn',
        'password': '5fUNbSRcPP3LN9K2I33Pr0ge',
        'database': 'db_rrpq0erbdujn',
        'charset': 'utf8mb4',
        'autocommit': True
    }
    
    def parse_folder_name(folder_name):
        """Parsea nombre de carpeta para extraer línea y mounter"""
        print(f"DEBUG: Input folder = '{folder_name}'")
        
        # Formato: "1line/L1 m1"
        match = re.search(r'(\d+)line[/\\]?.*?L(\d+)\s*m(\d+)', folder_name, re.IGNORECASE)
        if match:
            line_num = int(match.group(1))
            mounter_num = int(match.group(3))
            print(f"DEBUG: Parsed -> line={line_num}, mounter={mounter_num}")
            return line_num, mounter_num
        
        print("DEBUG: No match, using fallback (1, 1)")
        return 1, 1
    
    def test_query(filters):
        """Probar la consulta con filtros"""
        try:
            connection = mysql.connector.connect(**config)
            cursor = connection.cursor(dictionary=True)
            
            # Query base
            query = """
                SELECT
                    DATE_FORMAT(scan_date, '%%Y-%%m-%%d') as scan_date,
                    TIME_FORMAT(scan_time, '%%H:%%i:%%S') as scan_time,
                    slot_no,
                    result,
                    part_name,
                    quantity,
                    vendor,
                    lot_no,
                    barcode,
                    feeder_base,
                    previous_barcode,
                    source_file,
                    line_number,
                    mounter_number
                FROM historial_cambio_material_smt
                WHERE 1=1
            """
            params = []
            
            # Aplicar filtros
            if filters:
                if filters.get('folder'):
                    line_num, mounter_num = parse_folder_name(filters['folder'])
                    print(f"DEBUG: Adding filter -> line_number = {line_num}, mounter_number = {mounter_num}")
                    query += " AND line_number = %s AND mounter_number = %s"
                    params.extend([line_num, mounter_num])
                    
            query += " ORDER BY scan_date DESC, scan_time DESC LIMIT 10"
            
            print(f"DEBUG: Final query = {query}")
            print(f"DEBUG: Final params = {params}")
            print(f"DEBUG: Params count = {len(params)}")
            print(f"DEBUG: Placeholders count = {query.count('%s')}")
            
            cursor.execute(query, params)
            data = cursor.fetchall()
            
            print(f"SUCCESS: Found {len(data)} records")
            return {'success': True, 'data': data}
            
        except Exception as e:
            print(f"ERROR: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    # Test
    filters = {'folder': '1line/L1 m1'}
    result = test_query(filters)
    
    if result['success']:
        print("✅ Query funciona correctamente")
        if result['data']:
            print("Primer registro:")
            print(result['data'][0])
    else:
        print("❌ Error en query:", result['error'])

if __name__ == '__main__':
    test_and_fix()
