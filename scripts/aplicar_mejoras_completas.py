#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para aplicar todas las mejoras al sistema
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
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_0900_ai_ci'
}

def aplicar_trigger_mejorado():
    """Aplicar el trigger mejorado directamente en la base de datos"""
    try:
        print("🔄 Conectando a la base de datos...")
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("✅ Conexión establecida")
        
        # 1. Eliminar trigger existente
        print("🗑️  Eliminando trigger existente...")
        cursor.execute("DROP TRIGGER IF EXISTS tr_distribuir_salidas_por_tipo")
        print("✅ Trigger anterior eliminado")
        
        # 2. Crear trigger mejorado
        print("🔧 Creando trigger mejorado con soporte SMD...")
        
        trigger_sql = """
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
END
"""
        
        cursor.execute(trigger_sql)
        print("✅ Trigger mejorado creado exitosamente")
        
        # 3. Verificar que el trigger existe
        cursor.execute("""
            SELECT TRIGGER_NAME, EVENT_MANIPULATION, EVENT_OBJECT_TABLE 
            FROM INFORMATION_SCHEMA.TRIGGERS 
            WHERE TRIGGER_NAME = 'tr_distribuir_salidas_por_tipo'
        """)
        
        trigger_info = cursor.fetchone()
        if trigger_info:
            print(f"✅ Trigger verificado: {trigger_info[0]} en tabla {trigger_info[2]}")
        else:
            print("❌ Error: Trigger no se creó correctamente")
            return False
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("🎉 Trigger aplicado exitosamente")
        return True
        
    except Exception as e:
        print(f"❌ Error aplicando trigger: {e}")
        return False

