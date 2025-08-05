#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para corregir foreign keys y recrear tabla SMT con datos de prueba
"""

import mysql.connector
import logging
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

def fix_foreign_keys():
    """Corregir foreign keys agregando índices faltantes"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("🔧 Corrigiendo foreign keys...")
        
        # 1. Agregar índice a la tabla materiales si no existe
        print("📋 Verificando índice en tabla materiales...")
        
        try:
            cursor.execute("""
                ALTER TABLE materiales 
                ADD INDEX idx_numero_parte (numero_parte)
            """)
            print("✅ Índice agregado a tabla materiales")
        except mysql.connector.Error as e:
            if "Duplicate key name" in str(e):
                print("ℹ️ Índice ya existe en tabla materiales")
            else:
                print(f"⚠️ Error agregando índice: {e}")
        
        # 2. Recrear las tablas problemáticas sin foreign keys primero
        print("\n🗑️ Eliminando tablas problemáticas...")
        
        tables_to_recreate = ['inventario', 'movimientos_inventario', 'bom']
        for table in tables_to_recreate:
            try:
                cursor.execute(f"DROP TABLE IF EXISTS {table}")
                print(f"✅ Tabla {table} eliminada")
            except Exception as e:
                print(f"⚠️ Error eliminando {table}: {e}")
        
        # 3. Recrear tablas con foreign keys correctas
        print("\n🏗️ Recreando tablas...")
        
        # Tabla inventario
        cursor.execute("""
            CREATE TABLE inventario (
                id INT AUTO_INCREMENT PRIMARY KEY,
                numero_parte VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
                cantidad_actual INT DEFAULT 0,
                ultima_actualizacion DATETIME DEFAULT NOW(),
                INDEX idx_numero_parte_inv (numero_parte),
                FOREIGN KEY (numero_parte) REFERENCES materiales(numero_parte) ON DELETE CASCADE ON UPDATE CASCADE
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        """)
        print("✅ Tabla inventario recreada")
        
        # Tabla movimientos_inventario
        cursor.execute("""
            CREATE TABLE movimientos_inventario (
                id INT AUTO_INCREMENT PRIMARY KEY,
                numero_parte VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
                tipo_movimiento VARCHAR(50) NOT NULL,
                cantidad INT NOT NULL,
                comentarios TEXT,
                fecha_movimiento DATETIME DEFAULT NOW(),
                usuario VARCHAR(255),
                INDEX idx_numero_parte_mov (numero_parte),
                FOREIGN KEY (numero_parte) REFERENCES materiales(numero_parte) ON DELETE CASCADE ON UPDATE CASCADE
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        """)
        print("✅ Tabla movimientos_inventario recreada")
        
        # Tabla bom
        cursor.execute("""
            CREATE TABLE bom (
                id INT AUTO_INCREMENT PRIMARY KEY,
                modelo VARCHAR(255) NOT NULL,
                numero_parte VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
                descripcion TEXT,
                cantidad INT DEFAULT 1,
                side VARCHAR(50),
                ubicacion VARCHAR(255),
                categoria VARCHAR(255),
                proveedor VARCHAR(255),
                fecha_registro DATETIME DEFAULT NOW(),
                INDEX idx_numero_parte_bom (numero_parte),
                UNIQUE KEY unique_bom (modelo, numero_parte, side),
                FOREIGN KEY (numero_parte) REFERENCES materiales(numero_parte) ON DELETE CASCADE ON UPDATE CASCADE
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        """)
        print("✅ Tabla bom recreada")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("\n✅ Foreign keys corregidos exitosamente")
        return True
        
    except Exception as e:
        print(f"❌ Error corrigiendo foreign keys: {e}")
        return False

