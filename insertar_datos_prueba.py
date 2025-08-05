#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Insertar datos de prueba en historial_cambio_material_smt
"""

import mysql.connector
import sys
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

def insertar_datos_prueba():
    """Insertar datos de prueba"""
    try:
        print("🔧 Conectando a MySQL...")
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Verificar si hay datos
        cursor.execute("SELECT COUNT(*) FROM historial_cambio_material_smt")
        count = cursor.fetchone()[0]
        
        if count > 0:
            print(f"✅ Ya hay {count} registros en la tabla")
            return True
        
        print("📝 Insertando datos de prueba...")
        
        # Datos de prueba
        datos_prueba = []
        base_date = datetime.now()
        
        for i in range(20):
            fecha = base_date - timedelta(days=i//4)
            scan_date = fecha.strftime('%Y%m%d')
            scan_time = f"{10 + (i % 8):02d}:30:00"
            
            slot_no = f"S{(i % 4) + 1:02d}"
            result = "OK" if i % 3 != 0 else "NG"
            lot_no = f"LOT{2025000 + i:06d}"
            barcode = f"BC{1000000 + i:07d}"
            
            linea = "1line" if i % 2 == 0 else "2line"
            maquina = f"L{1 if linea == '1line' else 2} M{(i % 2) + 1}"
            archivo = f"20250{(i//5)+1:02d}0{(i%5)+1}.csv"
            
            part_name = f"Component_{chr(65 + (i % 5))}"
            quantity = 1
            seq = i + 1
            vendor = "Vendor_A" if i % 2 == 0 else "Vendor_B"
            
            datos_prueba.append((
                scan_date, scan_time, slot_no, result, lot_no, barcode,
                archivo, linea, maquina, part_name, quantity, seq, vendor
            ))
        
        # Insert query
        insert_query = """
            INSERT INTO historial_cambio_material_smt 
            (ScanDate, ScanTime, SlotNo, Result, LOTNO, Barcode, archivo, linea, maquina, 
             PartName, Quantity, SEQ, Vendor) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        cursor.executemany(insert_query, datos_prueba)
        conn.commit()
        
        print(f"✅ Insertados {len(datos_prueba)} registros de prueba")
        
        # Verificar inserción
        cursor.execute("SELECT COUNT(*) FROM historial_cambio_material_smt")
        new_count = cursor.fetchone()[0]
        print(f"📊 Total de registros ahora: {new_count}")
        
        # Mostrar algunos registros
        cursor.execute("""
            SELECT ScanDate, ScanTime, linea, maquina, Result, SlotNo 
            FROM historial_cambio_material_smt 
            ORDER BY ScanDate DESC, ScanTime DESC 
            LIMIT 5
        """)
        
        registros = cursor.fetchall()
        print("\n📋 Primeros 5 registros insertados:")
        for reg in registros:
            print(f"  - {reg[0]} {reg[1]} | {reg[2]}/{reg[3]} | {reg[4]} | {reg[5]}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = insertar_datos_prueba()
    sys.exit(0 if success else 1)
