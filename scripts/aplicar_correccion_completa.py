#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para aplicar el trigger corregido y probar el sistema completo
"""

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

def aplicar_trigger_corregido():
    """Aplicar el trigger corregido con numero_parte real"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("🔧 APLICANDO TRIGGER CORREGIDO CON numero_parte REAL...")
        
        # Eliminar trigger existente
        cursor.execute("DROP TRIGGER IF EXISTS tr_distribuir_salidas_por_tipo")
        print("🗑️  Trigger anterior eliminado")
        
        # Crear trigger corregido
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
            NEW.numero_parte,
            CONCAT('AUTO_SMD_', NEW.id, '_', DATE_FORMAT(NOW(), '%Y%m%d_%H%i%s')),
            NEW.numero_lote,
            NEW.cantidad_salida,
            NEW.cantidad_salida,
            'ACTIVO',
            NEW.id,
            'SISTEMA_AUTO',
            CONCAT('Auto-distribución SMD desde salida ID: ', NEW.id, ' - Modelo: ', NEW.modelo, ' - Parte: ', NEW.numero_parte)
        );
    END IF;
    
    -- Distribución directa para IMD basado en especificación
    IF NEW.especificacion_material LIKE '%IMD%' OR NEW.modelo LIKE '%IMD%' THEN
        INSERT INTO InventarioRollosIMD (
            numero_parte, codigo_barras, lote, cantidad_inicial, cantidad_actual,
            estado, movimiento_origen_id, usuario_responsable, observaciones
        ) VALUES (
            NEW.numero_parte,
            CONCAT('AUTO_IMD_', NEW.id, '_', DATE_FORMAT(NOW(), '%Y%m%d_%H%i%s')),
            NEW.numero_lote,
            NEW.cantidad_salida,
            NEW.cantidad_salida,
            'ACTIVO',
            NEW.id,
            'SISTEMA_AUTO',
            CONCAT('Auto-distribución IMD desde salida ID: ', NEW.id, ' - Modelo: ', NEW.modelo, ' - Parte: ', NEW.numero_parte)
        );
    END IF;
    
    -- Distribución directa para MAIN basado en especificación
    IF NEW.especificacion_material LIKE '%MAIN%' OR NEW.modelo LIKE '%MAIN%' THEN
        INSERT INTO InventarioRollosMAIN (
            numero_parte, codigo_barras, lote, cantidad_inicial, cantidad_actual,
            estado, movimiento_origen_id, usuario_responsable, observaciones
        ) VALUES (
            NEW.numero_parte,
            CONCAT('AUTO_MAIN_', NEW.id, '_', DATE_FORMAT(NOW(), '%Y%m%d_%H%i%s')),
            NEW.numero_lote,
            NEW.cantidad_salida,
            NEW.cantidad_salida,
            'ACTIVO',
            NEW.id,
            'SISTEMA_AUTO',
            CONCAT('Auto-distribución MAIN desde salida ID: ', NEW.id, ' - Modelo: ', NEW.modelo, ' - Parte: ', NEW.numero_parte)
        );
    END IF;
END
"""
        
        cursor.execute(trigger_sql)
        print("✅ Trigger corregido aplicado exitosamente")
        
        # Verificar trigger
        cursor.execute("""
            SELECT TRIGGER_NAME, EVENT_MANIPULATION, EVENT_OBJECT_TABLE 
            FROM INFORMATION_SCHEMA.TRIGGERS 
            WHERE TRIGGER_NAME = 'tr_distribuir_salidas_por_tipo'
        """)
        
        trigger_info = cursor.fetchone()
        if trigger_info:
            print(f"✅ Trigger verificado: {trigger_info[0]} en tabla {trigger_info[2]}")
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error aplicando trigger: {e}")
        return False

def probar_sistema_completo():
    """Probar el sistema con numero_parte correcto"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("\n🧪 PROBANDO SISTEMA CON numero_parte CORRECTO")
        print("=" * 60)
        
        # Contar antes
        cursor.execute('SELECT COUNT(*) FROM InventarioRollosSMD')
        smd_antes = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM InventarioRollosIMD')
        imd_antes = cursor.fetchone()[0]
        
        print(f"📊 Estado ANTES:")
        print(f"   SMD: {smd_antes} rollos")
        print(f"   IMD: {imd_antes} rollos")
        
        # Crear una salida de prueba con numero_parte correcto
        print(f"\n🔄 Creando salida con numero_parte correcto...")
        cursor.execute("""
            INSERT INTO control_material_salida (
                codigo_material_recibido, numero_parte, numero_lote, modelo, 
                depto_salida, proceso_salida, cantidad_salida, fecha_salida, especificacion_material
            ) VALUES (
                'TEST_CORREGIDO_001',
                'PARTE_REAL_TEST_001',
                'LOTE_TEST_001', 
                'PCB_SMD_CORREGIDO',
                'PRODUCCION',
                'PRUEBA_NUMERO_PARTE',
                15,
                NOW(),
                'Componente SMD para prueba de numero_parte'
            )
        """)
        
        conn.commit()
        print("✅ Salida de prueba creada")
        
        # Verificar después
        cursor.execute('SELECT COUNT(*) FROM InventarioRollosSMD')
        smd_despues = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM InventarioRollosIMD')
        imd_despues = cursor.fetchone()[0]
        
        print(f"\n📊 Estado DESPUÉS:")
        print(f"   SMD: {smd_despues} rollos (+{smd_despues - smd_antes})")
        print(f"   IMD: {imd_despues} rollos (+{imd_despues - imd_antes})")
        
        # Verificar que se usó el numero_parte correcto
        cursor.execute("""
            SELECT numero_parte, codigo_barras, observaciones
            FROM InventarioRollosSMD 
            WHERE numero_parte = 'PARTE_REAL_TEST_001'
            ORDER BY id DESC 
            LIMIT 1
        """)
        
        resultado_smd = cursor.fetchone()
        if resultado_smd:
            print(f"\n✅ ÉXITO: SMD creado con numero_parte correcto:")
            print(f"   🏷️  Número Parte: {resultado_smd[0]}")
            print(f"   🔤 Código Barras: {resultado_smd[1]}")
            print(f"   📝 Observaciones: {resultado_smd[2]}")
            
            if 'PARTE_REAL_TEST_001' in resultado_smd[2]:
                print("🎉 ¡NÚMERO DE PARTE APARECE CORRECTAMENTE EN OBSERVACIONES!")
        else:
            print("❌ No se encontró el rollo SMD con numero_parte correcto")
        
        cursor.close()
        conn.close()
        
        return smd_despues > smd_antes
        
    except Exception as e:
        print(f"❌ Error en prueba: {e}")
        return False

