import os
from app.config_mysql import get_mysql_connection_string
import pymysql

print('=== Verificando y corrigiendo estructura de inventario_consolidado ===')

try:
    config = get_mysql_connection_string()
    conn = pymysql.connect(**config)
    cursor = conn.cursor()
    
    # Verificar estructura actual
    print('Estructura actual de inventario_consolidado:')
    cursor.execute("DESCRIBE inventario_consolidado")
    columns = cursor.fetchall()
    
    existing_columns = []
    for col in columns:
        existing_columns.append(col[0])
        print(f"  {col[0]} - {col[1]}")
    
    # Columnas que necesitamos
    required_columns = [
        ('cantidad_salidas', 'DECIMAL(15,2) DEFAULT 0'),
        ('fecha_ultima_salida', 'DATETIME NULL'),
    ]
    
    print('\n🔄 Agregando columnas faltantes...')
    
    # Agregar columnas si no existen
    for column_name, column_definition in required_columns:
        if column_name not in existing_columns:
            try:
                alter_sql = f"ALTER TABLE inventario_consolidado ADD COLUMN {column_name} {column_definition}"
                cursor.execute(alter_sql)
                print(f"✅ Columna {column_name} agregada")
            except Exception as e:
                print(f"❌ Error agregando columna {column_name}: {e}")
        else:
            print(f"ℹ️ Columna {column_name} ya existe")
    
    # Ahora poblar datos iniciales de salidas
    print('\n🔄 Poblando datos iniciales de salidas...')
    
    cursor.execute('''
        SELECT 
            SUBSTRING_INDEX(codigo_material_recibido, ',', 1) as numero_parte,
            SUM(cantidad_salida) as total_salidas,
            MAX(fecha_salida) as fecha_ultima_salida
        FROM control_material_salida
        GROUP BY SUBSTRING_INDEX(codigo_material_recibido, ',', 1)
    ''')
    
    salidas = cursor.fetchall()
    
    for salida in salidas:
        numero_parte = salida[0]
        total_salidas = float(salida[1]) if salida[1] else 0.0
        fecha_ultima_salida = salida[2]
        
        # Actualizar inventario consolidado con salidas
        cursor.execute('''
            UPDATE inventario_consolidado 
            SET 
                cantidad_salidas = %s,
                cantidad_actual = cantidad_entradas - %s,
                fecha_ultima_salida = %s,
                fecha_actualizacion = NOW()
            WHERE numero_parte = %s
        ''', (total_salidas, total_salidas, fecha_ultima_salida, numero_parte))
        
        print(f"  ✅ {numero_parte}: {total_salidas} salidas")
    
    # Verificar el resultado final
    print('\n=== Verificando inventario consolidado final ===')
    cursor.execute('''
        SELECT 
            numero_parte,
            cantidad_entradas,
            cantidad_salidas,
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
    
    print('\n✅ Estructura corregida y datos poblados exitosamente')
    
except Exception as e:
    print(f'❌ Error: {e}')
