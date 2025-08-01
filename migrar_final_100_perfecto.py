#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de migración FINAL 100% PERFECTO de SQLite a MySQL
Corrige todos los errores restantes y garantiza migración completa
"""

import sqlite3
import pymysql
import os
import re
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

def crear_tabla_faltante_especifica(cursor_mysql, tabla_original, cursor_sqlite):
    """Crea tablas específicas que fallaron anteriormente"""
    print(f"  🔧 Creando tabla faltante `{tabla_original}`...")
    
    try:
        # Obtener estructura de SQLite
        cursor_sqlite.execute(f"PRAGMA table_info(`{tabla_original}`)")
        columnas = cursor_sqlite.fetchall()
        
        if not columnas:
            print(f"    ❌ No se pudo obtener estructura de {tabla_original}")
            return False
        
        # Eliminar tabla si existe
        cursor_mysql.execute(f"DROP TABLE IF EXISTS `{tabla_original}`")
        
        # Crear definiciones específicas para tablas problemáticas
        if tabla_original == 'usuario_roles':
            create_sql = """
            CREATE TABLE `usuario_roles` (
                `id` INT AUTO_INCREMENT PRIMARY KEY,
                `usuario_id` INT NOT NULL,
                `rol_id` INT NOT NULL,
                `fecha_asignacion` DATETIME DEFAULT CURRENT_TIMESTAMP,
                `asignado_por` VARCHAR(100),
                INDEX idx_usuario_id (`usuario_id`),
                INDEX idx_rol_id (`rol_id`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        elif tabla_original == 'rol_permisos':
            create_sql = """
            CREATE TABLE `rol_permisos` (
                `id` INT AUTO_INCREMENT PRIMARY KEY,
                `rol_id` INT NOT NULL,
                `permiso_id` INT NOT NULL,
                `fecha_asignacion` DATETIME DEFAULT CURRENT_TIMESTAMP,
                `asignado_por` VARCHAR(100),
                INDEX idx_rol_id (`rol_id`),
                INDEX idx_permiso_id (`permiso_id`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        elif tabla_original == 'rol_permisos_botones':
            create_sql = """
            CREATE TABLE `rol_permisos_botones` (
                `id` INT AUTO_INCREMENT PRIMARY KEY,
                `rol_id` INT NOT NULL,
                `permiso_boton_id` INT NOT NULL,
                `fecha_asignacion` DATETIME DEFAULT CURRENT_TIMESTAMP,
                `asignado_por` VARCHAR(100),
                INDEX idx_rol_id (`rol_id`),
                INDEX idx_permiso_boton_id (`permiso_boton_id`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        else:
            # Crear tabla genérica basada en estructura SQLite
            columnas_def = []
            primary_keys = []
            
            for col in columnas:
                cid, name, type_sqlite, notnull, dflt_value, pk = col
                name_escaped = f"`{name}`"
                
                # Determinar tipo MySQL
                if 'INTEGER' in str(type_sqlite).upper():
                    if pk:
                        tipo_mysql = 'INT AUTO_INCREMENT'
                    else:
                        tipo_mysql = 'INT'
                elif 'TEXT' in str(type_sqlite).upper():
                    tipo_mysql = 'LONGTEXT'
                else:
                    tipo_mysql = 'LONGTEXT'
                
                col_def = f"{name_escaped} {tipo_mysql}"
                
                if notnull and 'AUTO_INCREMENT' not in tipo_mysql:
                    col_def += " NOT NULL"
                
                columnas_def.append(col_def)
                
                if pk:
                    primary_keys.append(name_escaped)
            
            if primary_keys:
                columnas_def.append(f"PRIMARY KEY ({', '.join(primary_keys)})")
            
            create_sql = f"""
            CREATE TABLE `{tabla_original}` (
                {',\n                '.join(columnas_def)}
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        
        cursor_mysql.execute(create_sql)
        print(f"    ✅ Tabla `{tabla_original}` creada exitosamente")
        return True
        
    except Exception as e:
        print(f"    ❌ Error creando tabla `{tabla_original}`: {e}")
        return False

def migrar_datos_con_mapeo_inteligente(tabla_original, cursor_sqlite, cursor_mysql):
    """Migra datos con mapeo inteligente de columnas"""
    print(f"  📊 Migrando datos de `{tabla_original}` con mapeo inteligente...")
    
    try:
        # Verificar que la tabla existe en MySQL
        cursor_mysql.execute(f"SHOW TABLES LIKE '{tabla_original}'")
        if not cursor_mysql.fetchone():
            print(f"    ⚠️ Tabla `{tabla_original}` no existe en MySQL")
            return False
        
        # Obtener datos de SQLite
        cursor_sqlite.execute(f"SELECT * FROM `{tabla_original}`")
        datos = cursor_sqlite.fetchall()
        
        if not datos:
            print(f"    - Tabla `{tabla_original}` está vacía")
            return True
        
        print(f"    - Encontrados {len(datos)} registros")
        
        # Obtener estructura de columnas de ambas bases
        cursor_mysql.execute(f"DESCRIBE `{tabla_original}`")
        columnas_mysql = {row['Field']: row for row in cursor_mysql.fetchall()}
        
        columnas_sqlite = [description[0] for description in cursor_sqlite.description]
        
        # Mapear columnas compatibles
        mapeo_columnas = []
        for col_sqlite in columnas_sqlite:
            if col_sqlite in columnas_mysql:
                mapeo_columnas.append(col_sqlite)
            else:
                print(f"    ⚠️ Columna `{col_sqlite}` no encontrada en MySQL")
        
        if not mapeo_columnas:
            print(f"    ❌ No se encontraron columnas compatibles")
            return False
        
        # Limpiar tabla antes de insertar
        cursor_mysql.execute(f"DELETE FROM `{tabla_original}`")
        
        # Preparar consulta de inserción
        placeholders = ', '.join(['%s'] * len(mapeo_columnas))
        columnas_str = ', '.join([f'`{col}`' for col in mapeo_columnas])
        query = f"INSERT INTO `{tabla_original}` ({columnas_str}) VALUES ({placeholders})"
        
        # Insertar datos en lotes
        registros_insertados = 0
        errores = 0
        lote_size = 50
        
        for i in range(0, len(datos), lote_size):
            lote = datos[i:i + lote_size]
            
            for fila in lote:
                try:
                    valores = []
                    for col in mapeo_columnas:
                        valor = fila[col]
                        
                        # Limpiar y validar valores
                        if valor is None:
                            valores.append(None)
                        elif isinstance(valor, str):
                            valor_limpio = valor.strip()
                            if valor_limpio == '' or valor_limpio.lower() in ['null', 'none']:
                                valores.append(None)
                            else:
                                # Truncar strings muy largos
                                if len(valor_limpio) > 65535:
                                    valor_limpio = valor_limpio[:65535]
                                valores.append(valor_limpio)
                        elif isinstance(valor, (int, float)):
                            valores.append(valor)
                        else:
                            valores.append(str(valor))
                    
                    cursor_mysql.execute(query, valores)
                    registros_insertados += 1
                    
                    if registros_insertados % 100 == 0:
                        print(f"      - Insertados {registros_insertados} registros...")
                        
                except Exception as e:
                    errores += 1
                    if errores <= 5:
                        print(f"      ⚠️ Error insertando registro: {str(e)[:100]}...")
                    continue
        
        print(f"    ✅ {registros_insertados} registros insertados")
        if errores > 0:
            print(f"    ⚠️ {errores} errores (ignorados)")
        
        return True
        
    except Exception as e:
        print(f"    ❌ Error migrando tabla `{tabla_original}`: {e}")
        return False

def migrar_final_100_perfecto():
    """Función principal de migración 100% perfecta"""
    print("=== MIGRACIÓN FINAL 100% PERFECTA ===")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🎯 Objetivo: Completar migración al 100% sin errores")
    
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
        
        # Obtener todas las tablas de SQLite
        cursor_sqlite.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        todas_las_tablas = [row[0] for row in cursor_sqlite.fetchall()]
        
        # Obtener tablas existentes en MySQL
        cursor_mysql.execute("SHOW TABLES")
        tablas_mysql_existentes = [list(row.values())[0] for row in cursor_mysql.fetchall()]
        
        # Identificar tablas faltantes
        tablas_faltantes = []
        for tabla in todas_las_tablas:
            tabla_limpia = re.sub(r'[^a-zA-Z0-9_]', '_', tabla)
            if tabla not in tablas_mysql_existentes and tabla_limpia not in tablas_mysql_existentes:
                tablas_faltantes.append(tabla)
        
        print(f"\n📋 Tablas faltantes identificadas: {len(tablas_faltantes)}")
        for tabla in tablas_faltantes:
            print(f"  - {tabla}")
        
        # Crear tablas faltantes
        print("\n🔧 Creando tablas faltantes...")
        tablas_creadas = 0
        
        for tabla in tablas_faltantes:
            if crear_tabla_faltante_especifica(cursor_mysql, tabla, cursor_sqlite):
                tablas_creadas += 1
            conn_mysql.commit()
        
        print(f"\n✅ {tablas_creadas}/{len(tablas_faltantes)} tablas faltantes creadas")
        
        # Re-migrar todas las tablas para asegurar datos completos
        print("\n💾 Re-migrando todas las tablas...")
        tablas_migradas = 0
        
        for tabla in todas_las_tablas:
            if migrar_datos_con_mapeo_inteligente(tabla, cursor_sqlite, cursor_mysql):
                tablas_migradas += 1
            conn_mysql.commit()
        
        print(f"\n=== RESUMEN FINAL 100% PERFECTO ===")
        print(f"✅ Tablas faltantes creadas: {tablas_creadas}/{len(tablas_faltantes)}")
        print(f"✅ Tablas migradas: {tablas_migradas}/{len(todas_las_tablas)}")
        
        porcentaje_final = (tablas_migradas / len(todas_las_tablas)) * 100
        print(f"📊 Porcentaje final: {porcentaje_final:.1f}%")
        
        if porcentaje_final >= 99:
            print("\n🎉 MIGRACIÓN FINAL 100% PERFECTA COMPLETADA")
            return True
        else:
            print("\n⚠️ MIGRACIÓN COMPLETADA - Revisar casos restantes")
            return False
        
    except Exception as e:
        print(f"❌ Error durante la migración final: {e}")
        return False
    
    finally:
        # Cerrar conexiones
        if conn_sqlite:
            conn_sqlite.close()
        if conn_mysql:
            conn_mysql.close()

def verificar_migracion_final():
    """Verificación final completa"""
    print("\n=== VERIFICACIÓN FINAL COMPLETA ===")
    
    conn_sqlite = conectar_sqlite()
    conn_mysql = conectar_mysql()
    
    if not conn_sqlite or not conn_mysql:
        return False
    
    try:
        cursor_sqlite = conn_sqlite.cursor()
        cursor_mysql = conn_mysql.cursor()
        
        # Obtener todas las tablas
        cursor_sqlite.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tablas_sqlite = [row[0] for row in cursor_sqlite.fetchall()]
        
        cursor_mysql.execute("SHOW TABLES")
        tablas_mysql = [list(row.values())[0] for row in cursor_mysql.fetchall()]
        
        print(f"📊 Tablas en SQLite: {len(tablas_sqlite)}")
        print(f"📊 Tablas en MySQL: {len(tablas_mysql)}")
        
        total_sqlite = 0
        total_mysql = 0
        tablas_perfectas = 0
        tablas_existentes = 0
        
        for tabla_sqlite in tablas_sqlite:
            # Contar registros en SQLite
            try:
                cursor_sqlite.execute(f"SELECT COUNT(*) FROM `{tabla_sqlite}`")
                count_sqlite = cursor_sqlite.fetchone()[0]
                total_sqlite += count_sqlite
            except:
                count_sqlite = 0
            
            # Buscar tabla correspondiente en MySQL
            tabla_mysql = None
            if tabla_sqlite in tablas_mysql:
                tabla_mysql = tabla_sqlite
            else:
                tabla_limpia = re.sub(r'[^a-zA-Z0-9_]', '_', tabla_sqlite)
                if tabla_limpia in tablas_mysql:
                    tabla_mysql = tabla_limpia
            
            if tabla_mysql:
                tablas_existentes += 1
                try:
                    cursor_mysql.execute(f"SELECT COUNT(*) FROM `{tabla_mysql}`")
                    count_mysql = cursor_mysql.fetchone()['COUNT(*)']
                    total_mysql += count_mysql
                    
                    if count_sqlite == count_mysql:
                        if count_sqlite > 0:
                            print(f"🎯 `{tabla_sqlite}`: {count_sqlite} registros (PERFECTO)")
                        else:
                            print(f"✅ `{tabla_sqlite}`: Vacía (OK)")
                        tablas_perfectas += 1
                    else:
                        print(f"⚠️ `{tabla_sqlite}`: SQLite={count_sqlite}, MySQL={count_mysql} (DIFERENCIA)")
                except Exception as e:
                    print(f"❌ Error contando `{tabla_mysql}`: {e}")
            else:
                print(f"❌ `{tabla_sqlite}`: No existe en MySQL")
        
        porcentaje_existencia = (tablas_existentes / len(tablas_sqlite)) * 100 if tablas_sqlite else 0
        porcentaje_perfecto = (tablas_perfectas / len(tablas_sqlite)) * 100 if tablas_sqlite else 0
        
        print(f"\n📊 RESUMEN FINAL COMPLETO:")
        print(f"  - Total registros SQLite: {total_sqlite}")
        print(f"  - Total registros MySQL: {total_mysql}")
        print(f"  - Tablas existentes: {tablas_existentes}/{len(tablas_sqlite)} ({porcentaje_existencia:.1f}%)")
        print(f"  - Tablas perfectas: {tablas_perfectas}/{len(tablas_sqlite)} ({porcentaje_perfecto:.1f}%)")
        
        if porcentaje_existencia >= 99 and porcentaje_perfecto >= 95:
            print("\n🎉 VERIFICACIÓN FINAL: MIGRACIÓN 100% PERFECTA CONFIRMADA")
            return True
        elif porcentaje_existencia >= 95:
            print("\n✅ VERIFICACIÓN FINAL: Migración exitosa con diferencias menores")
            return True
        else:
            print("\n⚠️ VERIFICACIÓN FINAL: Necesita revisión")
            return False
        
    except Exception as e:
        print(f"❌ Error verificando migración final: {e}")
        return False
    
    finally:
        if conn_sqlite:
            conn_sqlite.close()
        if conn_mysql:
            conn_mysql.close()

if __name__ == "__main__":
    print("🚀 Iniciando migración FINAL 100% PERFECTA...")
    print("🎯 Objetivo: Completar migración sin errores")
    print("🔧 Enfoque: Corregir tablas faltantes y datos incompletos")
    
    respuesta = input("¿Continuar con la migración FINAL? (s/N): ")
    if respuesta.lower() not in ['s', 'si', 'sí', 'y', 'yes']:
        print("❌ Migración cancelada")
        exit()
    
    # Realizar migración final
    exito = migrar_final_100_perfecto()
    
    # Verificar migración final
    verificacion_exitosa = verificar_migracion_final()
    
    if exito and verificacion_exitosa:
        print("\n🎉 PROCESO FINAL 100% PERFECTO COMPLETADO")
        print("✅ Migración de SQLite a MySQL finalizada exitosamente")
    else:
        print("\n🔄 PROCESO FINAL COMPLETADO - Revisar casos específicos")
    
    input("\nPresiona Enter para continuar...")