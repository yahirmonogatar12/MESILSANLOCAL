#!/usr/bin/env python3
"""
Script para recalcular completamente la tabla inventario_consolidado
usando la columna numero_parte consistentemente
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
    print("🔧 RECÁLCULO COMPLETO DE INVENTARIO CONSOLIDADO")
    print("=" * 60)
    
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Paso 1: Limpiar tabla completamente
        print("🗑️ Limpiando tabla inventario_consolidado...")
        cursor.execute("DELETE FROM inventario_consolidado")
        print(f"✅ Eliminados {cursor.rowcount} registros anteriores")
        
        # Paso 2: Recalcular con JOIN correcto usando numero_parte
        print("\n🔄 Recalculando inventario usando numero_parte...")
        
        query = """
            INSERT INTO inventario_consolidado 
            (numero_parte, codigo_material, especificacion, propiedad_material, 
             total_entradas, total_salidas, cantidad_actual, total_lotes,
             fecha_primera_entrada, fecha_ultima_entrada, fecha_actualizacion)
            SELECT 
                entradas.numero_parte,
                entradas.codigo_material,
                entradas.especificacion,
                entradas.propiedad_material,
                entradas.total_entradas,
                COALESCE(salidas.total_salidas, 0) as total_salidas,
                entradas.total_entradas - COALESCE(salidas.total_salidas, 0) as cantidad_actual,
                entradas.total_lotes,
                entradas.fecha_primera_entrada,
                entradas.fecha_ultima_entrada,
                NOW() as fecha_actualizacion
            FROM (
                -- Subconsulta para las ENTRADAS desde control_material_almacen
                -- Agrupando SOLO por numero_parte para evitar duplicados
                SELECT 
                    cma.numero_parte,
                    MAX(cma.codigo_material_recibido) as codigo_material,
                    MAX(cma.especificacion) as especificacion,
                    MAX(cma.propiedad_material) as propiedad_material,
                    SUM(cma.cantidad_actual) as total_entradas,
                    COUNT(DISTINCT cma.numero_lote_material) as total_lotes,
                    MIN(cma.fecha_recibo) as fecha_primera_entrada,
                    MAX(cma.fecha_recibo) as fecha_ultima_entrada
                FROM control_material_almacen cma
                WHERE cma.numero_parte IS NOT NULL 
                AND cma.numero_parte != ''
                AND cma.numero_parte NOT LIKE '%,%'
                GROUP BY cma.numero_parte
            ) entradas
            LEFT JOIN (
                -- Subconsulta para las SALIDAS desde control_material_salida
                SELECT 
                    cms.numero_parte,
                    SUM(cms.cantidad_salida) as total_salidas
                FROM control_material_salida cms
                WHERE cms.numero_parte IS NOT NULL 
                AND cms.numero_parte != ''
                AND cms.numero_parte NOT LIKE '%,%'
                GROUP BY cms.numero_parte
            ) salidas ON entradas.numero_parte = salidas.numero_parte
        """
        
        cursor.execute(query)
        insertados = cursor.rowcount
        print(f"✅ Insertados {insertados} registros recalculados")
        
        # Confirmar cambios
        conn.commit()
        
        # Paso 3: Verificar resultado
        print("\n📊 VERIFICACIÓN:")
        cursor.execute("SELECT COUNT(*) FROM inventario_consolidado")
        total = cursor.fetchone()[0]
        print(f"  Total registros: {total}")
        
        # Verificar el número de parte específico EBC4702E901
        cursor.execute("""
            SELECT numero_parte, codigo_material, total_entradas, total_salidas, cantidad_actual
            FROM inventario_consolidado 
            WHERE numero_parte = 'EBC4702E901'
        """)
        verificacion = cursor.fetchone()
        if verificacion:
            print(f"\n✅ VERIFICACIÓN EBC4702E901:")
            print(f"  Numero Parte: {verificacion[0]}")
            print(f"  Codigo Material: {verificacion[1]}")
            print(f"  Total Entradas: {verificacion[2]}")
            print(f"  Total Salidas: {verificacion[3]}")
            print(f"  Cantidad Actual: {verificacion[4]}")
        else:
            print("❌ No se encontró el número de parte EBC4702E901")
        
        # Mostrar todos los registros para validación
        print(f"\n📋 TODOS LOS REGISTROS:")
        cursor.execute("""
            SELECT numero_parte, total_entradas, total_salidas, cantidad_actual 
            FROM inventario_consolidado 
            ORDER BY numero_parte
        """)
        todos = cursor.fetchall()
        for registro in todos:
            print(f"  {registro[0]}: Entradas={registro[1]}, Salidas={registro[2]}, Actual={registro[3]}")
        
        cursor.close()
        conn.close()
        
        print(f"\n✅ PROCESO COMPLETADO EXITOSAMENTE")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
