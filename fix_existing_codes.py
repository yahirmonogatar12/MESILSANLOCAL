import mysql.connector

DB_CONFIG = {
    'host': 'up-de-fra1-mysql-1.db.run-on-seenode.com',
    'port': 11550,
    'user': 'db_rrpq0erbdujn',
    'password': '5fUNbSRcPP3LN9K2I33Pr0ge',
    'database': 'db_rrpq0erbdujn'
}

print("🔧 CORRIGIENDO CÓDIGOS EXISTENTES EN INVENTARIO SMD")
print("=" * 60)

try:
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # Buscar rollos con códigos AUTO_SMD que tienen origen
    cursor.execute("""
        SELECT id, numero_parte, codigo_barras, movimiento_origen_id
        FROM InventarioRollosSMD 
        WHERE codigo_barras LIKE 'AUTO_SMD%' 
        AND movimiento_origen_id IS NOT NULL
    """)
    
    rollos_auto = cursor.fetchall()
    print(f"📋 Encontrados {len(rollos_auto)} rollos con códigos AUTO_SMD:")
    
    correcciones = 0
    
    for rollo in rollos_auto:
        id_rollo, numero_parte, codigo_auto, mov_origen = rollo
        
        # Buscar el código real en control_material_almacen
        cursor.execute("""
            SELECT codigo_material_recibido
            FROM control_material_almacen 
            WHERE id = %s
        """, (mov_origen,))
        
        origen = cursor.fetchone()
        if origen:
            codigo_real = origen[0]
            
            print(f"\n🔄 Corrigiendo rollo ID {id_rollo}:")
            print(f"   🏷️  Número Parte: {numero_parte}")
            print(f"   ❌ Código AUTO: {codigo_auto}")
            print(f"   ✅ Código Real: {codigo_real}")
            
            # Actualizar el código de barras
            cursor.execute("""
                UPDATE InventarioRollosSMD 
                SET codigo_barras = %s,
                    actualizado_en = NOW()
                WHERE id = %s
            """, (codigo_real, id_rollo))
            
            correcciones += 1
            print(f"   ✅ Actualizado")
        else:
            print(f"\n⚠️  Rollo ID {id_rollo}: No se encontró origen")
    
    conn.commit()
    
    print(f"\n🎉 CORRECCIONES COMPLETADAS:")
    print(f"   ✅ {correcciones} rollos corregidos")
    print(f"   📱 Ahora todos usan códigos reales para trazabilidad")
    
    # Verificar los resultados
    print(f"\n🔍 VERIFICACIÓN FINAL:")
    cursor.execute("""
        SELECT id, numero_parte, codigo_barras
        FROM InventarioRollosSMD 
        WHERE numero_parte != 'SISTEMA_INIT'
        ORDER BY id DESC
        LIMIT 5
    """)
    
    rollos_final = cursor.fetchall()
    for rollo in rollos_final:
        id_r, num_parte, codigo = rollo
        print(f"   📦 ID {id_r}: {num_parte} → {codigo}")
        if 'AUTO_SMD' in codigo:
            print(f"      ⚠️  Aún tiene código automático")
        else:
            print(f"      ✅ Código real de trazabilidad")

except Exception as e:
    print(f"❌ Error: {e}")
finally:
    cursor.close()
    conn.close()
