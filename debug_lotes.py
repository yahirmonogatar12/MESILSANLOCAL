#!/usr/bin/env python3
import os
import pymysql
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

try:
    conn = pymysql.connect(
        host=os.getenv('MYSQL_HOST', 'localhost'),
        port=int(os.getenv('MYSQL_PORT', '3306')),
        user=os.getenv('MYSQL_USERNAME', ''),
        password=os.getenv('MYSQL_PASSWORD', ''),
        database=os.getenv('MYSQL_DATABASE', ''),
        charset='utf8mb4',
        autocommit=True,
        cursorclass=pymysql.cursors.DictCursor
    )
    cursor = conn.cursor()
    
    numero_parte = 'EBC4702E901'
    
    print('🔍 Verificando datos en control_material_almacen:')
    cursor.execute('SELECT * FROM control_material_almacen WHERE numero_parte = %s', [numero_parte])
    rows = cursor.fetchall()
    print(f'Registros encontrados: {len(rows)}')
    for row in rows:
        print(f'Código: {row["codigo_material_recibido"]}, Lote: {row["numero_lote_material"]}, Cantidad: {row["cantidad_actual"]}')
    
    print()
    print('🔍 Verificando salidas:')
    cursor.execute('SELECT codigo_material_recibido, SUM(cantidad_salida) as total FROM control_material_salida WHERE numero_parte = %s GROUP BY codigo_material_recibido', [numero_parte])
    salidas = cursor.fetchall()
    print(f'Salidas encontradas: {len(salidas)}')
    for salida in salidas:
        print(f'Código: {salida["codigo_material_recibido"]}, Total salidas: {salida["total"]}')
    
    print()
    print('🔍 Ejecutando consulta CORREGIDA de lotes_detalle:')
    query = '''
        SELECT 
            codigo_material_recibido,
            numero_lote_material,
            total_entrada,
            total_salidas,
            (total_entrada - total_salidas) as cantidad_disponible
        FROM (
            SELECT 
                cma.codigo_material_recibido,
                cma.numero_lote_material,
                SUM(cma.cantidad_actual) as total_entrada,
                COALESCE((
                    SELECT SUM(cms.cantidad_salida) 
                    FROM control_material_salida cms 
                    WHERE cms.codigo_material_recibido = cma.codigo_material_recibido
                ), 0) as total_salidas
            FROM control_material_almacen cma
            WHERE cma.numero_parte = %s 
            GROUP BY cma.codigo_material_recibido, cma.numero_lote_material
        ) lotes_calc
        WHERE (total_entrada - total_salidas) > 0
        ORDER BY codigo_material_recibido
    '''
    cursor.execute(query, [numero_parte])
    lotes = cursor.fetchall()
    print(f'Lotes con cantidad disponible > 0 (CORREGIDA): {len(lotes)}')
    for lote in lotes:
        print(f'Código: {lote["codigo_material_recibido"]}, Total entrada: {lote["total_entrada"]}, Salidas: {lote["total_salidas"]}, Disponible: {lote["cantidad_disponible"]}')
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
