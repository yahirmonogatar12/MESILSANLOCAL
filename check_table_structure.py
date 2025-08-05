#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Revisar estructura real de la tabla SMT
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

def check_table_structure():
    """Revisar estructura real de la tabla"""
    try:
        print("🔗 Conectando a MySQL...")
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Verificar si la tabla existe
        cursor.execute("SHOW TABLES LIKE 'historial_cambio_material_smt'")
        if not cursor.fetchone():
            print("❌ La tabla historial_cambio_material_smt no existe")
            return False
        
        # Obtener estructura de la tabla
        print("📋 Estructura de la tabla historial_cambio_material_smt:")
        cursor.execute("DESCRIBE historial_cambio_material_smt")
        columns = cursor.fetchall()
        
        print("\n🗂️ Columnas disponibles:")
        for i, (column, type_info, null, key, default, extra) in enumerate(columns, 1):
            print(f"  {i:2d}. {column:<20} | {type_info:<15} | NULL: {null}")
        
        # Contar registros
        cursor.execute("SELECT COUNT(*) FROM historial_cambio_material_smt")
        count = cursor.fetchone()[0]
        print(f"\n📊 Total de registros: {count}")
        
        if count > 0:
            # Mostrar muestra de datos
            print("\n📋 Muestra de datos (primeros 3 registros):")
            cursor.execute("SELECT * FROM historial_cambio_material_smt LIMIT 3")
            sample = cursor.fetchall()
            
            column_names = [desc[0] for desc in cursor.description]
            print(f"\nColumnas: {', '.join(column_names)}")
            
            for i, row in enumerate(sample, 1):
                print(f"\nRegistro {i}:")
                for col_name, value in zip(column_names, row):
                    print(f"  {col_name}: {value}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔍 Revisando estructura de tabla SMT...")
    check_table_structure()
