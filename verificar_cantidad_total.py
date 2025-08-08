#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from app.db import get_db_connection, is_mysql_connection

def verificar_cantidad_total():
    conn = get_db_connection()
    cursor = conn.cursor()

    print('=== Verificar cálculo de cantidad total ===')
    print('Consultando datos de control_material_almacen agrupados por numero_parte...')

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
        LIMIT 5
    ''')

    results = cursor.fetchall()
    print(f'Número de resultados: {len(results)}')
    
    for i, row in enumerate(results):
        if hasattr(row, 'keys'):
            numero_parte = row.get('numero_parte', 'N/A')
            codigo_material = row.get('codigo_material', 'N/A')
            cantidad_total = row.get('cantidad_total_calculada', 0)
            total_lotes = row.get('total_lotes', 0)
            registros_totales = row.get('registros_totales', 0)
        else:
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

    print('=== Verificar registros individuales para la primera parte ===')
    if results:
        primera_parte = results[0][0] if isinstance(results[0], tuple) else results[0].get('numero_parte')
        if primera_parte:
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
                if hasattr(lote, 'keys'):
                    numero_lote = lote.get('numero_lote_material', 'N/A')
                    cantidad = lote.get('cantidad_actual', 0)
                    fecha = lote.get('fecha_recibo', 'N/A')
                else:
                    numero_lote = lote[0]
                    cantidad = lote[1]
                    fecha = lote[2]
                    
                total_manual += cantidad
                print(f'  - Lote: {numero_lote}')
                print(f'    Cantidad: {cantidad}')
                print(f'    Fecha: {fecha}')
            print(f'Total manual calculado: {total_manual}')

    conn.close()

if __name__ == '__main__':
    verificar_cantidad_total()
