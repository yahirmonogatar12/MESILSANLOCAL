import os
from app.config_mysql import get_mysql_connection_string
import pymysql
import json

print('=== Probando endpoint optimizado ===')

try:
    config = get_mysql_connection_string()
    conn = pymysql.connect(**config)
    cursor = conn.cursor()
    
    # Probar la consulta del endpoint optimizado
    query = '''
        SELECT 
            ic.numero_parte,
            ic.codigo_material,
            ic.especificacion,
            ic.propiedad_material,
            ic.cantidad_actual as cantidad_total,
            ic.total_lotes,
            ic.fecha_ultima_entrada as fecha_ultimo_recibo,
            ic.fecha_primera_entrada as fecha_primer_recibo,
            ic.total_entradas,
            ic.total_salidas
        FROM inventario_consolidado ic
        WHERE 1=1
        ORDER BY ic.fecha_ultima_entrada DESC
        LIMIT 5
    '''
    
    cursor.execute(query)
    rows = cursor.fetchall()
    
    print(f'=== Resultados del endpoint optimizado ===')
    for i, row in enumerate(rows):
        print(f'Registro {i+1}:')
        print(f'  Parte: {row[0]}')
        print(f'  Cantidad Total: {row[4]} (Entradas: {row[8]}, Salidas: {row[9]})')
        print(f'  Lotes: {row[5]}')
        print(f'  Último recibo: {row[6]}')
        print('---')
    
    cursor.close()
    conn.close()
    
    print(' Endpoint optimizado funcionando correctamente')
    
except Exception as e:
    print(f'❌ Error: {e}')
