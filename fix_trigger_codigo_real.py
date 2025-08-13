import mysql.connector

DB_CONFIG = {
    'host': 'up-de-fra1-mysql-1.db.run-on-seenode.com',
    'port': 11550,
    'user': 'db_rrpq0erbdujn',
    'password': '5fUNbSRcPP3LN9K2I33Pr0ge',
    'database': 'db_rrpq0erbdujn'
}

print("🔧 CORRIGIENDO TRIGGER PARA USAR CÓDIGO REAL")
print("=" * 60)

try:
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # Eliminar trigger actual
    print("🗑️ Eliminando trigger actual...")
    cursor.execute("DROP TRIGGER IF EXISTS tr_entrada_insert")
    
    # Crear trigger corregido que use codigo_material_recibido
    print("🔧 Creando trigger corregido...")
    
    trigger_sql = """
    CREATE TRIGGER tr_entrada_insert
    AFTER INSERT ON control_material_almacen
    FOR EACH ROW
    BEGIN
        -- Distribución automática a SMD
        IF NEW.propiedad_material = 'SMD' THEN
            INSERT INTO InventarioRollosSMD (
                numero_parte, codigo_barras, lote, cantidad_inicial, cantidad_actual,
                area_smd, fecha_entrada, origen_almacen, estado, movimiento_origen_id,
                usuario_responsable, observaciones, creado_en, actualizado_en
            ) VALUES (
                NEW.numero_parte,
                NEW.codigo_material_recibido,  -- ✅ USA CÓDIGO REAL
                NEW.numero_lote_material,
                NEW.cantidad_actual,
                NEW.cantidad_actual,
                'SMD_PRODUCTION',
                NEW.fecha_recibo,
                CONCAT('Auto-distribución SMD desde entrada ID: ', NEW.id, ' - Parte: ', NEW.numero_parte),
                'ACTIVO',
                NEW.id,
                'SISTEMA_AUTO',
                CONCAT('Auto-distribución SMD desde entrada ID: ', NEW.id, ' - Parte: ', NEW.numero_parte),
                NOW(),
                NOW()
            );
        END IF;
        
        -- Distribución automática a IMD  
        IF NEW.propiedad_material = 'IMD' THEN
            INSERT INTO InventarioRollosIMD (
                numero_parte, codigo_barras, lote, cantidad_inicial, cantidad_actual,
                area_imd, fecha_entrada, origen_almacen, estado, movimiento_origen_id,
                usuario_responsable, observaciones, creado_en, actualizado_en
            ) VALUES (
                NEW.numero_parte,
                NEW.codigo_material_recibido,  -- ✅ USA CÓDIGO REAL
                NEW.numero_lote_material,
                NEW.cantidad_actual,
                NEW.cantidad_actual,
                'IMD_PRODUCTION',
                NEW.fecha_recibo,
                CONCAT('Auto-distribución IMD desde entrada ID: ', NEW.id, ' - Parte: ', NEW.numero_parte),
                'ACTIVO',
                NEW.id,
                'SISTEMA_AUTO',
                CONCAT('Auto-distribución IMD desde entrada ID: ', NEW.id, ' - Parte: ', NEW.numero_parte),
                NOW(),
                NOW()
            );
        END IF;
        
        -- Distribución automática a MAIN
        IF NEW.propiedad_material = 'MAIN' THEN
            INSERT INTO InventarioRollosMAIN (
                numero_parte, codigo_barras, lote, cantidad_inicial, cantidad_actual,
                area_main, fecha_entrada, origen_almacen, estado, movimiento_origen_id,
                usuario_responsable, observaciones, creado_en, actualizado_en
            ) VALUES (
                NEW.numero_parte,
                NEW.codigo_material_recibido,  -- ✅ USA CÓDIGO REAL
                NEW.numero_lote_material,
                NEW.cantidad_actual,
                NEW.cantidad_actual,
                'MAIN_PRODUCTION',
                NEW.fecha_recibo,
                CONCAT('Auto-distribución MAIN desde entrada ID: ', NEW.id, ' - Parte: ', NEW.numero_parte),
                'ACTIVO',
                NEW.id,
                'SISTEMA_AUTO',
                CONCAT('Auto-distribución MAIN desde entrada ID: ', NEW.id, ' - Parte: ', NEW.numero_parte),
                NOW(),
                NOW()
            );
        END IF;
    END
    """
    
    cursor.execute(trigger_sql)
    conn.commit()
    
    print("✅ Trigger corregido creado exitosamente!")
    print("\n🎯 CAMBIOS APLICADOS:")
    print("   📱 codigo_barras = NEW.codigo_material_recibido")
    print("   🚫 Eliminado AUTO_SMD automático")
    print("   ✅ Ahora usa código real para trazabilidad")
    
    # Verificar que el trigger se creó correctamente
    cursor.execute("SHOW TRIGGERS WHERE Trigger = 'tr_entrada_insert'")
    result = cursor.fetchone()
    if result:
        print(f"\n✅ Trigger verificado: {result[0]}")
    
except Exception as e:
    print(f"❌ Error: {e}")
finally:
    cursor.close()
    conn.close()
