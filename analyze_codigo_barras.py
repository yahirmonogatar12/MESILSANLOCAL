import mysql.connector

DB_CONFIG = {
    'host': 'up-de-fra1-mysql-1.db.run-on-seenode.com',
    'port': 11550,
    'user': 'db_rrpq0erbdujn',
    'password': '5fUNbSRcPP3LN9K2I33Pr0ge',
    'database': 'db_rrpq0erbdujn'
}

print("🔍 ANALIZANDO CÓDIGOS EN INVENTARIO SMD")
print("=" * 60)

try:
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # Ver los rollos actuales y sus códigos
    cursor.execute("""
        SELECT id, numero_parte, codigo_barras, movimiento_origen_id
        FROM InventarioRollosSMD 
        WHERE numero_parte != 'SISTEMA_INIT'
        ORDER BY id DESC
        LIMIT 5
    """)
    
    rollos = cursor.fetchall()
    print("📦 ROLLOS ACTUALES EN INVENTARIO SMD:")
    print("-" * 80)
    
    for rollo in rollos:
        id_rollo, numero_parte, codigo_barras, mov_origen = rollo
        print(f"🆔 ID: {id_rollo}")
        print(f"🏷️  Número Parte: {numero_parte}")
        print(f"📱 Código Barras Actual: {codigo_barras}")
        print(f"🔗 Movimiento Origen: {mov_origen}")
        
        # Si hay movimiento origen, buscar el código_material_recibido real
        if mov_origen:
            cursor.execute("""
                SELECT codigo_material_recibido
                FROM control_material_almacen 
                WHERE id = %s
            """, (mov_origen,))
            
            origen = cursor.fetchone()
            if origen:
                codigo_real = origen[0]
                print(f"🎯 Código Material Recibido Real: {codigo_real}")
                
                if codigo_barras != codigo_real:
                    print("⚠️  PROBLEMA: Código de barras NO coincide con código material recibido")
                else:
                    print("✅ Código de barras coincide con código material recibido")
        else:
            print("🔍 Sin movimiento origen - datos de prueba")
        
        print("-" * 80)
    
    print("\n💡 ANÁLISIS:")
    print("   🎯 El código de barras DEBE ser el código_material_recibido")
    print("   📱 Ese código es el que se escanea para trazabilidad")
    print("   🔍 Verificando si hay inconsistencias...")

except Exception as e:
    print(f"❌ Error: {e}")
finally:
    cursor.close()
    conn.close()
