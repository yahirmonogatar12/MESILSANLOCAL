import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

def main():
    print('=== Probando nueva consulta corregida con entradas y salidas ===')
    
    config = {
        'host': os.getenv('MYSQL_HOST'),
        'port': int(os.getenv('MYSQL_PORT', '3306')),
        'user': os.getenv('MYSQL_USERNAME'),
        'passwd': os.getenv('MYSQL_PASSWORD'),
        'db': os.getenv('MYSQL_DATABASE'),
        'charset': 'utf8mb4',
        'autocommit': True
    }
    
    try:
        conn = pymysql.connect(**config)
        cursor = conn.cursor()
        
        # Nueva consulta que calcula basándose en entradas y salidas
        query = '''
            SELECT 
                entradas.numero_parte,
                entradas.codigo_material,
                entradas.especificacion,
                entradas.propiedad_material,
                COALESCE(entradas.total_entradas, 0) - COALESCE(salidas.total_salidas, 0) as cantidad_total,
                entradas.total_lotes,
                entradas.fecha_ultimo_recibo,
                entradas.fecha_primer_recibo,
                COALESCE(entradas.total_entradas, 0) as total_entradas,
                COALESCE(salidas.total_salidas, 0) as total_salidas
            FROM (
                SELECT 
                    cma.numero_parte,
                    cma.codigo_material,
                    cma.especificacion,
                    cma.propiedad_material,
                    SUM(cma.cantidad_recibida) as total_entradas,
                    COUNT(DISTINCT cma.numero_lote_material) as total_lotes,
                    MAX(cma.fecha_recibo) as fecha_ultimo_recibo,
                    MIN(cma.fecha_recibo) as fecha_primer_recibo
                FROM control_material_almacen cma
                WHERE 1=1
                GROUP BY cma.numero_parte, cma.codigo_material, cma.especificacion, cma.propiedad_material
            ) entradas
            LEFT JOIN (
                SELECT 
                    cms.numero_parte,
                    SUM(cms.cantidad_salida) as total_salidas
                FROM control_material_salida cms
                GROUP BY cms.numero_parte
            ) salidas ON entradas.numero_parte = salidas.numero_parte
            WHERE 1=1
            ORDER BY entradas.fecha_ultimo_recibo DESC
            LIMIT 3
        '''
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        print(f'Número de registros obtenidos: {len(rows)}')
        print('=== Datos corregidos ===')
        
        for i, row in enumerate(rows):
            numero_parte = row[0]
            cantidad_total = float(row[4]) if row[4] else 0.0
            total_entradas = float(row[8]) if row[8] else 0.0
            total_salidas = float(row[9]) if row[9] else 0.0
            
            print(f'Registro {i+1}:')
            print(f'  Número de parte: {numero_parte}')
            print(f'  Total entradas: {total_entradas:,}')
            print(f'  Total salidas: {total_salidas:,}')
            print(f'  Cantidad total (E-S): {cantidad_total:,}')
            print(f'  Cálculo verificado: {total_entradas - total_salidas:,}')
            print('---')
        
        cursor.close()
        conn.close()
        print('✅ Consulta nueva funcionando correctamente')
        
    except Exception as e:
        print(f'❌ Error: {e}')

if __name__ == "__main__":
    main()
