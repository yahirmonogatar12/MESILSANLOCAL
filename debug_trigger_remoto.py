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

def verificar_trigger_actual():
    """Verificar el trigger actual en la base de datos"""
    connection = conectar_db()
    if not connection:
        return
    
    try:
        cursor = connection.cursor()
        
        print("\n=== VERIFICANDO TRIGGER ACTUAL ===")
        
        # Verificar si existe el trigger
        cursor.execute("""
            SELECT TRIGGER_NAME, EVENT_MANIPULATION, EVENT_OBJECT_TABLE, DEFINER
            FROM information_schema.TRIGGERS 
            WHERE TRIGGER_SCHEMA = %s 
            AND EVENT_OBJECT_TABLE = 'control_material_almacen'
        """, (DB_CONFIG['database'],))
        
        triggers = cursor.fetchall()
        
        if not triggers:
            print("❌ No se encontraron triggers en la tabla control_material_almacen")
        else:
            print(f"📋 Triggers encontrados: {len(triggers)}")
            for trigger in triggers:
                print(f"   - {trigger[0]} ({trigger[1]} en {trigger[2]})")
        
        # Obtener la definición del trigger específico
        cursor.execute("""
            SHOW CREATE TRIGGER tr_smd_distribucion_corregido
        """)
        
        trigger_def = cursor.fetchone()
        if trigger_def:
            print("\n=== DEFINICIÓN DEL TRIGGER ===")
            print(trigger_def[2])  # SQL Original Statement
        else:
            print("❌ No se encontró el trigger tr_smd_distribucion_corregido")
        
        # Verificar últimos registros en control_material_almacen
        print("\n=== ÚLTIMOS REGISTROS EN control_material_almacen ===")
        cursor.execute("""
            SELECT id, codigo_material_recibido, numero_parte, fecha_entrada
            FROM control_material_almacen 
            ORDER BY id DESC 
            LIMIT 5
        """)
        
        registros = cursor.fetchall()
        for registro in registros:
            print(f"ID: {registro[0]} | Código: {registro[1]} | Parte: {registro[2]} | Fecha: {registro[3]}")
        
        # Verificar últimos registros en InventarioRollosSMD
        print("\n=== ÚLTIMOS REGISTROS EN InventarioRollosSMD ===")
        cursor.execute("""
            SELECT id, numero_parte, codigo_barras, fecha_entrada, movimiento_origen_id
            FROM InventarioRollosSMD 
            ORDER BY id DESC 
            LIMIT 5
        """)
        
        inventario = cursor.fetchall()
        for item in inventario:
            print(f"ID: {item[0]} | Parte: {item[1]} | Código: {item[2]} | Fecha: {item[3]} | Origen: {item[4]}")
            
    except Error as e:
        print(f"❌ Error ejecutando consulta: {e}")
        traceback.print_exc()
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

def recrear_trigger_corregido():
    """Recrear el trigger con la lógica correcta"""
    connection = conectar_db()
    if not connection:
        return
    
    try:
        cursor = connection.cursor()
        
        print("\n=== RECREANDO TRIGGER CORREGIDO ===")
        
        # 1. Eliminar triggers existentes
        print("🗑️ Eliminando triggers existentes...")
        
        try:
            cursor.execute("DROP TRIGGER IF EXISTS tr_smd_distribucion_corregido")
            print("   - tr_smd_distribucion_corregido eliminado")
        except:
            pass
            
        try:
            cursor.execute("DROP TRIGGER IF EXISTS tr_entrada_insert")
            print("   - tr_entrada_insert eliminado")
        except:
            pass
        
        # 2. Crear nuevo trigger corregido
        print("🔧 Creando nuevo trigger...")
        
        trigger_sql = """
        CREATE TRIGGER tr_smd_distribucion_corregido
        AFTER INSERT ON control_material_almacen
        FOR EACH ROW
        BEGIN
            DECLARE area_destino VARCHAR(50);
            
            -- Determinar área basada en el número de parte
            IF NEW.numero_parte LIKE '0R%' OR NEW.numero_parte LIKE 'R%' THEN
                SET area_destino = 'SMD_PRODUCTION';
            ELSE
                SET area_destino = 'SMD_STORAGE';
            END IF;
            
            -- Insertar en InventarioRollosSMD usando el código real recibido
            INSERT INTO InventarioRollosSMD (
                numero_parte,
                codigo_barras,
                estado,
                cantidad_inicial,
                cantidad_actual,
                area_smd,
                fecha_entrada,
                movimiento_origen_id
            ) VALUES (
                NEW.numero_parte,
                NEW.codigo_material_recibido,  -- USAR EL CÓDIGO REAL
                'ACTIVO',
                NEW.cantidad,
                NEW.cantidad,
                area_destino,
                NEW.fecha_entrada,
                NEW.id
            );
        END
        """
        
        cursor.execute(trigger_sql)
        connection.commit()
        
        print("✅ Trigger tr_smd_distribucion_corregido creado exitosamente!")
        
        # 3. Verificar que se creó correctamente
        cursor.execute("SHOW CREATE TRIGGER tr_smd_distribucion_corregido")
        trigger_def = cursor.fetchone()
        
        if trigger_def:
            print("✅ Trigger verificado correctamente")
        else:
            print("❌ Error: Trigger no se creó correctamente")
            
    except Error as e:
        print(f"❌ Error recreando trigger: {e}")
        traceback.print_exc()
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

def main():
    print("🔍 DIAGNÓSTICO Y CORRECCIÓN DEL TRIGGER SMD")
    print("=" * 50)
    
    # Verificar estado actual
    verificar_trigger_actual()
    
    # Preguntar si recrear
    respuesta = input("\n¿Recrear el trigger corregido? (s/n): ").strip().lower()
    
    if respuesta in ['s', 'si', 'y', 'yes']:
        recrear_trigger_corregido()
        print("\n🔄 Verificando después de la corrección...")
        verificar_trigger_actual()
    
    print("\n✅ Diagnóstico completado")

if __name__ == "__main__":
    main()
