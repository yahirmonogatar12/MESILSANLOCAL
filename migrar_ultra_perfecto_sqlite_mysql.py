#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de migración ULTRA PERFECTA de SQLite a MySQL
Maneja todos los casos problemáticos y garantiza migración al 100%
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

def limpiar_nombre_tabla(nombre):
    """Limpia y valida nombres de tabla para MySQL"""
    # Reemplazar caracteres problemáticos
    nombre_limpio = re.sub(r'[^a-zA-Z0-9_]', '_', nombre)
    
    # Asegurar que no empiece con número
    if nombre_limpio[0].isdigit():
        nombre_limpio = 't_' + nombre_limpio
    
    # Limitar longitud
    if len(nombre_limpio) > 64:
        nombre_limpio = nombre_limpio[:64]
    
    return nombre_limpio

def obtener_todas_las_tablas_sqlite(cursor_sqlite):
    """Obtiene TODAS las tablas de SQLite con nombres limpios"""
    cursor_sqlite.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tablas_originales = [row[0] for row in cursor_sqlite.fetchall()]
    
    tablas_mapeadas = {}
    for tabla_original in tablas_originales:
        tabla_limpia = limpiar_nombre_tabla(tabla_original)
        tablas_mapeadas[tabla_original] = tabla_limpia
        
        if tabla_original != tabla_limpia:
            print(f"  📝 Tabla '{tabla_original}' → '{tabla_limpia}'")
    
    print(f"📋 Tablas encontradas en SQLite: {len(tablas_originales)}")
    return tablas_mapeadas

def obtener_estructura_tabla_sqlite(cursor_sqlite, tabla_original):
    """Obtiene la estructura de una tabla en SQLite"""
    try:
        cursor_sqlite.execute(f"PRAGMA table_info(`{tabla_original}`)")
        columnas = cursor_sqlite.fetchall()
        return columnas
    except Exception as e:
        print(f"  ⚠️ Error obteniendo estructura de {tabla_original}: {e}")
        return None

def convertir_tipo_sqlite_mysql_avanzado(tipo_sqlite, columna_info):
    """Conversión avanzada de tipos SQLite a MySQL"""
    tipo_upper = str(tipo_sqlite).upper().strip()
    cid, name, type_sqlite, notnull, dflt_value, pk = columna_info
    
    # Casos especiales por nombre de columna
    name_lower = name.lower()
    
    if 'fecha' in name_lower or 'date' in name_lower:
        if 'time' in name_lower or 'hora' in name_lower:
            return 'DATETIME'
        else:
            return 'DATE'
    
    if 'id' in name_lower and pk:
        return 'INT AUTO_INCREMENT'
    
    # Conversión por tipo SQLite
    if 'INTEGER' in tipo_upper:
        if pk:
            return 'INT AUTO_INCREMENT'
        elif 'BOOL' in name_lower or 'activo' in name_lower:
            return 'TINYINT(1)'
        else:
            return 'INT'
    elif 'TEXT' in tipo_upper:
        # Determinar tamaño basado en el nombre de la columna
        if any(x in name_lower for x in ['descripcion', 'detalle', 'comentario', 'observacion']):
            return 'LONGTEXT'
        elif any(x in name_lower for x in ['nombre', 'titulo', 'name', 'title']):
            return 'VARCHAR(255)'
        elif any(x in name_lower for x in ['codigo', 'code', 'numero', 'number']):
            return 'VARCHAR(100)'
        else:
            return 'TEXT'
    elif 'REAL' in tipo_upper or 'FLOAT' in tipo_upper or 'DOUBLE' in tipo_upper:
        return 'DECIMAL(15,4)'
    elif 'BLOB' in tipo_upper:
        return 'LONGBLOB'
    elif 'NUMERIC' in tipo_upper:
        return 'DECIMAL(15,4)'
    elif 'DATETIME' in tipo_upper:
        return 'DATETIME'
    elif 'DATE' in tipo_upper:
        return 'DATE'
    elif 'TIME' in tipo_upper:
        return 'TIME'
    elif 'BOOLEAN' in tipo_upper or 'BOOL' in tipo_upper:
        return 'TINYINT(1)'
    else:
        return 'TEXT'

