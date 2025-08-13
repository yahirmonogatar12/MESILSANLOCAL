#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import mysql.connector
from mysql.connector import Error

# Configuración de la base de datos
DB_CONFIG = {
    'host': 'up-de-fra1-mysql-1.db.run-on-seenode.com',
    'port': 11550,
    'user': 'db_rrpq0erbdujn',
    'password': '5fUNbSRcPP3LN9K2I33Pr0ge',
    'database': 'db_rrpq0erbdujn'
}

def eliminar_todos_los_triggers():
    """Eliminar TODOS los triggers de la tabla control_material_almacen"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()
        
        print("=== ELIMINANDO TODOS LOS TRIGGERS ===")
        
        # Obtener todos los triggers de la tabla
        cursor.execute("SHOW TRIGGERS LIKE 'control_material_almacen'")
        triggers = cursor.fetchall()
        
        if triggers:
            print("Triggers encontrados:")
            for trigger in triggers:
                trigger_name = trigger[0]
                print(f"   - {trigger_name}")
                
                # Eliminar cada trigger
                try:
                    cursor.execute(f"DROP TRIGGER IF EXISTS {trigger_name}")
                    print(f"   ✅ {trigger_name} eliminado")
                except Exception as e:
                    print(f"   ❌ Error eliminando {trigger_name}: {e}")
            
            connection.commit()
        else:
            print("   ⚠️ No se encontraron triggers")
        
        return True
        
    except Error as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

def crear_trigger_unico():
    """Crear UN SOLO trigger correcto"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()
        
        print("\n=== CREANDO TRIGGER ÚNICO Y CORRECTO ===")
        
        trigger_sql = """
        CREATE TRIGGER tr_smd_distribucion_final
        AFTER INSERT ON control_material_almacen
        FOR EACH ROW
        BEGIN
            IF NEW.propiedad_material = 'SMD' THEN
                INSERT INTO InventarioRollosSMD (
                    numero_parte,
                    codigo_barras,
                    lote,
                    estado,
                    cantidad_inicial,
                    cantidad_actual,
                    area_smd,
                    fecha_entrada,
                    movimiento_origen_id,
                    usuario_responsable,
                    observaciones
                ) VALUES (
                    NEW.numero_parte,
                    NEW.codigo_material_recibido,
                    NEW.numero_lote_material,
                    'ACTIVO',
                    NEW.cantidad_actual,
                    NEW.cantidad_actual,
                    'SMD_PRODUCTION',
                    NEW.fecha_recibo,
                    NEW.id,
                    'SISTEMA_AUTO',
                    CONCAT('Auto-distribución SMD desde almacén ID: ', NEW.id, ' - Parte: ', NEW.numero_parte)
                );
            END IF;
        END
        """
        
        cursor.execute(trigger_sql)
        connection.commit()
        print("✅ Trigger único creado exitosamente: tr_smd_distribucion_final")
        
        # Verificar que se creó
        cursor.execute("SHOW TRIGGERS LIKE 'control_material_almacen'")
        triggers = cursor.fetchall()
        
        print("\nTriggers activos:")
        for trigger in triggers:
            print(f"   ✅ {trigger[0]} - {trigger[1]} {trigger[2]}")
        
        return True
        
    except Error as e:
        print(f"❌ Error creando trigger: {e}")
        return False
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

def limpiar_registros_duplicados():
    """Eliminar el registro duplicado con AUTO_SMD"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()
        
        print("\n=== LIMPIANDO REGISTROS DUPLICADOS ===")
        
        # Encontrar registros con AUTO_SMD
        cursor.execute("""
            SELECT id, numero_parte, codigo_barras, movimiento_origen_id
            FROM InventarioRollosSMD 
            WHERE codigo_barras LIKE 'AUTO_SMD_%'
            ORDER BY id DESC
        """)
        
        duplicados = cursor.fetchall()
        
        if duplicados:
            print("Registros con AUTO_SMD encontrados:")
            for dup in duplicados:
                print(f"   ID: {dup[0]} - Parte: {dup[1]} - Código: {dup[2]}")
            
            respuesta = input("\n¿Eliminar estos registros duplicados? (s/n): ").strip().lower()
            
            if respuesta == 's':
                for dup in duplicados:
                    cursor.execute("DELETE FROM InventarioRollosSMD WHERE id = %s", (dup[0],))
                    print(f"   ✅ Eliminado registro ID: {dup[0]}")
                
                connection.commit()
                print("✅ Registros duplicados eliminados")
            else:
                print("⚠️ Registros duplicados mantenidos")
        else:
            print("✅ No hay registros duplicados con AUTO_SMD")
        
        return True
        
    except Error as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

def main():
    print("CORRECCIÓN FINAL DEL SISTEMA SMD")
    print("=" * 50)
    
    # Paso 1: Eliminar todos los triggers
    if eliminar_todos_los_triggers():
        
        # Paso 2: Crear el trigger único correcto
        if crear_trigger_unico():
            
            # Paso 3: Limpiar registros duplicados
            limpiar_registros_duplicados()
            
            print("\n" + "=" * 50)
            print("✅ SISTEMA CORREGIDO COMPLETAMENTE")
            print("✅ Solo queda un trigger que usa codigo_material_recibido")
            print("✅ No habrá más códigos AUTO_SMD")
            print("=" * 50)
        else:
            print("❌ Error al crear el trigger")
    else:
        print("❌ Error al eliminar triggers")

if __name__ == "__main__":
    main()
