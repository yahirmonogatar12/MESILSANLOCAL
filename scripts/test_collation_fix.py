#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Solución alternativa para problemas de collation
Usa COLLATE explícito en las consultas en lugar de modificar la estructura de la DB
"""

import mysql.connector
from datetime import datetime
import sys

# Configuración de base de datos
DB_CONFIG = {
    'host': 'up-de-fra1-mysql-1.db.run-on-seenode.com',
    'port': 11550,
    'user': 'db_rrpq0erbdujn',
    'password': '5fUNbSRcPP3LN9K2I33Pr0ge',
    'database': 'db_rrpq0erbdujn',
    'charset': 'utf8mb4'
}

def test_problematic_query():
    """Probar la consulta problemática con diferentes enfoques"""
    print("=== PROBANDO SOLUCIONES PARA COLLATION ===")
    
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Datos de prueba
        test_data = {
            'codigo_material_recibido': '0RH5602C622,202508130001',
            'numero_lote': '0RH5602C',
            'modelo': 'TEST_MODEL',
            'depto_salida': 'SMD',
            'proceso_salida': 'MONTAJE',
            'cantidad_salida': 100.0,
            'fecha_salida': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'fecha_registro': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'especificacion_material': 'TEST SPECIFICATION'
        }
        
        print("\n1. Probando consulta original (probablemente falle)...")
        try:
            cursor.execute("""
                INSERT INTO control_material_salida (
                    codigo_material_recibido, numero_lote, modelo, depto_salida,
                    proceso_salida, cantidad_salida, fecha_salida, fecha_registro, especificacion_material
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, tuple(test_data.values()))
            
            test_id = cursor.lastrowid
            print(f"✓ Consulta original funcionó (ID: {test_id})")
            cursor.execute("DELETE FROM control_material_salida WHERE id = %s", (test_id,))
            conn.commit()
            
        except Exception as e:
            print(f"✗ Consulta original falló: {e}")
            
            print("\n2. Probando con COLLATE explícito...")
            try:
                cursor.execute("""
                    INSERT INTO control_material_salida (
                        codigo_material_recibido, numero_lote, modelo, depto_salida,
                        proceso_salida, cantidad_salida, fecha_salida, fecha_registro, especificacion_material
                    ) VALUES 
                    (
                        %s COLLATE utf8mb4_unicode_ci, 
                        %s COLLATE utf8mb4_unicode_ci, 
                        %s COLLATE utf8mb4_unicode_ci, 
                        %s COLLATE utf8mb4_unicode_ci,
                        %s COLLATE utf8mb4_unicode_ci, 
                        %s, 
                        %s, 
                        %s, 
                        %s COLLATE utf8mb4_unicode_ci
                    )
                """, tuple(test_data.values()))
                
                test_id = cursor.lastrowid
                print(f"✓ Consulta con COLLATE funcionó (ID: {test_id})")
                cursor.execute("DELETE FROM control_material_salida WHERE id = %s", (test_id,))
                conn.commit()
                
            except Exception as e2:
                print(f"✗ Consulta con COLLATE también falló: {e2}")
                
                print("\n3. Probando con CAST y COLLATE...")
                try:
                    cursor.execute("""
                        INSERT INTO control_material_salida (
                            codigo_material_recibido, numero_lote, modelo, depto_salida,
                            proceso_salida, cantidad_salida, fecha_salida, fecha_registro, especificacion_material
                        ) VALUES 
                        (
                            CAST(%s AS CHAR CHARSET utf8mb4) COLLATE utf8mb4_unicode_ci, 
                            CAST(%s AS CHAR CHARSET utf8mb4) COLLATE utf8mb4_unicode_ci, 
                            CAST(%s AS CHAR CHARSET utf8mb4) COLLATE utf8mb4_unicode_ci, 
                            CAST(%s AS CHAR CHARSET utf8mb4) COLLATE utf8mb4_unicode_ci,
                            CAST(%s AS CHAR CHARSET utf8mb4) COLLATE utf8mb4_unicode_ci, 
                            %s, 
                            %s, 
                            %s, 
                            CAST(%s AS CHAR CHARSET utf8mb4) COLLATE utf8mb4_unicode_ci
                        )
                    """, tuple(test_data.values()))
                    
                    test_id = cursor.lastrowid
                    print(f"✓ Consulta con CAST funcionó (ID: {test_id})")
                    cursor.execute("DELETE FROM control_material_salida WHERE id = %s", (test_id,))
                    conn.commit()
                    
                except Exception as e3:
                    print(f"✗ Todas las soluciones fallaron: {e3}")
                    return False
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"Error de conexión: {e}")
        return False

