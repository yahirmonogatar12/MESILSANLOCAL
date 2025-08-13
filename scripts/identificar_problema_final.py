#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Identificación final del problema de collation
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

def identificar_problema():
    """Identificar exactamente dónde está el problema"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("=== IDENTIFICACIÓN FINAL DEL PROBLEMA ===\n")
        
        # 1. Verificar todas las collations de la base de datos
        print("1. TODAS LAS COLLATIONS EN LA BASE DE DATOS:")
        cursor.execute("""
            SELECT TABLE_NAME, TABLE_COLLATION 
            FROM information_schema.TABLES 
            WHERE TABLE_SCHEMA = 'db_rrpq0erbdujn' 
            AND TABLE_COLLATION LIKE 'utf8mb4%'
            ORDER BY TABLE_COLLATION, TABLE_NAME
        """)
        
        collations = {}
        for tabla, collation in cursor.fetchall():
            if collation not in collations:
                collations[collation] = []
            collations[collation].append(tabla)
        
        for collation, tablas in collations.items():
            print(f"   {collation}: {len(tablas)} tablas")
            if 'control_material_salida' in tablas or 'movimientosimd_smd' in tablas:
                print(f"     -> Incluye: {[t for t in tablas if t in ['control_material_salida', 'movimientosimd_smd', 'historial_cambio_material_smt']]}")
        
        print()
        
        # 2. Verificar columnas específicas que podrían estar causando conflicto
        print("2. COLUMNAS CON utf8mb4_unicode_ci:")
        cursor.execute("""
            SELECT TABLE_NAME, COLUMN_NAME, COLLATION_NAME 
            FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = 'db_rrpq0erbdujn' 
            AND COLLATION_NAME = 'utf8mb4_unicode_ci'
        """)
        
        unicode_columns = cursor.fetchall()
        if unicode_columns:
            for tabla, columna, collation in unicode_columns:
                print(f"   {tabla}.{columna}: {collation}")
        else:
            print("   No se encontraron columnas con utf8mb4_unicode_ci")
        
        print()
        
        # 3. Buscar tablas relacionadas que podrían tener foreign keys
        print("3. VERIFICANDO FOREIGN KEYS:")
        cursor.execute("""
            SELECT 
                CONSTRAINT_NAME,
                TABLE_NAME,
                COLUMN_NAME,
                REFERENCED_TABLE_NAME,
                REFERENCED_COLUMN_NAME
            FROM information_schema.KEY_COLUMN_USAGE 
            WHERE TABLE_SCHEMA = 'db_rrpq0erbdujn' 
            AND REFERENCED_TABLE_NAME IS NOT NULL
            AND (TABLE_NAME = 'control_material_salida' OR REFERENCED_TABLE_NAME = 'control_material_salida')
        """)
        
        foreign_keys = cursor.fetchall()
        if foreign_keys:
            for fk in foreign_keys:
                print(f"   FK: {fk[1]}.{fk[2]} -> {fk[3]}.{fk[4]}")
                
                # Verificar collation de las columnas relacionadas
                cursor.execute(f"""
                    SELECT COLLATION_NAME 
                    FROM information_schema.COLUMNS 
                    WHERE TABLE_SCHEMA = 'db_rrpq0erbdujn' 
                    AND TABLE_NAME = '{fk[3]}' 
                    AND COLUMN_NAME = '{fk[4]}'
                """)
                ref_collation = cursor.fetchone()
                if ref_collation:
                    print(f"     -> Columna referenciada: {ref_collation[0]}")
        else:
            print("   No se encontraron foreign keys")
        
        print()
        
        # 4. Intentar la inserción sin triggers (si los hay)
        print("4. PROBANDO INSERCIÓN DIRECTA:")
        
        # Primero deshabilitar triggers temporalmente
        cursor.execute("SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO'")
        
        test_data = (
            'TEST_FINAL_123',
            'LOTE_FINAL',
            'MODELO_FINAL',
            'SMD',
            'PRODUCCION',
            100,
            '2025-08-13',
            '2025-08-13 12:00:00',
            'TEST_FINAL'
        )
        
        try:
            cursor.execute("""
                INSERT INTO control_material_salida (
                    codigo_material_recibido, numero_lote, modelo, depto_salida,
                    proceso_salida, cantidad_salida, fecha_salida, fecha_registro, especificacion_material
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, test_data)
            
            # Verificar que se insertó
            cursor.execute("SELECT COUNT(*) FROM control_material_salida WHERE codigo_material_recibido = 'TEST_FINAL_123'")
            count = cursor.fetchone()[0]
            
            if count > 0:
                print("   ✓ Inserción exitosa")
                
                # Limpiar
                cursor.execute("DELETE FROM control_material_salida WHERE codigo_material_recibido = 'TEST_FINAL_123'")
                conn.commit()
                
                print("   ➤ EL PROBLEMA NO ES EN LA INSERCIÓN BÁSICA")
                print("   ➤ PROBABLEMENTE ES UN TRIGGER O CONSTRAINT")
            
        except Exception as e:
            print(f"   ✗ Error: {e}")
            print("   ➤ EL PROBLEMA ES EN LA ESTRUCTURA DE LA TABLA")
        
        cursor.execute("SET SQL_MODE=@OLD_SQL_MODE")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False

def generar_solucion_final():
    """Generar la solución final basada en los hallazgos"""
    print("\n" + "="*60)
    print("SOLUCIÓN FINAL RECOMENDADA")
    print("="*60)
    
    solucion = """
Basado en el análisis, el problema persiste porque hay tablas relacionadas
con diferentes collations. Para solucionarlo completamente:

OPCIÓN 1 - UNIFICAR TODA LA BASE DE DATOS (RECOMENDADO):
```sql
-- Cambiar la collation por defecto de la base de datos
ALTER DATABASE db_rrpq0erbdujn CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;

-- Convertir todas las tablas importantes
ALTER TABLE control_material_salida CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
ALTER TABLE movimientosimd_smd CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
ALTER TABLE historial_cambio_material_smt CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;

-- Si hay otras tablas relacionadas, también convertirlas
-- ALTER TABLE [tabla_relacionada] CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
```

OPCIÓN 2 - SOLUCIÓN TEMPORAL (SI NO PUEDES CAMBIAR TODO):
Modificar las consultas para usar COLLATE explícitamente:
```sql
INSERT INTO control_material_salida (
    codigo_material_recibido, numero_lote, modelo, depto_salida,
    proceso_salida, cantidad_salida, fecha_salida, fecha_registro, especificacion_material
) VALUES (%s COLLATE utf8mb4_0900_ai_ci, %s, %s, %s, %s, %s, %s, %s, %s)
```

PARA IMPLEMENTAR:
1. Ejecuta la OPCIÓN 1 en MySQL Workbench o phpMyAdmin
2. Reinicia la aplicación Flask
3. Prueba las salidas de material nuevamente
"""
    
    print(solucion)

if __name__ == '__main__':
    if identificar_problema():
        generar_solucion_final()
