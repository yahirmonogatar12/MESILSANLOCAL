#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script completo para migrar todos los datos de SQLite local al MySQL del hosting
Incluye: usuarios, roles, permisos, tablas de control, etc.
"""

import sqlite3
import pymysql
import os
from datetime import datetime
import json
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración de SQLite local
SQLITE_PATH = os.path.join('app', 'database', 'ISEMM_MES.db')

# Configuración de MySQL del hosting
HOSTING_CONFIG = {
    'host': 'up-de-fra1-mysql-1.db.run-on-seenode.com',
    'port': 11550,
    'user': 'db_rrpq0erbdujn',
    'password': '5fUNbSRcPP3LN9K2I33Pr0ge',
    'database': 'db_rrpq0erbdujn',
    'charset': 'utf8mb4'
}

# Tablas a migrar en orden de dependencias
TABLAS_MIGRACION = [
    # Tablas base
    'roles',
    'usuarios_sistema',
    'usuario_roles',
    
    # Tablas de permisos
    'permisos_botones',
    'rol_permisos_botones',
    'rol_permisos',
    
    # Tablas de control
    'control_material_almacen',
    'control_material_salida',
    'inventario_general',
    'bom',
    
    # Tablas de configuración
    'configuraciones_usuario',
    'user_sessions'
]

def conectar_sqlite():
    """Conectar a SQLite local"""
    try:
        if not os.path.exists(SQLITE_PATH):
            print(f"❌ No se encontró SQLite en: {SQLITE_PATH}")
            return None
        
        conn = sqlite3.connect(SQLITE_PATH)
        conn.row_factory = sqlite3.Row
        print(f"✅ Conectado a SQLite: {SQLITE_PATH}")
        return conn
    except Exception as e:
        print(f"❌ Error conectando a SQLite: {e}")
        return None

def conectar_mysql_hosting():
    """Conectar a MySQL del hosting"""
    try:
        conn = pymysql.connect(**HOSTING_CONFIG)
        print(f"✅ Conectado a MySQL hosting: {HOSTING_CONFIG['host']}")
        return conn
    except Exception as e:
        print(f"❌ Error conectando a MySQL hosting: {e}")
        return None

def obtener_estructura_tabla_sqlite(sqlite_conn, tabla):
    """Obtener estructura de tabla de SQLite"""
    try:
        cursor = sqlite_conn.cursor()
        cursor.execute(f"PRAGMA table_info({tabla})")
        columnas = cursor.fetchall()
        
        estructura = []
        for col in columnas:
            estructura.append({
                'nombre': col[1],
                'tipo': col[2],
                'not_null': bool(col[3]),
                'default': col[4],
                'pk': bool(col[5])
            })
        
        return estructura
    except Exception as e:
        print(f"❌ Error obteniendo estructura de {tabla}: {e}")
        return []

def crear_tabla_mysql(mysql_conn, tabla, estructura):
    """Crear tabla en MySQL basada en estructura de SQLite"""
    try:
        cursor = mysql_conn.cursor()
        
        # Mapeo de tipos SQLite a MySQL
        tipo_map = {
            'INTEGER': 'INT',
            'TEXT': 'TEXT',
            'REAL': 'DECIMAL(10,2)',
            'DATETIME': 'DATETIME',
            'TIMESTAMP': 'TIMESTAMP',
            'BOOLEAN': 'BOOLEAN'
        }
        
        # Construir CREATE TABLE
        columnas_sql = []
        pk_columns = []
        
        for col in estructura:
            tipo_mysql = tipo_map.get(col['tipo'].upper(), 'TEXT')
            
            # Ajustes específicos
            if col['nombre'] == 'id' and col['pk']:
                tipo_mysql = 'INT AUTO_INCREMENT'
            elif 'fecha' in col['nombre'].lower() and tipo_mysql == 'TEXT':
                tipo_mysql = 'DATETIME'
            
            col_def = f"`{col['nombre']}` {tipo_mysql}"
            
            if col['not_null']:
                col_def += " NOT NULL"
            
            if col['default'] and col['default'] != 'NULL':
                if col['default'] == 'CURRENT_TIMESTAMP':
                    col_def += " DEFAULT CURRENT_TIMESTAMP"
                else:
                    col_def += f" DEFAULT {col['default']}"
            
            if col['pk']:
                pk_columns.append(col['nombre'])
            
            columnas_sql.append(col_def)
        
        # Agregar PRIMARY KEY
        if pk_columns:
            columnas_sql.append(f"PRIMARY KEY (`{'`, `'.join(pk_columns)}`)") 
        
        create_sql = f"CREATE TABLE IF NOT EXISTS `{tabla}` (\n  {',\n  '.join(columnas_sql)}\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
        
        print(f"📋 Creando tabla {tabla}...")
        cursor.execute(f"DROP TABLE IF EXISTS `{tabla}`")
        cursor.execute(create_sql)
        mysql_conn.commit()
        
        print(f"✅ Tabla {tabla} creada exitosamente")
        return True
        
    except Exception as e:
        print(f"❌ Error creando tabla {tabla}: {e}")
        return False

def migrar_datos_tabla(sqlite_conn, mysql_conn, tabla):
    """Migrar datos de una tabla específica"""
    try:
        # Verificar si la tabla existe en SQLite
        sqlite_cursor = sqlite_conn.cursor()
        sqlite_cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{tabla}'")
        if not sqlite_cursor.fetchone():
            print(f"⚠️ Tabla {tabla} no existe en SQLite")
            return True
        
        # Obtener datos de SQLite
        sqlite_cursor.execute(f"SELECT * FROM {tabla}")
        datos = sqlite_cursor.fetchall()
        
        if not datos:
            print(f"⚠️ Tabla {tabla} está vacía")
            return True
        
        # Obtener nombres de columnas
        columnas = [description[0] for description in sqlite_cursor.description]
        
        # Insertar en MySQL
        mysql_cursor = mysql_conn.cursor()
        
        # Construir query de inserción
        placeholders = ', '.join(['%s'] * len(columnas))
        columnas_str = ', '.join([f'`{col}`' for col in columnas])
        insert_sql = f"INSERT INTO `{tabla}` ({columnas_str}) VALUES ({placeholders})"
        
        # Convertir datos
        datos_convertidos = []
        for fila in datos:
            fila_convertida = []
            for valor in fila:
                if valor is None:
                    fila_convertida.append(None)
                elif isinstance(valor, str) and valor.strip() == '':
                    fila_convertida.append(None)
                else:
                    fila_convertida.append(valor)
            datos_convertidos.append(tuple(fila_convertida))
        
        # Insertar por lotes
        batch_size = 100
        total_insertados = 0
        
        for i in range(0, len(datos_convertidos), batch_size):
            batch = datos_convertidos[i:i + batch_size]
            mysql_cursor.executemany(insert_sql, batch)
            total_insertados += len(batch)
        
        mysql_conn.commit()
        
        print(f"✅ Migrados {total_insertados} registros de {tabla}")
        return True
        
    except Exception as e:
        print(f"❌ Error migrando datos de {tabla}: {e}")
        mysql_conn.rollback()
        return False

def verificar_migracion(mysql_conn, tabla):
    """Verificar que la migración fue exitosa"""
    try:
        cursor = mysql_conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM `{tabla}`")
        count = cursor.fetchone()[0]
        print(f"📊 Tabla {tabla}: {count} registros")
        return count
    except Exception as e:
        print(f"❌ Error verificando {tabla}: {e}")
        return 0

def configurar_hosting_local():
    """Configurar el entorno local para usar MySQL del hosting"""
    try:
        # Crear archivo de configuración para hosting
        config_hosting = f"""# Configuración para conectar localmente al MySQL del hosting
