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
    
    print("🔍 ANALIZANDO RELACIÓN SMD CON ALMACÉN")
    print("="*50)
    
    # Verificar algunos datos de ejemplo de InventarioRollosSMD
    cursor.execute("""
        SELECT id, numero_parte, codigo_barras, movimiento_origen_id, lote
        FROM InventarioRollosSMD 
        LIMIT 3
    """)
    
    rollos_smd = cursor.fetchall()
    print("📦 DATOS ACTUALES EN InventarioRollosSMD:")
    for rollo in rollos_smd:
        print(f"   🆔 ID: {rollo[0]}")
        print(f"   🏷️ Número Parte: {rollo[1]}")
        print(f"   📱 Código Barras: {rollo[2]}")
        print(f"   🔗 Movimiento Origen: {rollo[3]}")
        print(f"   📦 Lote: {rollo[4]}")
        print("   " + "-"*40)
    
    # Si hay movimiento_origen_id, verificar la relación
    if rollos_smd and rollos_smd[0][3]:
        mov_id = rollos_smd[0][3]
        print(f"\n🔗 VERIFICANDO RELACIÓN CON MOVIMIENTO {mov_id}:")
        
        cursor.execute("""
            SELECT numero_parte, codigo_material, especificacion, lote
            FROM control_material_almacen 
            WHERE id = %s
        """, (mov_id,))
        
        origen = cursor.fetchone()
        if origen:
            print(f"   🏷️ Número Parte Origen: {origen[0]}")
            print(f"   📱 Código Material Origen: {origen[1]}")
            print(f"   📄 Especificación: {origen[2]}")
            print(f"   📦 Lote Origen: {origen[3]}")
        else:
            print("   ❌ No se encontró el movimiento origen")
    
    # Verificar si codigo_barras es realmente el codigo_material_recibido
    print(f"\n💡 ANÁLISIS:")
    print(f"   • codigo_barras en SMD: ¿Es el código único para escaneo?")
    print(f"   • numero_parte en SMD: ¿Es el número de parte real?")
    print(f"   • Necesidad: codigo_material_recibido único para SMounter")

except Exception as e:
    print(f"❌ Error: {e}")
finally:
    cursor.close()
    conn.close()
