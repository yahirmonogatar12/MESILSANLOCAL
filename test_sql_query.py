#!/usr/bin/env python3
"""
Script para probar directamente la consulta SQL del API
"""

import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_sql_query():
    """Prueba la consulta SQL del API"""
    try:
        from app.db import get_db_connection
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Consulta simple de prueba
        query = """
            SELECT
                linea,
                maquina, 
                ScanDate,
                ScanTime,
                SlotNo,
                Result,
                PreviousBarcode,
                Productdate,
                PartName,
                Quantity,
                SEQ,
                Vendor,
                LOTNO,
                Barcode,
                FeederBase,
                archivo
            FROM historial_cambio_material_smt
            WHERE ScanDate >= %s
            ORDER BY ScanDate DESC, ScanTime DESC
            LIMIT 5
        """
        
        params = ['20250801']
        
        print("🔍 Ejecutando consulta...")
        print(f"Query: {query}")
        print(f"Params: {params}")
        
        cursor.execute(query, params)
        resultados = cursor.fetchall()
        
        print(f"✅ Consulta exitosa!")
        print(f"📊 Registros encontrados: {len(resultados)}")
        
        if resultados:
            print("\n📋 Primer registro:")
            row = resultados[0]
            print(f"  linea: {row[0]}")
            print(f"  maquina: {row[1]}")
            print(f"  ScanDate: {row[2]}")
            print(f"  ScanTime: {row[3]}")
            print(f"  SlotNo: {row[4]}")
            print(f"  Result: {row[5]}")
            print(f"  PartName: {row[8]}")
            print(f"  Quantity: {row[9]}")
            
            # Formatear como lo hace el API
            scan_date = str(row[2]) if row[2] else ''
            if len(scan_date) == 8:  # YYYYMMDD
                formatted_date = f"{scan_date[:4]}-{scan_date[4:6]}-{scan_date[6:8]}"
            else:
                formatted_date = scan_date
            
            formatted_row = {
                'equipment': row[0] or '',          # linea
                'slot_no': str(row[4]) if row[4] else '',  # SlotNo  
                'regist_date': formatted_date,      # ScanDate formateado
                'warehousing': row[11] or '',       # Vendor
                'regist_quantity': row[9] or 0,     # Quantity
                'current_quantity': row[9] or 0,    # Quantity (mismo valor)
                'part_name': row[8] or '',          # PartName
            }
            
            print("\n🎯 Registro formateado:")
            for key, value in formatted_row.items():
                print(f"  {key}: {value}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    test_sql_query()
