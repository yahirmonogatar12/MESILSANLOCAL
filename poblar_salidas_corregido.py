import os
from app.config_mysql import get_mysql_connection_string
import pymysql

print('=== Poblando datos de salidas con nombres correctos ===')

try:
    config = get_mysql_connection_string()
    conn = pymysql.connect(**config)
    cursor = conn.cursor()
    
    # Poblar datos iniciales de salidas usando los nombres correctos
    print(' Poblando datos iniciales de salidas...')
    
    cursor.execute('''
        SELECT 
            SUBSTRING_INDEX(codigo_material_recibido, ',', 1) as numero_parte,
            SUM(cantidad_salida) as total_salidas,
            MAX(fecha_salida) as fecha_ultima_salida_nueva
        FROM control_material_salida
        GROUP BY SUBSTRING_INDEX(codigo_material_recibido, ',', 1)
    ''')
    
    salidas = cursor.fetchall()
    
    for salida in salidas:
        numero_parte = salida[0]
        total_salidas = float(salida[1]) if salida[1] else 0.0
        fecha_ultima_salida_nueva = salida[2]
        
        # Actualizar inventario consolidado con salidas usando nombres correctos
        cursor.execute('''
            UPDATE inventario_consolidado 
            SET 
                cantidad_salidas = %s,
                total_salidas = %s,
                cantidad_actual = total_entradas - %s,
                fecha_ultima_salida = %s,
                fecha_actualizacion = NOW()
            WHERE numero_parte = %s
        ''', (total_salidas, total_salidas, total_salidas, fecha_ultima_salida_nueva, numero_parte))
        
        print(f"   {numero_parte}: {total_salidas} salidas")
    
    # Verificar el resultado final
    print('\n=== Verificando inventario consolidado final ===')
    cursor.execute('''
        SELECT 
            numero_parte,
            total_entradas,
            total_salidas,
            cantidad_actual,
            total_lotes
        FROM inventario_consolidado
        LIMIT 5
    ''')
    
    resultados = cursor.fetchall()
    for row in resultados:
        print(f"  {row[0]}: Entradas={row[1]}, Salidas={row[2]}, Actual={row[3]}, Lotes={row[4]}")
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print('\n Datos de salidas poblados exitosamente')
    
except Exception as e:
    print(f'❌ Error: {e}')
