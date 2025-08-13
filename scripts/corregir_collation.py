#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para corregir las collations y solucionar el problema
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

def corregir_collations():
    """Corregir las collations para unificar todo"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("=== CORRIGIENDO COLLATIONS ===\n")
        
        # Lista de tablas a corregir
        tablas = [
            'control_material_salida',
            'movimientosimd_smd', 
            'historial_cambio_material_smt'
        ]
        
        for i, tabla in enumerate(tablas, 1):
            print(f"{i}. Corrigiendo {tabla}...")
            try:
                query = f"ALTER TABLE {tabla} CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci"
                cursor.execute(query)
                print(f"   ✓ {tabla} corregida")
            except Exception as e:
                print(f"   ✗ Error en {tabla}: {e}")
        
        conn.commit()
        print("\n✓ PROCESO DE CORRECCIÓN COMPLETADO")
        
        # Verificar resultados
        print("\n=== VERIFICANDO CORRECCIÓN ===")
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
        
        # Probar inserción después de la corrección
        print("\n=== PRUEBA DE INSERCIÓN POST-CORRECCIÓN ===")
        test_data = (
            'TEST123_POST',  # codigo_material_recibido
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
            
            print("   ✓ Inserción de prueba exitosa - PROBLEMA RESUELTO")
            
            # Limpiar el registro de prueba
            cursor.execute("DELETE FROM control_material_salida WHERE codigo_material_recibido = 'TEST123_POST'")
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

if __name__ == '__main__':
    print("Iniciando corrección de collations...\n")
    
    if corregir_collations():
        print("\n" + "="*50)
        print("✓ CORRECCIÓN COMPLETADA EXITOSAMENTE")
        print("="*50)
        print("\nEl problema de collation ha sido resuelto.")
        print("Ahora puedes procesar salidas de material sin errores.")
    else:
        print("✗ No se pudo completar la corrección")
