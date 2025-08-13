#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import mysql.connector
from mysql.connector import Error
import sys
import traceback

# Configuración de base de datos remota
DB_CONFIG = {
    'host': 'up-de-fra1-mysql-1.db.run-on-seenode.com',
    'port': 11550,
    'database': 'db_rrpq0erbdujn',
    'user': 'db_rrpq0erbdujn',
    'password': '5fUNbSRcPP3LN9K2I33Pr0ge',
    'charset': 'utf8mb4'
}

def conectar_db():
    """Conectar a la base de datos MySQL"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        print("✅ Conexión exitosa a la base de datos remota")
        return connection
    except Error as e:
        print(f"❌ Error conectando a MySQL: {e}")
        return None

def encontrar_todos_los_triggers():
    """Encontrar TODOS los triggers que afectan a control_material_almacen"""
    connection = conectar_db()
    if not connection:
        return
    
    try:
        cursor = connection.cursor()
        
        print("\n=== BUSCANDO TODOS LOS TRIGGERS ===")
        
        # Buscar todos los triggers en la base de datos
        cursor.execute("""
            SELECT TRIGGER_NAME, EVENT_MANIPULATION, EVENT_OBJECT_TABLE, DEFINER
            FROM information_schema.TRIGGERS 
            WHERE TRIGGER_SCHEMA = %s
        """, (DB_CONFIG['database'],))
        
        triggers = cursor.fetchall()
        
        print(f"📋 Total de triggers encontrados: {len(triggers)}")
        
        triggers_problema = []
        
        for trigger in triggers:
            trigger_name = trigger[0]
            event = trigger[1]
            table = trigger[2]
            definer = trigger[3]
            
            print(f"\n🔍 Trigger: {trigger_name}")
            print(f"   Evento: {event} en tabla: {table}")
            print(f"   Definer: {definer}")
            
            # Obtener la definición completa
            try:
                cursor.execute(f"SHOW CREATE TRIGGER {trigger_name}")
                trigger_def = cursor.fetchone()
                
                if trigger_def:
                    definition = trigger_def[2]
                    print(f"   Definición:")
                    print(f"   {definition[:200]}...")
                    
                    # Verificar si este trigger afecta InventarioRollosSMD
                    if 'InventarioRollosSMD' in definition:
                        triggers_problema.append(trigger_name)
                        print("   ⚠️  ESTE TRIGGER AFECTA InventarioRollosSMD")
                        
                        # Verificar si genera AUTO_SMD
                        if 'AUTO_SMD' in definition:
                            print("   🚨 ESTE TRIGGER GENERA CÓDIGOS AUTO_SMD")
                        elif 'codigo_material_recibido' in definition:
                            print("   ✅ ESTE TRIGGER USA EL CÓDIGO CORRECTO")
                    
            except Error as e:
                print(f"   ❌ Error obteniendo definición: {e}")
        
        print(f"\n📊 RESUMEN:")
        print(f"   Total triggers: {len(triggers)}")
        print(f"   Triggers que afectan InventarioRollosSMD: {len(triggers_problema)}")
        print(f"   Triggers problema: {triggers_problema}")
        
        return triggers_problema
        
    except Error as e:
        print(f"❌ Error ejecutando consulta: {e}")
        traceback.print_exc()
        return []
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

def eliminar_triggers_problema(triggers_problema):
    """Eliminar todos los triggers que causan problemas"""
    connection = conectar_db()
    if not connection:
        return
    
    try:
        cursor = connection.cursor()
        
        print(f"\n=== ELIMINANDO {len(triggers_problema)} TRIGGERS PROBLEMA ===")
        
        for trigger_name in triggers_problema:
            try:
                cursor.execute(f"DROP TRIGGER IF EXISTS {trigger_name}")
                print(f"✅ Trigger {trigger_name} eliminado")
            except Error as e:
                print(f"❌ Error eliminando {trigger_name}: {e}")
        
        connection.commit()
        print("✅ Todos los triggers problema eliminados")
        
    except Error as e:
        print(f"❌ Error eliminando triggers: {e}")
        traceback.print_exc()
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

def crear_trigger_unico_correcto():
    """Crear UN SOLO trigger correcto"""
    connection = conectar_db()
    if not connection:
        return
    
    try:
        cursor = connection.cursor()
        
        print("\n=== CREANDO TRIGGER ÚNICO Y CORRECTO ===")
        
        # Crear trigger final usando la estructura real
        trigger_sql = """
        CREATE TRIGGER tr_smd_distribucion_unico
        AFTER INSERT ON control_material_almacen
        FOR EACH ROW
        BEGIN
            -- Solo procesar materiales SMD
            IF NEW.propiedad_material = 'SMD' THEN
                
                -- Insertar en InventarioRollosSMD usando el código real recibido
                INSERT INTO InventarioRollosSMD (
                    numero_parte,
                    codigo_barras,
                    lote,
                    cantidad_inicial,
                    cantidad_actual,
                    area_smd,
                    fecha_entrada,
                    estado,
                    movimiento_origen_id,
                    usuario_responsable,
                    creado_en,
                    actualizado_en
                ) VALUES (
                    NEW.numero_parte,
                    NEW.codigo_material_recibido,  -- USAR EL CÓDIGO REAL
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
        connection.commit()
        
        print("✅ Trigger tr_smd_distribucion_unico creado exitosamente!")
        
        # Verificar que se creó correctamente
        cursor.execute("SHOW CREATE TRIGGER tr_smd_distribucion_unico")
        trigger_def = cursor.fetchone()
        
        if trigger_def:
            print("✅ Trigger verificado correctamente")
        else:
            print("❌ Error: Trigger no se creó correctamente")
            
    except Error as e:
        print(f"❌ Error creando trigger: {e}")
        traceback.print_exc()
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

def main():
    print("🔍 LIMPIEZA COMPLETA DE TRIGGERS DUPLICADOS")
    print("=" * 50)
    
    # Encontrar todos los triggers
    triggers_problema = encontrar_todos_los_triggers()
    
    if triggers_problema:
        print(f"\n⚠️  Se encontraron {len(triggers_problema)} triggers que afectan InventarioRollosSMD")
        print("📋 Triggers problema:")
        for trigger in triggers_problema:
            print(f"   - {trigger}")
        
        respuesta = input("\n¿Eliminar TODOS estos triggers? (s/n): ").strip().lower()
        
        if respuesta in ['s', 'si', 'y', 'yes']:
            eliminar_triggers_problema(triggers_problema)
            
            respuesta2 = input("\n¿Crear el trigger único correcto? (s/n): ").strip().lower()
            if respuesta2 in ['s', 'si', 'y', 'yes']:
                crear_trigger_unico_correcto()
    else:
        print("✅ No se encontraron triggers problema")
    
    print("\n✅ Limpieza completada")

if __name__ == "__main__":
    main()
