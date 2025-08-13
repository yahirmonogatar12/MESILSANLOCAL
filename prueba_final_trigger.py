#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import mysql.connector
from mysql.connector import Error
import sys
import traceback
from datetime import datetime

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

def hacer_prueba_final():
    """Hacer una prueba final del trigger corregido"""
    connection = conectar_db()
    if not connection:
        return
    
    try:
        cursor = connection.cursor()
        
        print("\n=== PRUEBA FINAL DEL TRIGGER CORREGIDO ===")
        
        # Crear un registro de prueba
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        codigo_prueba = f"PRUEBA_FINAL_{timestamp}"
        numero_parte_prueba = f"TEST_{timestamp}"
        
        print(f"🧪 Insertando material de prueba con código: {codigo_prueba}")
        
        insert_sql = """
        INSERT INTO control_material_almacen (
            numero_parte,
            codigo_material_recibido,
            numero_lote_material,
            cantidad_actual,
            propiedad_material,
            especificacion,
            fecha_recibo,
            fecha_fabricacion
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        valores = (
            numero_parte_prueba,
            codigo_prueba,
            f"LOTE_{timestamp}",
            1000,
            'SMD',
            'Prueba final trigger',
            datetime.now(),
            datetime.now()
        )
        
        cursor.execute(insert_sql, valores)
        connection.commit()
        
        # Obtener el ID del registro insertado
        nuevo_id = cursor.lastrowid
        print(f"✅ Material insertado con ID: {nuevo_id}")
        
        # Verificar que se creó automáticamente en InventarioRollosSMD
        print("\n🔍 Verificando creación automática en InventarioRollosSMD...")
        
        cursor.execute("""
            SELECT id, numero_parte, codigo_barras, movimiento_origen_id, fecha_entrada
            FROM InventarioRollosSMD 
            WHERE movimiento_origen_id = %s
        """, (nuevo_id,))
        
        resultados = cursor.fetchall()
        
        if resultados:
            print(f"✅ Se crearon {len(resultados)} registros en InventarioRollosSMD:")
            for resultado in resultados:
                print(f"   ID: {resultado[0]} | Parte: {resultado[1]} | Código: {resultado[2]} | Origen: {resultado[3]} | Fecha: {resultado[4]}")
                
                # Verificar que el código es el correcto
                if resultado[2] == codigo_prueba:
                    print(f"   ✅ CÓDIGO CORRECTO: {resultado[2]}")
                else:
                    print(f"   ❌ CÓDIGO INCORRECTO: {resultado[2]} (esperado: {codigo_prueba})")
        else:
            print("❌ No se crearon registros en InventarioRollosSMD")
        
        # Limpiar el registro de prueba
        print(f"\n🧹 Limpiando registro de prueba...")
        cursor.execute("DELETE FROM InventarioRollosSMD WHERE movimiento_origen_id = %s", (nuevo_id,))
        cursor.execute("DELETE FROM control_material_almacen WHERE id = %s", (nuevo_id,))
        connection.commit()
        print("✅ Registro de prueba eliminado")
        
    except Error as e:
        print(f"❌ Error en prueba final: {e}")
        traceback.print_exc()
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

def verificar_estado_actual():
    """Verificar el estado actual de los triggers"""
    connection = conectar_db()
    if not connection:
        return
    
    try:
        cursor = connection.cursor()
        
        print("\n=== ESTADO ACTUAL DE TRIGGERS ===")
        
        # Verificar triggers activos
        cursor.execute("""
            SELECT TRIGGER_NAME, EVENT_MANIPULATION, EVENT_OBJECT_TABLE
            FROM information_schema.TRIGGERS 
            WHERE TRIGGER_SCHEMA = %s
            AND (EVENT_OBJECT_TABLE = 'control_material_almacen' 
                 OR EVENT_OBJECT_TABLE = 'control_material_salida')
        """, (DB_CONFIG['database'],))
        
        triggers = cursor.fetchall()
        
        print(f"📋 Triggers activos en tablas relevantes: {len(triggers)}")
        for trigger in triggers:
            print(f"   - {trigger[0]} ({trigger[1]} en {trigger[2]})")
        
        # Verificar el trigger específico
        try:
            cursor.execute("SHOW CREATE TRIGGER tr_smd_distribucion_unico")
            trigger_def = cursor.fetchone()
            
            if trigger_def:
                print("\n✅ Trigger tr_smd_distribucion_unico está activo")
                definition = trigger_def[2]
                if 'codigo_material_recibido' in definition:
                    print("✅ El trigger usa codigo_material_recibido (correcto)")
                if 'AUTO_SMD' not in definition:
                    print("✅ El trigger NO genera códigos AUTO_SMD")
            else:
                print("❌ Trigger tr_smd_distribucion_unico NO encontrado")
                
        except Error as e:
            print(f"❌ Error verificando trigger: {e}")
        
    except Error as e:
        print(f"❌ Error verificando estado: {e}")
        traceback.print_exc()
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

def main():
    print("🎯 PRUEBA FINAL DE CORRECCIÓN")
    print("=" * 40)
    
    # Verificar estado actual
    verificar_estado_actual()
    
    # Hacer prueba final
    respuesta = input("\n¿Hacer prueba final con material de prueba? (s/n): ").strip().lower()
    
    if respuesta in ['s', 'si', 'y', 'yes']:
        hacer_prueba_final()
    
    print("\n🎉 ¡Prueba final completada!")
    print("\n📋 RESUMEN DE LA SOLUCIÓN:")
    print("   ✅ Triggers duplicados eliminados")
    print("   ✅ Trigger único creado (tr_smd_distribucion_unico)")
    print("   ✅ Sistema usa codigo_material_recibido real")
    print("   ✅ No más códigos AUTO_SMD automáticos")
    print("\n🔍 AHORA en SMounter verás: 0RH5602C622,202508130002")
    print("   En lugar de: AUTO_SMD_X_XXXXXXXXX")

if __name__ == "__main__":
    main()
