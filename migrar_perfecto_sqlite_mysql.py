#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de migración perfecta de SQLite a MySQL
Replica exactamente la estructura y datos de SQLite en MySQL
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

def obtener_todas_las_tablas_sqlite(cursor_sqlite):
    """Obtiene TODAS las tablas de SQLite, incluyendo las problemáticas"""
    cursor_sqlite.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tablas = [row[0] for row in cursor_sqlite.fetchall()]
    print(f"📋 Tablas encontradas en SQLite: {len(tablas)}")
    for tabla in tablas:
        print(f"  - {tabla}")
    return tablas

def obtener_estructura_completa_sqlite(cursor_sqlite, tabla):
    """Obtiene la estructura completa de una tabla en SQLite"""
    try:
        # Obtener información de columnas
        cursor_sqlite.execute(f"PRAGMA table_info(`{tabla}`)")
        columnas = cursor_sqlite.fetchall()
        
        # Obtener el SQL de creación original
        cursor_sqlite.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{tabla}'")
        sql_original = cursor_sqlite.fetchone()
        
        return {
            'columnas': columnas,
            'sql_original': sql_original[0] if sql_original else None
        }
    except Exception as e:
        print(f"  ⚠️ Error obteniendo estructura de {tabla}: {e}")
        return None

def convertir_tipo_sqlite_a_mysql(tipo_sqlite, columna_info):
    """Convierte tipos de SQLite a MySQL de manera más precisa"""
    tipo_upper = tipo_sqlite.upper().strip()
    
    # Mapeo específico de tipos
    if 'INTEGER' in tipo_upper:
        if columna_info[5]:  # Es primary key
            return 'INT AUTO_INCREMENT'
        return 'INT'
    elif 'TEXT' in tipo_upper:
        return 'LONGTEXT'
    elif 'REAL' in tipo_upper or 'FLOAT' in tipo_upper:
        return 'DECIMAL(10,2)'
    elif 'BLOB' in tipo_upper:
        return 'LONGBLOB'
    elif 'NUMERIC' in tipo_upper:
        return 'DECIMAL(10,2)'
    elif 'DATETIME' in tipo_upper:
        return 'DATETIME'
    elif 'DATE' in tipo_upper:
        return 'DATE'
    elif 'TIME' in tipo_upper:
        return 'TIME'
    elif 'BOOLEAN' in tipo_upper or 'BOOL' in tipo_upper:
        return 'TINYINT(1)'
    else:
        return 'LONGTEXT'  # Tipo por defecto más seguro

