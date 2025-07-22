#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para probar el sistema de permisos corregido
"""

import sqlite3
import os

def get_db_connection():
    db_path = os.path.join(os.path.dirname(__file__), 'app', 'database', 'ISEMM_MES.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def probar_permisos_usuario(username):
    """Probar el nuevo flujo de permisos para un usuario específico"""
    print(f"🧪 Probando permisos para usuario: {username}")
    print("=" * 60)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Obtener roles del usuario
    cursor.execute('''
        SELECT r.nombre, r.descripcion, r.nivel
        FROM usuarios_sistema u
        JOIN usuario_roles ur ON u.id = ur.usuario_id
        JOIN roles r ON ur.rol_id = r.id
        WHERE u.username = ? AND u.activo = 1 AND r.activo = 1
        ORDER BY r.nivel DESC
    ''', (username,))
    
    roles = cursor.fetchall()
    
    if not roles:
        print(f"❌ Usuario '{username}' no encontrado o sin roles activos")
        return
    
    print(f"👤 Usuario: {username}")
    print(f"🎭 Roles asignados:")
    for rol in roles:
        print(f"   🎭 {rol['nombre']} (Nivel {rol['nivel']}) - {rol['descripcion']}")
    
    rol_principal = roles[0]  # Tomar el rol con mayor nivel
    
    # 2. Obtener permisos del rol principal
    if rol_principal['nombre'] == 'superadmin':
        cursor.execute('SELECT pagina, seccion, boton FROM permisos_botones WHERE activo = 1 ORDER BY pagina, seccion, boton')
        permisos = cursor.fetchall()
        print(f"\n✅ Superadmin: Acceso a TODOS los permisos ({len(permisos)} permisos)")
    else:
        cursor.execute('''
            SELECT pb.pagina, pb.seccion, pb.boton 
            FROM usuarios_sistema u
            JOIN usuario_roles ur ON u.id = ur.usuario_id
            JOIN rol_permisos_botones rpb ON ur.rol_id = rpb.rol_id
            JOIN permisos_botones pb ON rpb.permiso_boton_id = pb.id
            WHERE u.username = ? AND u.activo = 1 AND pb.activo = 1
            ORDER BY pb.pagina, pb.seccion, pb.boton
        ''', (username,))
        permisos = cursor.fetchall()
    
    # 3. Formatear permisos en estructura jerárquica
    permisos_jerarquicos = {}
    total_permisos = 0
    
    for pagina, seccion, boton in permisos:
        if pagina not in permisos_jerarquicos:
            permisos_jerarquicos[pagina] = {}
        
        if seccion not in permisos_jerarquicos[pagina]:
            permisos_jerarquicos[pagina][seccion] = []
        
        permisos_jerarquicos[pagina][seccion].append(boton)
        total_permisos += 1
    
    print(f"\n📊 Total de permisos: {total_permisos}")
    
    # 4. Mostrar algunos permisos de ejemplo
    print(f"\n📋 Permisos por página:")
    for pagina, secciones in permisos_jerarquicos.items():
        total_pagina = sum(len(botones) for botones in secciones.values())
        print(f"   📄 {pagina}: {total_pagina} permisos")
        
        for seccion, botones in secciones.items():
            print(f"      📂 {seccion}: {len(botones)} botones")
            # Mostrar solo los primeros 3 botones para no saturar
            for i, boton in enumerate(botones[:3]):
                print(f"         🔘 {boton}")
            if len(botones) > 3:
                print(f"         ... y {len(botones) - 3} más")
    
    # 5. Probar algunos permisos específicos
    print(f"\n🧪 Probando permisos específicos:")
    
    permisos_test = [
        ('LISTA_DE_CONFIGPG', 'Configuración', 'Configuración de impresión'),
        ('LISTA_DE_MATERIALES', 'Control de material', 'Control de salida'),
        ('LISTA_INFORMACIONBASICA', 'Información básica', 'Gestión de departamentos')
    ]
    
    for pagina, seccion, boton in permisos_test:
        # Simular verificación de permiso
        tiene_permiso = False
        if pagina in permisos_jerarquicos and seccion in permisos_jerarquicos[pagina]:
            tiene_permiso = boton in permisos_jerarquicos[pagina][seccion]
        
        resultado = "✅ PERMITIDO" if tiene_permiso else "❌ DENEGADO"
        print(f"   {resultado}: {pagina} > {seccion} > {boton}")
    
    conn.close()
    print(f"\n✅ Prueba completada para usuario: {username}")

def probar_todos_usuarios():
    """Probar permisos para todos los usuarios activos"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT username FROM usuarios_sistema WHERE activo = 1 ORDER BY username")
    usuarios = cursor.fetchall()
    
    conn.close()
    
    print("🔍 Probando permisos para todos los usuarios activos...")
    print("=" * 60)
    
    for usuario in usuarios:
        probar_permisos_usuario(usuario['username'])
        print("\n" + "-" * 60 + "\n")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        username = sys.argv[1]
        probar_permisos_usuario(username)
    else:
        probar_todos_usuarios()
