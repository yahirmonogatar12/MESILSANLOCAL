#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para verificar el usuario admin en MySQL
"""

import pymysql
import hashlib

def verificar_admin():
    """Verificar si el usuario admin existe y está configurado correctamente"""
    try:
        connection = pymysql.connect(
            host='100.111.108.116',
            port=3306,
            user='ILSANMES',
            password='ISEMM2025',
            database='isemm2025',
            charset='utf8mb4'
        )
        
        cursor = connection.cursor(pymysql.cursors.DictCursor)
        
        # Buscar usuario admin
        cursor.execute("SELECT * FROM usuarios_sistema WHERE username = %s", ('admin',))
        admin_user = cursor.fetchone()
        
        if admin_user:
            print("✅ Usuario admin encontrado:")
            print(f"   ID: {admin_user['id']}")
            print(f"   Username: {admin_user['username']}")
            print(f"   Activo: {admin_user['activo']}")
            print(f"   Nombre: {admin_user.get('nombre_completo', 'N/A')}")
            print(f"   Departamento: {admin_user.get('departamento', 'N/A')}")
            
            # Verificar hash de contraseña
            expected_hash = hashlib.sha256('admin123'.encode()).hexdigest()
            actual_hash = admin_user['password_hash']
            
            print(f"\n🔐 Verificación de contraseña:")
            print(f"   Hash esperado (admin123): {expected_hash[:20]}...")
            print(f"   Hash actual: {actual_hash[:20]}...")
            print(f"   Coincide: {'✅ SÍ' if expected_hash == actual_hash else '❌ NO'}")
            
            if expected_hash != actual_hash:
                print("\n🔧 Actualizando contraseña del admin...")
                cursor.execute(
                    "UPDATE usuarios_sistema SET password_hash = %s WHERE username = %s",
                    (expected_hash, 'admin')
                )
                connection.commit()
                print("✅ Contraseña actualizada")
        else:
            print("❌ Usuario admin NO encontrado")
            print("\n🔧 Creando usuario admin...")
            
            # Crear usuario admin
            admin_hash = hashlib.sha256('admin123'.encode()).hexdigest()
            cursor.execute("""
                INSERT INTO usuarios_sistema 
                (username, password_hash, nombre_completo, departamento, cargo, activo)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, ('admin', admin_hash, 'Administrador', 'Sistemas', 'Administrador', True))
            
            connection.commit()
            admin_id = cursor.lastrowid
            print(f"✅ Usuario admin creado con ID: {admin_id}")
            
            # Asignar rol de admin
            cursor.execute(
                "INSERT IGNORE INTO usuario_roles (usuario_id, rol_id) VALUES (%s, %s)",
                (admin_id, 1)  # Rol admin
            )
            connection.commit()
            print("✅ Rol admin asignado")
        
        # Verificar roles
        cursor.execute("""
            SELECT ur.*, r.nombre as rol_nombre 
            FROM usuario_roles ur 
            JOIN roles r ON ur.rol_id = r.id 
            WHERE ur.usuario_id = (SELECT id FROM usuarios_sistema WHERE username = 'admin')
        """)
        roles = cursor.fetchall()
        
        print(f"\n👤 Roles asignados al admin:")
        if roles:
            for rol in roles:
                print(f"   - {rol['rol_nombre']} (ID: {rol['rol_id']})")
        else:
            print("   ❌ Sin roles asignados")
        
        cursor.close()
        connection.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Error verificando admin: {e}")
        return False

if __name__ == "__main__":
    print("🔍 Verificando usuario admin...")
    if verificar_admin():
        print("\n🎉 Verificación completada")
    else:
        print("\n❌ Error en la verificación")