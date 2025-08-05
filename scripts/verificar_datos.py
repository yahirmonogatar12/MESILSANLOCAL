#!/usr/bin/env python3
"""
Script para verificar los datos en la base de datos
"""

import mysql.connector

# Configuración de base de datos
DB_CONFIG = {
    'host': 'up-de-fra1-mysql-1.db.run-on-seenode.com',
    'port': 11550,
    'user': 'db_rrpq0erbdujn',
    'password': '5fUNbSRcPP3LN9K2I33Pr0ge',
    'database': 'db_rrpq0erbdujn',
    'charset': 'utf8mb4'
}

def verificar_datos():
    """Verifica los datos insertados"""
    connection = None
    cursor = None
    
    try:
        print("Conectando a la base de datos...")
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()
        
        # Contar total de registros
        cursor.execute('SELECT COUNT(*) FROM historial_cambio_material_smt')
        total = cursor.fetchone()[0]
        print(f"✅ Total registros: {total}")
        
        # Mostrar estadísticas
        cursor.execute("""
            SELECT 
                result,
                COUNT(*) as cantidad
            FROM historial_cambio_material_smt 
            GROUP BY result
        """)
        stats = cursor.fetchall()
        print("\n📊 Estadísticas por resultado:")
        for stat in stats:
            print(f"  {stat[0]}: {stat[1]} registros")
        
        # Mostrar por línea y mounter
        cursor.execute("""
            SELECT 
                line_number,
                mounter_number,
                COUNT(*) as cantidad,
                MAX(created_at) as ultimo_registro
            FROM historial_cambio_material_smt 
            GROUP BY line_number, mounter_number
            ORDER BY line_number, mounter_number
        """)
        lines = cursor.fetchall()
        print("\n🏭 Registros por línea y mounter:")
        for line in lines:
            print(f"  Línea {line[0]} - Mounter {line[1]}: {line[2]} registros (último: {line[3]})")
        
        # Mostrar algunos registros de ejemplo
        cursor.execute("""
            SELECT 
                scan_date, scan_time, result, part_name, line_number, mounter_number
            FROM historial_cambio_material_smt 
            ORDER BY created_at DESC 
            LIMIT 5
        """)
        samples = cursor.fetchall()
        print("\n📋 Últimos 5 registros:")
        for sample in samples:
            print(f"  {sample[0]} {sample[1]} | {sample[2]} | {sample[3]} | L{sample[4]}-M{sample[5]}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

if __name__ == "__main__":
    verificar_datos()
