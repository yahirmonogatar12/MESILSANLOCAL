#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para gestionar permisos de roles específicos
"""

import sqlite3
import os

def get_db_connection():
    db_path = os.path.join(os.path.dirname(__file__), 'app', 'database', 'ISEMM_MES.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def quitar_permisos_rol(rol_nombre, permisos_a_quitar):
    """Quitar permisos específicos de un rol"""
    print(f"🔧 Quitando permisos del rol: {rol_nombre}")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Obtener ID del rol
    cursor.execute("SELECT id FROM roles WHERE nombre = ?", (rol_nombre,))
    rol = cursor.fetchone()
    
    if not rol:
        print(f"❌ Rol '{rol_nombre}' no encontrado")
        return
    
    rol_id = rol['id']
    
    # Quitar cada permiso
    permisos_quitados = 0
    
    for pagina, seccion, boton in permisos_a_quitar:
        # Buscar el permiso
        cursor.execute('''
            SELECT id FROM permisos_botones 
            WHERE pagina = ? AND seccion = ? AND boton = ?
        ''', (pagina, seccion, boton))
        
        permiso = cursor.fetchone()
        
        if permiso:
            # Quitar el permiso del rol
            cursor.execute('''
                DELETE FROM rol_permisos_botones 
                WHERE rol_id = ? AND permiso_boton_id = ?
            ''', (rol_id, permiso['id']))
            
            if cursor.rowcount > 0:
                print(f"   ❌ Quitado: {pagina} > {seccion} > {boton}")
                permisos_quitados += 1
            else:
                print(f"   ⚠️ Ya no tenía: {pagina} > {seccion} > {boton}")
        else:
            print(f"   ⚠️ No encontrado: {pagina} > {seccion} > {boton}")
    
    conn.commit()
    conn.close()
    
    print(f"✅ Se quitaron {permisos_quitados} permisos del rol '{rol_nombre}'")

def crear_usuario_test():
    """Crear un usuario de prueba con permisos limitados"""
    print("👤 Creando usuario de prueba...")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verificar si el usuario ya existe
    cursor.execute("SELECT id FROM usuarios_sistema WHERE username = 'test_user'")
    if cursor.fetchone():
        print("⚠️ Usuario 'test_user' ya existe")
        return
    
    # Crear usuario
    cursor.execute('''
        INSERT INTO usuarios_sistema (
            username, password_hash, email, nombre_completo, 
            departamento, cargo, activo, fecha_creacion, creado_por
        ) VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), ?)
    ''', (
        'test_user',
        'c54437a17218bf679a119cb1192f18d55bf383ae8aaf298b8ffb2fb65ae51d1c',  # password: test123
        'test@ejemplo.com',
        'Usuario de Prueba',
        'Testing',
        'Tester',
        1,
        'admin'
    ))
    
    usuario_id = cursor.lastrowid
    
    # Asignar rol operador_almacen (permisos limitados)
    cursor.execute("SELECT id FROM roles WHERE nombre = 'operador_almacen'")
    rol = cursor.fetchone()
    
    if rol:
        cursor.execute('''
            INSERT INTO usuario_roles (usuario_id, rol_id, fecha_asignacion, asignado_por)
            VALUES (?, ?, datetime('now'), ?)
        ''', (usuario_id, rol['id'], 'admin'))
        
        print(f"✅ Usuario 'test_user' creado con rol 'operador_almacen'")
    else:
        print("❌ No se pudo asignar el rol")
    
    conn.commit()
    conn.close()

def main():
    print("🧪 Configurando entorno de prueba para permisos...")
    print("=" * 60)
    
    # 1. Crear usuario de prueba
    crear_usuario_test()
    
    # 2. Quitar algunos permisos del rol admin para testing
    permisos_a_quitar_admin = [
        ('LISTA_DE_CONFIGPG', 'Configuración', 'Configuración de impresión'),
        ('LISTA_DE_CONFIGPG', 'Configuración', 'Configuración de usuarios'),
        ('LISTA_DE_MATERIALES', 'Control de material', 'Control de salida'),
    ]
    
    respuesta = input("\n¿Quitar algunos permisos del admin para testing? (s/n): ")
    if respuesta.lower() in ['s', 'si', 'yes', 'y']:
        quitar_permisos_rol('admin', permisos_a_quitar_admin)
    
    print("\n" + "=" * 60)
    print("🎯 Entorno de prueba configurado!")
    print("\nUsuarios para probar:")
    print("1. admin (superadmin) - Todos los permisos")
    print("2. test_user (operador_almacen) - Permisos limitados")
    print("\nCredenciales test_user: test123")
    print("\nPuedes acceder a: http://localhost:5000")

if __name__ == "__main__":
    main()
