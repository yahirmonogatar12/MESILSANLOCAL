#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para verificar la estructura de la tabla rol_permisos_botones en la base de datos local
"""

import sqlite3
import os

def verificar_estructura_local():
    """Verificar estructura de la tabla en la base de datos local"""
    try:
        db_path = 'app/database/ISEMM_MES.db'
        if not os.path.exists(db_path):
            print(f"❌ No se encontró la base de datos local: {db_path}")
            return
            
        connection = sqlite3.connect(db_path)
        cursor = connection.cursor()
        
        # Verificar si la tabla existe
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='rol_permisos_botones'
        """)
        
        if not cursor.fetchone():
            print("❌ La tabla 'rol_permisos_botones' no existe en la base de datos local")
            
            # Listar todas las tablas relacionadas con permisos
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name LIKE '%permiso%'
            """)
            
            tablas_permisos = cursor.fetchall()
            if tablas_permisos:
                print("\n📋 Tablas relacionadas con permisos en la base de datos local:")
                for tabla in tablas_permisos:
                    print(f"  - {tabla[0]}")
                    
                    # Mostrar estructura de cada tabla
                    cursor.execute(f"PRAGMA table_info({tabla[0]})")
                    estructura = cursor.fetchall()
                    print(f"    Estructura:")
                    for campo in estructura:
                        print(f"      - {campo[1]} ({campo[2]})")
                    
                    # Mostrar algunos datos
                    cursor.execute(f"SELECT COUNT(*) FROM {tabla[0]}")
                    count = cursor.fetchone()[0]
                    print(f"    Registros: {count}")
                    
                    if count > 0:
                        cursor.execute(f"SELECT * FROM {tabla[0]} LIMIT 3")
                        datos = cursor.fetchall()
                        print(f"    Primeros registros: {datos}")
                    print()
            else:
                print("\n❌ No se encontraron tablas relacionadas con permisos")
            
            return
        
        print("✅ La tabla 'rol_permisos_botones' SÍ existe en la base de datos local")
        
        # Obtener estructura de la tabla
        cursor.execute("PRAGMA table_info(rol_permisos_botones)")
        estructura = cursor.fetchall()
        
        print("\n📋 Estructura de la tabla 'rol_permisos_botones':")
        for campo in estructura:
            print(f"  - {campo[1]} ({campo[2]}) - {'NOT NULL' if campo[3] else 'NULL'}")
        
        # Contar registros
        cursor.execute("SELECT COUNT(*) FROM rol_permisos_botones")
        total_registros = cursor.fetchone()[0]
        print(f"\n📊 Total de registros: {total_registros}")
        
        if total_registros > 0:
            # Mostrar algunos registros de ejemplo
            cursor.execute("SELECT * FROM rol_permisos_botones LIMIT 5")
            registros = cursor.fetchall()
            
            print("\n📝 Primeros 5 registros:")
            for registro in registros:
                print(f"  {registro}")
        
        connection.close()
        
    except Exception as e:
        print(f"❌ Error verificando estructura local: {e}")

if __name__ == "__main__":
    print("🔍 Verificando estructura de tabla 'rol_permisos_botones' en base de datos local...\n")
    verificar_estructura_local()