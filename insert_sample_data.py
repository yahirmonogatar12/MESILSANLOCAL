#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script simple para crear datos de prueba en la tabla SMT existente
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
    'charset': 'utf8mb4',
    'connection_timeout': 30,
    'autocommit': True
}

def insert_sample_data():
    """Insertar datos de prueba en la tabla existente"""
    try:
        print("🔗 Conectando a MySQL...")
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("✅ Conectado")
        
        # Verificar si la tabla existe
        cursor.execute("SHOW TABLES LIKE 'historial_cambio_material_smt'")
        if not cursor.fetchone():
            print("❌ Tabla historial_cambio_material_smt no existe")
            return False
        
        # Limpiar datos existentes
        cursor.execute("DELETE FROM historial_cambio_material_smt")
        print("🗑️ Datos anteriores eliminados")
        
        # Generar datos de prueba para hoy
        today = datetime.now()
        scan_date = today.strftime('%Y%m%d')
        
        print(f"📝 Insertando datos de prueba para {scan_date}...")
        
        # Datos base
        lineas = ['1LINE', '2LINE', '3LINE']
        maquinas = ['L1M1', 'L1M2', 'L2M1', 'L2M2']
        results = ['OK', 'NG']
        part_names = ['R0603_100R', 'C0603_100nF', 'IC_STM32F103']
        vendors = ['SAMSUNG', 'MURATA', 'ST']
        
        sample_data = []
        
        for i in range(50):  # 50 registros de prueba
            hour = random.randint(8, 17)
            minute = random.randint(0, 59)
            second = random.randint(0, 59)
            scan_time = f"{hour:02d}:{minute:02d}:{second:02d}"
            
            linea = random.choice(lineas)
            maquina = random.choice(maquinas)
            result = random.choices(results, weights=[80, 20])[0]
            part_name = random.choice(part_names)
            vendor = random.choice(vendors)
            
            record = (
                linea,  # linea
                maquina,  # maquina
                f"{scan_date}_{linea}.csv",  # archivo
                scan_date,  # ScanDate
                scan_time,  # ScanTime
                random.randint(1, 48),  # SlotNo
                result,  # Result
                f"PBC{random.randint(100000, 999999)}" if random.random() > 0.5 else "",  # PreviousBarcode
                scan_date,  # Productdate
                part_name,  # PartName
                random.randint(1, 5),  # Quantity
                f"SEQ{i+1:03d}",  # SEQ
                vendor,  # Vendor
                f"LOT{scan_date}{random.randint(1000, 9999)}",  # LOTNO
                f"BC{scan_date}{random.randint(100000, 999999)}",  # Barcode
                f"FB{random.randint(1, 20)}" if random.random() > 0.3 else ""  # FeederBase
            )
            sample_data.append(record)
        
        # Insertar datos
        insert_query = """
            INSERT INTO historial_cambio_material_smt 
            (linea, maquina, archivo, ScanDate, ScanTime, SlotNo, Result,
             PreviousBarcode, Productdate, PartName, Quantity, SEQ, Vendor,
             LOTNO, Barcode, FeederBase)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        cursor.executemany(insert_query, sample_data)
        
        print(f"✅ Insertados {len(sample_data)} registros")
        
        # Verificar
        cursor.execute("SELECT COUNT(*) FROM historial_cambio_material_smt")
        count = cursor.fetchone()[0]
        print(f"📊 Total registros: {count}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    if insert_sample_data():
        print("\n🎉 Datos de prueba insertados correctamente")
        print("▶️ Ahora puedes:")
        print("1. Reiniciar el servidor: python run.py")
        print("2. Ir a: http://127.0.0.1:5000/smt/historial")
        print("3. Verificar que se muestren los datos")
    else:
        print("\n❌ Error insertando datos de prueba")
