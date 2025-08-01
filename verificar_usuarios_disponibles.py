#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para verificar qué usuarios están disponibles en la base de datos
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

def verificar_usuarios():
    """Verificar usuarios disponibles"""
    conn = get_db_connection()
    if not conn:
        return
    
    try:
        cursor = conn.cursor()
        
        print("=== Usuarios en la base de datos ===")
        
        # Verificar usuarios_sistema
        cursor.execute("SELECT id, username, activo FROM usuarios_sistema ORDER BY username")
        usuarios = cursor.fetchall()
        
        if usuarios:
            print(f"\n👥 Usuarios encontrados ({len(usuarios)}):")
            for usuario in usuarios:
                estado = "✅ Activo" if usuario['activo'] else "❌ Inactivo"
                print(f"  - ID: {usuario['id']}, Usuario: {usuario['username']}, Estado: {estado}")
        else:
            print("❌ No se encontraron usuarios en usuarios_sistema")
        
        # Verificar si existe tabla usuarios (legacy)
        try:
            cursor.execute("SELECT id, username FROM usuarios LIMIT 5")
            usuarios_legacy = cursor.fetchall()
            if usuarios_legacy:
                print(f"\n👥 Usuarios legacy encontrados ({len(usuarios_legacy)}):")
                for usuario in usuarios_legacy:
                    print(f"  - ID: {usuario['id']}, Usuario: {usuario['username']}")
        except:
            print("\n📝 No hay tabla usuarios legacy")
        
        # Buscar específicamente el usuario Problema
        cursor.execute("SELECT * FROM usuarios_sistema WHERE username = %s", ('Problema',))
        problema = cursor.fetchone()
        
        if problema:
            print(f"\n🔍 Usuario 'Problema' encontrado:")
            print(f"  - ID: {problema['id']}")
            print(f"  - Username: {problema['username']}")
            print(f"  - Activo: {problema['activo']}")
            print(f"  - Fecha creación: {problema.get('fecha_creacion', 'N/A')}")
        else:
            print(f"\n❌ Usuario 'Problema' NO encontrado")
            
            # Sugerir usuarios alternativos
            cursor.execute("SELECT username FROM usuarios_sistema WHERE activo = 1 LIMIT 3")
            activos = cursor.fetchall()
            if activos:
                print(f"\n💡 Usuarios activos disponibles:")
                for u in activos:
                    print(f"  - {u['username']}")
        
    except Exception as e:
        print(f"Error verificando usuarios: {e}")
    finally:
        conn.close()

def main():
    print("Verificando usuarios disponibles en la base de datos...\n")
    verificar_usuarios()

if __name__ == '__main__':
    main()