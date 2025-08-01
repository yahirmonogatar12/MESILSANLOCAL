#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para verificar si la tabla rol_permisos_botones existe en la base de datos del hosting
Usando conexión directa a MySQL
"""

import mysql.connector
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv('hosting_config_mysql_directo.env')

def conectar_hosting():
    """Conectar a la base de datos del hosting"""
    try:
        connection = mysql.connector.connect(
            host=os.getenv('MYSQL_HOST'),
            user=os.getenv('MYSQL_USERNAME'),
            password=os.getenv('MYSQL_PASSWORD'),
            database=os.getenv('MYSQL_DATABASE'),
            port=int(os.getenv('MYSQL_PORT', 3306))
        )
        print(f"✅ Conexión exitosa a la base de datos del hosting: {os.getenv('MYSQL_DATABASE')}")
        return connection
    except Exception as e:
        print(f"❌ Error conectando a la base de datos del hosting: {e}")
        return None

def verificar_tabla_rol_permisos_botones():
    """Verificar si existe la tabla rol_permisos_botones"""
    connection = conectar_hosting()
    if not connection:
        return
    
    try:
        cursor = connection.cursor()
        
        # Verificar si la tabla existe
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_schema = %s 
            AND table_name = 'rol_permisos_botones'
        """, (os.getenv('MYSQL_DATABASE'),))
        
        existe = cursor.fetchone()[0] > 0
        
        if existe:
            print("✅ La tabla 'rol_permisos_botones' SÍ existe en la base de datos")
            
            # Obtener estructura de la tabla
            cursor.execute("DESCRIBE rol_permisos_botones")
            estructura = cursor.fetchall()
            
            print("\n📋 Estructura de la tabla 'rol_permisos_botones':")
            for campo in estructura:
                print(f"  - {campo[0]} ({campo[1]}) - {campo[3] if campo[3] else 'NOT NULL'}")
            
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
                    
                # Verificar roles únicos
                cursor.execute("SELECT DISTINCT rol_id FROM rol_permisos_botones")
                roles = cursor.fetchall()
                print(f"\n👥 Roles con permisos asignados: {[r[0] for r in roles]}")
                
                # Verificar permisos del rol superadmin (ID 1)
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM rol_permisos_botones 
                    WHERE rol_id = 1
                """)
                permisos_superadmin = cursor.fetchone()[0]
                print(f"\n🔑 Permisos asignados al rol superadmin (ID 1): {permisos_superadmin}")
                
        else:
            print("❌ La tabla 'rol_permisos_botones' NO existe en la base de datos")
            
            # Listar todas las tablas que contienen 'permiso' en el nombre
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = %s 
                AND table_name LIKE '%permiso%'
            """, (os.getenv('MYSQL_DATABASE'),))
            
            tablas_permisos = cursor.fetchall()
            if tablas_permisos:
                print("\n📋 Tablas relacionadas con permisos encontradas:")
                for tabla in tablas_permisos:
                    print(f"  - {tabla[0]}")
            else:
                print("\n❌ No se encontraron tablas relacionadas con permisos")
                
            # Listar todas las tablas disponibles
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = %s 
                ORDER BY table_name
            """, (os.getenv('MYSQL_DATABASE'),))
            
            todas_tablas = cursor.fetchall()
            print("\n📋 Todas las tablas en la base de datos:")
            for tabla in todas_tablas:
                print(f"  - {tabla[0]}")
        
    except Exception as e:
        print(f"❌ Error verificando la tabla: {e}")
    finally:
        if connection:
            connection.close()
            print("\n🔐 Conexión cerrada")

if __name__ == "__main__":
    print("🔍 Verificando existencia de tabla 'rol_permisos_botones' en hosting...\n")
    verificar_tabla_rol_permisos_botones()