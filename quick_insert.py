#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Insertar datos básicos que funcionen inmediatamente
"""

import mysql.connector
from datetime import datetime, timedelta
import random

# Configuración MySQL
DB_CONFIG = {
    'host': 'up-de-fra1-mysql-1.db.run-on-seenode.com',
    'port': 11550,
    'user': 'db_rrpq0erbdujn',
    'password': '5fUNbSRcPP3LN9K2I33Pr0ge',
    'database': 'db_rrpq0erbdujn',
    'charset': 'utf8mb4'
}

def insert_basic_data():
    """Insertar datos básicos garantizados"""
    try:
        print("🔗 Conectando...")
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Limpiar tabla primero
        cursor.execute("DELETE FROM historial_cambio_material_smt")
        print("🗑️ Tabla limpiada")
        
        # Insertar datos para múltiples fechas
        today = datetime.now()
        
        basic_data = []
        for day_offset in range(7):  # Últimos 7 días
            date = today - timedelta(days=day_offset)
            scan_date = date.strftime('%Y%m%d')
            
            # 10 registros por día
            for i in range(10):
                record = (
                    '1LINE',                           # linea
                    'L1M1',                           # maquina
                    f'{scan_date}_test.csv',          # archivo
                    scan_date,                        # ScanDate
                    f'{8+i:02d}:30:00',              # ScanTime
                    i+1,                             # SlotNo
                    'OK' if i % 3 != 0 else 'NG',   # Result
                    f'PBC{scan_date}{i:03d}',        # PreviousBarcode
                    scan_date,                        # Productdate
                    'R0603_100R',                     # PartName
                    1,                               # Quantity
                    f'SEQ{i+1:03d}',                 # SEQ
                    'SAMSUNG',                       # Vendor
                    f'LOT{scan_date}{i:03d}',        # LOTNO
                    f'BC{scan_date}{i:06d}',         # Barcode
                    f'FB{i+1}'                       # FeederBase
                )
                basic_data.append(record)
        
        # Insertar en lote
        insert_query = """
            INSERT INTO historial_cambio_material_smt 
            (linea, maquina, archivo, ScanDate, ScanTime, SlotNo, Result,
             PreviousBarcode, Productdate, PartName, Quantity, SEQ, Vendor,
             LOTNO, Barcode, FeederBase)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        cursor.executemany(insert_query, basic_data)
        conn.commit()
        
        print(f"✅ Insertados {len(basic_data)} registros básicos")
        
        # Verificar inmediatamente
        cursor.execute("SELECT COUNT(*) FROM historial_cambio_material_smt")
        count = cursor.fetchone()[0]
        print(f"📊 Total en tabla: {count}")
        
        # Verificar fechas
        cursor.execute("SELECT DISTINCT ScanDate FROM historial_cambio_material_smt ORDER BY ScanDate DESC")
        fechas = cursor.fetchall()
        print(f"📅 Fechas insertadas: {[f[0] for f in fechas]}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("📝 Insertando datos básicos...")
    if insert_basic_data():
        print("\n🎉 ¡Datos insertados!")
        print("▶️ Ahora ve a: http://127.0.0.1:5000/smt/historial")
        print("▶️ Debería mostrar datos inmediatamente")
    else:
        print("\n❌ Error insertando datos")
