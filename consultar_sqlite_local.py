#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para consultar la estructura de la base de datos SQLite local
y verificar las tablas de usuarios y permisos
"""

import sqlite3
import os

def conectar_sqlite():
    """Conectar a la base de datos SQLite local"""
    db_path = os.path.join('app', 'database', 'ISEMM_MES.db')
    if not os.path.exists(db_path):
        print(f"❌ No se encontró la base de datos SQLite en: {db_path}")
        return None
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        print(f"✅ Conectado a SQLite: {db_path}")
        return conn
    except Exception as e:
        print(f"❌ Error conectando a SQLite: {e}")
        return None

def listar_tablas(conn):
    """Listar todas las tablas en la base de datos"""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tablas = cursor.fetchall()
        
        print("\n🗂️ Tablas en la base de datos SQLite:")
        print("=" * 50)
        for tabla in tablas:
            print(f"   - {tabla[0]}")
        
        return [tabla[0] for tabla in tablas]
    except Exception as e:
        print(f"❌ Error listando tablas: {e}")
        return []

def describir_tabla(conn, nombre_tabla):
    """Describir la estructura de una tabla"""
    try:
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({nombre_tabla})")
        columnas = cursor.fetchall()
        
        print(f"\n📋 Estructura de la tabla '{nombre_tabla}':")
        print("-" * 60)
        for col in columnas:
            print(f"   {col[1]} ({col[2]}) - PK: {bool(col[5])} - NOT NULL: {bool(col[3])}")
        
        return columnas
    except Exception as e:
        print(f"❌ Error describiendo tabla {nombre_tabla}: {e}")
        return []

def consultar_usuarios(conn):
    """Consultar usuarios en las tablas relacionadas"""
    tablas_usuarios = ['usuarios_sistema', 'usuarios', 'user_sessions', 'usuario_roles']
    
    for tabla in tablas_usuarios:
        try:
            cursor = conn.cursor()
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{tabla}'")
            if cursor.fetchone():
                print(f"\n👥 Datos en la tabla '{tabla}':")
                print("-" * 50)
                
                cursor.execute(f"SELECT * FROM {tabla} LIMIT 10")
                rows = cursor.fetchall()
                
                if rows:
                    # Mostrar nombres de columnas
                    columnas = [description[0] for description in cursor.description]
                    print(f"   Columnas: {', '.join(columnas)}")
                    print()
                    
                    # Mostrar datos
                    for i, row in enumerate(rows, 1):
                        print(f"   {i}. {dict(row)}")
                else:
                    print("   (Sin datos)")
            else:
                print(f"\n❌ Tabla '{tabla}' no existe")
        except Exception as e:
            print(f"❌ Error consultando tabla {tabla}: {e}")

def consultar_permisos(conn):
    """Consultar permisos en las tablas relacionadas"""
    tablas_permisos = ['roles', 'permisos_botones', 'rol_permisos_botones', 'rol_permisos']
    
    for tabla in tablas_permisos:
        try:
            cursor = conn.cursor()
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{tabla}'")
            if cursor.fetchone():
                print(f"\n🔐 Datos en la tabla '{tabla}':")
                print("-" * 50)
                
                cursor.execute(f"SELECT * FROM {tabla} LIMIT 10")
                rows = cursor.fetchall()
                
                if rows:
                    # Mostrar nombres de columnas
                    columnas = [description[0] for description in cursor.description]
                    print(f"   Columnas: {', '.join(columnas)}")
                    print()
                    
                    # Mostrar datos
                    for i, row in enumerate(rows, 1):
                        print(f"   {i}. {dict(row)}")
                else:
                    print("   (Sin datos)")
            else:
                print(f"\n❌ Tabla '{tabla}' no existe")
        except Exception as e:
            print(f"❌ Error consultando tabla {tabla}: {e}")

def main():
    print("🔍 Consultando base de datos SQLite local...")
    print("=" * 60)
    
    # Conectar a SQLite
    conn = conectar_sqlite()
    if not conn:
        return
    
    try:
        # Listar todas las tablas
        tablas = listar_tablas(conn)
        
        # Describir tablas relacionadas con usuarios y permisos
        tablas_importantes = ['usuarios_sistema', 'usuarios', 'roles', 'permisos_botones', 
                             'rol_permisos_botones', 'rol_permisos', 'usuario_roles']
        
        for tabla in tablas_importantes:
            if tabla in tablas:
                describir_tabla(conn, tabla)
        
        # Consultar datos de usuarios
        consultar_usuarios(conn)
        
        # Consultar datos de permisos
        consultar_permisos(conn)
        
    finally:
        conn.close()
        print("\n🔚 Consulta completada")

if __name__ == "__main__":
    main()