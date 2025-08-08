#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import os

def verificar_cantidad_total_simple():
    # Buscar la base de datos en el directorio actual
    db_files = ['app/database/ISEMM_MES.db', 'app/database/ISEMM_MES2.db', 'database.db', 'control_material.db']
    db_path = None
    
    for db_file in db_files:
        if os.path.exists(db_file):
            db_path = db_file
            break
    
    if not db_path:
        print("❌ No se encontró ninguna base de datos SQLite")
        return
    
    print(f"✅ Usando base de datos: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar que existe la tabla
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='control_material_almacen'")
        if not cursor.fetchone():
            print("❌ La tabla control_material_almacen no existe")
            return
        
        print('=== Verificar cálculo de cantidad total ===')
        
        # Verificar el cálculo real
        cursor.execute('''
            SELECT 
                numero_parte,
                codigo_material,
                SUM(cantidad_actual) as cantidad_total_calculada,
                COUNT(DISTINCT numero_lote_material) as total_lotes,
                COUNT(*) as registros_totales
            FROM control_material_almacen 
            WHERE cantidad_actual > 0
            GROUP BY numero_parte, codigo_material
            LIMIT 10
        ''')

        results = cursor.fetchall()
        print(f'Número de resultados: {len(results)}')
        
        if not results:
            print("❌ No hay datos en la tabla control_material_almacen")
            # Verificar si hay datos en general
            cursor.execute('SELECT COUNT(*) FROM control_material_almacen')
            total_records = cursor.fetchone()[0]
            print(f"Total de registros en la tabla: {total_records}")
            return
        
        for i, row in enumerate(results):
            numero_parte = row[0]
            codigo_material = row[1] 
            cantidad_total = row[2]
            total_lotes = row[3]
            registros_totales = row[4]
                
            print(f'{i+1}. Parte: {numero_parte}')
            print(f'   Código: {codigo_material}')
            print(f'   Cantidad Total: {cantidad_total}')
            print(f'   Total Lotes: {total_lotes}')
            print(f'   Registros: {registros_totales}')
            print()

        # Verificar registros individuales para la primera parte
        if results:
            primera_parte = results[0][0]
            print(f'=== Verificar registros individuales para {primera_parte} ===')
            
            cursor.execute('''
                SELECT numero_lote_material, cantidad_actual, fecha_recibo
                FROM control_material_almacen 
                WHERE numero_parte = ? AND cantidad_actual > 0
                ORDER BY fecha_recibo DESC
            ''', [primera_parte])
            
            lotes = cursor.fetchall()
            print(f'Lotes disponibles para {primera_parte}:')
            total_manual = 0
            for lote in lotes:
                numero_lote = lote[0]
                cantidad = lote[1]
                fecha = lote[2]
                    
                total_manual += cantidad
                print(f'  - Lote: {numero_lote}')
                print(f'    Cantidad: {cantidad}')
                print(f'    Fecha: {fecha}')
            print(f'Total manual calculado: {total_manual}')
            
            # Comparar con el total de la consulta agrupada
            total_agrupado = results[0][2]
            print(f'Total agrupado: {total_agrupado}')
            if total_manual == total_agrupado:
                print('✅ Los cálculos coinciden')
            else:
                print('❌ Los cálculos NO coinciden')

        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    verificar_cantidad_total_simple()
