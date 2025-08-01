#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script completo de migración de SQLite a MySQL
Elimina todas las tablas de MySQL y las recrea con la estructura de SQLite
Luego migra todos los datos
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

# Mapeo de tipos de datos SQLite a MySQL
TIPOS_SQLITE_MYSQL = {
    'INTEGER': 'INT',
    'TEXT': 'TEXT',
    'REAL': 'DECIMAL(10,2)',
    'BLOB': 'LONGBLOB',
    'NUMERIC': 'DECIMAL(10,2)'
}

def conectar_sqlite():
    """Conecta a la base de datos SQLite"""
    try:
        if not os.path.exists(SQLITE_DB_PATH):
            print(f"❌ Error: Archivo SQLite no encontrado en {SQLITE_DB_PATH}")
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
        return None

def obtener_tablas_sqlite(cursor_sqlite):
    """Obtiene la lista de tablas en SQLite"""
    cursor_sqlite.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tablas = [row[0] for row in cursor_sqlite.fetchall()]
    # Filtrar tablas con nombres problemáticos
    tablas_validas = []
    for tabla in tablas:
        if '-' in tabla or ' ' in tabla or tabla.lower() in ['table', 'table-name']:
            print(f"  ⚠️ Saltando tabla con nombre problemático: {tabla}")
            continue
        tablas_validas.append(tabla)
    return tablas_validas

def obtener_estructura_tabla_sqlite(cursor_sqlite, tabla):
    """Obtiene la estructura de una tabla en SQLite"""
    cursor_sqlite.execute(f"PRAGMA table_info({tabla})")
    return cursor_sqlite.fetchall()

def convertir_tipo_sqlite_mysql(tipo_sqlite):
    """Convierte tipos de datos de SQLite a MySQL"""
    tipo_upper = tipo_sqlite.upper()
    for sqlite_type, mysql_type in TIPOS_SQLITE_MYSQL.items():
        if sqlite_type in tipo_upper:
            return mysql_type
    return 'VARCHAR(255)'  # Tipo por defecto

def crear_tabla_mysql(cursor_mysql, tabla, estructura_sqlite):
    """Crea una tabla en MySQL basada en la estructura de SQLite"""
    print(f"  🔧 Creando tabla {tabla} en MySQL...")
    
    # Construir definición de columnas
    columnas = []
    primary_key = None
    
    for col in estructura_sqlite:
        cid, name, type_sqlite, notnull, dflt_value, pk = col
        
        # Convertir tipo
        tipo_mysql = convertir_tipo_sqlite_mysql(type_sqlite)
        
        # Construir definición de columna
        col_def = f"`{name}` {tipo_mysql}"
        
        # Agregar AUTO_INCREMENT para primary key INTEGER
        if pk and tipo_mysql == 'INT':
            col_def += " AUTO_INCREMENT"
            primary_key = name
        
        # Agregar NOT NULL
        if notnull:
            col_def += " NOT NULL"
        
        # Agregar valor por defecto (solo para tipos que lo permiten)
        if dflt_value is not None and tipo_mysql not in ['TEXT', 'LONGTEXT', 'MEDIUMTEXT', 'LONGBLOB', 'MEDIUMBLOB', 'BLOB']:
            if tipo_mysql.startswith('VARCHAR'):
                col_def += f" DEFAULT '{dflt_value}'"
            else:
                col_def += f" DEFAULT {dflt_value}"
        
        columnas.append(col_def)
    
    # Agregar primary key
    if primary_key:
        columnas.append(f"PRIMARY KEY (`{primary_key}`)")
    
    # Crear tabla
    create_sql = f"""
    CREATE TABLE `{tabla}` (
        {',\n        '.join(columnas)}
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """
    
    try:
        cursor_mysql.execute(create_sql)
        print(f"    ✅ Tabla {tabla} creada exitosamente")
        return True
    except Exception as e:
        print(f"    ❌ Error creando tabla {tabla}: {e}")
        return False

