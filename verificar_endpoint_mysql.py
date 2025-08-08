import os
from app.config_mysql import get_mysql_connection_string
import pymysql
import json

print('=== Probando endpoint /api/inventario/consultar con MySQL ===')

try:
    config = get_mysql_connection_string()
    conn = pymysql.connect(**config)
    cursor = conn.cursor()
    
    # Simular la misma consulta que hace el endpoint
    query = '''
        SELECT 
            cma.numero_parte,
            cma.codigo_material,
            cma.especificacion,
            cma.propiedad_material,
            SUM(cma.cantidad_actual) as cantidad_total,
            COUNT(DISTINCT cma.numero_lote_material) as total_lotes,
            MAX(cma.fecha_recibo) as fecha_ultimo_recibo,
            MIN(cma.fecha_recibo) as fecha_primer_recibo
        FROM control_material_almacen cma
        WHERE 1=1
        GROUP BY cma.numero_parte, cma.codigo_material, cma.especificacion, cma.propiedad_material
        ORDER BY fecha_ultimo_recibo DESC
        LIMIT 3
    '''
    
    cursor.execute(query)
    rows = cursor.fetchall()
    
    print(f'Número de registros obtenidos: {len(rows)}')
    print('=== Datos de inventario ===')
    
    for i, row in enumerate(rows):
        numero_parte = row[0]
        cantidad_total = float(row[4]) if row[4] else 0.0
        
        print(f'Registro {i+1}:')
        print(f'  Número de parte: {numero_parte}')
        print(f'  Código material: {row[1]}')
        print(f'  Especificación: {row[2]}')
        print(f'  Cantidad total: {cantidad_total}')
        print(f'  Total lotes: {row[5]}')
        print(f'  Último recibo: {row[6]}')
        print(f'  Primer recibo: {row[7]}')
        
        # Verificar lotes disponibles para este número de parte
        lotes_query = '''
            SELECT numero_lote_material, cantidad_actual, fecha_recibo
            FROM control_material_almacen 
            WHERE numero_parte = %s AND cantidad_actual > 0
            ORDER BY fecha_recibo DESC
        '''
        cursor.execute(lotes_query, [numero_parte])
        lotes_rows = cursor.fetchall()
        
        print(f'  Lotes disponibles: {len(lotes_rows)}')
        for lote_row in lotes_rows[:3]:  # Mostrar solo los primeros 3
            print(f'    - Lote: {lote_row[0]}, Cantidad: {lote_row[1]}, Fecha: {lote_row[2]}')
        
        print('---')
    
    cursor.close()
    conn.close()
    print('✅ Verificación completa')
    
except Exception as e:
    print(f'❌ Error: {e}')
