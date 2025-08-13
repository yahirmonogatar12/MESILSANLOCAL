#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script completo para corregir todos los errores detectados en el sistema
"""

import os
import re
from datetime import datetime

def corregir_db_mysql():
    """Corregir errores en db_mysql.py"""
    ruta_archivo = r"c:\Users\yahir\OneDrive\Escritorio\MES\MES\MESILSANLOCAL\app\db_mysql.py"
    
    print("🔧 Corrigiendo errores en db_mysql.py...")
    
    try:
        # Leer el archivo
        with open(ruta_archivo, 'r', encoding='utf-8') as f:
            contenido = f.read()
        
        # Hacer backup
        with open(ruta_archivo + '.backup', 'w', encoding='utf-8') as f:
            f.write(contenido)
        print("✅ Backup creado: db_mysql.py.backup")
        
        correcciones = 0
        
        # 1. Corregir cantidad_recibida por cantidad_actual
        if "cantidad_recibida" in contenido:
            contenido = contenido.replace("cantidad_recibida", "cantidad_actual")
            correcciones += 1
            print("✅ Corregido: cantidad_recibida → cantidad_actual")
        
        # 2. Corregir cantidad_actual por cantidad_total en inventario_general
        patron_insert = r"INSERT INTO inventario_general \(numero_parte, cantidad_actual, fecha_actualizacion\)"
        if re.search(patron_insert, contenido):
            contenido = re.sub(patron_insert, "INSERT INTO inventario_general (numero_parte, cantidad_total, fecha_actualizacion)", contenido)
            correcciones += 1
            print("✅ Corregido: cantidad_actual → cantidad_total en INSERT")
        
        # 3. Corregir en UPDATE también
        patron_update = r"cantidad_actual = VALUES\(cantidad_actual\)"
        if re.search(patron_update, contenido):
            contenido = re.sub(patron_update, "cantidad_total = VALUES(cantidad_total)", contenido)
            correcciones += 1
            print("✅ Corregido: cantidad_actual → cantidad_total en UPDATE")
        
        # Escribir archivo corregido
        with open(ruta_archivo, 'w', encoding='utf-8') as f:
            f.write(contenido)
        
        print(f"📊 Correcciones aplicadas en db_mysql.py: {correcciones}")
        return True
        
    except Exception as e:
        print(f"❌ Error corrigiendo db_mysql.py: {e}")
        return False

def verificar_trigger_smd():
    """Crear un trigger mejorado que incluya SMD"""
    print("🔧 Creando trigger mejorado que incluya distribución SMD...")
    
    trigger_sql = """-- Trigger mejorado para distribución automática con SMD incluido

-- Eliminar trigger existente
DROP TRIGGER IF EXISTS tr_distribuir_salidas_por_tipo;

-- Crear trigger mejorado
CREATE TRIGGER tr_distribuir_salidas_por_tipo
    AFTER INSERT ON control_material_salida
    FOR EACH ROW
BEGIN
    -- Distribución directa para SMD basado en especificación
    IF NEW.especificacion_material LIKE '%SMD%' OR NEW.modelo LIKE '%SMD%' THEN
        INSERT INTO InventarioRollosSMD (
            numero_parte, codigo_barras, lote, cantidad_inicial, cantidad_actual,
            estado, movimiento_origen_id, usuario_responsable, observaciones
        ) VALUES (
            NEW.codigo_material_recibido,
            CONCAT('AUTO_SMD_', NEW.id, '_', DATE_FORMAT(NOW(), '%Y%m%d_%H%i%s')),
            NEW.numero_lote,
            NEW.cantidad_salida,
            NEW.cantidad_salida,
            'ACTIVO',
            NEW.id,
            'SISTEMA_AUTO',
            CONCAT('Auto-distribución SMD desde salida ID: ', NEW.id, ' - Modelo: ', NEW.modelo)
        );
    END IF;
    
    -- Distribución directa para IMD basado en especificación
    IF NEW.especificacion_material LIKE '%IMD%' OR NEW.modelo LIKE '%IMD%' THEN
        INSERT INTO InventarioRollosIMD (
            numero_parte, codigo_barras, lote, cantidad_inicial, cantidad_actual,
            estado, movimiento_origen_id, usuario_responsable, observaciones
        ) VALUES (
            NEW.codigo_material_recibido,
            CONCAT('AUTO_IMD_', NEW.id, '_', DATE_FORMAT(NOW(), '%Y%m%d_%H%i%s')),
            NEW.numero_lote,
            NEW.cantidad_salida,
            NEW.cantidad_salida,
            'ACTIVO',
            NEW.id,
            'SISTEMA_AUTO',
            CONCAT('Auto-distribución IMD desde salida ID: ', NEW.id, ' - Modelo: ', NEW.modelo)
        );
    END IF;
    
    -- Distribución directa para MAIN basado en especificación
    IF NEW.especificacion_material LIKE '%MAIN%' OR NEW.modelo LIKE '%MAIN%' THEN
        INSERT INTO InventarioRollosMAIN (
            numero_parte, codigo_barras, lote, cantidad_inicial, cantidad_actual,
            estado, movimiento_origen_id, usuario_responsable, observaciones
        ) VALUES (
            NEW.codigo_material_recibido,
            CONCAT('AUTO_MAIN_', NEW.id, '_', DATE_FORMAT(NOW(), '%Y%m%d_%H%i%s')),
            NEW.numero_lote,
            NEW.cantidad_salida,
            NEW.cantidad_salida,
            'ACTIVO',
            NEW.id,
            'SISTEMA_AUTO',
            CONCAT('Auto-distribución MAIN desde salida ID: ', NEW.id, ' - Modelo: ', NEW.modelo)
        );
    END IF;
