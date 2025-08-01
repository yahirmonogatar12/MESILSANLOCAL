#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import pymysql
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv('hosting_config_mysql_directo.env')

def conectar_hosting():
    """Conectar a la base de datos del hosting"""
    try:
        conn = pymysql.connect(
            host=os.getenv('MYSQL_HOST'),
            port=int(os.getenv('MYSQL_PORT')),
            user=os.getenv('MYSQL_USERNAME'),
            password=os.getenv('MYSQL_PASSWORD'),
            database=os.getenv('MYSQL_DATABASE'),
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        print(f"✅ Conectado a la base de datos del hosting: {os.getenv('MYSQL_HOST')}")
        return conn
    except Exception as e:
        print(f"❌ Error conectando al hosting: {e}")
        return None

def listar_todas_las_tablas(conn):
    """Listar todas las tablas en la base de datos"""
    try:
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES")
        tablas = cursor.fetchall()
        
        print(f"\n📋 Total de tablas en la base de datos: {len(tablas)}")
        
        # Buscar tablas relacionadas con usuarios
        tablas_usuarios = []
        for tabla in tablas:
            nombre_tabla = list(tabla.values())[0]
            if 'user' in nombre_tabla.lower() or 'usuario' in nombre_tabla.lower():
                tablas_usuarios.append(nombre_tabla)
            print(f"  - {nombre_tabla}")
        
        print(f"\n👥 Tablas relacionadas con usuarios encontradas: {len(tablas_usuarios)}")
        for tabla in tablas_usuarios:
            print(f"  - {tabla}")
        
        return [list(tabla.values())[0] for tabla in tablas]
    except Exception as e:
        print(f"❌ Error listando tablas: {e}")
        return []

def verificar_tabla_especifica(conn, nombre_tabla):
    """Verificar una tabla específica"""
    try:
        cursor = conn.cursor()
        
        # Verificar estructura
        cursor.execute(f"DESCRIBE {nombre_tabla}")
        estructura = cursor.fetchall()
        
        print(f"\n📋 Estructura de la tabla '{nombre_tabla}':")
        for campo in estructura:
            print(f"  - {campo['Field']}: {campo['Type']} {'(NULL)' if campo['Null'] == 'YES' else '(NOT NULL)'}")
        
        # Verificar datos
        cursor.execute(f"SELECT COUNT(*) as total FROM {nombre_tabla}")
        total = cursor.fetchone()['total']
        print(f"\n📊 Total de registros en '{nombre_tabla}': {total}")
        
        if total > 0 and total <= 10:
            cursor.execute(f"SELECT * FROM {nombre_tabla} LIMIT 5")
            registros = cursor.fetchall()
            print(f"\n📝 Primeros registros de '{nombre_tabla}':")
            for i, registro in enumerate(registros, 1):
                print(f"  Registro {i}:")
                for campo, valor in registro.items():
                    if 'password' in campo.lower():
                        print(f"    {campo}: {'***' if valor else 'NULL'}")
                    else:
                        print(f"    {campo}: {valor}")
        
    except Exception as e:
        print(f"❌ Error verificando tabla '{nombre_tabla}': {e}")

def main():
    print("🔍 Verificando tablas de usuarios en el hosting...\n")
    
    # Conectar al hosting
    conn = conectar_hosting()
    if not conn:
        return
    
    try:
        # Listar todas las tablas
        tablas = listar_todas_las_tablas(conn)
        
        # Verificar tablas específicas relacionadas con usuarios
        tablas_verificar = []
        for tabla in tablas:
            if any(palabra in tabla.lower() for palabra in ['user', 'usuario', 'login', 'auth']):
                tablas_verificar.append(tabla)
        
        if tablas_verificar:
            print(f"\n🔍 Verificando tablas relacionadas con usuarios...")
            for tabla in tablas_verificar:
                verificar_tabla_especifica(conn, tabla)
        else:
            print("\n⚠️  No se encontraron tablas relacionadas con usuarios")
        
        print("\n✅ Verificación completada")
        
    except Exception as e:
        print(f"❌ Error durante la verificación: {e}")
    finally:
        conn.close()
        print("\n🔌 Conexión cerrada")

if __name__ == "__main__":
    main()