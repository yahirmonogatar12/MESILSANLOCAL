import sqlite3

def cambiar_rol_temporal():
    conn = sqlite3.connect('app/database/ISEMM_MES.db')
    cursor = conn.cursor()
    
    # Obtener ID del rol superadmin
    cursor.execute('SELECT id FROM roles WHERE nombre = "superadmin"')
    superadmin_rol_id = cursor.fetchone()[0]
    
    # Obtener usuario test_user
    cursor.execute('SELECT id FROM usuarios_sistema WHERE username = "test_user"')
    user_result = cursor.fetchone()
    
    if user_result:
        user_id = user_result[0]
        
        print(f"Cambiando test_user (ID: {user_id}) a superadmin (rol ID: {superadmin_rol_id})")
        
        # Actualizar el rol del usuario
        cursor.execute('UPDATE usuario_roles SET rol_id = ? WHERE usuario_id = ?', 
                      (superadmin_rol_id, user_id))
        
        conn.commit()
        
        # Verificar el cambio
        cursor.execute('''
            SELECT u.username, r.nombre as rol
            FROM usuarios_sistema u 
            JOIN usuario_roles ur ON u.id = ur.usuario_id 
            JOIN roles r ON ur.rol_id = r.id 
            WHERE u.username = "test_user"
        ''')
        
        result = cursor.fetchone()
        if result:
            print(f"✅ Usuario actualizado: {result[0]} - {result[1]}")
        else:
            print("❌ No se pudo verificar el cambio")
    else:
        print("❌ Usuario test_user no encontrado")
    
    conn.close()

def restaurar_rol_original():
    conn = sqlite3.connect('app/database/ISEMM_MES.db')
    cursor = conn.cursor()
    
    # Obtener ID del rol operador_almacen
    cursor.execute('SELECT id FROM roles WHERE nombre = "operador_almacen"')
    operador_rol_id = cursor.fetchone()[0]
    
    # Obtener usuario test_user
    cursor.execute('SELECT id FROM usuarios_sistema WHERE username = "test_user"')
    user_result = cursor.fetchone()
    
    if user_result:
        user_id = user_result[0]
        
        print(f"Restaurando test_user (ID: {user_id}) a operador_almacen (rol ID: {operador_rol_id})")
        
        # Actualizar el rol del usuario
        cursor.execute('UPDATE usuario_roles SET rol_id = ? WHERE usuario_id = ?', 
                      (operador_rol_id, user_id))
        
        conn.commit()
        print("✅ Rol restaurado")
    
    conn.close()

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "restaurar":
        restaurar_rol_original()
    else:
        cambiar_rol_temporal()