END;"""
    
    # Guardar el trigger en un archivo SQL
    ruta_trigger = r"c:\Users\yahir\OneDrive\Escritorio\MES\MES\MESILSANLOCAL\scripts\trigger_distribucion_completo.sql"
    with open(ruta_trigger, 'w', encoding='utf-8') as f:
        f.write(trigger_sql)
    
    print(f"✅ Trigger guardado en: {ruta_trigger}")
    print("📋 Para aplicarlo, ejecuta este archivo SQL en tu base de datos")
    
    return True

def generar_script_prueba_sistema():
    """Generar script de prueba para verificar que todo funciona"""
    print("🧪 Generando script de prueba del sistema...")
    
    script_prueba = """#!/usr/bin/env python3
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
        print(f'\\n🔄 Probando distribución SMD...')
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
        
        print(f'\\n📊 Estado DESPUÉS:')
        print(f'   SMD: {smd_despues} rollos (+{smd_despues - smd_antes})')
        print(f'   IMD: {imd_despues} rollos (+{imd_despues - imd_antes})')
        print(f'   MAIN: {main_despues} rollos (+{main_despues - main_antes})')
        
        # Verificar resultados
        exito_smd = smd_despues > smd_antes
        exito_imd = imd_despues > imd_antes  
        exito_main = main_despues > main_antes
        
        print(f'\\n🎯 RESULTADOS:')
        print(f'   SMD: {"✅ FUNCIONANDO" if exito_smd else "❌ NO FUNCIONANDO"}')
        print(f'   IMD: {"✅ FUNCIONANDO" if exito_imd else "❌ NO FUNCIONANDO"}')
        print(f'   MAIN: {"✅ FUNCIONANDO" if exito_main else "❌ NO FUNCIONANDO"}')
        
        if exito_smd and exito_imd and exito_main:
            print(f'\\n🎉 ¡SISTEMA COMPLETAMENTE FUNCIONAL!')
            print(f'   Todos los tipos de material se distribuyen automáticamente')
        else:
            print(f'\\n⚠️  Sistema parcialmente funcional - revisar triggers')
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f'❌ Error en prueba: {e}')

if __name__ == "__main__":
    probar_distribucion_completa()
    input("Presione Enter para continuar...")
"""
    
    ruta_prueba = r"c:\Users\yahir\OneDrive\Escritorio\MES\MES\MESILSANLOCAL\scripts\probar_sistema_completo.py"
    with open(ruta_prueba, 'w', encoding='utf-8') as f:
        f.write(script_prueba)
    
    print(f"✅ Script de prueba guardado en: {ruta_prueba}")
    return True

def main():
    """Función principal"""
    print("=" * 70)
    print("🔧 CORRECCIÓN COMPLETA DEL SISTEMA")
    print("=" * 70)
    print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. Corregir db_mysql.py
    print("\n1️⃣ Corrigiendo db_mysql.py...")
    corregir_db_mysql()
    
    # 2. Crear trigger mejorado
    print("\n2️⃣ Creando trigger mejorado...")
    verificar_trigger_smd()
    
    # 3. Generar script de prueba
    print("\n3️⃣ Generando script de prueba...")
    generar_script_prueba_sistema()
    
    print("\n" + "=" * 70)
    print("✅ CORRECCIÓN COMPLETA TERMINADA")
    print("=" * 70)
    
    print("\n📋 PRÓXIMOS PASOS:")
    print("1. 🗄️  Ejecutar el archivo SQL del trigger en la base de datos:")
    print("   📁 trigger_distribucion_completo.sql")
    print("")
    print("2. 🧪 Ejecutar el script de prueba:")
    print("   📁 probar_sistema_completo.py")
    print("")
    print("3. 🔄 Reiniciar la aplicación Flask para aplicar cambios en db_mysql.py")
    print("")
    print("4. ✅ Verificar que los errores de columnas ya no aparezcan")

if __name__ == "__main__":
    main()
    input("\nPresione Enter para salir...")