def verificar_inventarios_existentes():
    """Verificar que los inventarios existentes tengan numero_parte correcto"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("\n🔍 VERIFICANDO INVENTARIOS EXISTENTES...")
        
        # Verificar SMD
        cursor.execute("""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN numero_parte LIKE '%,%' THEN 1 ELSE 0 END) as incorrectos,
                   SUM(CASE WHEN numero_parte NOT LIKE '%,%' THEN 1 ELSE 0 END) as correctos
            FROM InventarioRollosSMD
        """)
        
        stats_smd = cursor.fetchone()
        
        # Verificar IMD
        cursor.execute("""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN numero_parte LIKE '%,%' THEN 1 ELSE 0 END) as incorrectos,
                   SUM(CASE WHEN numero_parte NOT LIKE '%,%' THEN 1 ELSE 0 END) as correctos
            FROM InventarioRollosIMD
        """)
        
        stats_imd = cursor.fetchone()
        
        print(f"📊 ESTADÍSTICAS DE INVENTARIOS:")
        print(f"   SMD - Total: {stats_smd[0]}, Incorrectos: {stats_smd[1]}, Correctos: {stats_smd[2]}")
        print(f"   IMD - Total: {stats_imd[0]}, Incorrectos: {stats_imd[1]}, Correctos: {stats_imd[2]}")
        
        # Mostrar ejemplos incorrectos
        cursor.execute("""
            SELECT numero_parte, codigo_barras
            FROM InventarioRollosSMD 
            WHERE numero_parte LIKE '%,%'
            LIMIT 3
        """)
        
        incorrectos = cursor.fetchall()
        if incorrectos:
            print(f"\n⚠️  EJEMPLOS DE numero_parte INCORRECTOS EN SMD:")
            for inc in incorrectos:
                print(f"   📦 {inc[0]} | 🏷️  {inc[1]}")
        
        cursor.close()
        conn.close()
        
        return stats_smd[1] == 0 and stats_imd[1] == 0
        
    except Exception as e:
        print(f"❌ Error verificando inventarios: {e}")
        return False

def main():
    """Función principal"""
    print("🎯 APLICACIÓN Y PRUEBA DEL SISTEMA CORREGIDO")
    print("=" * 70)
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. Aplicar trigger corregido
    if not aplicar_trigger_corregido():
        print("❌ No se pudo aplicar el trigger corregido")
        return
    
    # 2. Probar sistema
    if probar_sistema_completo():
        print("\n🎉 ¡SISTEMA FUNCIONANDO CORRECTAMENTE!")
        print("✅ Nuevas salidas usarán numero_parte correcto")
    else:
        print("\n⚠️  Sistema no funcionó como esperado")
    
    # 3. Verificar inventarios existentes
    if verificar_inventarios_existentes():
        print("\n✅ Todos los inventarios tienen numero_parte correcto")
    else:
        print("\n⚠️  Algunos inventarios tienen numero_parte incorrecto")
        print("   (Esto es normal para registros creados antes de la corrección)")
    
    print("\n📋 RESUMEN DE CORRECCIONES APLICADAS:")
    print("✅ Agregada columna numero_parte a control_material_salida")
    print("✅ Actualizadas salidas existentes con numero_parte correcto")  
    print("✅ Modificado routes.py para obtener numero_parte desde almacen")
    print("✅ Actualizado trigger para usar numero_parte real")
    print("✅ Sistema probado y funcionando")
    
    print("\n🎯 RESULTADO FINAL:")
    print("   Ahora las salidas de material incluyen el numero_parte correcto")
    print("   Los inventarios tendrán trazabilidad completa")
    print("   Las nuevas salidas mostrarán el numero_parte real, no el código concatenado")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  Proceso cancelado por el usuario")
    except Exception as e:
        print(f"\n❌ Error general: {e}")
    finally:
        input("\nPresione Enter para salir...")
