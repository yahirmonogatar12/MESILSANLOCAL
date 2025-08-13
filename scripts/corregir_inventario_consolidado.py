#!/usr/bin/env python3
"""
Script para corregir la tabla inventario_consolidado
- Elimina registros con números de parte concatenados
- Recalcula el inventario consolidado con números de parte reales
"""

import mysql.connector
import sys
from datetime import datetime

# Configuración de la base de datos
DB_CONFIG = {
    'host': 'up-de-fra1-mysql-1.db.run-on-seenode.com',
    'port': 11550,
    'user': 'db_rrpq0erbdujn',
    'password': '5fUNbSRcPP3LN9K2I33Pr0ge',
    'database': 'db_rrpq0erbdujn',
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_0900_ai_ci'
}

def main():
    print("🔧 CORRECCIÓN DE INVENTARIO CONSOLIDADO")
    print("=" * 60)
    
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Paso 1: Verificar estado actual
        print("📊 ESTADO ACTUAL:")
        cursor.execute("SELECT COUNT(*) FROM inventario_consolidado")
        total_registros = cursor.fetchone()[0]
        print(f"  Total registros: {total_registros}")
        
        # Identificar registros con números de parte concatenados
        cursor.execute("""
            SELECT COUNT(*) FROM inventario_consolidado 
            WHERE numero_parte LIKE '%,%'
        """)
        registros_concatenados = cursor.fetchone()[0]
        print(f"  Registros con números concatenados: {registros_concatenados}")
        
        if registros_concatenados == 0:
            print("✅ No hay registros con números de parte concatenados")
            return
        
        # Mostrar algunos ejemplos problemáticos
        cursor.execute("""
            SELECT numero_parte, codigo_material, cantidad_actual 
            FROM inventario_consolidado 
            WHERE numero_parte LIKE '%,%' 
            LIMIT 5
        """)
        ejemplos = cursor.fetchall()
        print("\n📝 EJEMPLOS PROBLEMÁTICOS:")
        for i, ejemplo in enumerate(ejemplos, 1):
            print(f"  {i}. NP: {ejemplo[0]} | CM: {ejemplo[1]} | Cantidad: {ejemplo[2]}")
        
        # Paso 2: Confirmar eliminación
        print("\n⚠️  ACCIÓN REQUERIDA:")
        print("Se eliminarán los registros con números de parte concatenados")
        print("Estos registros se pueden recalcular desde las tablas de origen")
        
        respuesta = input("\n¿Continuar con la limpieza? (s/N): ").strip().lower()
        if respuesta != 's':
            print("❌ Operación cancelada")
            return
        
        # Paso 3: Eliminar registros problemáticos
        print("\n🗑️  ELIMINANDO REGISTROS PROBLEMÁTICOS:")
        cursor.execute("""
            DELETE FROM inventario_consolidado 
            WHERE numero_parte LIKE '%,%'
        """)
        eliminados = cursor.rowcount
        print(f"✅ Eliminados {eliminados} registros con números concatenados")
        
        # Paso 4: Recalcular desde tabla control_material_almacen
        print("\n🔄 RECALCULANDO DESDE ALMACÉN:")
        cursor.execute("""
            INSERT INTO inventario_consolidado 
            (numero_parte, codigo_material, especificacion, propiedad_material, 
             total_entradas, total_salidas, cantidad_actual, total_lotes,
             fecha_primera_entrada, fecha_ultima_entrada, fecha_actualizacion)
            SELECT 
                cma.numero_parte,
                cma.codigo_material_recibido as codigo_material,
                cma.especificacion,
                cma.propiedad_material,
                SUM(cma.cantidad_actual) as total_entradas,
                COALESCE(salidas.total_salidas, 0) as total_salidas,
                SUM(cma.cantidad_actual) - COALESCE(salidas.total_salidas, 0) as cantidad_actual,
                COUNT(DISTINCT cma.numero_lote_material) as total_lotes,
                MIN(cma.fecha_recibo) as fecha_primera_entrada,
                MAX(cma.fecha_recibo) as fecha_ultima_entrada,
                NOW() as fecha_actualizacion
            FROM control_material_almacen cma
            LEFT JOIN (
                SELECT 
                    numero_parte,
                    SUM(cantidad_salida) as total_salidas
                FROM control_material_salida 
                WHERE numero_parte IS NOT NULL
                GROUP BY numero_parte
            ) salidas ON cma.numero_parte = salidas.numero_parte
            WHERE cma.numero_parte IS NOT NULL 
            AND cma.numero_parte NOT LIKE '%,%'
            GROUP BY cma.numero_parte, cma.codigo_material_recibido, 
                     cma.especificacion, cma.propiedad_material, salidas.total_salidas
            ON DUPLICATE KEY UPDATE
                total_entradas = VALUES(total_entradas),
                total_salidas = VALUES(total_salidas),
                cantidad_actual = VALUES(cantidad_actual),
                total_lotes = VALUES(total_lotes),
                fecha_primera_entrada = VALUES(fecha_primera_entrada),
                fecha_ultima_entrada = VALUES(fecha_ultima_entrada),
                fecha_actualizacion = NOW()
        """)
        recalculados = cursor.rowcount
        print(f"✅ Recalculados {recalculados} registros desde almacén")
        
        # Confirmar cambios
        conn.commit()
        
        # Paso 5: Verificar resultado final
        print("\n📊 ESTADO FINAL:")
        cursor.execute("SELECT COUNT(*) FROM inventario_consolidado")
        total_final = cursor.fetchone()[0]
        print(f"  Total registros: {total_final}")
        
        cursor.execute("""
            SELECT COUNT(*) FROM inventario_consolidado 
            WHERE numero_parte LIKE '%,%'
        """)
        concatenados_final = cursor.fetchone()[0]
        print(f"  Registros con números concatenados: {concatenados_final}")
        
        # Verificar que el número de parte específico esté correcto
        cursor.execute("""
            SELECT numero_parte, codigo_material, cantidad_actual 
            FROM inventario_consolidado 
            WHERE numero_parte = '0RH5602C622'
        """)
        verificacion = cursor.fetchone()
        if verificacion:
            print(f"\n✅ VERIFICACIÓN 0RH5602C622:")
            print(f"  Numero Parte: {verificacion[0]}")
            print(f"  Codigo Material: {verificacion[1]}")
            print(f"  Cantidad: {verificacion[2]}")
        
        print("\n🎉 CORRECCIÓN COMPLETADA EXITOSAMENTE")
        
    except mysql.connector.Error as e:
        print(f"❌ Error de MySQL: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        sys.exit(1)
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()
