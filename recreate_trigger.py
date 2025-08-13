import mysql.connector

DB_CONFIG = {
    'host': 'up-de-fra1-mysql-1.db.run-on-seenode.com',
    'port': 11550,
    'user': 'db_rrpq0erbdujn',
    'password': '5fUNbSRcPP3LN9K2I33Pr0ge',
    'database': 'db_rrpq0erbdujn'
}

print("🔧 RECREANDO TRIGGER CORRECTO PARA TRAZABILIDAD")
print("=" * 60)

try:
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    print("🗑️ Eliminando triggers existentes...")
    cursor.execute("DROP TRIGGER IF EXISTS tr_entrada_insert")
    cursor.execute("DROP TRIGGER IF EXISTS tr_actualizar_inventario_entrada") 
    cursor.execute("DROP TRIGGER IF EXISTS tr_actualizar_inventario_update")
    
    print("🔧 Creando trigger correcto...")
    
    trigger_sql = """
    CREATE TRIGGER tr_smd_distribucion_corregido
    AFTER INSERT ON control_material_almacen
    FOR EACH ROW
    BEGIN
        IF NEW.propiedad_material = 'SMD' THEN
            INSERT INTO InventarioRollosSMD (
                numero_parte, codigo_barras, lote, cantidad_inicial, cantidad_actual,
                area_smd, fecha_entrada, estado, movimiento_origen_id,
                usuario_responsable, creado_en, actualizado_en
            ) VALUES (
                NEW.numero_parte,
                NEW.codigo_material_recibido,
                NEW.numero_lote_material,
                NEW.cantidad_actual,
                NEW.cantidad_actual,
                'SMD_PRODUCTION',
                NEW.fecha_recibo,
                'ACTIVO',
                NEW.id,
                'SISTEMA_AUTO',
                NOW(),
                NOW()
            );
        END IF;
    END
    """
    
    cursor.execute(trigger_sql)
    conn.commit()
    
    print("✅ Trigger creado exitosamente!")
    print("\n🎯 CARACTERÍSTICAS DEL NUEVO TRIGGER:")
    print("   📱 codigo_barras = NEW.codigo_material_recibido")
    print("   🏷️  numero_parte = NEW.numero_parte")
    print("   🚫 NO genera códigos AUTO_SMD")
    print("   ✅ Usa códigos reales para trazabilidad")
    
    # Verificar trigger
    cursor.execute("SHOW TRIGGERS")
    triggers = cursor.fetchall()
    
    print(f"\n📋 TRIGGERS ACTIVOS:")
    for t in triggers:
        if 'control_material_almacen' in t[2]:
            print(f"   🔧 {t[0]} - {t[1]} {t[2]}")

except Exception as e:
    print(f"❌ Error: {e}")
finally:
    cursor.close()
    conn.close()
