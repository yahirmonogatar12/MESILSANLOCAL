import os
from app.config_mysql import get_mysql_connection_string
import pymysql

print('=== Verificando tabla de salidas ===')

try:
    config = get_mysql_connection_string()
    conn = pymysql.connect(**config)
    cursor = conn.cursor()
    
    # Buscar tablas relacionadas con salidas
    print('Tablas disponibles:')
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()
    
    salida_tables = []
    for table in tables:
        table_name = table[0]
        if 'salida' in table_name.lower() or 'material' in table_name.lower():
            salida_tables.append(table_name)
            print(f"  - {table_name}")
    
    # Verificar estructura de las tablas de salida
    for table_name in salida_tables:
        if 'salida' in table_name.lower():
            print(f'\n=== Estructura de {table_name} ===')
            cursor.execute(f"DESCRIBE {table_name}")
            columns = cursor.fetchall()
            
            for col in columns:
                print(f"  {col[0]} - {col[1]} ({col[2]})")
            
            # Mostrar algunos datos de ejemplo
            print(f'\n=== Datos de ejemplo en {table_name} ===')
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
            rows = cursor.fetchall()
            
            for i, row in enumerate(rows):
                print(f"  Registro {i+1}: {row}")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f'❌ Error: {e}')
