#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de debug para verificar el sistema de permisos de dropdowns
"""

import sqlite3
import os

def get_db_connection():
    # Usar la base de datos principal del sistema
    db_path = os.path.join(os.path.dirname(__file__), 'app', 'database', 'ISEMM_MES.db')
    if not os.path.exists(db_path):
        print(f"❌ Base de datos no encontrada en: {db_path}")
        return None
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def verificar_sistema_permisos():
    print("🔍 Verificando sistema de permisos de dropdowns...")
    print("=" * 60)
    
    conn = get_db_connection()
    if not conn:
        return
    
    cursor = conn.cursor()
    
    # 1. Verificar si existen las tablas necesarias
    print("\n📋 1. Verificando tablas existentes:")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%permiso%'")
    tablas = cursor.fetchall()
    
    for tabla in tablas:
        print(f"   ✅ {tabla['name']}")
    
    # 2. Verificar permisos de botones disponibles
    print("\n🔘 2. Permisos de botones disponibles:")
    try:
        cursor.execute("SELECT COUNT(*) as total FROM permisos_botones")
        total_permisos = cursor.fetchone()['total']
        print(f"   📊 Total permisos: {total_permisos}")
        
        if total_permisos > 0:
            cursor.execute("""
                SELECT pagina, COUNT(*) as cantidad
                FROM permisos_botones 
                GROUP BY pagina 
                ORDER BY pagina
            """)
            por_pagina = cursor.fetchall()
            
            for fila in por_pagina:
                print(f"   📄 {fila['pagina']}: {fila['cantidad']} permisos")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # 3. Verificar usuarios existentes
    print("\n👥 3. Usuarios en el sistema:")
    try:
        cursor.execute("SELECT username, rol, activo FROM usuarios_sistema ORDER BY username")
        usuarios = cursor.fetchall()
        
        for usuario in usuarios:
            estado = "✅ Activo" if usuario['activo'] else "❌ Inactivo"
            print(f"   👤 {usuario['username']} ({usuario['rol']}) - {estado}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # 4. Verificar roles y sus permisos
    print("\n🎭 4. Roles y permisos asignados:")
    try:
        cursor.execute("SELECT id, nombre, descripcion FROM roles WHERE activo = 1")
        roles = cursor.fetchall()
        
        for rol in roles:
            cursor.execute("""
                SELECT COUNT(*) as total_permisos
                FROM rol_permisos_botones rpb
                WHERE rpb.rol_id = ?
            """, (rol['id'],))
            
            total = cursor.fetchone()['total_permisos']
            print(f"   🎭 {rol['nombre']}: {total} permisos asignados")
            
            if total > 0:
                cursor.execute("""
                    SELECT pb.pagina, COUNT(*) as cantidad
                    FROM rol_permisos_botones rpb
                    JOIN permisos_botones pb ON rpb.permiso_boton_id = pb.id
                    WHERE rpb.rol_id = ?
                    GROUP BY pb.pagina
                    ORDER BY pb.pagina
                """, (rol['id'],))
                
                por_pagina = cursor.fetchall()
                for fila in por_pagina:
                    print(f"      📄 {fila['pagina']}: {fila['cantidad']}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # 5. Verificar permisos específicos para un usuario de prueba
    print("\n🧪 5. Testing permisos para superadmin:")
    try:
        cursor.execute("""
            SELECT pb.pagina, pb.seccion, pb.boton
            FROM usuarios_sistema u
            LEFT JOIN usuario_roles ur ON u.id = ur.usuario_id
            LEFT JOIN rol_permisos_botones rpb ON ur.rol_id = rpb.rol_id
            LEFT JOIN permisos_botones pb ON rpb.permiso_boton_id = pb.id
            WHERE u.username = 'superadmin' AND pb.id IS NOT NULL
            LIMIT 5
        """)
        
        permisos_test = cursor.fetchall()
        
        if permisos_test:
            print("   📋 Algunos permisos encontrados:")
            for permiso in permisos_test:
                print(f"      ✅ {permiso['pagina']} > {permiso['seccion']} > {permiso['boton']}")
        else:
            print("   ⚠️ No se encontraron permisos para superadmin")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    conn.close()
    print("\n✅ Verificación completada!")

def dar_todos_los_permisos_a_superadmin():
    """Asignar todos los permisos al rol superadmin"""
    print("\n🔧 Asignando todos los permisos al superadmin...")
    
    conn = get_db_connection()
    if not conn:
        return
    
    cursor = conn.cursor()
    
    try:
        # Obtener el rol superadmin
        cursor.execute("SELECT id FROM roles WHERE nombre = 'superadmin'")
        rol_super = cursor.fetchone()
        
        if not rol_super:
            print("❌ Rol superadmin no encontrado")
            return
        
        rol_id = rol_super['id']
        
        # Obtener todos los permisos de botones
        cursor.execute("SELECT id FROM permisos_botones")
        todos_permisos = cursor.fetchall()
        
        # Limpiar permisos existentes del superadmin
        cursor.execute("DELETE FROM rol_permisos_botones WHERE rol_id = ?", (rol_id,))
        
        # Asignar todos los permisos
        for permiso in todos_permisos:
            cursor.execute("""
                INSERT OR IGNORE INTO rol_permisos_botones (rol_id, permiso_boton_id)
                VALUES (?, ?)
            """, (rol_id, permiso['id']))
        
        conn.commit()
        print(f"✅ Asignados {len(todos_permisos)} permisos al superadmin")
        
    except Exception as e:
        print(f"❌ Error asignando permisos: {e}")
        conn.rollback()
    
    conn.close()

if __name__ == "__main__":
    verificar_sistema_permisos()
    
    respuesta = input("\n¿Deseas asignar todos los permisos al superadmin? (s/n): ")
    if respuesta.lower() in ['s', 'si', 'yes', 'y']:
        dar_todos_los_permisos_a_superadmin()
        print("\n🔄 Ejecutando verificación nuevamente...")
        verificar_sistema_permisos()
