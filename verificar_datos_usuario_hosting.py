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

def verificar_estructura_usuarios(conn):
    """Verificar la estructura de la tabla usuarios"""
    try:
        cursor = conn.cursor()
        cursor.execute("DESCRIBE usuarios")
        estructura = cursor.fetchall()
        
        print("\n📋 Estructura de la tabla 'usuarios':")
        for campo in estructura:
            print(f"  - {campo['Field']}: {campo['Type']} {'(NULL)' if campo['Null'] == 'YES' else '(NOT NULL)'}")
        
        return [campo['Field'] for campo in estructura]
    except Exception as e:
        print(f"❌ Error verificando estructura de usuarios: {e}")
        return []

def verificar_datos_usuarios(conn):
    """Verificar los datos de usuarios existentes"""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM usuarios")
        usuarios = cursor.fetchall()
        
        print(f"\n👥 Total de usuarios en la base de datos: {len(usuarios)}")
        
        if usuarios:
            print("\n📝 Usuarios encontrados:")
            for i, usuario in enumerate(usuarios, 1):
                print(f"\n  Usuario {i}:")
                for campo, valor in usuario.items():
                    if campo == 'password_hash':
                        print(f"    {campo}: {'***' if valor else 'NULL'}")
                    else:
                        print(f"    {campo}: {valor}")
        else:
            print("⚠️  No se encontraron usuarios en la base de datos")
        
        return usuarios
    except Exception as e:
        print(f"❌ Error verificando datos de usuarios: {e}")
        return []

def verificar_tablas_relacionadas(conn):
    """Verificar tablas relacionadas con usuarios"""
    tablas_verificar = ['roles', 'usuario_roles', 'sesiones_activas']
    
    for tabla in tablas_verificar:
        try:
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) as total FROM {tabla}")
            resultado = cursor.fetchone()
            print(f"\n📊 Tabla '{tabla}': {resultado['total']} registros")
            
            if resultado['total'] > 0 and resultado['total'] <= 10:
                cursor.execute(f"SELECT * FROM {tabla} LIMIT 5")
                registros = cursor.fetchall()
                print(f"  Primeros registros:")
                for registro in registros:
                    print(f"    {registro}")
                    
        except Exception as e:
            print(f"❌ Error verificando tabla '{tabla}': {e}")

def main():
    print("🔍 Verificando datos de usuario en el hosting...\n")
    
    # Conectar al hosting
    conn = conectar_hosting()
    if not conn:
        return
    
    try:
        # Verificar estructura de usuarios
        campos = verificar_estructura_usuarios(conn)
        
        # Verificar datos de usuarios
        usuarios = verificar_datos_usuarios(conn)
        
        # Verificar tablas relacionadas
        verificar_tablas_relacionadas(conn)
        
        print("\n✅ Verificación completada")
        
    except Exception as e:
        print(f"❌ Error durante la verificación: {e}")
    finally:
        conn.close()
        print("\n🔌 Conexión cerrada")

if __name__ == "__main__":
    main()