def probar_distribucion_completa():
    """Probar que el sistema funciona con los 3 tipos"""
    try:
        print("\n🧪 PROBANDO SISTEMA COMPLETO")
        print("=" * 50)
        
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Contar registros antes
        cursor.execute('SELECT COUNT(*) FROM InventarioRollosSMD')
        smd_antes = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM InventarioRollosIMD')
        imd_antes = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM InventarioRollosMAIN')
        main_antes = cursor.fetchone()[0]
        
        print(f"📊 Estado ANTES:")
        print(f"   SMD: {smd_antes} rollos")
        print(f"   IMD: {imd_antes} rollos")
        print(f"   MAIN: {main_antes} rollos")
        
        # Prueba 1: Material SMD
        print(f"\n🔄 Probando distribución SMD...")
        cursor.execute("""
            INSERT INTO control_material_salida (
                codigo_material_recibido, 
                numero_lote, 
                modelo, 
                especificacion_material,
                cantidad_salida,
                depto_salida,
                proceso_salida
            ) VALUES (
                'TEST_RESISTOR_SMD_FINAL',
                'SMD_FINAL_001', 
                'PCB_SMD_FINAL',
                'Resistor para línea SMD',
                25,
                'PRODUCCION',
                'PRUEBA_SMD_FINAL'
            )
        """)
        
        # Prueba 2: Material IMD  
        print(f"🔄 Probando distribución IMD...")
        cursor.execute("""
            INSERT INTO control_material_salida (
                codigo_material_recibido, 
                numero_lote, 
                modelo, 
                especificacion_material,
                cantidad_salida,
                depto_salida,
                proceso_salida
            ) VALUES (
                'TEST_CAPACITOR_IMD_FINAL',
                'IMD_FINAL_001', 
                'PCB_IMD_FINAL',
                'Capacitor para línea IMD',
                75,
                'PRODUCCION',
                'PRUEBA_IMD_FINAL'
            )
        """)
        
        # Prueba 3: Material MAIN
        print(f"🔄 Probando distribución MAIN...")
        cursor.execute("""
            INSERT INTO control_material_salida (
                codigo_material_recibido, 
                numero_lote, 
                modelo, 
                especificacion_material,
                cantidad_salida,
                depto_salida,
                proceso_salida
            ) VALUES (
                'TEST_IC_MAIN_FINAL',
                'MAIN_FINAL_001', 
                'PCB_MAIN_FINAL',
                'IC para línea MAIN',
                10,
                'PRODUCCION',
                'PRUEBA_MAIN_FINAL'
            )
        """)
        
        conn.commit()
        
        # Verificar distribución
        cursor.execute('SELECT COUNT(*) FROM InventarioRollosSMD')
        smd_despues = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM InventarioRollosIMD')
        imd_despues = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM InventarioRollosMAIN')
        main_despues = cursor.fetchone()[0]
        
        print(f"\n📊 Estado DESPUÉS:")
        print(f"   SMD: {smd_despues} rollos (+{smd_despues - smd_antes})")
        print(f"   IMD: {imd_despues} rollos (+{imd_despues - imd_antes})")
        print(f"   MAIN: {main_despues} rollos (+{main_despues - main_antes})")
        
        # Verificar resultados
        exito_smd = smd_despues > smd_antes
        exito_imd = imd_despues > imd_antes  
        exito_main = main_despues > main_antes
        
        print(f"\n🎯 RESULTADOS:")
        print(f"   SMD: {'✅ FUNCIONANDO' if exito_smd else '❌ NO FUNCIONANDO'}")
        print(f"   IMD: {'✅ FUNCIONANDO' if exito_imd else '❌ NO FUNCIONANDO'}")
        print(f"   MAIN: {'✅ FUNCIONANDO' if exito_main else '❌ NO FUNCIONANDO'}")
        
        if exito_smd and exito_imd and exito_main:
            print(f"\n🎉 ¡SISTEMA COMPLETAMENTE FUNCIONAL!")
            print(f"   ✅ Todos los tipos de material se distribuyen automáticamente")
            print(f"   ✅ Los errores de columnas están corregidos")
            print(f"   ✅ SMD ahora funciona correctamente")
        else:
            print(f"\n⚠️  Sistema parcialmente funcional")
            if not exito_smd:
                print(f"   ❌ SMD no está distribuyendo")
            if not exito_imd:
                print(f"   ❌ IMD no está distribuyendo")
            if not exito_main:
                print(f"   ❌ MAIN no está distribuyendo")
        
        cursor.close()
        conn.close()
        return exito_smd and exito_imd and exito_main
        
    except Exception as e:
        print(f"❌ Error en prueba: {e}")
        return False

def main():
    """Función principal"""
    print("🚀 APLICANDO TODAS LAS MEJORAS AL SISTEMA")
    print("=" * 60)
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("")
    
    # 1. Aplicar trigger mejorado
    print("1️⃣ Aplicando trigger mejorado en base de datos...")
    if not aplicar_trigger_mejorado():
        print("❌ Falló la aplicación del trigger")
        return
    
    # 2. Probar sistema completo
    print("\n2️⃣ Probando sistema completo...")
    if probar_distribucion_completa():
        print("\n" + "=" * 60)
        print("🎉 ¡TODAS LAS MEJORAS APLICADAS EXITOSAMENTE!")
        print("=" * 60)
        print("\n📋 EL SISTEMA AHORA:")
        print("✅ Distribuye automáticamente materiales SMD")
        print("✅ Distribuye automáticamente materiales IMD") 
        print("✅ Distribuye automáticamente materiales MAIN")
        print("✅ No tiene errores de columnas faltantes")
        print("✅ Funciona correctamente con la base de datos")
        print("\n🎯 RESPUESTA: SÍ, cuando des salida a un rollo")
        print("   se irá automáticamente a su tabla correspondiente")
    else:
        print("\n" + "=" * 60)
        print("⚠️  APLICACIÓN PARCIAL")
        print("=" * 60)
        print("📋 Revisa los errores mostrados arriba")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  Proceso cancelado por el usuario")
    except Exception as e:
        print(f"\n❌ Error general: {e}")
    finally:
        input("\nPresione Enter para salir...")
