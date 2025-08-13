#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import mysql.connector
from mysql.connector import Error

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

def investigar_estructura_inventario():
    """Investigar la estructura de inventario_general"""
    connection = conectar_db()
    if not connection:
        return
    
    try:
        cursor = connection.cursor()
        
        print("=== INVESTIGANDO ESTRUCTURA DE inventario_general ===")
        
        # Verificar si existe la tabla
        cursor.execute("SHOW TABLES LIKE 'inventario_general'")
        if not cursor.fetchone():
            print("❌ La tabla inventario_general NO EXISTE")
            return
        
        # Mostrar estructura
        cursor.execute("DESCRIBE inventario_general")
        campos = cursor.fetchall()
        
        print("📋 Estructura de inventario_general:")
        for campo in campos:
            print(f"   {campo[0]} | {campo[1]} | NULL: {campo[2]} | Key: {campo[3]} | Default: {campo[4]}")
            
        # Mostrar algunos registros
        cursor.execute("SELECT * FROM inventario_general LIMIT 5")
        registros = cursor.fetchall()
        
        if registros:
            print("\n📦 Últimos registros:")
            cursor.execute("SHOW COLUMNS FROM inventario_general")
            columnas = [col[0] for col in cursor.fetchall()]
            
            for i, registro in enumerate(registros):
                print(f"\nRegistro {i+1}:")
                for j, valor in enumerate(registro):
                    print(f"   {columnas[j]}: {valor}")
        else:
            print("⚠️ No hay registros en inventario_general")
            
    except Error as e:
        print(f"❌ Error: {e}")
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

def investigar_proceso_salidas():
    """Investigar cómo funciona el proceso de salidas"""
    connection = conectar_db()
    if not connection:
        return
    
    try:
        cursor = connection.cursor()
        
        print("\n=== INVESTIGANDO PROCESO DE SALIDAS ===")
        
        # Verificar estructura de control_material_salida
        cursor.execute("DESCRIBE control_material_salida")
        campos_salida = cursor.fetchall()
        
        print("📋 Estructura de control_material_salida:")
        for campo in campos_salida:
            print(f"   {campo[0]} | {campo[1]} | NULL: {campo[2]} | Key: {campo[3]} | Default: {campo[4]}")
        
        # Últimas salidas
        cursor.execute("""
            SELECT id, codigo_material_recibido, proceso_salida, especificacion, numero_parte, fecha_salida
            FROM control_material_salida 
            ORDER BY id DESC LIMIT 5
        """)
        
        salidas = cursor.fetchall()
        
        print("\n📦 Últimas 5 salidas:")
        for salida in salidas:
            print(f"   ID: {salida[0]} | Código: {salida[1]} | Proceso: {salida[2]} | Especificación: {salida[3]} | Parte: {salida[4]} | Fecha: {salida[5]}")
        
        # Verificar si hay triggers en control_material_salida
        cursor.execute("""
            SELECT TRIGGER_NAME, EVENT_MANIPULATION
            FROM information_schema.TRIGGERS 
            WHERE TRIGGER_SCHEMA = %s
            AND EVENT_OBJECT_TABLE = 'control_material_salida'
        """, (DB_CONFIG['database'],))
        
        triggers_salida = cursor.fetchall()
        
        print(f"\n🔧 Triggers en control_material_salida: {len(triggers_salida)}")
        for trigger in triggers_salida:
            print(f"   - {trigger[0]} ({trigger[1]})")
            
    except Error as e:
        print(f"❌ Error: {e}")
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

def investigar_relacion_entrada_salida():
    """Investigar cómo se relacionan las entradas con las salidas"""
    connection = conectar_db()
    if not connection:
        return
    
    try:
        cursor = connection.cursor()
        
        print("\n=== INVESTIGANDO RELACIÓN ENTRADA-SALIDA ===")
        
        # Buscar el material específico en entradas
        cursor.execute("""
            SELECT id, numero_parte, codigo_material_recibido, especificacion, propiedad_material
            FROM control_material_almacen 
            WHERE numero_parte = '0RH5602C622'
            ORDER BY id DESC LIMIT 1
        """)
        
        entrada = cursor.fetchone()
        
        if entrada:
            print(f"📦 Material en almacén:")
            print(f"   ID: {entrada[0]} | Parte: {entrada[1]} | Código: {entrada[2]} | Especificación: {entrada[3]} | Propiedad: {entrada[4]}")
            
            # Buscar salidas del mismo material
            cursor.execute("""
                SELECT id, codigo_material_recibido, proceso_salida, especificacion, numero_parte
                FROM control_material_salida 
                WHERE numero_parte = '0RH5602C622'
                ORDER BY id DESC LIMIT 3
            """)
            
            salidas = cursor.fetchall()
            
            print(f"\n📤 Salidas del mismo material:")
            if salidas:
                for salida in salidas:
                    print(f"   ID: {salida[0]} | Código: {salida[1]} | Proceso: {salida[2]} | Especificación: {salida[3]} | Parte: {salida[4]}")
            else:
                print("   ⚠️ No hay salidas registradas para este material")
                
            # Verificar en inventarios específicos
            print(f"\n🔍 Verificando en inventarios específicos:")
            
            # SMD
            cursor.execute("""
                SELECT COUNT(*) FROM InventarioRollosSMD 
                WHERE numero_parte = '0RH5602C622'
            """)
            count_smd = cursor.fetchone()[0]
            print(f"   SMD: {count_smd} registros")
            
            # MAIN
            cursor.execute("""
                SELECT COUNT(*) FROM InventarioRollosMAIN 
                WHERE numero_parte = '0RH5602C622'
            """)
            count_main = cursor.fetchone()[0]
            print(f"   MAIN: {count_main} registros")
            
            # IMD
            cursor.execute("""
                SELECT COUNT(*) FROM InventarioRollosIMD 
                WHERE numero_parte = '0RH5602C622'
            """)
            count_imd = cursor.fetchone()[0]
            print(f"   IMD: {count_imd} registros")
            
        else:
            print("❌ No se encontró el material 0RH5602C622 en control_material_almacen")
            
    except Error as e:
        print(f"❌ Error: {e}")
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

def main():
    print("🔍 DIAGNÓSTICO COMPLETO DEL SISTEMA DE SALIDAS")
    print("=" * 60)
    
    # Investigar inventario_general
    investigar_estructura_inventario()
    
    # Investigar proceso de salidas
    investigar_proceso_salidas()
    
    # Investigar relación entrada-salida
    investigar_relacion_entrada_salida()
    
    print("\n" + "=" * 60)
    print("✅ DIAGNÓSTICO COMPLETADO")

if __name__ == "__main__":
    main()
