#!/usr/bin/env python3
from app.db_mysql import execute_query

print('=== INSERTANDO PERMISO IMD TERMINADO MANUALMENTE ===')
try:
    # Insertar el permiso manualmente
    result = execute_query('''
        INSERT IGNORE INTO permisos_botones (pagina, seccion, boton, descripcion, activo)
        VALUES ('LISTA_CONTROL_DE_PROCESO', 'Inventario', 'IMD-SMD TERMINADO', 'Acceso al inventario de productos IMD terminados', 1)
    ''')
    
    print(f"Resultado de inserción: {result}")
    
    # Verificar que se haya insertado
    permisos = execute_query('''
        SELECT id, pagina, seccion, boton, descripcion 
        FROM permisos_botones 
        WHERE boton = 'IMD-SMD TERMINADO'
    ''', fetch='all')
    
    if permisos:
        print(' Permiso IMD-SMD TERMINADO encontrado:')
        for permiso in permisos:
            print(f'  ID: {permiso["id"] if isinstance(permiso, dict) else permiso[0]}')
            print(f'  Página: {permiso["pagina"] if isinstance(permiso, dict) else permiso[1]}')
            print(f'  Sección: {permiso["seccion"] if isinstance(permiso, dict) else permiso[2]}')
            print(f'  Botón: {permiso["boton"] if isinstance(permiso, dict) else permiso[3]}')
            print(f'  Descripción: {permiso["descripcion"] if isinstance(permiso, dict) else permiso[4]}')
            
        # Asignar el permiso al rol superadmin
        print('\n=== ASIGNANDO PERMISO AL ROL SUPERADMIN ===')
        permiso_id = permiso["id"] if isinstance(permiso, dict) else permiso[0]
        
        # Obtener ID del rol superadmin
        rol_superadmin = execute_query('''
            SELECT id FROM roles WHERE nombre = 'superadmin'
        ''', fetch='one')
        
        if rol_superadmin:
            rol_id = rol_superadmin[0]
            print(f"ID del rol superadmin: {rol_id}")
            
            # Asignar permiso al rol
            result_asign = execute_query('''
                INSERT IGNORE INTO rol_permisos_botones (rol_id, permiso_boton_id)
                VALUES (%s, %s)
            ''', (rol_id, permiso_id))
            
            print(f"Resultado de asignación: {result_asign}")
            print(" Permiso asignado al rol superadmin")
        else:
            print("❌ No se encontró el rol superadmin")
    else:
        print('❌ NO se pudo insertar el permiso')
        
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
