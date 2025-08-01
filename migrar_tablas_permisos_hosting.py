#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para migrar las tablas de permisos faltantes al hosting MySQL
Tablas: roles, rol_permisos, rol_permisos_botones
"""

import pymysql
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración de la base de datos local (Tailscale)
LOCAL_CONFIG = {
    'host': '100.111.108.116',
    'port': 3306,
    'user': 'ILSANMES',
    'password': 'ISEMM2025',
    'database': 'isemm2025',
    'charset': 'utf8mb4'
}

# Configuración de la base de datos del hosting
HOSTING_CONFIG = {
    'host': 'up-de-fra1-mysql-1.db.run-on-seenode.com',
    'port': 11550,
    'user': 'db_rrpq0erbdujn',
    'password': '5fUNbSRcPP3LN9K2I33Pr0ge',
    'database': 'db_rrpq0erbdujn',
    'charset': 'utf8mb4'
}

# Tablas de permisos a migrar
TABLAS_PERMISOS = ['roles', 'rol_permisos', 'rol_permisos_botones']

def conectar_db(config):
    """Conectar a la base de datos"""
    try:
        connection = pymysql.connect(**config)
        print(f"✅ Conectado a {config['host']}:{config['port']}")
        return connection
    except Exception as e:
        print(f"❌ Error conectando a {config['host']}: {e}")
        return None

def obtener_estructura_tabla(cursor, tabla):
    """Obtener la estructura de una tabla"""
    cursor.execute(f"SHOW CREATE TABLE {tabla}")
    result = cursor.fetchone()
    return result[1] if result else None

def obtener_datos_tabla(cursor, tabla):
    """Obtener todos los datos de una tabla"""
    cursor.execute(f"SELECT * FROM {tabla}")
    return cursor.fetchall()

def obtener_columnas_tabla(cursor, tabla):
    """Obtener las columnas de una tabla"""
    cursor.execute(f"DESCRIBE {tabla}")
    return [row[0] for row in cursor.fetchall()]

def crear_tabla_si_no_existe(cursor, tabla, create_statement):
    """Crear tabla si no existe"""
    try:
        # Verificar si la tabla existe
        cursor.execute(f"SHOW TABLES LIKE '{tabla}'")
        if cursor.fetchone():
            print(f"⚠️  Tabla {tabla} ya existe, eliminándola para recrear...")
            cursor.execute(f"DROP TABLE {tabla}")
        
        # Crear la tabla
        cursor.execute(create_statement)
        print(f"✅ Tabla {tabla} creada exitosamente")
        return True
    except Exception as e:
        print(f"❌ Error creando tabla {tabla}: {e}")
        return False

def insertar_datos(cursor, tabla, columnas, datos):
    """Insertar datos en una tabla"""
    if not datos:
        print(f"⚠️  No hay datos para insertar en {tabla}")
        return 0
    
    try:
        # Preparar la consulta de inserción
        placeholders = ', '.join(['%s'] * len(columnas))
        query = f"INSERT INTO {tabla} ({', '.join(columnas)}) VALUES ({placeholders})"
        
        # Insertar datos
        cursor.executemany(query, datos)
        count = cursor.rowcount
        print(f"✅ Insertados {count} registros en {tabla}")
        return count
    except Exception as e:
        print(f"❌ Error insertando datos en {tabla}: {e}")
        return 0

def migrar_tablas_permisos():
    """Migrar las tablas de permisos al hosting"""
    print("🚀 Iniciando migración de tablas de permisos...")
    
    # Conectar a ambas bases de datos
    conn_local = conectar_db(LOCAL_CONFIG)
    conn_hosting = conectar_db(HOSTING_CONFIG)
    
    if not conn_local or not conn_hosting:
        print("❌ No se pudo conectar a las bases de datos")
        return False
    
    try:
        cursor_local = conn_local.cursor()
        cursor_hosting = conn_hosting.cursor()
        
        total_migrados = 0
        
        for tabla in TABLAS_PERMISOS:
            print(f"\n📋 Procesando tabla: {tabla}")
            
            try:
                # Obtener estructura de la tabla
                estructura = obtener_estructura_tabla(cursor_local, tabla)
                if not estructura:
                    print(f"⚠️  Tabla {tabla} no encontrada en la base local")
                    continue
                
                # Crear tabla en el hosting
                if not crear_tabla_si_no_existe(cursor_hosting, tabla, estructura):
                    continue
                
                # Obtener datos de la tabla local
                datos = obtener_datos_tabla(cursor_local, tabla)
                columnas = obtener_columnas_tabla(cursor_local, tabla)
                
                # Insertar datos en el hosting
                count = insertar_datos(cursor_hosting, tabla, columnas, datos)
                total_migrados += count
                
            except Exception as e:
                print(f"❌ Error procesando tabla {tabla}: {e}")
                continue
        
        # Confirmar cambios
        conn_hosting.commit()
        print(f"\n🎉 Migración completada exitosamente!")
        print(f"📊 Total de registros migrados: {total_migrados}")
        
        # Verificar las tablas creadas
        print("\n🔍 Verificando tablas creadas en el hosting:")
        for tabla in TABLAS_PERMISOS:
            cursor_hosting.execute(f"SELECT COUNT(*) FROM {tabla}")
            count = cursor_hosting.fetchone()[0]
            print(f"  - {tabla}: {count} registros")
        
        return True
        
    except Exception as e:
        print(f"❌ Error durante la migración: {e}")
        return False
    
    finally:
        if conn_local:
            conn_local.close()
        if conn_hosting:
            conn_hosting.close()

def verificar_permisos_hosting():
    """Verificar que las tablas de permisos existen en el hosting"""
    print("\n🔍 Verificando tablas de permisos en el hosting...")
    
    conn = conectar_db(HOSTING_CONFIG)
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        for tabla in TABLAS_PERMISOS:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {tabla}")
                count = cursor.fetchone()[0]
                print(f"✅ {tabla}: {count} registros")
            except Exception as e:
                print(f"❌ Error verificando {tabla}: {e}")
        
        return True
        
    finally:
        conn.close()

if __name__ == "__main__":
    print("=" * 60)
    print("🔐 MIGRACIÓN DE TABLAS DE PERMISOS AL HOSTING")
    print("=" * 60)
    
    # Ejecutar migración
    if migrar_tablas_permisos():
        # Verificar resultado
        verificar_permisos_hosting()
        print("\n✅ Las tablas de permisos han sido migradas exitosamente al hosting!")
        print("🎯 Ahora el sistema de permisos debería funcionar correctamente.")
    else:
        print("\n❌ La migración falló. Revisa los errores anteriores.")