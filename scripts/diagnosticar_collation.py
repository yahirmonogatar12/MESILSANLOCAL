#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diagnóstico de problemas de collation en MySQL
"""

import mysql.connector

DB_CONFIG = {
    'host': 'up-de-fra1-mysql-1.db.run-on-seenode.com',
    'port': 11550,
    'user': 'db_rrpq0erbdujn',
    'password': '5fUNbSRcPP3LN9K2I33Pr0ge',
    'database': 'db_rrpq0erbdujn',
    'charset': 'utf8mb4'
}

def diagnosticar_collations():
    """Diagnosticar problemas de collation"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("=== DIAGNÓSTICO DE COLLATIONS ===\n")
        
        # 1. Verificar collation de la base de datos
        print("1. COLLATION DE BASE DE DATOS:")
        cursor.execute("SELECT @@collation_database")
        db_collation = cursor.fetchone()[0]
        print(f"   Base de datos: {db_collation}\n")
        
        # 2. Verificar collations de tablas principales
        print("2. COLLATIONS DE TABLAS:")
        tablas = ['control_material_salida', 'movimientosimd_smd', 'historial_cambio_material_smt']
        
        for tabla in tablas:
            cursor.execute(f"""
                SELECT TABLE_COLLATION 
                FROM information_schema.TABLES 
                WHERE TABLE_SCHEMA = 'db_rrpq0erbdujn' 
                AND TABLE_NAME = '{tabla}'
            """)
            result = cursor.fetchone()
            if result:
                print(f"   {tabla}: {result[0]}")
            else:
                print(f"   {tabla}: NO EXISTE")
        
        print()
        
        # 3. Verificar collations de columnas específicas
        print("3. COLLATIONS DE COLUMNAS CRÍTICAS:")
        
        # Columnas de control_material_salida
        cursor.execute(f"""
            SELECT COLUMN_NAME, COLLATION_NAME 
            FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = 'db_rrpq0erbdujn' 
            AND TABLE_NAME = 'control_material_salida'
            AND COLLATION_NAME IS NOT NULL
        """)
        
        print("   control_material_salida:")
        for columna, collation in cursor.fetchall():
            print(f"     {columna}: {collation}")
        
        # Columnas de movimientosimd_smd
        cursor.execute(f"""
            SELECT COLUMN_NAME, COLLATION_NAME 
            FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = 'db_rrpq0erbdujn' 
            AND TABLE_NAME = 'movimientosimd_smd'
            AND COLLATION_NAME IS NOT NULL
        """)
        
        print("   movimientosimd_smd:")
        for columna, collation in cursor.fetchall():
            print(f"     {columna}: {collation}")
        
        print()
        
        # 4. Verificar triggers
        print("4. TRIGGERS ACTIVOS:")
        cursor.execute("SHOW TRIGGERS")
        
        triggers_encontrados = False
        for trigger in cursor.fetchall():
            if trigger[1] in tablas:  # trigger[1] es la tabla
                print(f"   {trigger[0]} en {trigger[1]} ({trigger[2]} {trigger[3]})")
                triggers_encontrados = True
        
        if not triggers_encontrados:
            print("   No se encontraron triggers en las tablas principales")
        
        print()
        
        # 5. Probar inserción simple
        print("5. PRUEBA DE INSERCIÓN:")
        test_data = (
            'TEST123',  # codigo_material_recibido
            'LOTE_TEST',  # numero_lote
            'MODELO_TEST',  # modelo
            'SMD',  # depto_salida
            'PRODUCCION',  # proceso_salida
            100,  # cantidad_salida
            '2025-08-13',  # fecha_salida
            '2025-08-13 12:00:00',  # fecha_registro
            'TEST'  # especificacion_material
        )
        
        try:
            cursor.execute("""
                INSERT INTO control_material_salida (
                    codigo_material_recibido, numero_lote, modelo, depto_salida,
                    proceso_salida, cantidad_salida, fecha_salida, fecha_registro, especificacion_material
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, test_data)
            
            print("   ✓ Inserción de prueba exitosa")
            
            # Limpiar el registro de prueba
            cursor.execute("DELETE FROM control_material_salida WHERE codigo_material_recibido = 'TEST123'")
            conn.commit()
            
        except Exception as e:
            print(f"   ✗ Error en inserción de prueba: {e}")
            conn.rollback()
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"Error de conexión: {e}")
        return False

def generar_solucion():
    """Generar script de solución para collations"""
    print("\n=== SOLUCIÓN RECOMENDADA ===\n")
    
    script_sql = """
-- Script para unificar collations
-- Ejecutar como administrador de base de datos

-- 1. Cambiar collation de la base de datos
ALTER DATABASE db_rrpq0erbdujn CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 2. Cambiar collation de tabla control_material_salida
ALTER TABLE control_material_salida CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 3. Cambiar collation de tabla movimientosimd_smd
ALTER TABLE movimientosimd_smd CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 4. Cambiar collation de tabla historial_cambio_material_smt
ALTER TABLE historial_cambio_material_smt CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 5. Verificar cambios
SELECT TABLE_NAME, TABLE_COLLATION 
FROM information_schema.TABLES 
WHERE TABLE_SCHEMA = 'db_rrpq0erbdujn' 
AND TABLE_NAME IN ('control_material_salida', 'movimientosimd_smd', 'historial_cambio_material_smt');
"""
    
    print("Ejecute el siguiente script SQL en MySQL:")
    print(script_sql)
    
    # Guardar script en archivo
    with open('fix_collation.sql', 'w', encoding='utf-8') as f:
        f.write(script_sql)
    
    print("Script guardado en: fix_collation.sql")

if __name__ == '__main__':
    print("Iniciando diagnóstico de collations...\n")
    
    if diagnosticar_collations():
        generar_solucion()
    else:
        print("No se pudo completar el diagnóstico")
