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

def investigar_estructura_tablas():
    """Investigar la estructura de las tablas principales"""
    connection = conectar_db()
    if not connection:
        return
    
    try:
        cursor = connection.cursor()
        
        print("\n=== ESTRUCTURA DE control_material_almacen ===")
        cursor.execute("DESCRIBE control_material_almacen")
        campos_almacen = cursor.fetchall()
        
        for campo in campos_almacen:
            print(f"  {campo[0]} | {campo[1]} | NULL: {campo[2]} | Key: {campo[3]} | Default: {campo[4]}")
        
        print("\n=== ESTRUCTURA DE InventarioRollosSMD ===")
        cursor.execute("DESCRIBE InventarioRollosSMD")
        campos_inventario = cursor.fetchall()
        
        for campo in campos_inventario:
            print(f"  {campo[0]} | {campo[1]} | NULL: {campo[2]} | Key: {campo[3]} | Default: {campo[4]}")
        
        print("\n=== ÚLTIMOS 3 REGISTROS EN control_material_almacen ===")
        cursor.execute("SELECT * FROM control_material_almacen ORDER BY id DESC LIMIT 3")
        registros = cursor.fetchall()
        
        # Obtener nombres de columnas
        cursor.execute("SHOW COLUMNS FROM control_material_almacen")
        columnas = [col[0] for col in cursor.fetchall()]
        
        for i, registro in enumerate(registros):
            print(f"\n📋 Registro {i+1}:")
            for j, valor in enumerate(registro):
                print(f"   {columnas[j]}: {valor}")
        
        print("\n=== ÚLTIMOS 3 REGISTROS EN InventarioRollosSMD ===")
        cursor.execute("SELECT * FROM InventarioRollosSMD ORDER BY id DESC LIMIT 3")
        inventario = cursor.fetchall()
        
        # Obtener nombres de columnas
        cursor.execute("SHOW COLUMNS FROM InventarioRollosSMD")
        columnas_inv = [col[0] for col in cursor.fetchall()]
        
        for i, item in enumerate(inventario):
            print(f"\n📦 Item {i+1}:")
            for j, valor in enumerate(item):
                print(f"   {columnas_inv[j]}: {valor}")
                
    except Error as e:
        print(f"❌ Error ejecutando consulta: {e}")
        traceback.print_exc()
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

def crear_trigger_con_estructura_correcta():
    """Crear trigger usando la estructura real de las tablas"""
    connection = conectar_db()
    if not connection:
        return
    
    try:
        cursor = connection.cursor()
        
        print("\n=== CREANDO TRIGGER CON ESTRUCTURA CORRECTA ===")
        
        # Primero, obtener la estructura de control_material_almacen
        cursor.execute("SHOW COLUMNS FROM control_material_almacen")
        columnas_almacen = {col[0]: col[1] for col in cursor.fetchall()}
        
        cursor.execute("SHOW COLUMNS FROM InventarioRollosSMD")
        columnas_inventario = {col[0]: col[1] for col in cursor.fetchall()}
        
        print("📋 Campos disponibles en control_material_almacen:")
        for campo, tipo in columnas_almacen.items():
            print(f"   - {campo} ({tipo})")
        
        print("\n📦 Campos disponibles en InventarioRollosSMD:")
        for campo, tipo in columnas_inventario.items():
            print(f"   - {campo} ({tipo})")
        
        # Crear trigger basado en los campos reales
        trigger_sql = """
        CREATE TRIGGER tr_smd_distribucion_final
        AFTER INSERT ON control_material_almacen
        FOR EACH ROW
        BEGIN
            DECLARE area_destino VARCHAR(50);
            
            -- Solo procesar materiales SMD
            IF NEW.propiedad_material = 'SMD' THEN
                
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
                    area_destino,
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
        
        print("✅ Trigger tr_smd_distribucion_final creado exitosamente!")
        
        # Verificar que se creó correctamente
        cursor.execute("SHOW CREATE TRIGGER tr_smd_distribucion_final")
        trigger_def = cursor.fetchone()
        
        if trigger_def:
            print("✅ Trigger verificado correctamente")
            print("\n🔧 Definición del trigger:")
            print(trigger_def[2])
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
    print("🔍 INVESTIGACIÓN DE ESTRUCTURA Y CORRECCIÓN FINAL")
    print("=" * 60)
    
    # Investigar estructura
    investigar_estructura_tablas()
    
    # Preguntar si crear trigger
    respuesta = input("\n¿Crear el trigger final con la estructura correcta? (s/n): ").strip().lower()
    
    if respuesta in ['s', 'si', 'y', 'yes']:
        crear_trigger_con_estructura_correcta()
    
    print("\n✅ Investigación completada")

if __name__ == "__main__":
    main()
