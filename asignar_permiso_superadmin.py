#!/usr/bin/env python3
from app.db_mysql import execute_query

print('=== ASIGNANDO PERMISO IMD A ROL SUPERADMIN ===')
try:
    # Obtener ID del permiso IMD-SMD TERMINADO
    permiso = execute_query('''
        SELECT id FROM permisos_botones 
        WHERE boton = 'IMD-SMD TERMINADO' 
        LIMIT 1
    ''', fetch='one')
    
    if permiso:
        if isinstance(permiso, dict):
            permiso_id = permiso['id']
        else:
            permiso_id = permiso[0]
        print(f"ID del permiso IMD-SMD TERMINADO: {permiso_id}")
        
        # Obtener ID del rol superadmin
        rol = execute_query('''
            SELECT id FROM roles WHERE nombre = 'superadmin'
        ''', fetch='one')
        
        if rol:
            if isinstance(rol, dict):
                rol_id = rol['id']
            else:
                rol_id = rol[0]
            print(f"ID del rol superadmin: {rol_id}")
            
            # Asignar permiso al rol
            result = execute_query('''
                INSERT IGNORE INTO rol_permisos_botones (rol_id, permiso_boton_id)
                VALUES (%s, %s)
            ''', (rol_id, permiso_id))
            
            print(f"Resultado de asignación: {result}")
            print("✅ Permiso asignado al rol superadmin")
            
            # Verificar asignación
            verificacion = execute_query('''
                SELECT COUNT(*) as count
                FROM rol_permisos_botones rpb
                JOIN permisos_botones pb ON rpb.permiso_boton_id = pb.id
                JOIN roles r ON rpb.rol_id = r.id
                WHERE pb.boton = 'IMD-SMD TERMINADO' AND r.nombre = 'superadmin'
            ''', fetch='one')
            
            if verificacion:
                count = verificacion['count'] if isinstance(verificacion, dict) else verificacion[0]
                print(f"Verificación: {count} asignaciones encontradas")
        else:
            print("❌ No se encontró el rol superadmin")
    else:
        print("❌ No se encontró el permiso IMD-SMD TERMINADO")
        
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
