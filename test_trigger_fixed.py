import mysql.connector

DB_CONFIG = {
    'host': 'up-de-fra1-mysql-1.db.run-on-seenode.com',
    'port': 11550,
    'user': 'db_rrpq0erbdujn',
    'password': '5fUNbSRcPP3LN9K2I33Pr0ge',
    'database': 'db_rrpq0erbdujn'
}

print("🧪 PROBANDO TRIGGER CORREGIDO")
print("=" * 50)

try:
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # Crear una entrada de prueba en almacén SMD
    print("📤 Creando entrada de prueba SMD...")
    
    test_entry = {
        'codigo_material_recibido': 'CODIGO_REAL_TRAZABILIDAD_001',
        'numero_parte': 'TEST_PARTE_NUEVA',
        'numero_lote_material': 'LOTE_TEST_001',
        'cantidad_actual': 500,
        'propiedad_material': 'SMD',
        'especificacion': 'Prueba trigger corregido'
    }
    
    insert_query = """
        INSERT INTO control_material_almacen (
            codigo_material_recibido, numero_parte, numero_lote_material, 
            cantidad_actual, propiedad_material, especificacion, fecha_recibo
        ) VALUES (%s, %s, %s, %s, %s, %s, NOW())
    """
    
    cursor.execute(insert_query, (
        test_entry['codigo_material_recibido'],
        test_entry['numero_parte'],
        test_entry['numero_lote_material'],
        test_entry['cantidad_actual'],
        test_entry['propiedad_material'],
        test_entry['especificacion']
    ))
    
    almacen_id = cursor.lastrowid
    conn.commit()
    
    print(f"✅ Entrada creada en almacén ID: {almacen_id}")
    
    # Verificar que el trigger distribuyó a SMD con código correcto
    print("🔍 Verificando distribución automática a SMD...")
    
    cursor.execute("""
        SELECT numero_parte, codigo_barras, movimiento_origen_id
        FROM InventarioRollosSMD 
        WHERE movimiento_origen_id = %s
    """, (almacen_id,))
    
    smd_entry = cursor.fetchone()
    
    if smd_entry:
        numero_parte, codigo_barras, origen_id = smd_entry
        print("✅ Distribución automática exitosa!")
        print(f"   🏷️  Número Parte: {numero_parte}")
        print(f"   📱 Código Barras: {codigo_barras}")
        print(f"   🔗 Origen ID: {origen_id}")
        
        # Verificar que el código de barras es el correcto
        codigo_esperado = test_entry['codigo_material_recibido']
        if codigo_barras == codigo_esperado:
            print("🎉 ¡ÉXITO! Código de barras = Código material recibido")
            print("✅ Trazabilidad correcta establecida")
        else:
            print("❌ PROBLEMA: Códigos no coinciden")
            print(f"   Esperado: {codigo_esperado}")
            print(f"   Obtenido: {codigo_barras}")
    else:
        print("❌ No se encontró distribución automática")
    
    # Limpiar la prueba
    print("\n🧹 Limpiando prueba...")
    cursor.execute("DELETE FROM InventarioRollosSMD WHERE movimiento_origen_id = %s", (almacen_id,))
    cursor.execute("DELETE FROM control_material_almacen WHERE id = %s", (almacen_id,))
    conn.commit()
    
    print("🎯 PRUEBA COMPLETADA")

except Exception as e:
    print(f"❌ Error: {e}")
finally:
    cursor.close()
    conn.close()
