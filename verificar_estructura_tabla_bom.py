#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para verificar la estructura real de la tabla BOM
"""

import pymysql
from app.config_mysql import get_mysql_connection_string

def get_db_connection():
    """Crear conexión a MySQL"""
    try:
        config = get_mysql_connection_string()
        if not config:
            print("Error: No se pudo obtener configuración de MySQL")
            return None
            
        connection = pymysql.connect(
            host=config['host'],
            user=config['user'],
            password=config['passwd'],
            database=config['db'],
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        return connection
    except Exception as e:
        print(f"Error conectando a MySQL: {e}")
        return None

def verificar_estructura_tabla():
    """Verificar la estructura real de la tabla BOM"""
    conn = get_db_connection()
    if not conn:
        return
    
    try:
        cursor = conn.cursor()
        
        print("=== Estructura de la tabla BOM ===")
        
        # Obtener estructura de la tabla
        cursor.execute("DESCRIBE bom")
        columnas = cursor.fetchall()
        
        print(f"\n📋 Columnas de la tabla BOM ({len(columnas)}):")
        for i, col in enumerate(columnas, 1):
            print(f"  {i:2d}. {col['Field']:25} | {col['Type']:15} | Null: {col['Null']:3} | Key: {col['Key']:3} | Default: {col['Default']}")
        
        # Obtener un registro de ejemplo
        cursor.execute("SELECT * FROM bom LIMIT 1")
        ejemplo = cursor.fetchone()
        
        if ejemplo:
            print(f"\n🔍 Ejemplo de registro:")
            for campo, valor in ejemplo.items():
                print(f"  {campo:25} = {valor}")
        
        # Verificar si hay registros
        cursor.execute("SELECT COUNT(*) as total FROM bom")
        total = cursor.fetchone()['total']
        print(f"\n📊 Total de registros en la tabla: {total}")
        
        # Verificar modelos únicos
        cursor.execute("SELECT DISTINCT modelo FROM bom ORDER BY modelo LIMIT 10")
        modelos = cursor.fetchall()
        
        print(f"\n🏷️ Primeros 10 modelos únicos:")
        for i, modelo in enumerate(modelos, 1):
            print(f"  {i:2d}. {modelo['modelo']}")
        
        # Verificar registros para EBR30299301
        cursor.execute("SELECT COUNT(*) as total FROM bom WHERE modelo = %s", ('EBR30299301',))
        total_modelo = cursor.fetchone()['total']
        print(f"\n📊 Registros para modelo EBR30299301: {total_modelo}")
        
        if total_modelo > 0:
            cursor.execute("SELECT * FROM bom WHERE modelo = %s LIMIT 3", ('EBR30299301',))
            ejemplos = cursor.fetchall()
            
            print(f"\n🔍 Primeros 3 registros de EBR30299301:")
            for i, registro in enumerate(ejemplos, 1):
                print(f"\n  Registro {i}:")
                for campo, valor in registro.items():
                    if valor is not None and str(valor).strip():
                        print(f"    {campo:20} = {valor}")
        
    except Exception as e:
        print(f"Error verificando estructura: {e}")
    finally:
        conn.close()

def main():
    print("Verificando estructura real de la tabla BOM...\n")
    verificar_estructura_tabla()

if __name__ == '__main__':
    main()