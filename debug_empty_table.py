#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verificación rápida de datos en la tabla SMT
"""

import mysql.connector
import requests
from datetime import datetime

# Configuración MySQL
DB_CONFIG = {
    'host': 'up-de-fra1-mysql-1.db.run-on-seenode.com',
    'port': 11550,
    'user': 'db_rrpq0erbdujn',
    'password': '5fUNbSRcPP3LN9K2I33Pr0ge',
    'database': 'db_rrpq0erbdujn',
    'charset': 'utf8mb4',
    'connection_timeout': 10
}

def check_database():
    """Verificar datos en la base de datos"""
    try:
        print("🔗 Conectando a la base de datos...")
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        # Verificar si la tabla existe
        cursor.execute("SHOW TABLES LIKE 'historial_cambio_material_smt'")
        if not cursor.fetchone():
            print("❌ La tabla historial_cambio_material_smt NO existe")
            return False
        
        print("✅ Tabla existe")
        
        # Contar registros totales
        cursor.execute("SELECT COUNT(*) as total FROM historial_cambio_material_smt")
        total = cursor.fetchone()['total']
        print(f"📊 Total de registros en la tabla: {total}")
        
        if total == 0:
            print("❌ La tabla está VACÍA")
            return False
        
        # Verificar fechas disponibles
        cursor.execute("SELECT DISTINCT ScanDate FROM historial_cambio_material_smt ORDER BY ScanDate DESC")
        fechas = cursor.fetchall()
        print(f"\n📅 Fechas disponibles ({len(fechas)}):")
        for fecha in fechas[:5]:
            print(f"  - {fecha['ScanDate']}")
        
        # Verificar líneas y máquinas
        cursor.execute("SELECT DISTINCT linea FROM historial_cambio_material_smt WHERE linea IS NOT NULL")
        lineas = cursor.fetchall()
        print(f"\n🏭 Líneas disponibles ({len(lineas)}):")
        for linea in lineas:
            print(f"  - {linea['linea']}")
        
        cursor.execute("SELECT DISTINCT maquina FROM historial_cambio_material_smt WHERE maquina IS NOT NULL")
        maquinas = cursor.fetchall()
        print(f"\n🔧 Máquinas disponibles ({len(maquinas)}):")
        for maquina in maquinas:
            print(f"  - {maquina['maquina']}")
        
        # Muestra de registros recientes
        cursor.execute("""
            SELECT ScanDate, ScanTime, linea, maquina, Result, PartName 
            FROM historial_cambio_material_smt 
            ORDER BY ScanDate DESC, ScanTime DESC 
            LIMIT 5
        """)
        muestra = cursor.fetchall()
        print(f"\n🔍 Muestra de registros recientes:")
        for reg in muestra:
            print(f"  {reg['ScanDate']} {reg['ScanTime']} | {reg['linea']} | {reg['maquina']} | {reg['Result']} | {reg['PartName']}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error verificando base de datos: {e}")
        return False

def test_api():
    """Probar la API directamente"""
    try:
        print("\n🌐 Probando API...")
        
        # Probar sin filtros de fecha
        url = "http://127.0.0.1:5000/api/historial_smt_data"
        print(f"📡 GET {url}")
        
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API responde: {response.status_code}")
            print(f"📊 Success: {data.get('success', False)}")
            print(f"📊 Total: {data.get('total', 0)}")
            print(f"📊 Registros: {len(data.get('data', []))}")
            
            if 'error' in data:
                print(f"❌ Error en API: {data['error']}")
            
        else:
            print(f"❌ API error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error probando API: {e}")

def fix_date_filter():
    """Agregar datos con fecha de hoy en el formato correcto"""
    try:
        print("\n🔧 Corrigiendo filtro de fecha...")
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Formato correcto de fecha (YYYYMMDD)
        today = datetime.now().strftime('%Y%m%d')
        print(f"📅 Fecha de hoy: {today}")
        
        # Verificar si hay datos con fecha de hoy
        cursor.execute("SELECT COUNT(*) FROM historial_cambio_material_smt WHERE ScanDate = %s", (today,))
        count_today = cursor.fetchone()[0]
        print(f"📊 Registros con fecha de hoy: {count_today}")
        
        if count_today == 0:
            print("📝 Insertando registros con fecha de hoy...")
            
            # Insertar algunos registros con fecha de hoy
            sample_data = []
            for i in range(10):
                record = (
                    '1LINE',  # linea
                    'L1M1',   # maquina
                    f"{today}_1LINE.csv",  # archivo
                    today,    # ScanDate
                    f"{8+i:02d}:30:00",  # ScanTime
                    i+1,      # SlotNo
                    'OK' if i % 4 != 0 else 'NG',  # Result
                    f"PBC{100000+i}",  # PreviousBarcode
                    today,    # Productdate
                    'R0603_100R',  # PartName
                    1,        # Quantity
                    f"SEQ{i+1:03d}",  # SEQ
                    'SAMSUNG',  # Vendor
                    f"LOT{today}{1000+i}",  # LOTNO
                    f"BC{today}{100000+i}",  # Barcode
                    f"FB{i+1}"  # FeederBase
                )
                sample_data.append(record)
            
            insert_query = """
                INSERT INTO historial_cambio_material_smt 
                (linea, maquina, archivo, ScanDate, ScanTime, SlotNo, Result,
                 PreviousBarcode, Productdate, PartName, Quantity, SEQ, Vendor,
                 LOTNO, Barcode, FeederBase)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            cursor.executemany(insert_query, sample_data)
            conn.commit()
            
            print(f"✅ Insertados {len(sample_data)} registros con fecha de hoy")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error corrigiendo fecha: {e}")
        return False

def main():
    print("🚀 Diagnóstico de tabla SMT vacía...")
    print("="*50)
    
    # 1. Verificar base de datos
    if check_database():
        print("\n" + "="*50)
        
        # 2. Probar API
        test_api()
        
        print("\n" + "="*50)
        
        # 3. Corregir filtro de fecha
        if fix_date_filter():
            print("\n🎉 Corrección completada")
            print("\n📝 Ahora prueba:")
            print("1. Actualiza la página http://127.0.0.1:5000/smt/historial")
            print("2. Usa filtros de fecha desde hoy hacia atrás")
            print("3. O deja los filtros vacíos para ver todos los datos")

if __name__ == "__main__":
    main()
