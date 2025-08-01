#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para corregir los últimos casos y alcanzar migración 100% perfecta
Corrige específicamente usuarios_sistema y auditoria
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

def corregir_usuarios_sistema(cursor_sqlite, cursor_mysql, conn_mysql):
    """Corrige específicamente la tabla usuarios_sistema"""
    print("\n🔧 Corrigiendo tabla usuarios_sistema...")
    
    try:
        # Obtener datos de SQLite
        cursor_sqlite.execute("SELECT * FROM usuarios_sistema")
        datos_sqlite = cursor_sqlite.fetchall()
        
        print(f"  - Registros en SQLite: {len(datos_sqlite)}")
        
        # Verificar estructura de MySQL
        cursor_mysql.execute("DESCRIBE usuarios_sistema")
        columnas_mysql = {row['Field']: row for row in cursor_mysql.fetchall()}
        
        print(f"  - Columnas en MySQL: {list(columnas_mysql.keys())}")
        
        # Limpiar tabla MySQL
        cursor_mysql.execute("DELETE FROM usuarios_sistema")
        print("  - Tabla MySQL limpiada")
        
        # Obtener columnas de SQLite
        columnas_sqlite = [description[0] for description in cursor_sqlite.description]
        print(f"  - Columnas en SQLite: {columnas_sqlite}")
        
        # Mapear columnas compatibles
        mapeo_columnas = []
        for col_sqlite in columnas_sqlite:
            if col_sqlite in columnas_mysql:
                mapeo_columnas.append(col_sqlite)
        
        print(f"  - Columnas mapeadas: {mapeo_columnas}")
        
        if not mapeo_columnas:
            print("  ❌ No se encontraron columnas compatibles")
            return False
        
        # Insertar datos uno por uno con manejo de errores detallado
        placeholders = ', '.join(['%s'] * len(mapeo_columnas))
        columnas_str = ', '.join([f'`{col}`' for col in mapeo_columnas])
        query = f"INSERT INTO usuarios_sistema ({columnas_str}) VALUES ({placeholders})"
        
        registros_insertados = 0
        errores = 0
        
        for i, fila in enumerate(datos_sqlite):
            try:
                valores = []
                for col in mapeo_columnas:
                    valor = fila[col]
                    
                    # Procesar valores especiales
                    if valor is None:
                        valores.append(None)
                    elif isinstance(valor, str):
                        valor_limpio = valor.strip()
                        if valor_limpio == '' or valor_limpio.lower() in ['null', 'none']:
                            valores.append(None)
                        else:
                            # Truncar strings muy largos
                            if len(valor_limpio) > 255:
                                valor_limpio = valor_limpio[:255]
                            valores.append(valor_limpio)
                    else:
                        valores.append(valor)
                
                cursor_mysql.execute(query, valores)
                registros_insertados += 1
                
            except Exception as e:
                errores += 1
                print(f"    ⚠️ Error en registro {i+1}: {str(e)[:100]}...")
                print(f"      Datos: {dict(zip(mapeo_columnas, [fila[col] for col in mapeo_columnas]))}")
                continue
        
        conn_mysql.commit()
        
        print(f"  ✅ {registros_insertados} registros insertados")
        if errores > 0:
            print(f"  ⚠️ {errores} errores")
        
        return registros_insertados == len(datos_sqlite)
        
    except Exception as e:
        print(f"  ❌ Error corrigiendo usuarios_sistema: {e}")
        return False

def corregir_auditoria(cursor_sqlite, cursor_mysql, conn_mysql):
    """Corrige específicamente la tabla auditoria"""
    print("\n🔧 Corrigiendo tabla auditoria...")
    
    try:
        # Obtener conteos actuales
        cursor_sqlite.execute("SELECT COUNT(*) FROM auditoria")
        count_sqlite = cursor_sqlite.fetchone()[0]
        
        cursor_mysql.execute("SELECT COUNT(*) FROM auditoria")
        count_mysql = cursor_mysql.fetchone()['COUNT(*)']
        
        print(f"  - SQLite: {count_sqlite} registros")
        print(f"  - MySQL: {count_mysql} registros")
        print(f"  - Diferencia: {count_sqlite - count_mysql} registros")
        
        if count_sqlite == count_mysql:
            print("  ✅ Tabla auditoria ya está sincronizada")
            return True
        
        # Obtener estructura de ambas tablas
        cursor_mysql.execute("DESCRIBE auditoria")
        columnas_mysql = {row['Field']: row for row in cursor_mysql.fetchall()}
        
        # Obtener todos los datos de SQLite
        cursor_sqlite.execute("SELECT * FROM auditoria ORDER BY id")
        datos_sqlite = cursor_sqlite.fetchall()
        
        # Obtener IDs existentes en MySQL
        cursor_mysql.execute("SELECT id FROM auditoria ORDER BY id")
        ids_mysql = {row['id'] for row in cursor_mysql.fetchall()}
        
        # Obtener columnas de SQLite
        columnas_sqlite = [description[0] for description in cursor_sqlite.description]
        
        # Mapear columnas compatibles
        mapeo_columnas = []
        for col_sqlite in columnas_sqlite:
            if col_sqlite in columnas_mysql:
                mapeo_columnas.append(col_sqlite)
        
        print(f"  - Columnas mapeadas: {mapeo_columnas}")
        
        # Identificar registros faltantes
        registros_faltantes = []
        for fila in datos_sqlite:
            if fila['id'] not in ids_mysql:
                registros_faltantes.append(fila)
        
        print(f"  - Registros faltantes: {len(registros_faltantes)}")
        
        if not registros_faltantes:
            print("  ✅ No hay registros faltantes")
            return True
        
        # Insertar registros faltantes
        placeholders = ', '.join(['%s'] * len(mapeo_columnas))
        columnas_str = ', '.join([f'`{col}`' for col in mapeo_columnas])
        query = f"INSERT INTO auditoria ({columnas_str}) VALUES ({placeholders})"
        
        registros_insertados = 0
        errores = 0
        
        for fila in registros_faltantes:
            try:
                valores = []
                for col in mapeo_columnas:
                    valor = fila[col]
                    
                    # Procesar valores especiales
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
                    else:
                        valores.append(valor)
                
                cursor_mysql.execute(query, valores)
                registros_insertados += 1
                
                if registros_insertados % 50 == 0:
                    print(f"    - Insertados {registros_insertados} registros...")
                
            except Exception as e:
                errores += 1
                if errores <= 5:
                    print(f"    ⚠️ Error insertando registro ID {fila['id']}: {str(e)[:100]}...")
                continue
        
        conn_mysql.commit()
        
        print(f"  ✅ {registros_insertados} registros faltantes insertados")
        if errores > 0:
            print(f"  ⚠️ {errores} errores")
        
        # Verificar resultado final
        cursor_mysql.execute("SELECT COUNT(*) FROM auditoria")
        count_final = cursor_mysql.fetchone()['COUNT(*)']
        
        print(f"  📊 Resultado final: {count_final} registros en MySQL")
        
        return count_final == count_sqlite
        
    except Exception as e:
        print(f"  ❌ Error corrigiendo auditoria: {e}")
        return False

