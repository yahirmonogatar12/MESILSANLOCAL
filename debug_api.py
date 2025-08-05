#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug API endpoint para verificar respuesta
"""

import mysql.connector
import json

# Configuración MySQL
DB_CONFIG = {
    'host': 'up-de-fra1-mysql-1.db.run-on-seenode.com',
    'port': 11550,
    'user': 'db_rrpq0erbdujn',
    'password': '5fUNbSRcPP3LN9K2I33Pr0ge',
    'database': 'db_rrpq0erbdujn',
    'charset': 'utf8mb4'
}

def test_api_response():
    """Test directo de la lógica de la API"""
    try:
        print("🧪 Simulando respuesta de API...")
        
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        # Simular query de la API
        folder = "1line"  # Filtro de ejemplo
        
        if folder:
            cursor.execute("""
                SELECT 
                    ScanDate, ScanTime, SlotNo, Result, 
                    LOTNO, Barcode, archivo, linea, maquina,
                    PartName, Quantity, SEQ, Vendor
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
                    PartName, Quantity, SEQ, Vendor
                FROM historial_cambio_material_smt 
                ORDER BY ScanDate DESC, ScanTime DESC 
                LIMIT 1000
            """)
        
        results = cursor.fetchall()
        print(f"📊 Query ejecutada, {len(results)} registros encontrados")
        
        # Formatear como la API
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
        
        # Calcular estadísticas
        total_records = len(data)
        ok_count = sum(1 for row in data if row['result'] == 'OK')
        ng_count = sum(1 for row in data if row['result'] == 'NG')
        
        stats = {
            'total': total_records,
            'ok': ok_count,
            'ng': ng_count
        }
        
        response = {
            'success': True,
            'data': data,
            'stats': stats,
            'total': total_records
        }
        
        print(f"✅ Respuesta formateada:")
        print(f"  - Success: {response['success']}")
        print(f"  - Total registros: {response['total']}")
        print(f"  - Stats: {response['stats']}")
        
        if data:
            print(f"  - Primer registro: {data[0]}")
        else:
            print("  - No hay datos en la respuesta")
        
        # Guardar respuesta en archivo para debug
        with open('debug_api_response.json', 'w') as f:
            json.dump(response, f, indent=2, default=str)
        
        print(f"💾 Respuesta guardada en debug_api_response.json")
        
        cursor.close()
        conn.close()
        
        return len(data) > 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_api_response()