def recreate_smt_table():
    """Recrear tabla SMT con datos de prueba"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("\n🗑️ Eliminando tabla SMT existente...")
        cursor.execute("DROP TABLE IF EXISTS historial_cambio_material_smt")
        
        print("🏗️ Creando tabla SMT con estructura correcta...")
        cursor.execute("""
            CREATE TABLE historial_cambio_material_smt (
                id INT AUTO_INCREMENT PRIMARY KEY,
                linea VARCHAR(32),
                maquina VARCHAR(32),
                archivo VARCHAR(128),
                ScanDate VARCHAR(20),
                ScanTime VARCHAR(20),
                SlotNo INT,
                Result VARCHAR(20),
                PreviousBarcode VARCHAR(128),
                Productdate VARCHAR(32),
                PartName VARCHAR(64),
                Quantity INT,
                SEQ VARCHAR(32),
                Vendor VARCHAR(64),
                LOTNO VARCHAR(255),
                Barcode VARCHAR(255),
                FeederBase VARCHAR(20),
                fecha_subida TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_scan_date (ScanDate),
                INDEX idx_linea (linea),
                INDEX idx_maquina (maquina),
                INDEX idx_result (Result)
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        """)
        
        print("✅ Tabla SMT creada")
        
        # Insertar datos de prueba
        print("\n📝 Insertando datos de prueba...")
        
        # Generar datos para los últimos 7 días
        today = datetime.now()
        sample_data = []
        
        lineas = ['1LINE', '2LINE', '3LINE']
        maquinas = ['L1M1', 'L1M2', 'L2M1', 'L2M2', 'L3M1', 'L3M2']
        results = ['OK', 'NG']
        part_names = ['R0603_100R', 'C0603_100nF', 'IC_STM32F103', 'LED_RED_0805']
        vendors = ['SAMSUNG', 'MURATA', 'ST', 'OSRAM']
        
        for day_offset in range(7):
            date = today - timedelta(days=day_offset)
            scan_date = date.strftime('%Y%m%d')
            
            # Generar 50-100 registros por día
            num_records = random.randint(50, 100)
            
            for i in range(num_records):
                # Hora aleatoria del día
                hour = random.randint(6, 22)
                minute = random.randint(0, 59)
                second = random.randint(0, 59)
                scan_time = f"{hour:02d}:{minute:02d}:{second:02d}"
                
                # Datos aleatorios
                linea = random.choice(lineas)
                maquina = random.choice(maquinas)
                slot_no = random.randint(1, 48)
                result = random.choices(results, weights=[85, 15])[0]  # 85% OK, 15% NG
                part_name = random.choice(part_names)
                vendor = random.choice(vendors)
                quantity = random.randint(1, 10)
                seq = f"SEQ{i+1:04d}"
                lotno = f"LOT{scan_date}{random.randint(1000, 9999)}"
                barcode = f"BC{scan_date}{random.randint(100000, 999999)}"
                previous_barcode = f"PBC{random.randint(100000, 999999)}" if random.random() > 0.3 else ""
                feeder_base = f"FB{random.randint(1, 20)}" if random.random() > 0.4 else ""
                archivo = f"{scan_date}_{linea}_{maquina}.csv"
                
                sample_data.append((
                    linea, maquina, archivo, scan_date, scan_time, slot_no, result,
                    previous_barcode, scan_date, part_name, quantity, seq, vendor,
                    lotno, barcode, feeder_base
                ))
        
        # Insertar en lotes
        insert_query = """
            INSERT INTO historial_cambio_material_smt 
            (linea, maquina, archivo, ScanDate, ScanTime, SlotNo, Result,
             PreviousBarcode, Productdate, PartName, Quantity, SEQ, Vendor,
             LOTNO, Barcode, FeederBase)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        cursor.executemany(insert_query, sample_data)
        conn.commit()
        
        print(f"✅ Insertados {len(sample_data)} registros de prueba")
        
        # Verificar inserción
        cursor.execute("SELECT COUNT(*) FROM historial_cambio_material_smt")
        count = cursor.fetchone()[0]
        print(f"📊 Total de registros en tabla: {count}")
        
        # Mostrar muestra de datos
        cursor.execute("""
            SELECT linea, maquina, ScanDate, Result, PartName, LOTNO 
            FROM historial_cambio_material_smt 
            ORDER BY ScanDate DESC, ScanTime DESC 
            LIMIT 5
        """)
        sample = cursor.fetchall()
        
        print("\n📋 Muestra de datos insertados:")
        for row in sample:
            print(f"  {row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]} | {row[5]}")
        
        cursor.close()
        conn.close()
        
        print("\n✅ Tabla SMT recreada exitosamente con datos de prueba")
        return True
        
    except Exception as e:
        print(f"❌ Error recreando tabla SMT: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Función principal"""
    print("🚀 Iniciando corrección de base de datos...")
    
    # 1. Corregir foreign keys
    if fix_foreign_keys():
        print("\n" + "="*50)
        
        # 2. Recrear tabla SMT
        if recreate_smt_table():
            print("\n🎉 Corrección completada exitosamente!")
            print("\n📝 Próximos pasos:")
            print("1. Reinicia el servidor Flask")
            print("2. Ve a http://127.0.0.1:5000/smt/historial") 
            print("3. Verifica que se muestren los datos de prueba")
            print("4. Prueba los filtros de línea y máquina")
        else:
            print("\n❌ Error recreando tabla SMT")
    else:
        print("\n❌ Error corrigiendo foreign keys")

if __name__ == "__main__":
    main()