def generate_collation_patch():
    """Generar parche para el código de la aplicación"""
    patch_content = '''
# PARCHE PARA SOLUCIONAR PROBLEMAS DE COLLATION
# Agregar esta función a tu módulo de base de datos

def ejecutar_insercion_con_collation_segura(cursor, query, params):
    """
    Ejecutar inserción manejando problemas de collation automáticamente
    """
    try:
        # Intentar consulta normal primero
        cursor.execute(query, params)
        return cursor.lastrowid
    except mysql.connector.Error as e:
        if "Illegal mix of collations" in str(e):
            # Si hay problema de collation, usar CAST
            print("⚠ Problema de collation detectado, aplicando corrección...")
            
            # Reemplazar placeholders con CAST para strings
            query_fixed = query
            param_list = list(params)
            
            # Para INSERT INTO control_material_salida específicamente
            if "control_material_salida" in query:
                query_fixed = """
                    INSERT INTO control_material_salida (
                        codigo_material_recibido, numero_lote, modelo, depto_salida,
                        proceso_salida, cantidad_salida, fecha_salida, fecha_registro, especificacion_material
                    ) VALUES 
                    (
                        CAST(%s AS CHAR CHARSET utf8mb4) COLLATE utf8mb4_unicode_ci, 
                        CAST(%s AS CHAR CHARSET utf8mb4) COLLATE utf8mb4_unicode_ci, 
                        CAST(%s AS CHAR CHARSET utf8mb4) COLLATE utf8mb4_unicode_ci, 
                        CAST(%s AS CHAR CHARSET utf8mb4) COLLATE utf8mb4_unicode_ci,
                        CAST(%s AS CHAR CHARSET utf8mb4) COLLATE utf8mb4_unicode_ci, 
                        %s, 
                        %s, 
                        %s, 
                        CAST(%s AS CHAR CHARSET utf8mb4) COLLATE utf8mb4_unicode_ci
                    )
                """
            
            cursor.execute(query_fixed, params)
            return cursor.lastrowid
        else:
            # Re-lanzar si no es problema de collation
            raise e

# EJEMPLO DE USO:
# En lugar de:
#   cursor.execute(query, params)
# 
# Usar:
#   ejecutar_insercion_con_collation_segura(cursor, query, params)
'''
    
    with open('scripts/collation_patch.py', 'w', encoding='utf-8') as f:
        f.write(patch_content)
    
    print("\n=== PARCHE GENERADO ===")
    print("Se ha creado 'scripts/collation_patch.py' con una función helper.")
    print("Puedes importar y usar 'ejecutar_insercion_con_collation_segura' en tu código.")

def main():
    """Función principal"""
    print("=" * 60)
    print("SOLUCIÓN ALTERNATIVA PARA PROBLEMAS DE COLLATION")
    print("=" * 60)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    if test_problematic_query():
        print("\n✓ Se encontró una solución funcional")
        generate_collation_patch()
        
        print("\n" + "=" * 60)
        print("✓ SOLUCIÓN ALTERNATIVA LISTA")
        print("=" * 60)
        print("Usa la función del parche en tu código para manejar collations automáticamente.")
        
        return True
    else:
        print("\n✗ No se pudo encontrar una solución")
        return False

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
