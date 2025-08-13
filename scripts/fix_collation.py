#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para diagnosticar y corregir problemas de collation en MySQL
Soluciona el error: Illegal mix of collations
"""

import mysql.connector
import sys
from datetime import datetime

# Configuración de base de datos
DB_CONFIG = {
    'host': 'up-de-fra1-mysql-1.db.run-on-seenode.com',
    'port': 11550,
    'user': 'db_rrpq0erbdujn',
    'password': '5fUNbSRcPP3LN9K2I33Pr0ge',
    'database': 'db_rrpq0erbdujn',
    'charset': 'utf8mb4'
}

def conectar_db():
    """Establecer conexión con la base de datos"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        print("✓ Conexión a base de datos establecida")
        return connection
    except Exception as e:
        print(f"✗ Error conectando a la base de datos: {e}")
        return None

def diagnosticar_collations():
    """Diagnosticar problemas de collation"""
    print("=== DIAGNÓSTICO DE COLLATIONS ===")
    
    connection = conectar_db()
    if not connection:
        return False
    
    cursor = connection.cursor()
    
    try:
        # 1. Verificar collation de la base de datos
        cursor.execute("SELECT DEFAULT_COLLATION_NAME FROM information_schema.SCHEMATA WHERE SCHEMA_NAME = 'db_rrpq0erbdujn'")
        db_collation = cursor.fetchone()
        print(f"Collation de la base de datos: {db_collation[0] if db_collation else 'No encontrada'}")
        
        # 2. Verificar collation de tablas críticas
        tablas_criticas = ['control_material_salida', 'movimientosimd_smd', 'historial_cambio_material_smt']
        
        for tabla in tablas_criticas:
            print(f"\n--- Tabla: {tabla} ---")
            cursor.execute(f"""
                SELECT COLUMN_NAME, COLLATION_NAME, DATA_TYPE 
                FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = 'db_rrpq0erbdujn' 
                AND TABLE_NAME = '{tabla}'
                AND COLLATION_NAME IS NOT NULL
                ORDER BY ORDINAL_POSITION
            """)
            
            columns = cursor.fetchall()
            if columns:
                for col_name, collation, data_type in columns:
                    print(f"  {col_name}: {collation} ({data_type})")
            else:
                print(f"  No se encontraron columnas con collation para {tabla}")
        
        cursor.close()
        connection.close()
        return True
        
    except Exception as e:
        print(f"Error en diagnóstico: {e}")
        cursor.close()
        connection.close()
        return False

def corregir_collations():
    """Corregir collations para unificar a utf8mb4_unicode_ci"""
    print("\n=== CORRECCIÓN DE COLLATIONS ===")
    
    connection = conectar_db()
    if not connection:
        return False
    
    cursor = connection.cursor()
    
    try:
        # Definir la collation objetivo
        target_collation = 'utf8mb4_unicode_ci'
        
        print(f"Objetivo: Unificar todas las columnas a {target_collation}")
        
        # Obtener todas las columnas de texto que necesitan corrección
        cursor.execute(f"""
            SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE, COLLATION_NAME
            FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = 'db_rrpq0erbdujn' 
            AND COLLATION_NAME IS NOT NULL
            AND COLLATION_NAME != '{target_collation}'
            AND TABLE_NAME IN ('control_material_salida', 'movimientosimd_smd', 'historial_cambio_material_smt', 'InventarioRollosSMD', 'HistorialMovimientosRollosSMD')
            ORDER BY TABLE_NAME, ORDINAL_POSITION
        """)
        
        columnas_a_corregir = cursor.fetchall()
        
        if not columnas_a_corregir:
            print("✓ No se encontraron columnas que necesiten corrección")
            return True
        
        print(f"Se encontraron {len(columnas_a_corregir)} columnas para corregir:")
        
        # Generar y ejecutar comandos ALTER TABLE
        for tabla, columna, tipo_dato, collation_actual in columnas_a_corregir:
            print(f"\nCorrigiendo {tabla}.{columna} ({collation_actual} -> {target_collation})")
            
            # Mapear tipos de datos
            if 'varchar' in tipo_dato.lower():
                nuevo_tipo = tipo_dato
            elif 'text' in tipo_dato.lower():
                nuevo_tipo = tipo_dato
            elif 'char' in tipo_dato.lower():
                nuevo_tipo = tipo_dato
            else:
                continue  # Saltar tipos no textuales
            
            try:
                # Construir comando ALTER TABLE
                alter_sql = f"""
                    ALTER TABLE {tabla} 
                    MODIFY COLUMN {columna} {nuevo_tipo} 
                    CHARACTER SET utf8mb4 COLLATE {target_collation}
                """
                
                cursor.execute(alter_sql)
                connection.commit()
                print(f"  ✓ {tabla}.{columna} corregida")
                
            except Exception as e:
                print(f"  ✗ Error corrigiendo {tabla}.{columna}: {e}")
                continue
        
        cursor.close()
        connection.close()
        
        print(f"\n✓ Corrección de collations completada")
        return True
        
    except Exception as e:
        print(f"Error en corrección: {e}")
        cursor.close()
        connection.close()
        return False

def verificar_solucion():
    """Verificar que la solución funciona probando una inserción"""
    print("\n=== VERIFICACIÓN DE SOLUCIÓN ===")
    
    connection = conectar_db()
    if not connection:
        return False
    
    cursor = connection.cursor()
    
    try:
        # Probar la consulta que estaba fallando
        test_data = (
            '0RH5602C622,202508130001',  # codigo_material_recibido
            '0RH5602C',                   # numero_lote
            'TEST_MODEL',                 # modelo
            'SMD',                        # depto_salida
            'MONTAJE',                    # proceso_salida
            100.0,                        # cantidad_salida
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),  # fecha_salida
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),  # fecha_registro
            'TEST SPECIFICATION'          # especificacion_material
        )
        
        # Intentar inserción de prueba
        cursor.execute("""
            INSERT INTO control_material_salida (
                codigo_material_recibido, numero_lote, modelo, depto_salida,
                proceso_salida, cantidad_salida, fecha_salida, fecha_registro, especificacion_material
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, test_data)
        
        # Si llegamos aquí, la inserción funcionó
        test_id = cursor.lastrowid
        print(f"✓ Inserción de prueba exitosa (ID: {test_id})")
        
        # Eliminar el registro de prueba
        cursor.execute("DELETE FROM control_material_salida WHERE id = %s", (test_id,))
        connection.commit()
        print("✓ Registro de prueba eliminado")
        
        cursor.close()
        connection.close()
        return True
        
    except Exception as e:
        print(f"✗ La solución aún no funciona: {e}")
        cursor.close()
        connection.close()
        return False

def main():
    """Función principal"""
    print("=" * 60)
    print("CORRECTOR DE PROBLEMAS DE COLLATION - MYSQL")
    print("=" * 60)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Paso 1: Diagnóstico
    if not diagnosticar_collations():
        print("✗ Falló el diagnóstico")
        return False
    
    # Paso 2: Corrección
    if not corregir_collations():
        print("✗ Falló la corrección")
        return False
    
    # Paso 3: Verificación
    if not verificar_solucion():
        print("✗ La solución no funciona completamente")
        return False
    
    print("\n" + "=" * 60)
    print("✓ PROBLEMA DE COLLATION SOLUCIONADO")
    print("=" * 60)
    print("Ahora puedes realizar salidas de material sin problemas de collation.")
    
    return True

if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n✗ Proceso cancelado por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n✗ Error inesperado: {e}")
        sys.exit(1)