# Generado automáticamente: {datetime.now()}

# Base de datos MySQL del hosting
DB_TYPE=mysql
MYSQL_HOST={HOSTING_CONFIG['host']}
MYSQL_PORT={HOSTING_CONFIG['port']}
MYSQL_DATABASE={HOSTING_CONFIG['database']}
MYSQL_USERNAME={HOSTING_CONFIG['user']}
MYSQL_PASSWORD={HOSTING_CONFIG['password']}

# Configuración del Proxy MySQL HTTP - DESHABILITADO
USE_HTTP_PROXY=false

# Configuración Flask
SECRET_KEY=tu_clave_secreta_super_segura_cambiar_en_produccion_2024
FLASK_ENV=development
FLASK_DEBUG=True

# Configuración de seguridad
SESSION_COOKIE_SECURE=False
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax

# Configuración de aplicación
APP_NAME=ISEMM_MES
APP_VERSION=1.0.0
"""
        
        # Respaldar .env actual
        if os.path.exists('.env'):
            backup_name = f'.env.backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
            os.rename('.env', backup_name)
            print(f"📁 Respaldo creado: {backup_name}")
        
        # Escribir nueva configuración
        with open('.env', 'w', encoding='utf-8') as f:
            f.write(config_hosting)
        
        print("✅ Configuración local actualizada para usar MySQL del hosting")
        return True
        
    except Exception as e:
        print(f"❌ Error configurando entorno local: {e}")
        return False

def main():
    print("🚀 Iniciando migración completa SQLite → MySQL Hosting")
    print("=" * 70)
    
    # Conectar a bases de datos
    sqlite_conn = conectar_sqlite()
    if not sqlite_conn:
        return
    
    mysql_conn = conectar_mysql_hosting()
    if not mysql_conn:
        sqlite_conn.close()
        return
    
    try:
        # Estadísticas iniciales
        print("\n📊 ESTADÍSTICAS INICIALES:")
        print("-" * 50)
        
        tablas_migradas = 0
        total_registros = 0
        
        # Migrar cada tabla
        for tabla in TABLAS_MIGRACION:
            print(f"\n🔄 Procesando tabla: {tabla}")
            print("-" * 30)
            
            # Obtener estructura de SQLite
            estructura = obtener_estructura_tabla_sqlite(sqlite_conn, tabla)
            if not estructura:
                print(f"⚠️ Saltando {tabla} (no existe o sin estructura)")
                continue
            
            # Crear tabla en MySQL
            if crear_tabla_mysql(mysql_conn, tabla, estructura):
                # Migrar datos
                if migrar_datos_tabla(sqlite_conn, mysql_conn, tabla):
                    # Verificar migración
                    count = verificar_migracion(mysql_conn, tabla)
                    total_registros += count
                    tablas_migradas += 1
                else:
                    print(f"❌ Falló migración de datos para {tabla}")
            else:
                print(f"❌ Falló creación de tabla {tabla}")
        
        # Configurar entorno local
        print("\n🔧 CONFIGURANDO ENTORNO LOCAL:")
        print("-" * 50)
        configurar_hosting_local()
        
        # Resumen final
        print("\n📊 RESUMEN DE MIGRACIÓN:")
        print("=" * 50)
        print(f"   ✅ Tablas migradas: {tablas_migradas}/{len(TABLAS_MIGRACION)}")
        print(f"   📦 Total registros: {total_registros}")
        print(f"   🎯 Base de datos destino: {HOSTING_CONFIG['host']}")
        print(f"   ⚙️ Configuración local: Actualizada")
        
        if tablas_migradas == len(TABLAS_MIGRACION):
            print("\n🎉 ¡MIGRACIÓN COMPLETADA EXITOSAMENTE!")
            print("\n📋 PRÓXIMOS PASOS:")
            print("   1. Reiniciar la aplicación Flask")
            print("   2. Verificar login con usuarios migrados")
            print("   3. Probar funcionalidad de permisos")
            print("   4. Verificar que los botones funcionen")
        else:
            print("\n⚠️ MIGRACIÓN PARCIAL - Revisar errores")
        
    except Exception as e:
        print(f"\n❌ Error durante la migración: {e}")
    
    finally:
        sqlite_conn.close()
        mysql_conn.close()
        print("\n🔚 Migración finalizada")

if __name__ == "__main__":
    main()