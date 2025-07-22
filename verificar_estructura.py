#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para verificar estructura de tablas de usuarios
"""

import sqlite3
import os

def verificar_estructura_bd():
    db_path = os.path.join(os.path.dirname(__file__), 'app', 'database', 'ISEMM_MES.db')
    
    if not os.path.exists(db_path):
        print(f"❌ Base de datos no encontrada: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("🔍 Verificando estructura de tablas de usuarios...")
    print("=" * 60)
    
    # Obtener todas las tablas
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tablas = cursor.fetchall()
    
    print("\n📋 Tablas disponibles:")
    for tabla in tablas:
        print(f"   📄 {tabla[0]}")
    
    # Verificar estructura de tabla usuarios
    tablas_usuario = ['usuarios', 'usuarios_sistema']
    
    for tabla_nombre in tablas_usuario:
        try:
            cursor.execute(f"PRAGMA table_info({tabla_nombre})")
            columnas = cursor.fetchall()
            
            if columnas:
                print(f"\n🏗️ Estructura de tabla '{tabla_nombre}':")
                for col in columnas:
                    print(f"   🔹 {col[1]} ({col[2]}) - {'NOT NULL' if col[3] else 'NULL'}")
                
                # Mostrar algunos datos de ejemplo
                cursor.execute(f"SELECT * FROM {tabla_nombre} LIMIT 3")
                datos = cursor.fetchall()
                
                if datos:
                    print(f"\n📊 Datos de ejemplo en '{tabla_nombre}':")
                    for fila in datos:
                        print(f"   📄 {fila}")
            
        except Exception as e:
            print(f"❌ Error verificando tabla '{tabla_nombre}': {e}")
    
    # Verificar estructura de tabla roles
    try:
        cursor.execute("PRAGMA table_info(roles)")
        columnas = cursor.fetchall()
        
        if columnas:
            print(f"\n🎭 Estructura de tabla 'roles':")
            for col in columnas:
                print(f"   🔹 {col[1]} ({col[2]}) - {'NOT NULL' if col[3] else 'NULL'}")
            
            cursor.execute("SELECT * FROM roles WHERE activo = 1")
            roles = cursor.fetchall()
            
            print(f"\n📊 Roles activos:")
            for rol in roles:
                print(f"   🎭 {rol}")
                
    except Exception as e:
        print(f"❌ Error verificando tabla 'roles': {e}")
    
    # Verificar relación usuario_roles
    try:
        cursor.execute("PRAGMA table_info(usuario_roles)")
        columnas = cursor.fetchall()
        
        if columnas:
            print(f"\n🔗 Estructura de tabla 'usuario_roles':")
            for col in columnas:
                print(f"   🔹 {col[1]} ({col[2]}) - {'NOT NULL' if col[3] else 'NULL'}")
            
            cursor.execute("SELECT * FROM usuario_roles LIMIT 5")
            relaciones = cursor.fetchall()
            
            print(f"\n📊 Relaciones usuario-rol:")
            for rel in relaciones:
                print(f"   🔗 {rel}")
                
    except Exception as e:
        print(f"❌ Error verificando tabla 'usuario_roles': {e}")
    
    conn.close()
    print("\n✅ Verificación completada!")

if __name__ == "__main__":
    verificar_estructura_bd()
