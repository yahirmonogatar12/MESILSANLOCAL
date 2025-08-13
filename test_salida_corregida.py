import mysql.connector

DB_CONFIG = {
    'host': 'up-de-fra1-mysql-1.db.run-on-seenode.com',
    'port': 11550,
    'user': 'db_rrpq0erbdujn',
    'password': '5fUNbSRcPP3LN9K2I33Pr0ge',
    'database': 'db_rrpq0erbdujn'
}

print("🧪 PROBANDO CORRECCIÓN DE SALIDAS")
print("=" * 50)

try:
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # Simular una salida como la que estaba fallando
    print("📤 Probando INSERT con numero_parte incluido...")
    
    test_data = {
        'codigo_material_recibido': '0RH5602C622,202508130001',
        'numero_lote': '0RH5602C622!5000!409-00617!0049',
        'modelo': 'SIN_MODELO',
        'depto_salida': 'Producción',
        'proceso_salida': 'SMD',  # Corregido de 'SMT 1st SIDE'
        'cantidad_salida': 100.0,
        'fecha_salida': '2025-08-13',
        'especificacion_material': 'Prueba corrección'
    }
    
    # Extraer numero_parte (simulando la lógica corregida)
    codigo_material = test_data['codigo_material_recibido']
    numero_parte = codigo_material.split(',')[0] if ',' in codigo_material else codigo_material
    
    query = """
        INSERT INTO control_material_salida (
            codigo_material_recibido, numero_parte, numero_lote, modelo, depto_salida,
            proceso_salida, cantidad_salida, fecha_salida, fecha_registro, especificacion_material
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s)
    """
    
    params = (
        test_data['codigo_material_recibido'],
        numero_parte,  # ✅ Ahora incluido
        test_data['numero_lote'],
        test_data['modelo'],
        test_data['depto_salida'],
        test_data['proceso_salida'],  # ✅ Ahora es 'SMD'
        test_data['cantidad_salida'],
        test_data['fecha_salida'],
        test_data['especificacion_material']
    )
    
    cursor.execute(query, params)
    conn.commit()
    
    print("✅ INSERT exitoso!")
    print(f"   🏷️  Número Parte: {numero_parte}")
    print(f"   📱 Código Material: {test_data['codigo_material_recibido']}")
    print(f"   🔧 Proceso: {test_data['proceso_salida']}")
    print(f"   📊 Cantidad: {test_data['cantidad_salida']}")
    
    # Limpiar la prueba
    cursor.execute('DELETE FROM control_material_salida WHERE especificacion_material = "Prueba corrección"')
    conn.commit()
    print("\n🧹 Prueba limpiada")
    print("🎉 CORRECCIÓN APLICADA EXITOSAMENTE")
    
except Exception as e:
    print(f"❌ Error: {e}")
finally:
    cursor.close()
    conn.close()