def eliminar_todas_las_tablas_mysql(cursor_mysql):
    """Elimina todas las tablas de MySQL"""
    print("\n🗑️ Eliminando todas las tablas de MySQL...")
    
    try:
        # Desactivar verificación de claves foráneas
        cursor_mysql.execute("SET FOREIGN_KEY_CHECKS = 0")
        
        # Obtener lista de tablas
        cursor_mysql.execute("SHOW TABLES")
        tablas = [row[f'Tables_in_{MYSQL_CONFIG["database"]}'] for row in cursor_mysql.fetchall()]
        
        # Eliminar cada tabla
        for tabla in tablas:
            cursor_mysql.execute(f"DROP TABLE IF EXISTS `{tabla}`")
            print(f"  - Tabla {tabla} eliminada")
        
        # Reactivar verificación de claves foráneas
        cursor_mysql.execute("SET FOREIGN_KEY_CHECKS = 1")
        
        print(f"  ✅ {len(tablas)} tablas eliminadas")
        return True
        
    except Exception as e:
        print(f"  ❌ Error eliminando tablas: {e}")
        return False

def migrar_datos_tabla(tabla, cursor_sqlite, cursor_mysql):
    """Migra los datos de una tabla específica"""
    print(f"  📊 Migrando datos de {tabla}...")
    
    try:
        # Obtener datos de SQLite
        cursor_sqlite.execute(f"SELECT * FROM `{tabla}`")
        datos = cursor_sqlite.fetchall()
        
        if not datos:
            print(f"    - Tabla {tabla} está vacía")
            return True
        
        print(f"    - Encontrados {len(datos)} registros")
        
        # Obtener nombres de columnas
        columnas = [description[0] for description in cursor_sqlite.description]
        
        # Preparar consulta de inserción
        placeholders = ', '.join(['%s'] * len(columnas))
        columnas_str = ', '.join([f'`{col}`' for col in columnas])
        query = f"INSERT INTO `{tabla}` ({columnas_str}) VALUES ({placeholders})"
        
        # Insertar datos
        registros_insertados = 0
        errores = 0
        
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
                
                if registros_insertados % 100 == 0:
                    print(f"      - Insertados {registros_insertados} registros...")
                    
            except Exception as e:
                errores += 1
                if errores <= 5:  # Mostrar solo los primeros 5 errores
                    print(f"      ⚠️ Error insertando registro: {e}")
                continue
        
        print(f"    ✅ {registros_insertados} registros insertados")
        if errores > 0:
            print(f"    ⚠️ {errores} errores")
        
        return True
        
    except Exception as e:
        print(f"    ❌ Error migrando tabla {tabla}: {e}")
        return False

def migrar_completo():
    """Función principal de migración completa"""
    print("=== MIGRACIÓN COMPLETA DE SQLITE A MYSQL ===")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
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
        
        # Eliminar todas las tablas de MySQL
        if not eliminar_todas_las_tablas_mysql(cursor_mysql):
            return False
        
        conn_mysql.commit()
        
        # Obtener lista de tablas de SQLite
        tablas = obtener_tablas_sqlite(cursor_sqlite)
        print(f"\n📋 Tablas encontradas en SQLite: {len(tablas)}")
        for tabla in tablas:
            print(f"  - {tabla}")
        
        # Recrear tablas en MySQL
        print("\n🔧 Recreando tablas en MySQL...")
        tablas_creadas = 0
        
        for tabla in tablas:
            estructura = obtener_estructura_tabla_sqlite(cursor_sqlite, tabla)
            if crear_tabla_mysql(cursor_mysql, tabla, estructura):
                tablas_creadas += 1
            conn_mysql.commit()
        
        print(f"\n✅ {tablas_creadas} tablas recreadas")
        
        # Migrar datos
        print("\n💾 Migrando datos...")
        tablas_migradas = 0
        
        for tabla in tablas:
            if migrar_datos_tabla(tabla, cursor_sqlite, cursor_mysql):
                tablas_migradas += 1
            conn_mysql.commit()
        
        print(f"\n=== RESUMEN DE MIGRACIÓN COMPLETA ===")
        print(f"✅ Tablas recreadas: {tablas_creadas}/{len(tablas)}")
        print(f"✅ Tablas migradas: {tablas_migradas}/{len(tablas)}")
        
        if tablas_creadas == len(tablas) and tablas_migradas == len(tablas):
            print("\n🎉 MIGRACIÓN COMPLETA EXITOSA")
        else:
            print("\n⚠️ MIGRACIÓN COMPLETADA CON ALGUNOS ERRORES")
        
        return tablas_creadas == len(tablas) and tablas_migradas == len(tablas)
        
    except Exception as e:
        print(f"❌ Error durante la migración: {e}")
        return False
    
    finally:
        # Cerrar conexiones
        if conn_sqlite:
            conn_sqlite.close()
        if conn_mysql:
            conn_mysql.close()