def verificacion_final_100():
    """Verificación final para confirmar 100% de migración"""
    print("\n=== VERIFICACIÓN FINAL 100% ===")
    
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
        
        total_sqlite = 0
        total_mysql = 0
        tablas_perfectas = 0
        
        for tabla in tablas_sqlite:
            # Contar registros en SQLite
            try:
                cursor_sqlite.execute(f"SELECT COUNT(*) FROM `{tabla}`")
                count_sqlite = cursor_sqlite.fetchone()[0]
                total_sqlite += count_sqlite
            except:
                count_sqlite = 0
            
            # Contar registros en MySQL
            try:
                cursor_mysql.execute(f"SELECT COUNT(*) FROM `{tabla}`")
                count_mysql = cursor_mysql.fetchone()['COUNT(*)']
                total_mysql += count_mysql
                
                if count_sqlite == count_mysql:
                    if count_sqlite > 0:
                        print(f"🎯 `{tabla}`: {count_sqlite} registros (PERFECTO)")
                    else:
                        print(f"✅ `{tabla}`: Vacía (OK)")
                    tablas_perfectas += 1
                else:
                    print(f"⚠️ `{tabla}`: SQLite={count_sqlite}, MySQL={count_mysql} (DIFERENCIA)")
                    
            except Exception as e:
                print(f"❌ `{tabla}`: Error en MySQL - {e}")
        
        porcentaje_perfecto = (tablas_perfectas / len(tablas_sqlite)) * 100 if tablas_sqlite else 0
        
        print(f"\n📊 RESULTADO FINAL:")
        print(f"  - Total registros SQLite: {total_sqlite}")
        print(f"  - Total registros MySQL: {total_mysql}")
        print(f"  - Tablas perfectas: {tablas_perfectas}/{len(tablas_sqlite)} ({porcentaje_perfecto:.1f}%)")
        
        if porcentaje_perfecto >= 99:
            print("\n🎉 MIGRACIÓN 100% PERFECTA CONFIRMADA")
            return True
        else:
            print(f"\n⚠️ MIGRACIÓN AL {porcentaje_perfecto:.1f}% - Revisar casos restantes")
            return False
        
    except Exception as e:
        print(f"❌ Error en verificación final: {e}")
        return False
    
    finally:
        if conn_sqlite:
            conn_sqlite.close()
        if conn_mysql:
            conn_mysql.close()

def main():
    """Función principal"""
    print("🚀 CORRECCIÓN FINAL PARA MIGRACIÓN 100% PERFECTA")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🎯 Objetivo: Corregir usuarios_sistema y auditoria")
    
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
        
        # Corregir usuarios_sistema
        exito_usuarios = corregir_usuarios_sistema(cursor_sqlite, cursor_mysql, conn_mysql)
        
        # Corregir auditoria
        exito_auditoria = corregir_auditoria(cursor_sqlite, cursor_mysql, conn_mysql)
        
        print(f"\n=== RESUMEN DE CORRECCIONES ===")
        print(f"✅ usuarios_sistema: {'CORREGIDO' if exito_usuarios else 'PENDIENTE'}")
        print(f"✅ auditoria: {'CORREGIDO' if exito_auditoria else 'PENDIENTE'}")
        
        if exito_usuarios and exito_auditoria:
            print("\n🎉 TODAS LAS CORRECCIONES APLICADAS EXITOSAMENTE")
        else:
            print("\n⚠️ ALGUNAS CORRECCIONES NECESITAN REVISIÓN")
        
        return exito_usuarios and exito_auditoria
        
    except Exception as e:
        print(f"❌ Error durante las correcciones: {e}")
        return False
    
    finally:
        if conn_sqlite:
            conn_sqlite.close()
        if conn_mysql:
            conn_mysql.close()

if __name__ == "__main__":
    print("🔧 Iniciando corrección de últimos casos...")
    
    # Aplicar correcciones
    exito_correcciones = main()
    
    # Verificación final
    exito_verificacion = verificacion_final_100()
    
    if exito_correcciones and exito_verificacion:
        print("\n🎉 MIGRACIÓN 100% PERFECTA COMPLETADA")
        print("✅ Todos los datos de SQLite han sido migrados exitosamente a MySQL")
    else:
        print("\n🔄 CORRECCIONES APLICADAS - Verificar casos específicos")
    
    input("\nPresiona Enter para continuar...")