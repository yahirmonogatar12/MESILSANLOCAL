from app.db_mysql import execute_query, obtener_modelos_bom

print('=== VERIFICANDO TABLA BOM ===')
try:
    # Verificar que la tabla existe
    tables = execute_query('SHOW TABLES LIKE "bom"', fetch='all')
    print(f'Tabla BOM existe: {len(tables) > 0}')
    
    if len(tables) == 0:
        print('❌ La tabla BOM no existe!')
        exit()
    
    # Verificar datos en tabla BOM
    count = execute_query('SELECT COUNT(*) as total FROM bom', fetch='one')
    print(f'Total registros BOM: {count["total"] if count else 0}')
    
    print(f'Total registros BOM: {count["total"] if count else 0}')
    
    if count and count["total"] > 0:
        print('\n--- MODELOS ÚNICOS EN BOM ---')
        modelos = execute_query('SELECT DISTINCT modelo FROM bom ORDER BY modelo', fetch='all')
        print(f'Modelos únicos: {len(modelos) if modelos else 0}')
        
        for i, modelo in enumerate(modelos or []):
            print(f'  {i+1}: {modelo["modelo"]}')
            
        print('\n--- PROBANDO FUNCIÓN obtener_modelos_bom ---')
        modelos_funcion = obtener_modelos_bom()
        print(f'Resultado función: {type(modelos_funcion)}')
        
        if isinstance(modelos_funcion, list) and modelos_funcion:
            print('Primeros 3 modelos:')
            for i, modelo in enumerate(modelos_funcion[:3]):
                print(f'  {i+1}: {modelo}')
    else:
        print('\n❌ NO HAY DATOS EN LA TABLA BOM')
        print('Para que aparezca el dropdown necesitas:')
        print('1. Ir a Control de BOM')
        print('2. Usar "Importar al excel" para cargar un archivo Excel con modelos')
        
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