def verificar_migracion_completa():
    """Verifica que la migración completa se realizó correctamente"""
    print("\n=== VERIFICACIÓN DE MIGRACIÓN COMPLETA ===")
    
    conn_sqlite = conectar_sqlite()
    conn_mysql = conectar_mysql()
    
    if not conn_sqlite or not conn_mysql:
        return False
    
    try:
        cursor_sqlite = conn_sqlite.cursor()
        cursor_mysql = conn_mysql.cursor()
        
        # Obtener tablas de SQLite
        tablas = obtener_tablas_sqlite(cursor_sqlite)
        
        total_sqlite = 0
        total_mysql = 0
        coincidencias = 0
        
        for tabla in tablas:
            # Contar registros en SQLite
            cursor_sqlite.execute(f"SELECT COUNT(*) FROM `{tabla}`")
            count_sqlite = cursor_sqlite.fetchone()[0]
            total_sqlite += count_sqlite
            
            # Contar registros en MySQL
            try:
                cursor_mysql.execute(f"SELECT COUNT(*) FROM `{tabla}`")
                count_mysql = cursor_mysql.fetchone()['COUNT(*)']
                total_mysql += count_mysql
                
                if count_sqlite == count_mysql:
                    print(f"✅ {tabla}: {count_sqlite} registros (coincide)")
                    coincidencias += 1
                else:
                    print(f"❌ {tabla}: SQLite={count_sqlite}, MySQL={count_mysql} (no coincide)")
            except:
                print(f"⚠️ {tabla}: No existe en MySQL")
        
        print(f"\n📊 Resumen:")
        print(f"  - Total registros SQLite: {total_sqlite}")
        print(f"  - Total registros MySQL: {total_mysql}")
        print(f"  - Tablas que coinciden: {coincidencias}/{len(tablas)}")
        
        return coincidencias == len(tablas)
        
    except Exception as e:
        print(f"❌ Error verificando migración: {e}")
        return False
    
    finally:
        if conn_sqlite:
            conn_sqlite.close()
        if conn_mysql:
            conn_mysql.close()

if __name__ == "__main__":
    print("🚀 Iniciando migración completa de SQLite a MySQL...")
    print("⚠️ ADVERTENCIA: Esto eliminará TODAS las tablas de MySQL y las recreará")
    
    respuesta = input("¿Continuar? (s/N): ")
    if respuesta.lower() not in ['s', 'si', 'sí', 'y', 'yes']:
        print("❌ Migración cancelada")
        exit()
    
    # Realizar migración completa
    if migrar_completo():
        # Verificar migración
        verificar_migracion_completa()
        print("\n🎉 Proceso de migración completa finalizado")
    else:
        print("\n❌ Error en el proceso de migración completa")
    
    input("\nPresiona Enter para continuar...")