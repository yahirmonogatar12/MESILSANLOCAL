#!/usr/bin/env python3
"""
Script para crear un usuario de prueba con permisos limitados
"""

import sqlite3
import os
import hashlib

def crear_usuario_prueba():
    """Crear un usuario de prueba con permisos limitados"""
    # Conectar a la base de datos
    db_path = os.path.join('app', 'database', 'ISEMM_MES.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("👤 Creando usuario de prueba con permisos limitados...")
        
        # Crear rol "operador_limitado" si no existe
        cursor.execute('INSERT OR IGNORE INTO roles (nombre, descripcion, activo) VALUES (?, ?, ?)',
                      ('operador_limitado', 'Operador con permisos limitados', 1))
        
        cursor.execute('SELECT id FROM roles WHERE nombre = ?', ('operador_limitado',))
        rol_limitado_id = cursor.fetchone()[0]
        print(f"✅ Rol 'operador_limitado' creado/encontrado (ID: {rol_limitado_id})")
        
        # Asignar solo algunos permisos específicos al rol limitado
        permisos_limitados = [
            # Solo algunos permisos de LISTA_INFORMACIONBASICA
            ('LISTA_INFORMACIONBASICA', 'Información básica', 'Consultar licencias'),
            ('LISTA_INFORMACIONBASICA', 'Información básica', 'Gestión de clientes'),
            # Solo algunos permisos de LISTA_DE_MATERIALES
            ('LISTA_DE_MATERIALES', 'Control de material', 'Control de material de almacén'),
            ('LISTA_DE_MATERIALES', 'Control de material', 'Estatus de material'),
        ]
        
        # Limpiar permisos existentes del rol
        cursor.execute('DELETE FROM rol_permisos_botones WHERE rol_id = ?', (rol_limitado_id,))
        
        # Asignar permisos limitados
        permisos_asignados = 0
        for pagina, seccion, boton in permisos_limitados:
            cursor.execute('''
                SELECT id FROM permisos_botones 
                WHERE pagina = ? AND seccion = ? AND boton = ? AND activo = 1
            ''', (pagina, seccion, boton))
            
            permiso_result = cursor.fetchone()
            if permiso_result:
                permiso_id = permiso_result[0]
                cursor.execute('''
                    INSERT OR IGNORE INTO rol_permisos_botones (rol_id, permiso_boton_id)
                    VALUES (?, ?)
                ''', (rol_limitado_id, permiso_id))
                permisos_asignados += 1
                print(f"   ✅ {pagina} > {seccion} > {boton}")
        
        print(f"📊 {permisos_asignados} permisos asignados al rol limitado")
        
        # Crear usuario de prueba
        username = "usuario_limitado"
        password = "test123"
        
        # Hash de la contraseña
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        # Verificar si el usuario ya existe
        cursor.execute('SELECT id FROM usuarios_sistema WHERE username = ?', (username,))
        if cursor.fetchone():
            print(f"⚠️ Usuario '{username}' ya existe")
        else:
            # Crear usuario
            cursor.execute('''
                INSERT INTO usuarios_sistema 
                (username, password_hash, email, nombre_completo, departamento, cargo, activo, fecha_creacion)
                VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ''', (username, password_hash, f"{username}@test.com", "Usuario de Prueba Limitado", 
                  "Pruebas", "Operador", 1))
            
            usuario_id = cursor.lastrowid
            
            # Asignar rol al usuario
            cursor.execute('''
                INSERT OR IGNORE INTO usuario_roles (usuario_id, rol_id)
                VALUES (?, ?)
            ''', (usuario_id, rol_limitado_id))
            
            print(f"✅ Usuario '{username}' creado exitosamente")
            print(f"   ID: {usuario_id}")
            print(f"   Contraseña: {password}")
        
        conn.commit()
        
        print("\n📋 Resumen del usuario de prueba:")
        print("=" * 40)
        print(f"👤 Usuario: {username}")
        print(f"🔐 Contraseña: {password}")
        print(f"🛡️ Rol: operador_limitado")
        print(f"📊 Permisos: {permisos_asignados} permisos específicos")
        print("\n🧪 Para probar:")
        print("1. Inicia sesión con este usuario")
        print("2. Ve a las listas de Información Básica y Materiales")
        print("3. Solo algunos botones estarán habilitados")
        print("4. Los demás aparecerán deshabilitados/grises")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    crear_usuario_prueba()
