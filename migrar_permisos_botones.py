#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para migrar específicamente la tabla permisos_botones de SQLite a MySQL
Elimina la tabla actual de MySQL y la recrea con la estructura correcta
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

def recrear_tabla_permisos_botones(cursor_mysql):
    """Elimina y recrea la tabla permisos_botones en MySQL con la estructura correcta"""
    print("\n🔄 Recreando tabla permisos_botones en MySQL...")
    
    try:
        # Eliminar tabla existente
        cursor_mysql.execute("DROP TABLE IF EXISTS permisos_botones")
        print("  - Tabla permisos_botones eliminada")
        
        # Crear tabla con estructura de SQLite
        create_table_sql = """
        CREATE TABLE permisos_botones (
            id INT AUTO_INCREMENT PRIMARY KEY,
            pagina VARCHAR(255) NOT NULL,
            seccion VARCHAR(255) NOT NULL,
            boton VARCHAR(255) NOT NULL,
            descripcion TEXT,
            activo TINYINT(1) DEFAULT 1,
            INDEX idx_pagina_seccion_boton (pagina, seccion, boton)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        
        cursor_mysql.execute(create_table_sql)
        print("  - Tabla permisos_botones recreada con estructura correcta")
        return True
        
    except Exception as e:
        print(f"  ❌ Error recreando tabla: {e}")
        return False

def migrar_permisos_botones():
    """Migra específicamente la tabla permisos_botones"""
    print("=== MIGRACIÓN DE TABLA PERMISOS_BOTONES ===")
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
        
        # Recrear tabla en MySQL
        if not recrear_tabla_permisos_botones(cursor_mysql):
            return False
        
        # Obtener datos de SQLite
        print("\n📊 Obteniendo datos de SQLite...")
        cursor_sqlite.execute("SELECT * FROM permisos_botones")
        datos = cursor_sqlite.fetchall()
        
        if not datos:
            print("  - Tabla permisos_botones está vacía en SQLite")
            return True
        
        print(f"  - Encontrados {len(datos)} registros")
        
        # Insertar datos en MySQL
        print("\n💾 Insertando datos en MySQL...")
        query = """
        INSERT INTO permisos_botones (id, pagina, seccion, boton, descripcion, activo)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        
        registros_insertados = 0
        errores = 0
        
        for fila in datos:
            try:
                valores = (
                    fila['id'],
                    fila['pagina'],
                    fila['seccion'],
                    fila['boton'],
                    fila['descripcion'],
                    fila['activo']
                )
                
                cursor_mysql.execute(query, valores)
                registros_insertados += 1
                
                if registros_insertados % 100 == 0:
                    print(f"  - Insertados {registros_insertados} registros...")
                    
            except Exception as e:
                errores += 1
                print(f"  ⚠️ Error insertando registro ID {fila['id']}: {e}")
                continue
        
        # Confirmar cambios
        conn_mysql.commit()
        
        print(f"\n=== RESUMEN DE MIGRACIÓN ===")
        print(f"✅ Registros insertados exitosamente: {registros_insertados}")
        print(f"❌ Errores: {errores}")
        print(f"📊 Total de registros procesados: {len(datos)}")
        
        if errores == 0:
            print("\n🎉 MIGRACIÓN DE PERMISOS_BOTONES COMPLETADA EXITOSAMENTE")
        else:
            print(f"\n⚠️ MIGRACIÓN COMPLETADA CON {errores} ERRORES")
        
        return errores == 0
        
    except Exception as e:
        print(f"❌ Error durante la migración: {e}")
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
        
        # Contar registros en SQLite
        cursor_sqlite.execute("SELECT COUNT(*) FROM permisos_botones")
        count_sqlite = cursor_sqlite.fetchone()[0]
        
        # Contar registros en MySQL
        cursor_mysql.execute("SELECT COUNT(*) FROM permisos_botones")
        count_mysql = cursor_mysql.fetchone()['COUNT(*)']
        
        print(f"📊 SQLite: {count_sqlite} registros")
        print(f"📊 MySQL: {count_mysql} registros")
        
        if count_sqlite == count_mysql:
            print("✅ Los conteos coinciden - migración exitosa")
            return True
        else:
            print("❌ Los conteos no coinciden - revisar migración")
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
    print("🚀 Iniciando migración específica de tabla permisos_botones...")
    
    # Realizar migración
    if migrar_permisos_botones():
        # Verificar migración
        verificar_migracion()
        print("\n🎉 Proceso de migración finalizado")
    else:
        print("\n❌ Error en el proceso de migración")
    
    input("\nPresiona Enter para continuar...")