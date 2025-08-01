#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de migración de datos de SQLite a MySQL
Migra todos los datos existentes de la base de datos SQLite a MySQL
"""

import sqlite3
import pymysql
import os
from datetime import datetime
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración de bases de datos
SQLITE_DB_PATH = 'app/database/ISEMM_MES.db'
MYSQL_CONFIG = {
    'host': os.getenv('MYSQL_HOST', 'localhost'),
    'user': os.getenv('MYSQL_USERNAME', 'root'),
    'password': os.getenv('MYSQL_PASSWORD', ''),
    'database': os.getenv('MYSQL_DATABASE', 'isemm_mes'),
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

def conectar_sqlite():
    """Conecta a la base de datos SQLite"""
    try:
        if not os.path.exists(SQLITE_DB_PATH):
            print(f"Error: Archivo SQLite no encontrado en {SQLITE_DB_PATH}")
            return None
        conn = sqlite3.connect(SQLITE_DB_PATH)
        conn.row_factory = sqlite3.Row
        print(f"✅ Conectado a SQLite: {SQLITE_DB_PATH}")
        return conn
    except Exception as e:
        print(f"❌ Error conectando a SQLite: {e}")
        return None

def conectar_mysql():
    """Conecta a la base de datos MySQL"""
    try:
        conn = pymysql.connect(**MYSQL_CONFIG)
        print(f"✅ Conectado a MySQL: {MYSQL_CONFIG['host']}:{MYSQL_CONFIG['database']}")
        return conn
    except Exception as e:
        print(f"❌ Error conectando a MySQL: {e}")
        print(f"   Configuración: {MYSQL_CONFIG}")
        return None

def obtener_tablas_sqlite(cursor_sqlite):
    """Obtiene la lista de tablas en SQLite"""
    cursor_sqlite.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    return [row[0] for row in cursor_sqlite.fetchall()]

def migrar_tabla(tabla, cursor_sqlite, cursor_mysql):
    """Migra una tabla específica de SQLite a MySQL"""
    print(f"\nMigrando tabla: {tabla}")
    
    try:
        # Obtener datos de SQLite
        cursor_sqlite.execute(f"SELECT * FROM {tabla}")
        datos = cursor_sqlite.fetchall()
        
        if not datos:
            print(f"  - Tabla {tabla} está vacía")
            return True
        
        print(f"  - Encontrados {len(datos)} registros")
        
        # Obtener nombres de columnas
        columnas = [description[0] for description in cursor_sqlite.description]
        
        # Verificar si la tabla existe en MySQL
        cursor_mysql.execute(f"SHOW TABLES LIKE '{tabla}'")
        if not cursor_mysql.fetchone():
            print(f"  - Tabla {tabla} no existe en MySQL, saltando...")
            return True
        
        # Limpiar tabla en MySQL antes de insertar
        cursor_mysql.execute(f"DELETE FROM {tabla}")
        print(f"  - Tabla {tabla} limpiada en MySQL")
        
        # Preparar consulta de inserción
        placeholders = ', '.join(['%s'] * len(columnas))
        columnas_str = ', '.join(columnas)
        query = f"INSERT INTO {tabla} ({columnas_str}) VALUES ({placeholders})"
        
        # Insertar datos
        registros_insertados = 0
        for fila in datos:
            try:
                valores = []
                for valor in fila:
                    # Convertir valores None a NULL
                    if valor is None:
                        valores.append(None)
                    else:
                        valores.append(valor)
                
                cursor_mysql.execute(query, valores)
                registros_insertados += 1
            except Exception as e:
                print(f"    Error insertando registro: {e}")
                print(f"    Valores: {valores}")
                continue
        
        print(f"  - {registros_insertados} registros insertados exitosamente")
        return True
        
    except Exception as e:
        print(f"  Error migrando tabla {tabla}: {e}")
        return False

def migrar_datos():
    """Función principal de migración"""
    print("=== MIGRACIÓN DE DATOS SQLITE A MYSQL ===")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Verificar que existe la base de datos SQLite
    if not os.path.exists(SQLITE_DB_PATH):
        print(f"Error: No se encontró la base de datos SQLite en {SQLITE_DB_PATH}")
        return False
    
    # Conectar a las bases de datos
    conn_sqlite = conectar_sqlite()
    if not conn_sqlite:
        return False
    
    conn_mysql = conectar_mysql()
    if not conn_mysql:
        conn_sqlite.close()
        return False
    
    try:
        cursor_sqlite = conn_sqlite.cursor()
        cursor_mysql = conn_mysql.cursor()
        
        # Obtener lista de tablas
        tablas = obtener_tablas_sqlite(cursor_sqlite)
        print(f"\nTablas encontradas en SQLite: {len(tablas)}")
        for tabla in tablas:
            print(f"  - {tabla}")
        
        # Migrar cada tabla
        tablas_exitosas = 0
        tablas_fallidas = 0
        
        for tabla in tablas:
            if migrar_tabla(tabla, cursor_sqlite, cursor_mysql):
                tablas_exitosas += 1
            else:
                tablas_fallidas += 1
            
            # Confirmar cambios después de cada tabla
            conn_mysql.commit()
        
        print(f"\n=== RESUMEN DE MIGRACIÓN ===")
        print(f"Tablas migradas exitosamente: {tablas_exitosas}")
        print(f"Tablas con errores: {tablas_fallidas}")
        print(f"Total de tablas: {len(tablas)}")
        
        if tablas_fallidas == 0:
            print("\n✅ MIGRACIÓN COMPLETADA EXITOSAMENTE")
        else:
            print("\n⚠️  MIGRACIÓN COMPLETADA CON ALGUNOS ERRORES")
        
        return tablas_fallidas == 0
        
    except Exception as e:
        print(f"Error durante la migración: {e}")
        return False
    
    finally:
        # Cerrar conexiones
        if conn_sqlite:
            conn_sqlite.close()
        if conn_mysql:
            conn_mysql.close()

def verificar_migracion():
    """Verifica que la migración se realizó correctamente"""
    print("\n=== VERIFICACIÓN DE MIGRACIÓN ===")
    
    conn_sqlite = conectar_sqlite()
    conn_mysql = conectar_mysql()
    
    if not conn_sqlite or not conn_mysql:
        return False
    
    try:
        cursor_sqlite = conn_sqlite.cursor()
        cursor_mysql = conn_mysql.cursor()
        
        # Obtener tablas de SQLite
        tablas = obtener_tablas_sqlite(cursor_sqlite)
        
        for tabla in tablas:
            # Contar registros en SQLite
            cursor_sqlite.execute(f"SELECT COUNT(*) FROM {tabla}")
            count_sqlite = cursor_sqlite.fetchone()[0]
            
            # Contar registros en MySQL
            try:
                cursor_mysql.execute(f"SELECT COUNT(*) FROM {tabla}")
                count_mysql = cursor_mysql.fetchone()['COUNT(*)']
                
                if count_sqlite == count_mysql:
                    print(f"✅ {tabla}: {count_sqlite} registros (coincide)")
                else:
                    print(f"❌ {tabla}: SQLite={count_sqlite}, MySQL={count_mysql} (no coincide)")
            except:
                print(f"⚠️  {tabla}: No existe en MySQL")
        
        return True
        
    except Exception as e:
        print(f"Error verificando migración: {e}")
        return False
    
    finally:
        if conn_sqlite:
            conn_sqlite.close()
        if conn_mysql:
            conn_mysql.close()

if __name__ == "__main__":
    print("Iniciando migración de SQLite a MySQL...")
    
    # Realizar migración
    if migrar_datos():
        # Verificar migración
        verificar_migracion()
        print("\n🎉 Proceso de migración finalizado")
    else:
        print("\n❌ Error en el proceso de migración")
    
    input("\nPresiona Enter para continuar...")