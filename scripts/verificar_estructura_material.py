#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verificar estructura de tablas relacionadas con control_material
"""

import mysql.connector

DB_CONFIG = {
    'host': 'up-de-fra1-mysql-1.db.run-on-seenode.com',
    'port': 11550,
    'user': 'db_rrpq0erbdujn',
    'password': '5fUNbSRcPP3LN9K2I33Pr0ge',
    'database': 'db_rrpq0erbdujn',
    'charset': 'utf8mb4'
}

def verificar_estructura():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("=== TABLAS RELACIONADAS CON CONTROL_MATERIAL ===")
        cursor.execute("SHOW TABLES LIKE '%control_material%'")
        tablas = cursor.fetchall()
        
        for tabla in tablas:
            print(f"\n• {tabla[0]}:")
            cursor.execute(f"DESCRIBE {tabla[0]}")
            for col in cursor.fetchall():
                print(f"  {col[0]}: {col[1]}")
        
        print("\n=== VERIFICANDO DATOS DE EJEMPLO ===")
        
        # Verificar si hay datos en control_material_almacen
        cursor.execute("SELECT COUNT(*) FROM control_material_almacen")
        count_almacen = cursor.fetchone()[0]
        print(f"control_material_almacen: {count_almacen} registros")
        
        if count_almacen > 0:
            cursor.execute("SELECT codigo_material_recibido, numero_parte, propiedad_material FROM control_material_almacen LIMIT 3")
            print("  Ejemplos:")
            for row in cursor.fetchall():
                print(f"    {row[0]} | {row[1]} | {row[2]}")
        
        # Verificar control_material_salida
        cursor.execute("SELECT COUNT(*) FROM control_material_salida")
        count_salida = cursor.fetchone()[0]
        print(f"\ncontrol_material_salida: {count_salida} registros")
        
        if count_salida > 0:
            cursor.execute("SELECT codigo_material_recibido, especificacion_material FROM control_material_salida ORDER BY id DESC LIMIT 5")
            print("  Últimas salidas:")
            for row in cursor.fetchall():
                print(f"    {row[0]} -> '{row[1]}'")
        
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    verificar_estructura()
