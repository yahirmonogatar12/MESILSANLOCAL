#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para verificar el estado actual de la base de datos después de la importación
"""

import sys
import os

# Agregar el directorio app al path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

try:
    from db_mysql import execute_query, get_db_connection
except ImportError:
    print("❌ Error: No se puede importar db_mysql")
    sys.exit(1)

def verificar_estado_base_datos():
    """Verificar el estado actual de la base de datos"""
    print("🔍 === VERIFICACIÓN ESTADO BASE DE DATOS ===\n")
    
    try:
        # 1. Contar total de registros
        print("📊 1. CONTEO DE REGISTROS:")
        query_count = "SELECT COUNT(*) as total FROM materiales"
        result = execute_query(query_count, fetch='one')
        if result:
            total_registros = result['total']
            print(f"   Total de materiales en DB: {total_registros}")
        else:
            print("   ❌ Error obteniendo conteo total")
            return
        
        # 2. Verificar registros recientes
        print("\n📅 2. REGISTROS RECIENTES (últimos 10):")
        query_recent = """
            SELECT numero_parte, codigo_material, fecha_registro 
            FROM materiales 
            ORDER BY fecha_registro DESC 
            LIMIT 10
        """
        recent = execute_query(query_recent, fetch='all')
        if recent:
            for i, record in enumerate(recent, 1):
                print(f"   {i}. {record['numero_parte']} - {record['codigo_material']} - {record['fecha_registro']}")
        else:
            print("   ❌ No se encontraron registros recientes")
        
        # 3. Verificar duplicados
        print("\n🔍 3. VERIFICACIÓN DE DUPLICADOS:")
        query_duplicates = """
            SELECT numero_parte, COUNT(*) as count 
            FROM materiales 
            GROUP BY numero_parte 
            HAVING COUNT(*) > 1 
            ORDER BY count DESC
            LIMIT 5
        """
        duplicates = execute_query(query_duplicates, fetch='all')
        if duplicates:
            print(f"   ⚠️ Se encontraron {len(duplicates)} números de parte duplicados:")
            for dup in duplicates:
                print(f"      - {dup['numero_parte']}: {dup['count']} veces")
        else:
            print("   ✅ No se encontraron duplicados")
        
        # 4. Verificar campos vacíos
        print("\n📋 4. VERIFICACIÓN DE CAMPOS VACÍOS:")
        
        # Contar registros con numero_parte vacío
        query_empty_numero = "SELECT COUNT(*) as count FROM materiales WHERE numero_parte IS NULL OR numero_parte = ''"
        empty_numero = execute_query(query_empty_numero, fetch='one')
        if empty_numero and empty_numero['count'] > 0:
            print(f"   ⚠️ Registros con numero_parte vacío: {empty_numero['count']}")
        else:
            print("   ✅ Todos los registros tienen numero_parte")
        
        # Contar registros con codigo_material vacío
        query_empty_codigo = "SELECT COUNT(*) as count FROM materiales WHERE codigo_material IS NULL OR codigo_material = ''"
        empty_codigo = execute_query(query_empty_codigo, fetch='one')
        if empty_codigo and empty_codigo['count'] > 0:
            print(f"   ⚠️ Registros con codigo_material vacío: {empty_codigo['count']}")
        else:
            print("   ✅ Todos los registros tienen codigo_material")
        
        # 5. Verificar estructura de tabla
        print("\n🏗️ 5. ESTRUCTURA DE TABLA:")
        query_structure = "DESCRIBE materiales"
        structure = execute_query(query_structure, fetch='all')
        if structure:
            print(f"   La tabla tiene {len(structure)} columnas:")
            for col in structure:
                print(f"      - {col['Field']}: {col['Type']} {'NULL' if col['Null'] == 'YES' else 'NOT NULL'}")
        
        # 6. Verificar últimas actualizaciones por fecha
        print("\n⏰ 6. DISTRIBUCIÓN POR FECHA DE REGISTRO:")
        query_dates = """
            SELECT DATE(fecha_registro) as fecha, COUNT(*) as count 
            FROM materiales 
            GROUP BY DATE(fecha_registro) 
            ORDER BY fecha DESC 
            LIMIT 5
        """
        dates = execute_query(query_dates, fetch='all')
        if dates:
            for date_record in dates:
                print(f"      {date_record['fecha']}: {date_record['count']} registros")
        
        # 7. Verificar problemas de encoding
        print("\n🔤 7. VERIFICACIÓN DE ENCODING:")
        query_encoding = """
            SELECT numero_parte, propiedad_material 
            FROM materiales 
            WHERE propiedad_material LIKE '%�%' 
               OR numero_parte LIKE '%�%'
            LIMIT 5
        """
        encoding_issues = execute_query(query_encoding, fetch='all')
        if encoding_issues:
            print(f"   ⚠️ Se encontraron {len(encoding_issues)} registros con problemas de encoding:")
            for issue in encoding_issues:
                print(f"      - {issue['numero_parte']}: {issue['propiedad_material'][:50]}...")
        else:
            print("   ✅ No se detectaron problemas de encoding")
        
        # Resumen final
        print(f"\n📊 === RESUMEN ===")
        print(f"✅ Total de registros en base de datos: {total_registros}")
        if total_registros == 259:
            print("🎯 El conteo coincide con los 259 registros reportados como exitosos")
        elif total_registros < 259:
            print(f"⚠️ Faltan {259 - total_registros} registros en la base de datos")
        else:
            print(f"ℹ️ Hay {total_registros - 259} registros adicionales en la base de datos")
        
        return True
        
    except Exception as e:
        print(f"❌ Error verificando estado de base de datos: {e}")
        return False

def verificar_conexion_db():
    """Verificar que la conexión a la base de datos funciona"""
    print("🔌 Verificando conexión a base de datos...")
    try:
        conn = get_db_connection()
        if conn:
            print("✅ Conexión a base de datos exitosa")
            conn.close()
            return True
        else:
            print("❌ Error: No se pudo conectar a la base de datos")
            return False
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Iniciando verificación de base de datos...\n")
    
    # Verificar conexión primero
    if not verificar_conexion_db():
        print("❌ No se puede continuar sin conexión a la base de datos")
        sys.exit(1)
    
    # Verificar estado
    verificar_estado_base_datos()
    
    print("\n✅ Verificación completada")
