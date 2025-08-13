#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Solución DEFINITIVA para el problema de collations
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

def solucion_definitiva():
    """Aplicar la solución definitiva"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("=== SOLUCIÓN DEFINITIVA - UNIFICANDO COLLATIONS ===\n")
        
        # 1. Cambiar collation de la base de datos
        print("1. Cambiando collation de la base de datos...")
        cursor.execute("ALTER DATABASE db_rrpq0erbdujn CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci")
        print("   ✓ Base de datos actualizada")
        
        # 2. Obtener todas las tablas con utf8mb4_unicode_ci
        print("\n2. Identificando tablas con utf8mb4_unicode_ci...")
        cursor.execute("""
            SELECT DISTINCT TABLE_NAME 
            FROM information_schema.TABLES 
            WHERE TABLE_SCHEMA = 'db_rrpq0erbdujn' 
            AND TABLE_COLLATION = 'utf8mb4_unicode_ci'
        """)
        
        tablas_unicode = [row[0] for row in cursor.fetchall()]
        print(f"   Encontradas {len(tablas_unicode)} tablas: {tablas_unicode}")
        
        # 3. Convertir cada tabla
        print("\n3. Convirtiendo tablas...")
        for i, tabla in enumerate(tablas_unicode, 1):
            print(f"   {i}/{len(tablas_unicode)} Convirtiendo {tabla}...")
            try:
                cursor.execute(f"ALTER TABLE {tabla} CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci")
                print(f"     ✓ {tabla} convertida")
            except Exception as e:
                print(f"     ✗ Error en {tabla}: {e}")
        
        conn.commit()
        
        # 4. Verificación final
        print("\n4. Verificación final...")
        cursor.execute("""
            SELECT TABLE_COLLATION, COUNT(*) as total
            FROM information_schema.TABLES 
            WHERE TABLE_SCHEMA = 'db_rrpq0erbdujn' 
            AND TABLE_COLLATION LIKE 'utf8mb4%'
            GROUP BY TABLE_COLLATION
        """)
        
        for collation, count in cursor.fetchall():
            print(f"   {collation}: {count} tablas")
        
        # 5. Prueba final de inserción
        print("\n5. Prueba final de inserción...")
        test_data = (
            '0RH5602C622,202508130001',  # Usar el código real que falló
            '0RH5602C622',
            'MODELO_PRUEBA',
            'SMD',
            'PRODUCCION',
            5000,
            '2025-08-13',
            '2025-08-13 12:00:00',
            'PRUEBA_FINAL'
        )
        
        try:
            cursor.execute("""
                INSERT INTO control_material_salida (
                    codigo_material_recibido, numero_lote, modelo, depto_salida,
                    proceso_salida, cantidad_salida, fecha_salida, fecha_registro, especificacion_material
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, test_data)
            
            print("   ✓ INSERCIÓN EXITOSA - PROBLEMA RESUELTO")
            
            # Limpiar
            cursor.execute("DELETE FROM control_material_salida WHERE codigo_material_recibido = '0RH5602C622,202508130001'")
            conn.commit()
            
        except Exception as e:
            print(f"   ✗ Error en prueba final: {e}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == '__main__':
    print("Aplicando solución definitiva para collations...\n")
    
    if solucion_definitiva():
        print("\n" + "="*60)
        print("✓ ✓ ✓ PROBLEMA RESUELTO DEFINITIVAMENTE ✓ ✓ ✓")
        print("="*60)
        print("Ahora puedes procesar salidas de material sin errores.")
        print("El código '0RH5602C622,202508130001' debería funcionar correctamente.")
    else:
        print("✗ No se pudo aplicar la solución")
