#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Script de prueba para verificar que el sistema funciona correctamente
'''

import mysql.connector
from datetime import datetime

# Configuración de base de datos
DB_CONFIG = {
    'host': 'up-de-fra1-mysql-1.db.run-on-seenode.com',
    'port': 11550,
    'user': 'db_rrpq0erbdujn',
    'password': '5fUNbSRcPP3LN9K2I33Pr0ge',
    'database': 'db_rrpq0erbdujn',
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_0900_ai_ci'
}

def probar_distribucion_completa():
    '''Probar distribución automática para SMD, IMD y MAIN'''
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print('🧪 PRUEBA COMPLETA DEL SISTEMA DE DISTRIBUCIÓN')
        print('=' * 60)
        
        # Contar registros antes
        cursor.execute('SELECT COUNT(*) FROM InventarioRollosSMD')
        smd_antes = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM InventarioRollosIMD')
        imd_antes = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM InventarioRollosMAIN')
        main_antes = cursor.fetchone()[0]
        
        print(f'📊 Estado ANTES:')
        print(f'   SMD: {smd_antes} rollos')
        print(f'   IMD: {imd_antes} rollos')
        print(f'   MAIN: {main_antes} rollos')
        
        # Prueba 1: Material SMD
        print(f'\n🔄 Probando distribución SMD...')
        cursor.execute('''
            INSERT INTO control_material_salida (
                codigo_material_recibido, 
                numero_lote, 
                modelo, 
                especificacion_material,
                cantidad_salida,
                depto_salida,
                proceso_salida
            ) VALUES (
                'TEST_RESISTOR_SMD',
                'SMD_TEST_001', 
                'PCB_SMD_TEST',
                'Resistor para línea SMD',
                25,
                'PRODUCCION',
                'PRUEBA_SMD'
            )
        ''')
        
        # Prueba 2: Material IMD  
        print(f'🔄 Probando distribución IMD...')
        cursor.execute('''
            INSERT INTO control_material_salida (
                codigo_material_recibido, 
                numero_lote, 
                modelo, 
                especificacion_material,
                cantidad_salida,
                depto_salida,
                proceso_salida
            ) VALUES (
                'TEST_CAPACITOR_IMD',
                'IMD_TEST_001', 
                'PCB_IMD_TEST',
                'Capacitor para línea IMD',
                75,
                'PRODUCCION',
                'PRUEBA_IMD'
            )
        ''')
        
        # Prueba 3: Material MAIN
        print(f'🔄 Probando distribución MAIN...')
        cursor.execute('''
            INSERT INTO control_material_salida (
                codigo_material_recibido, 
                numero_lote, 
                modelo, 
                especificacion_material,
                cantidad_salida,
                depto_salida,
                proceso_salida
            ) VALUES (
                'TEST_IC_MAIN',
                'MAIN_TEST_001', 
                'PCB_MAIN_TEST',
                'IC para línea MAIN',
                10,
                'PRODUCCION',
                'PRUEBA_MAIN'
            )
        ''')
        
        conn.commit()
        
        # Verificar distribución
        cursor.execute('SELECT COUNT(*) FROM InventarioRollosSMD')
        smd_despues = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM InventarioRollosIMD')
        imd_despues = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM InventarioRollosMAIN')
        main_despues = cursor.fetchone()[0]
        
        print(f'\n📊 Estado DESPUÉS:')
        print(f'   SMD: {smd_despues} rollos (+{smd_despues - smd_antes})')
        print(f'   IMD: {imd_despues} rollos (+{imd_despues - imd_antes})')
        print(f'   MAIN: {main_despues} rollos (+{main_despues - main_antes})')
        
        # Verificar resultados
        exito_smd = smd_despues > smd_antes
        exito_imd = imd_despues > imd_antes  
        exito_main = main_despues > main_antes
        
        print(f'\n🎯 RESULTADOS:')
        print(f'   SMD: {"✅ FUNCIONANDO" if exito_smd else "❌ NO FUNCIONANDO"}')
        print(f'   IMD: {"✅ FUNCIONANDO" if exito_imd else "❌ NO FUNCIONANDO"}')
        print(f'   MAIN: {"✅ FUNCIONANDO" if exito_main else "❌ NO FUNCIONANDO"}')
        
        if exito_smd and exito_imd and exito_main:
            print(f'\n🎉 ¡SISTEMA COMPLETAMENTE FUNCIONAL!')
            print(f'   Todos los tipos de material se distribuyen automáticamente')
        else:
            print(f'\n⚠️  Sistema parcialmente funcional - revisar triggers')
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f'❌ Error en prueba: {e}')

if __name__ == "__main__":
    probar_distribucion_completa()
    input("Presione Enter para continuar...")
