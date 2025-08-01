#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para corregir incompatibilidades SQLite-MySQL en todo el sistema ISEMM_MES
Este script identifica y corrige automáticamente todas las consultas SQL incompatibles
"""

import os
import re
import shutil
from datetime import datetime

def crear_backup_archivo(archivo_path):
    """Crear backup de un archivo antes de modificarlo"""
    backup_path = f"{archivo_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(archivo_path, backup_path)
    print(f"📁 Backup creado: {backup_path}")
    return backup_path

def corregir_consultas_sqlite_master(contenido):
    """Corregir consultas sqlite_master para MySQL"""
    # Reemplazar sqlite_master por INFORMATION_SCHEMA
    contenido = re.sub(
        r"SELECT name FROM sqlite_master WHERE type='table' AND name='([^']+)'",
        r"SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = '\1'",
        contenido
    )
    
    contenido = re.sub(
        r"SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'",
        r"SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = DATABASE()",
        contenido
    )
    
    # Reemplazar PRAGMA table_info
    contenido = re.sub(
        r"PRAGMA table_info\(([^)]+)\)",
        r"SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = \1",
        contenido
    )
    
    return contenido

def corregir_datetime_now(contenido):
    """Corregir datetime('now') por NOW()"""
    contenido = re.sub(r"datetime\('now'\)", "NOW()", contenido)
    return contenido

def corregir_insert_or_replace(contenido):
    """Corregir INSERT OR REPLACE por INSERT ... ON DUPLICATE KEY UPDATE"""
    # Patrón más específico para INSERT OR REPLACE
    patron = r"INSERT OR REPLACE INTO\s+(\w+)\s*\(([^)]+)\)\s*VALUES\s*\(([^)]+)\)"
    
    def reemplazar_insert_or_replace(match):
        tabla = match.group(1)
        columnas = match.group(2)
        valores = match.group(3)
        
        # Crear la parte UPDATE para ON DUPLICATE KEY
        columnas_lista = [col.strip() for col in columnas.split(',')]
        valores_lista = [val.strip() for val in valores.split(',')]
        
        update_parts = []
        for i, col in enumerate(columnas_lista):
            if i < len(valores_lista):
                update_parts.append(f"{col} = VALUES({col})")
        
        update_clause = ", ".join(update_parts)
        
        return f"INSERT INTO {tabla} ({columnas}) VALUES ({valores}) ON DUPLICATE KEY UPDATE {update_clause}"
    
    contenido = re.sub(patron, reemplazar_insert_or_replace, contenido, flags=re.IGNORECASE)
    return contenido

def corregir_placeholders_sql(contenido):
    """Corregir placeholders ? por %s para MySQL"""
    # Solo reemplazar ? que están en contexto SQL (no en strings de Python)
    # Buscar patrones como cursor.execute("...", (...)) y reemplazar ? por %s
    
    def reemplazar_en_execute(match):
        query = match.group(1)
        # Reemplazar ? por %s en la query
        query_corregida = query.replace('?', '%s')
        return f'cursor.execute("{query_corregida}"'
    
    # Patrón para cursor.execute con comillas dobles
    contenido = re.sub(
        r'cursor\.execute\("([^"]*\?[^"]*)"',
        reemplazar_en_execute,
        contenido
    )
    
    # Patrón para cursor.execute con comillas simples
    def reemplazar_en_execute_simple(match):
        query = match.group(1)
        query_corregida = query.replace('?', '%s')
        return f"cursor.execute('{query_corregida}'"
    
    contenido = re.sub(
        r"cursor\.execute\('([^']*\?[^']*)'",,
        reemplazar_en_execute_simple,
        contenido
    )
    
    return contenido

def corregir_autoincrement(contenido):
    """Corregir AUTOINCREMENT por AUTO_INCREMENT"""
    contenido = re.sub(r"INTEGER PRIMARY KEY AUTOINCREMENT", "INT AUTO_INCREMENT PRIMARY KEY", contenido)
    contenido = re.sub(r"AUTOINCREMENT", "AUTO_INCREMENT", contenido)
    return contenido

def corregir_archivo(archivo_path):
    """Corregir un archivo específico"""
    print(f"🔧 Procesando: {archivo_path}")
    
    try:
        with open(archivo_path, 'r', encoding='utf-8') as f:
            contenido_original = f.read()
        
        contenido = contenido_original
        
        # Aplicar todas las correcciones
        contenido = corregir_consultas_sqlite_master(contenido)
        contenido = corregir_datetime_now(contenido)
        contenido = corregir_insert_or_replace(contenido)
        contenido = corregir_placeholders_sql(contenido)
        contenido = corregir_autoincrement(contenido)
        
        # Solo escribir si hay cambios
        if contenido != contenido_original:
            crear_backup_archivo(archivo_path)
            
            with open(archivo_path, 'w', encoding='utf-8') as f:
                f.write(contenido)
            
            print(f"✅ Archivo corregido: {archivo_path}")
            return True
        else:
            print(f"ℹ️ Sin cambios necesarios: {archivo_path}")
            return False
            
    except Exception as e:
        print(f"❌ Error procesando {archivo_path}: {e}")
        return False

def encontrar_archivos_python(directorio_base):
    """Encontrar todos los archivos Python en el proyecto"""
    archivos_python = []
    
    for root, dirs, files in os.walk(directorio_base):
        # Excluir directorios de backup y cache
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'backup']]
        
        for file in files:
            if file.endswith('.py'):
                archivo_path = os.path.join(root, file)
                archivos_python.append(archivo_path)
    
    return archivos_python

def main():
    """Función principal"""
    print("🚀 Iniciando corrección de incompatibilidades SQLite-MySQL")
    print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # Directorio base del proyecto
    directorio_base = os.path.dirname(os.path.abspath(__file__))
    
    # Encontrar archivos Python
    archivos_python = encontrar_archivos_python(directorio_base)
    
    print(f"📁 Encontrados {len(archivos_python)} archivos Python")
    print("="*60)
    
    archivos_modificados = 0
    archivos_procesados = 0
    
    for archivo in archivos_python:
        archivos_procesados += 1
        if corregir_archivo(archivo):
            archivos_modificados += 1
    
    print("="*60)
    print(f"📊 RESUMEN:")
    print(f"   • Archivos procesados: {archivos_procesados}")
    print(f"   • Archivos modificados: {archivos_modificados}")
    print(f"   • Archivos sin cambios: {archivos_procesados - archivos_modificados}")
    
    if archivos_modificados > 0:
        print("\n⚠️ IMPORTANTE:")
        print("   • Se han creado backups de todos los archivos modificados")
        print("   • Revisa los cambios antes de ejecutar la aplicación")
        print("   • Prueba la aplicación en un entorno de desarrollo primero")
    
    print("\n✅ Corrección completada")

if __name__ == "__main__":
    main()