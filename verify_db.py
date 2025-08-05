#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verificación rápida de conexión a la base de datos
"""

import mysql.connector

# Configuración MySQL
DB_CONFIG = {
    'host': 'up-de-fra1-mysql-1.db.run-on-seenode.com',
    'port': 11550,
    'user': 'db_rrpq0erbdujn',
    'password': '5fUNbSRcPP3LN9K2I33Pr0ge',
    'database': 'db_rrpq0erbdujn',
    'charset': 'utf8mb4'
}

try:
    print("🔗 Conectando a la base de datos...")
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    print("✅ Conexión exitosa")
    
    # Verificar tablas existentes
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()
    
    print(f"\n📋 Tablas disponibles ({len(tables)}):")
    for table in tables:
        print(f"  - {table[0]}")
    
    # Verificar si la tabla SMT existe y tiene datos
    if ('historial_cambio_material_smt',) in tables:
        cursor.execute("SELECT COUNT(*) FROM historial_cambio_material_smt")
        count = cursor.fetchone()[0]
        print(f"\n📊 Registros en tabla SMT: {count}")
        
        if count > 0:
            cursor.execute("SELECT linea, maquina, ScanDate, Result FROM historial_cambio_material_smt LIMIT 3")
            sample = cursor.fetchall()
            print("\n🔍 Muestra de datos:")
            for row in sample:
                print(f"  {row[0]} | {row[1]} | {row[2]} | {row[3]}")
    
    cursor.close()
    conn.close()
    
    print("\n✅ Verificación completada")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