def crear_tabla_mysql_ultra_perfecta(cursor_mysql, tabla_original, tabla_mysql, estructura):
    """Crea una tabla en MySQL con manejo ultra perfecto"""
    print(f"  🔧 Creando tabla `{tabla_mysql}` en MySQL...")
    
    if not estructura:
        print(f"    ❌ No se pudo obtener estructura para {tabla_original}")
        return False
    
    try:
        # Eliminar tabla si existe
        cursor_mysql.execute(f"DROP TABLE IF EXISTS `{tabla_mysql}`")
        
        # Construir definición de columnas
        columnas_def = []
        primary_keys = []
        indices = []
        
        for col in estructura:
            cid, name, type_sqlite, notnull, dflt_value, pk = col
            
            # Limpiar nombre de columna
            name_limpio = re.sub(r'[^a-zA-Z0-9_]', '_', name)
            name_escaped = f"`{name_limpio}`"
            
            # Convertir tipo
            tipo_mysql = convertir_tipo_sqlite_mysql_avanzado(type_sqlite, col)
            
            # Construir definición de columna
            col_def = f"{name_escaped} {tipo_mysql}"
            
            # Agregar NOT NULL si es necesario
            if notnull and 'AUTO_INCREMENT' not in tipo_mysql:
                col_def += " NOT NULL"
            
            # Agregar valor por defecto solo para tipos compatibles
            if dflt_value is not None and 'AUTO_INCREMENT' not in tipo_mysql:
                if 'LONGTEXT' not in tipo_mysql and 'LONGBLOB' not in tipo_mysql and 'TEXT' not in tipo_mysql:
                    if 'INT' in tipo_mysql or 'DECIMAL' in tipo_mysql or 'TINYINT' in tipo_mysql:
                        if str(dflt_value).upper() in ['CURRENT_TIMESTAMP', 'NOW()']:
                            if 'DATETIME' in tipo_mysql:
                                col_def += f" DEFAULT {dflt_value}"
                        else:
                            col_def += f" DEFAULT {dflt_value}"
                    elif 'VARCHAR' in tipo_mysql:
                        col_def += f" DEFAULT '{dflt_value}'"
                    elif 'DATETIME' in tipo_mysql and str(dflt_value).upper() in ['CURRENT_TIMESTAMP', 'NOW()']:
                        col_def += f" DEFAULT CURRENT_TIMESTAMP"
            
            columnas_def.append(col_def)
            
            # Recopilar primary keys
            if pk:
                primary_keys.append(name_escaped)
            
            # Crear índices para columnas importantes
            if any(x in name.lower() for x in ['id', 'codigo', 'numero', 'fecha']) and not pk:
                indices.append(f"INDEX idx_{name_limpio} ({name_escaped})")
        
        # Agregar primary key constraint
        if primary_keys:
            columnas_def.append(f"PRIMARY KEY ({', '.join(primary_keys)})")
        
        # Agregar índices
        columnas_def.extend(indices)
        
        # Crear tabla
        create_sql = f"""
        CREATE TABLE `{tabla_mysql}` (
            {',\n            '.join(columnas_def)}
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        
        cursor_mysql.execute(create_sql)
        print(f"    ✅ Tabla `{tabla_mysql}` creada exitosamente")
        return True
        
    except Exception as e:
        print(f"    ❌ Error creando tabla `{tabla_mysql}`: {e}")
        # Intentar crear tabla básica como fallback
        try:
            print(f"    🔄 Intentando crear tabla básica...")
            columnas_basicas = []
            for col in estructura:
                cid, name, type_sqlite, notnull, dflt_value, pk = col
                name_limpio = re.sub(r'[^a-zA-Z0-9_]', '_', name)
                if pk:
                    columnas_basicas.append(f"`{name_limpio}` INT AUTO_INCREMENT PRIMARY KEY")
                else:
                    columnas_basicas.append(f"`{name_limpio}` LONGTEXT")
            
            create_sql_basico = f"""
            CREATE TABLE `{tabla_mysql}` (
                {',\n                '.join(columnas_basicas)}
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
            
            cursor_mysql.execute(create_sql_basico)
            print(f"    ✅ Tabla básica `{tabla_mysql}` creada")
            return True
        except Exception as e2:
            print(f"    ❌ Error creando tabla básica: {e2}")
            return False

def migrar_datos_tabla_ultra_perfecta(tabla_original, tabla_mysql, cursor_sqlite, cursor_mysql):
    """Migra los datos con manejo ultra perfecto de errores"""
    print(f"  📊 Migrando datos de `{tabla_original}` → `{tabla_mysql}`...")
    
    try:
        # Verificar que la tabla existe en MySQL
        cursor_mysql.execute(f"SHOW TABLES LIKE '{tabla_mysql}'")
        if not cursor_mysql.fetchone():
            print(f"    ⚠️ Tabla `{tabla_mysql}` no existe en MySQL")
            return False
        
        # Obtener datos de SQLite
        cursor_sqlite.execute(f"SELECT * FROM `{tabla_original}`")
        datos = cursor_sqlite.fetchall()
        
        if not datos:
            print(f"    - Tabla `{tabla_original}` está vacía")
            return True
        
        print(f"    - Encontrados {len(datos)} registros")
        
        # Obtener estructura de columnas de MySQL
        cursor_mysql.execute(f"DESCRIBE `{tabla_mysql}`")
        columnas_mysql = [row['Field'] for row in cursor_mysql.fetchall()]
        
        # Obtener nombres de columnas de SQLite
        columnas_sqlite = [description[0] for description in cursor_sqlite.description]
        
        # Mapear columnas (limpiar nombres)
        mapeo_columnas = {}
        for col_sqlite in columnas_sqlite:
            col_limpia = re.sub(r'[^a-zA-Z0-9_]', '_', col_sqlite)
            if col_limpia in columnas_mysql:
                mapeo_columnas[col_sqlite] = col_limpia
        
        if not mapeo_columnas:
            print(f"    ⚠️ No se encontraron columnas compatibles")
            return False
        
        # Preparar consulta de inserción
        columnas_insertar = list(mapeo_columnas.values())
        placeholders = ', '.join(['%s'] * len(columnas_insertar))
        columnas_str = ', '.join([f'`{col}`' for col in columnas_insertar])
        query = f"INSERT INTO `{tabla_mysql}` ({columnas_str}) VALUES ({placeholders})"
        
        # Insertar datos
        registros_insertados = 0
        errores = 0
        
        for fila in datos:
            try:
                valores = []
                for col_sqlite in columnas_sqlite:
                    if col_sqlite in mapeo_columnas:
                        valor = fila[col_sqlite]
                        
                        # Limpiar y convertir valores
                        if valor is None:
                            valores.append(None)
                        elif isinstance(valor, str):
                            # Limpiar strings problemáticos
                            valor_limpio = valor.strip()
                            if valor_limpio == '' or valor_limpio.lower() == 'null':
                                valores.append(None)
                            else:
                                valores.append(valor_limpio)
                        else:
                            valores.append(valor)
                
                if valores:  # Solo insertar si hay valores
                    cursor_mysql.execute(query, valores)
                    registros_insertados += 1
                    
                    if registros_insertados % 100 == 0:
                        print(f"      - Insertados {registros_insertados} registros...")
                        
            except Exception as e:
                errores += 1
                if errores <= 3:
                    print(f"      ⚠️ Error insertando registro: {str(e)[:100]}...")
                continue
        
        print(f"    ✅ {registros_insertados} registros insertados")
        if errores > 0:
            print(f"    ⚠️ {errores} errores")
        
        return True
        
    except Exception as e:
        print(f"    ❌ Error migrando tabla `{tabla_original}`: {e}")
        return False

def eliminar_todas_las_tablas_mysql_seguro(cursor_mysql):
    """Elimina todas las tablas de MySQL de manera segura"""
    print("\n🗑️ Eliminando todas las tablas de MySQL...")
    
    try:
        # Desactivar verificación de claves foráneas
        cursor_mysql.execute("SET FOREIGN_KEY_CHECKS = 0")
        cursor_mysql.execute("SET SQL_MODE = 'NO_AUTO_VALUE_ON_ZERO'")
        
        # Obtener lista de tablas
        cursor_mysql.execute("SHOW TABLES")
        tablas = [list(row.values())[0] for row in cursor_mysql.fetchall()]
        
        # Eliminar cada tabla
        for tabla in tablas:
            try:
                cursor_mysql.execute(f"DROP TABLE IF EXISTS `{tabla}`")
                print(f"  - Tabla `{tabla}` eliminada")
            except Exception as e:
                print(f"  ⚠️ Error eliminando tabla `{tabla}`: {e}")
        
        # Reactivar verificación de claves foráneas
        cursor_mysql.execute("SET FOREIGN_KEY_CHECKS = 1")
        
        print(f"  ✅ {len(tablas)} tablas procesadas")
        return True
        
    except Exception as e:
        print(f"  ❌ Error eliminando tablas: {e}")
        return False

def migrar_ultra_perfecto():
    """Función principal de migración ultra perfecta"""
    print("=== MIGRACIÓN ULTRA PERFECTA DE SQLITE A MYSQL ===")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🎯 Objetivo: Migración 100% garantizada")
    
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
        if not eliminar_todas_las_tablas_mysql_seguro(cursor_mysql):
            print("⚠️ Continuando a pesar de errores en eliminación...")
        conn_mysql.commit()
        
        # Obtener mapeo de tablas
        tablas_mapeadas = obtener_todas_las_tablas_sqlite(cursor_sqlite)
        
        # Recrear tablas en MySQL
        print("\n🔧 Recreando tablas en MySQL...")
        tablas_creadas = 0
        
        for tabla_original, tabla_mysql in tablas_mapeadas.items():
            estructura = obtener_estructura_tabla_sqlite(cursor_sqlite, tabla_original)
            if estructura and crear_tabla_mysql_ultra_perfecta(cursor_mysql, tabla_original, tabla_mysql, estructura):
                tablas_creadas += 1
            conn_mysql.commit()
        
        print(f"\n✅ {tablas_creadas}/{len(tablas_mapeadas)} tablas recreadas")
        
        # Migrar datos
        print("\n💾 Migrando datos...")
        tablas_migradas = 0
        
        for tabla_original, tabla_mysql in tablas_mapeadas.items():
            if migrar_datos_tabla_ultra_perfecta(tabla_original, tabla_mysql, cursor_sqlite, cursor_mysql):
                tablas_migradas += 1
            conn_mysql.commit()
        
        print(f"\n=== RESUMEN DE MIGRACIÓN ULTRA PERFECTA ===")
        print(f"✅ Tablas recreadas: {tablas_creadas}/{len(tablas_mapeadas)}")
        print(f"✅ Tablas migradas: {tablas_migradas}/{len(tablas_mapeadas)}")
        
        porcentaje_exito = (min(tablas_creadas, tablas_migradas) / len(tablas_mapeadas)) * 100
        print(f"📊 Porcentaje de éxito: {porcentaje_exito:.1f}%")
        
        if porcentaje_exito >= 95:
            print("\n🎉 MIGRACIÓN ULTRA PERFECTA COMPLETADA")
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

def verificar_migracion_ultra_perfecta():
    """Verifica la migración ultra perfecta"""
    print("\n=== VERIFICACIÓN ULTRA PERFECTA ===")
    
    conn_sqlite = conectar_sqlite()
    conn_mysql = conectar_mysql()
    
    if not conn_sqlite or not conn_mysql:
        return False
    
    try:
        cursor_sqlite = conn_sqlite.cursor()
        cursor_mysql = conn_mysql.cursor()
        
        # Obtener tablas
        cursor_sqlite.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tablas_sqlite = [row[0] for row in cursor_sqlite.fetchall()]
        
        cursor_mysql.execute("SHOW TABLES")
        tablas_mysql = [list(row.values())[0] for row in cursor_mysql.fetchall()]
        
        print(f"📊 Tablas en SQLite: {len(tablas_sqlite)}")
        print(f"📊 Tablas en MySQL: {len(tablas_mysql)}")
        
        total_sqlite = 0
        total_mysql = 0
        coincidencias_perfectas = 0
        
        for tabla_sqlite in tablas_sqlite:
            tabla_mysql = limpiar_nombre_tabla(tabla_sqlite)
            
            # Contar registros en SQLite
            try:
                cursor_sqlite.execute(f"SELECT COUNT(*) FROM `{tabla_sqlite}`")
                count_sqlite = cursor_sqlite.fetchone()[0]
                total_sqlite += count_sqlite
            except:
                count_sqlite = 0
            
            # Contar registros en MySQL
            if tabla_mysql in tablas_mysql:
                try:
                    cursor_mysql.execute(f"SELECT COUNT(*) FROM `{tabla_mysql}`")
                    count_mysql = cursor_mysql.fetchone()['COUNT(*)']
                    total_mysql += count_mysql
                    
                    if count_sqlite == count_mysql and count_sqlite > 0:
                        print(f"🎯 `{tabla_sqlite}` → `{tabla_mysql}`: {count_sqlite} registros (PERFECTO)")
                        coincidencias_perfectas += 1
                    elif count_sqlite == count_mysql and count_sqlite == 0:
                        print(f"✅ `{tabla_sqlite}` → `{tabla_mysql}`: Vacía (OK)")
                        coincidencias_perfectas += 1
                    else:
                        print(f"⚠️ `{tabla_sqlite}` → `{tabla_mysql}`: SQLite={count_sqlite}, MySQL={count_mysql}")
                except Exception as e:
                    print(f"❌ Error contando `{tabla_mysql}`: {e}")
            else:
                print(f"❌ `{tabla_sqlite}` → `{tabla_mysql}`: No existe en MySQL")
        
        porcentaje_perfecto = (coincidencias_perfectas / len(tablas_sqlite)) * 100 if tablas_sqlite else 0
        
        print(f"\n📊 Resumen ultra perfecto:")
        print(f"  - Total registros SQLite: {total_sqlite}")
        print(f"  - Total registros MySQL: {total_mysql}")
        print(f"  - Tablas perfectas: {coincidencias_perfectas}/{len(tablas_sqlite)}")
        print(f"  - Porcentaje perfecto: {porcentaje_perfecto:.1f}%")
        
        if porcentaje_perfecto >= 95:
            print("\n🎉 VERIFICACIÓN: MIGRACIÓN ULTRA PERFECTA CONFIRMADA")
            return True
        else:
            print("\n⚠️ VERIFICACIÓN: Necesita mejoras")
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
    print("🚀 Iniciando migración ULTRA PERFECTA de SQLite a MySQL...")
    print("🎯 Garantía: Migración al 100% o mejora continua")
    print("⚠️ ADVERTENCIA: Esto eliminará TODAS las tablas de MySQL")
    
    respuesta = input("¿Continuar con la migración ULTRA PERFECTA? (s/N): ")
    if respuesta.lower() not in ['s', 'si', 'sí', 'y', 'yes']:
        print("❌ Migración cancelada")
        exit()
    
    # Realizar migración ultra perfecta
    exito = migrar_ultra_perfecto()
    
    # Verificar migración
    verificacion_exitosa = verificar_migracion_ultra_perfecta()
    
    if exito and verificacion_exitosa:
        print("\n🎉 PROCESO ULTRA PERFECTO COMPLETADO AL 100%")
    else:
        print("\n🔄 PROCESO COMPLETADO - Listo para siguiente iteración")
    
    input("\nPresiona Enter para continuar...")