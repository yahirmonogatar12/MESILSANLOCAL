#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Recrear tabla SMT simple y compatible
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

def recreate_simple_table():
    """Recrear tabla SMT simple y básica"""
    try:
        print("🔗 Conectando a MySQL...")
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Eliminar tabla existente
        print("🗑️ Eliminando tabla anterior...")
        cursor.execute("DROP TABLE IF EXISTS historial_cambio_material_smt")
        
        # Crear tabla simple y básica
        print("🏗️ Creando tabla simple...")
        cursor.execute("""
            CREATE TABLE historial_cambio_material_smt (
                id INT AUTO_INCREMENT PRIMARY KEY,
                fecha DATE NOT NULL,
                hora TIME NOT NULL,
                linea VARCHAR(50),
                maquina VARCHAR(50),
                resultado VARCHAR(20),
                componente VARCHAR(100),
                cantidad INT DEFAULT 1,
                lote VARCHAR(100),
                codigo_barras VARCHAR(200),
                archivo VARCHAR(200),
                observaciones TEXT,
                fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        
        print("✅ Tabla creada exitosamente")
        
        # Insertar datos simples de prueba
        print("📝 Insertando datos de prueba...")
        
        today = datetime.now().date()
        sample_data = []
        
        for i in range(100):  # 100 registros
            day_offset = random.randint(0, 7)  # Últimos 7 días
            fecha = today - timedelta(days=day_offset)
            hora = f"{random.randint(8, 17):02d}:{random.randint(0, 59):02d}:{random.randint(0, 59):02d}"
            
            record = (
                fecha,
                hora,
                random.choice(['1LINE', '2LINE', '3LINE']),
                random.choice(['L1M1', 'L1M2', 'L2M1', 'L2M2']),
                random.choice(['OK', 'NG']),
                random.choice(['R0603_100R', 'C0603_100nF', 'IC_STM32F103', 'LED_RED_0805']),
                random.randint(1, 10),
                f"LOTE{fecha.strftime('%Y%m%d')}{i:03d}",
                f"BC{fecha.strftime('%Y%m%d')}{i:06d}",
                f"{fecha.strftime('%Y%m%d')}_datos.csv",
                f"Registro automatico {i+1}"
            )
            sample_data.append(record)
        
        insert_query = """
            INSERT INTO historial_cambio_material_smt 
            (fecha, hora, linea, maquina, resultado, componente, cantidad, 
             lote, codigo_barras, archivo, observaciones)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        cursor.executemany(insert_query, sample_data)
        conn.commit()
        
        print(f"✅ Insertados {len(sample_data)} registros")
        
        # Verificar
        cursor.execute("SELECT COUNT(*) FROM historial_cambio_material_smt")
        count = cursor.fetchone()[0]
        print(f"📊 Total de registros: {count}")
        
        # Mostrar muestra
        cursor.execute("""
            SELECT fecha, hora, linea, maquina, resultado, componente 
            FROM historial_cambio_material_smt 
            ORDER BY fecha DESC, hora DESC 
            LIMIT 5
        """)
        muestra = cursor.fetchall()
        
        print("\n📋 Muestra de datos:")
        for row in muestra:
            print(f"  {row[0]} {row[1]} | {row[2]} | {row[3]} | {row[4]} | {row[5]}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Recreando tabla SMT simple...")
    if recreate_simple_table():
        print("\n🎉 Tabla recreada exitosamente!")
        print("✅ Estructura simple y compatible")
        print("✅ 100 registros de prueba insertados")
        print("✅ Sin filtros complicados")
    else:
        print("\n❌ Error recreando tabla")
