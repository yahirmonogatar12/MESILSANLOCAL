import mysql.connector

DB_CONFIG = {
    'host': 'up-de-fra1-mysql-1.db.run-on-seenode.com',
    'port': 11550,
    'user': 'db_rrpq0erbdujn',
    'password': '5fUNbSRcPP3LN9K2I33Pr0ge',
    'database': 'db_rrpq0erbdujn'
}

try:
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # Verificar tabla InventarioRollosSMD
    print("🔍 VERIFICANDO TABLA InventarioRollosSMD")
    cursor.execute("SHOW TABLES LIKE 'InventarioRollosSMD'")
    resultado = cursor.fetchall()
    
    if resultado:
        print("✅ Tabla InventarioRollosSMD existe")
        
        # Ver estructura
        cursor.execute("""
            SELECT COLUMN_NAME, DATA_TYPE 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = 'db_rrpq0erbdujn' 
            AND TABLE_NAME = 'InventarioRollosSMD'
            ORDER BY ORDINAL_POSITION
        """)
        
        columnas = cursor.fetchall()
        print("📋 Columnas de InventarioRollosSMD:")
        for col in columnas:
            print(f"   🏷️ {col[0]} ({col[1]})")
    else:
        print("❌ Tabla InventarioRollosSMD NO existe")
        print("💡 Verificando control_material_almacen para SMD...")
        
        cursor.execute("""
            SELECT numero_parte, codigo_material, especificacion
            FROM control_material_almacen 
            WHERE propiedad_material = 'SMD'
            LIMIT 2
        """)
        
        datos = cursor.fetchall()
        print("📋 Ejemplo de datos SMD en control_material_almacen:")
        for row in datos:
            print(f"   🔧 Número Parte: {row[0]}")
            print(f"   📱 Código Material: {row[1]}")
            print(f"   📄 Especificación: {row[2]}")
            print("   " + "-"*40)

except Exception as e:
    print(f"❌ Error: {e}")
finally:
    cursor.close()
    conn.close()
