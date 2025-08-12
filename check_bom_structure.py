from app.config_mysql import execute_query

print('=== ESTRUCTURA DE TABLA BOM ===')
try:
    estructura = execute_query('DESCRIBE bom', fetch='all')
    print('Columnas en la tabla bom:')
    for col in estructura:
        print(f'  - {col["Field"]} ({col["Type"]})')
except Exception as e:
    print(f'Error: {e}')