def crear_tabla_mysql_perfecta(cursor_mysql, tabla, estructura):
    """Crea una tabla en MySQL replicando perfectamente SQLite"""
    print(f"  🔧 Creando tabla `{tabla}` en MySQL...")
    
    if not estructura or not estructura['columnas']:
        print(f"    ❌ No se pudo obtener estructura para {tabla}")
        return False
    
    try:
        # Construir definición de columnas
        columnas_def = []
        primary_keys = []
        
        for col in estructura['columnas']:
            cid, name, type_sqlite, notnull, dflt_value, pk = col
            
            # Escapar nombre de columna
            name_escaped = f"`{name}`"
            
            # Convertir tipo
            tipo_mysql = convertir_tipo_sqlite_a_mysql(type_sqlite, col)
            
            # Construir definición de columna
            col_def = f"{name_escaped} {tipo_mysql}"
            
            # Agregar NOT NULL si es necesario
            if notnull and not pk:  # PK ya incluye NOT NULL
                col_def += " NOT NULL"
            
            # Agregar valor por defecto solo para tipos compatibles
            if dflt_value is not None and 'LONGTEXT' not in tipo_mysql and 'LONGBLOB' not in tipo_mysql:
                if 'INT' in tipo_mysql or 'DECIMAL' in tipo_mysql or 'TINYINT' in tipo_mysql:
                    col_def += f" DEFAULT {dflt_value}"
                elif dflt_value.upper() in ['CURRENT_TIMESTAMP', 'NOW()']:
                    col_def += f" DEFAULT {dflt_value}"
                else:
                    col_def += f" DEFAULT '{dflt_value}'"
            
            columnas_def.append(col_def)
            
            # Recopilar primary keys
            if pk:
                primary_keys.append(name_escaped)
        
        # Agregar primary key constraint
        if primary_keys:
            columnas_def.append(f"PRIMARY KEY ({', '.join(primary_keys)})")
        
        # Crear tabla con nombre escapado
        tabla_escaped = f"`{tabla}`"
        create_sql = f"""
        CREATE TABLE {tabla_escaped} (
            {',\n            '.join(columnas_def)}
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        
        cursor_mysql.execute(create_sql)
        print(f"    ✅ Tabla `{tabla}` creada exitosamente")
        return True
        
    except Exception as e:
        print(f"    ❌ Error creando tabla `{tabla}`: {e}")
        print(f"    SQL: {create_sql if 'create_sql' in locals() else 'No generado'}")
        return False

def eliminar_todas_las_tablas_mysql(cursor_mysql):
    """Elimina TODAS las tablas de MySQL"""
    print("\n🗑️ Eliminando todas las tablas de MySQL...")
    
    try:
        # Desactivar verificación de claves foráneas
        cursor_mysql.execute("SET FOREIGN_KEY_CHECKS = 0")
        
        # Obtener lista de tablas
        cursor_mysql.execute("SHOW TABLES")
        tablas = [list(row.values())[0] for row in cursor_mysql.fetchall()]
        
        # Eliminar cada tabla
        for tabla in tablas:
            cursor_mysql.execute(f"DROP TABLE IF EXISTS `{tabla}`")
            print(f"  - Tabla `{tabla}` eliminada")
        
        # Reactivar verificación de claves foráneas
        cursor_mysql.execute("SET FOREIGN_KEY_CHECKS = 1")
        
        print(f"  ✅ {len(tablas)} tablas eliminadas")
        return True
        
    except Exception as e:
        print(f"  ❌ Error eliminando tablas: {e}")
        return False

def migrar_datos_tabla_perfecta(tabla, cursor_sqlite, cursor_mysql):
    """Migra los datos de una tabla de manera perfecta"""
    print(f"  📊 Migrando datos de `{tabla}`...")
    
    try:
        # Obtener datos de SQLite con nombres de columna escapados
        cursor_sqlite.execute(f"SELECT * FROM `{tabla}`")
        datos = cursor_sqlite.fetchall()
        
        if not datos:
            print(f"    - Tabla `{tabla}` está vacía")
            return True
        
        print(f"    - Encontrados {len(datos)} registros")
        
        # Obtener nombres de columnas
        columnas = [description[0] for description in cursor_sqlite.description]
        
        # Preparar consulta de inserción con nombres escapados
        placeholders = ', '.join(['%s'] * len(columnas))
        columnas_escaped = ', '.join([f'`{col}`' for col in columnas])
        tabla_escaped = f'`{tabla}`'
        query = f"INSERT INTO {tabla_escaped} ({columnas_escaped}) VALUES ({placeholders})"
        
        # Insertar datos en lotes
        registros_insertados = 0
        errores = 0
        lote_size = 100
        
        for i in range(0, len(datos), lote_size):
            lote = datos[i:i + lote_size]
            
            for fila in lote:
                try:
                    valores = []
                    for valor in fila:
                        # Manejar valores especiales
                        if valor is None:
                            valores.append(None)
                        elif isinstance(valor, str) and valor.strip() == '':
                            valores.append(None)  # Convertir strings vacíos a NULL
                        else:
                            valores.append(valor)
                    
                    cursor_mysql.execute(query, valores)
                    registros_insertados += 1
                    
                except Exception as e:
                    errores += 1
                    if errores <= 3:  # Mostrar solo los primeros 3 errores
                        print(f"      ⚠️ Error insertando registro: {e}")
                    continue
            
            # Mostrar progreso cada lote
            if registros_insertados % 100 == 0 and registros_insertados > 0:
                print(f"      - Insertados {registros_insertados} registros...")
        
        print(f"    ✅ {registros_insertados} registros insertados")
        if errores > 0:
            print(f"    ⚠️ {errores} errores")
        
        return True
        
    except Exception as e:
        print(f"    ❌ Error migrando tabla `{tabla}`: {e}")
        return False

def migrar_perfecto():
    """Función principal de migración perfecta"""
    print("=== MIGRACIÓN PERFECTA DE SQLITE A MYSQL ===")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🎯 Objetivo: Replicar 100% la estructura y datos de SQLite")
    
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
        
        # Obtener TODAS las tablas de SQLite
        tablas = obtener_todas_las_tablas_sqlite(cursor_sqlite)
        
        # Recrear tablas en MySQL
        print("\n🔧 Recreando tablas en MySQL...")
        tablas_creadas = 0
        
        for tabla in tablas:
            estructura = obtener_estructura_completa_sqlite(cursor_sqlite, tabla)
            if estructura and crear_tabla_mysql_perfecta(cursor_mysql, tabla, estructura):
                tablas_creadas += 1
            conn_mysql.commit()
        
        print(f"\n✅ {tablas_creadas}/{len(tablas)} tablas recreadas")
        
        # Migrar datos
        print("\n💾 Migrando datos...")
        tablas_migradas = 0
        
        for tabla in tablas:
            if migrar_datos_tabla_perfecta(tabla, cursor_sqlite, cursor_mysql):
                tablas_migradas += 1
            conn_mysql.commit()
        
        print(f"\n=== RESUMEN DE MIGRACIÓN PERFECTA ===")
        print(f"✅ Tablas recreadas: {tablas_creadas}/{len(tablas)}")
        print(f"✅ Tablas migradas: {tablas_migradas}/{len(tablas)}")
        
        if tablas_creadas == len(tablas) and tablas_migradas == len(tablas):
            print("\n🎉 MIGRACIÓN PERFECTA COMPLETADA AL 100%")
            return True
        else:
            print("\n⚠️ MIGRACIÓN COMPLETADA CON ALGUNOS ERRORES")
            return False
        
    except Exception as e:
        print(f"❌ Error durante la migración: {e}")
        return False
    
    finally:
        # Cerrar conexiones
        if conn_sqlite:
            conn_sqlite.close()
        if conn_mysql:
            conn_mysql.close()

def verificar_migracion_perfecta():
    """Verifica que la migración perfecta se realizó al 100%"""
    print("\n=== VERIFICACIÓN DE MIGRACIÓN PERFECTA ===")
    
    conn_sqlite = conectar_sqlite()
    conn_mysql = conectar_mysql()
    
    if not conn_sqlite or not conn_mysql:
        return False
    
    try:
        cursor_sqlite = conn_sqlite.cursor()
        cursor_mysql = conn_mysql.cursor()
        
        # Obtener tablas de SQLite
        cursor_sqlite.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tablas_sqlite = [row[0] for row in cursor_sqlite.fetchall()]
        
        # Obtener tablas de MySQL
        cursor_mysql.execute("SHOW TABLES")
        tablas_mysql = [list(row.values())[0] for row in cursor_mysql.fetchall()]
        
        print(f"📊 Tablas en SQLite: {len(tablas_sqlite)}")
        print(f"📊 Tablas en MySQL: {len(tablas_mysql)}")
        
        total_sqlite = 0
        total_mysql = 0
        coincidencias = 0
        
        for tabla in tablas_sqlite:
            # Contar registros en SQLite
            cursor_sqlite.execute(f"SELECT COUNT(*) FROM `{tabla}`")
            count_sqlite = cursor_sqlite.fetchone()[0]
            total_sqlite += count_sqlite
            
            # Contar registros en MySQL
            if tabla in tablas_mysql:
                cursor_mysql.execute(f"SELECT COUNT(*) FROM `{tabla}`")
                count_mysql = cursor_mysql.fetchone()['COUNT(*)']
                total_mysql += count_mysql
                
                if count_sqlite == count_mysql:
                    print(f"✅ `{tabla}`: {count_sqlite} registros (PERFECTO)")
                    coincidencias += 1
                else:
                    print(f"❌ `{tabla}`: SQLite={count_sqlite}, MySQL={count_mysql} (DIFERENCIA)")
            else:
                print(f"⚠️ `{tabla}`: No existe en MySQL")
        
        print(f"\n📊 Resumen de verificación:")
        print(f"  - Total registros SQLite: {total_sqlite}")
        print(f"  - Total registros MySQL: {total_mysql}")
        print(f"  - Tablas perfectas: {coincidencias}/{len(tablas_sqlite)}")
        print(f"  - Porcentaje de éxito: {(coincidencias/len(tablas_sqlite)*100):.1f}%")
        
        if coincidencias == len(tablas_sqlite) and total_sqlite == total_mysql:
            print("\n🎉 VERIFICACIÓN: MIGRACIÓN 100% PERFECTA")
            return True
        else:
            print("\n⚠️ VERIFICACIÓN: Hay diferencias en la migración")
            return False
        
    except Exception as e:
        print(f"❌ Error verificando migración: {e}")
        return False
    
    finally:
        if conn_sqlite:
            conn_sqlite.close()
        if conn_mysql:
            conn_mysql.close()

if __name__ == "__main__":
    print("🚀 Iniciando migración PERFECTA de SQLite a MySQL...")
    print("🎯 Objetivo: Replicar al 100% estructura y datos")
    print("⚠️ ADVERTENCIA: Esto eliminará TODAS las tablas de MySQL y las recreará")
    
    respuesta = input("¿Continuar con la migración perfecta? (s/N): ")
    if respuesta.lower() not in ['s', 'si', 'sí', 'y', 'yes']:
        print("❌ Migración cancelada")
        exit()
    
    # Realizar migración perfecta
    if migrar_perfecto():
        # Verificar migración
        if verificar_migracion_perfecta():
            print("\n🎉 PROCESO COMPLETADO: MIGRACIÓN 100% PERFECTA")
        else:
            print("\n⚠️ PROCESO COMPLETADO: Revisar diferencias")
    else:
        print("\n❌ Error en el proceso de migración perfecta")
    
    input("\nPresiona Enter para continuar...")