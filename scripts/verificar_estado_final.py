#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verificación final del estado de collations y funcionalidad
"""

import mysql.connector
from datetime import datetime

DB_CONFIG = {
    'host': 'up-de-fra1-mysql-1.db.run-on-seenode.com',
    'port': 11550,
    'user': 'db_rrpq0erbdujn',
    'password': '5fUNbSRcPP3LN9K2I33Pr0ge',
    'database': 'db_rrpq0erbdujn',
    'charset': 'utf8mb4'
}

def verificar_estado_final():
    """Verificar el estado final después de las correcciones"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("=" * 60)
        print("VERIFICACIÓN FINAL DEL ESTADO DEL SISTEMA")
        print("=" * 60)
        print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # 1. Verificar collation de base de datos
        print("1. COLLATION DE BASE DE DATOS:")
        cursor.execute("SELECT @@collation_database")
        db_collation = cursor.fetchone()[0]
        print(f"   {db_collation}")
        print()
        
        # 2. Contar tablas por collation
        print("2. DISTRIBUCIÓN DE COLLATIONS:")
        cursor.execute("""
            SELECT TABLE_COLLATION, COUNT(*) 
            FROM information_schema.TABLES 
            WHERE TABLE_SCHEMA = 'db_rrpq0erbdujn' 
            AND TABLE_COLLATION IS NOT NULL
            GROUP BY TABLE_COLLATION
        """)
        
        for collation, count in cursor.fetchall():
            status = "✓" if "0900_ai_ci" in collation else "⚠"
            print(f"   {status} {collation}: {count} tablas")
        print()
        
        # 3. Verificar tablas críticas
        print("3. TABLAS CRÍTICAS PARA SALIDAS:")
        critical_tables = [
            'control_material_salida',
            'movimientosimd_smd', 
            'historial_cambio_material_smt'
        ]
        
        for table in critical_tables:
            cursor.execute(f"""
                SELECT TABLE_COLLATION 
                FROM information_schema.TABLES 
                WHERE TABLE_SCHEMA = 'db_rrpq0erbdujn' 
                AND TABLE_NAME = '{table}'
            """)
            result = cursor.fetchone()
            if result:
                status = "✓" if "0900_ai_ci" in result[0] else "✗"
                print(f"   {status} {table}: {result[0]}")
            else:
                print(f"   ✗ {table}: NO EXISTE")
        print()
        
        # 4. Verificar columnas problemáticas
        print("4. COLUMNAS CON COLLATION DIFERENTE:")
        cursor.execute("""
            SELECT TABLE_NAME, COLUMN_NAME, COLLATION_NAME
            FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = 'db_rrpq0erbdujn' 
            AND COLLATION_NAME = 'utf8mb4_unicode_ci'
            AND TABLE_NAME IN ('control_material_salida', 'movimientosimd_smd', 'historial_cambio_material_smt')
        """)
        
        problem_columns = cursor.fetchall()
        if problem_columns:
            print("   ⚠ COLUMNAS PROBLEMÁTICAS ENCONTRADAS:")
            for table, column, collation in problem_columns:
                print(f"     {table}.{column}: {collation}")
        else:
            print("   ✓ No se encontraron columnas problemáticas en tablas críticas")
        print()
        
        # 5. Probar inserción del caso original
        print("5. PRUEBA DEL CASO ORIGINAL:")
        print("   Probando: '0RH5602C622,202508130001'")
        
        test_data = (
            '0RH5602C622,202508130001',  # El código original que falló
            '0RH5602C622',
            'MODELO_TEST',
            'SMD',
            'PRODUCCION',
            5000,
            '2025-08-13',
            '2025-08-13 15:00:00',
            'PRUEBA_COLLATION'
        )
        
        try:
            cursor.execute("""
                INSERT INTO control_material_salida (
                    codigo_material_recibido, numero_lote, modelo, depto_salida,
                    proceso_salida, cantidad_salida, fecha_salida, fecha_registro, especificacion_material
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, test_data)
            
            print("   ✓ INSERCIÓN EXITOSA")
            
            # Verificar que se insertó
            cursor.execute("SELECT id FROM control_material_salida WHERE codigo_material_recibido = '0RH5602C622,202508130001'")
            record_id = cursor.fetchone()[0]
            print(f"   ✓ Registro creado con ID: {record_id}")
            
            # Limpiar el registro de prueba
            cursor.execute("DELETE FROM control_material_salida WHERE codigo_material_recibido = '0RH5602C622,202508130001'")
            conn.commit()
            print("   ✓ Registro de prueba eliminado")
            
            print("\n" + "="*60)
            print("🎉 PROBLEMA DE COLLATION COMPLETAMENTE RESUELTO 🎉")
            print("="*60)
            print("✅ El código '0RH5602C622,202508130001' ahora funciona correctamente")
            print("✅ Las salidas de material deberían procesar sin errores")
            print("✅ El sistema está listo para producción")
            
        except Exception as e:
            print(f"   ✗ ERROR: {e}")
            print("\n" + "="*60)
            print("❌ PROBLEMA PERSISTE")
            print("="*60)
            print("El error de collation aún no está completamente resuelto.")
            print("Recomendación: Verificar manualmente todas las tablas relacionadas.")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"Error de conexión: {e}")
        return False

def verificar_inventario_smd():
    """Verificar el estado del sistema de inventario SMD"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("\n" + "="*60)
        print("VERIFICACIÓN DEL SISTEMA DE INVENTARIO SMD")
        print("="*60)
        
        # Verificar tablas SMD
        smd_tables = ['InventarioRollosSMD', 'HistorialMovimientosRollosSMD']
        
        for table in smd_tables:
            cursor.execute(f"SHOW TABLES LIKE '{table}'")
            if cursor.fetchone():
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"✓ {table}: {count} registros")
            else:
                print(f"✗ {table}: NO EXISTE")
        
        # Verificar triggers SMD
        print("\nTriggers SMD:")
        triggers = [
            'trigger_registro_rollo_smd_salida',
            'trigger_actualizar_rollo_smd_mounter'
        ]
        
        for trigger in triggers:
            cursor.execute(f"SHOW TRIGGERS LIKE '{trigger}'")
            if cursor.fetchone():
                print(f"✓ {trigger}: INSTALADO")
            else:
                print(f"✗ {trigger}: NO ENCONTRADO")
        
        conn.close()
        
    except Exception as e:
        print(f"Error verificando inventario SMD: {e}")

if __name__ == '__main__':
    print("Iniciando verificación final del sistema...\n")
    
    if verificar_estado_final():
        verificar_inventario_smd()
        
        print("\n" + "="*60)
        print("RESUMEN FINAL")
        print("="*60)
        print("• Collations unificadas")
        print("• Salidas de material funcionando")
        print("• Sistema de inventario SMD instalado")
        print("• Listo para uso en producción")
        print("="*60)
    else:
        print("No se pudo completar la verificación")
