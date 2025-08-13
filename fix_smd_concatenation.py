import mysql.connector

DB_CONFIG = {
    'host': 'up-de-fra1-mysql-1.db.run-on-seenode.com',
    'port': 11550,
    'user': 'db_rrpq0erbdujn',
    'password': '5fUNbSRcPP3LN9K2I33Pr0ge',
    'database': 'db_rrpq0erbdujn'
}

print("🔧 CORRIGIENDO DATOS CONCATENADOS EN SMD")
print("=" * 50)

try:
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # Buscar datos con concatenación
    cursor.execute("""
        SELECT id, numero_parte, codigo_barras
        FROM InventarioRollosSMD 
        WHERE numero_parte LIKE '%,%'
    """)
    
    concatenados = cursor.fetchall()
    print(f"📋 Encontrados {len(concatenados)} rollos con concatenación:")
    
    for rollo in concatenados:
        id_rollo, numero_parte, codigo_barras = rollo
        print(f"   🆔 ID: {id_rollo}")
        print(f"   ❌ Número concatenado: {numero_parte}")
        
        # Extraer el número de parte real (antes de la coma)
        numero_real = numero_parte.split(',')[0]
        print(f"   ✅ Número correcto: {numero_real}")
        
        # Actualizar
        cursor.execute("""
            UPDATE InventarioRollosSMD 
            SET numero_parte = %s 
            WHERE id = %s
        """, (numero_real, id_rollo))
        
        print(f"   🔄 Actualizado rollo ID {id_rollo}")
        print("   " + "-"*40)
    
    conn.commit()
    print(f"\n✅ Corregidos {len(concatenados)} rollos SMD")
    print("🎯 Ahora todos los números de parte son reales")
    
except Exception as e:
    print(f"❌ Error: {e}")
finally:
    cursor.close()
    conn.close()
