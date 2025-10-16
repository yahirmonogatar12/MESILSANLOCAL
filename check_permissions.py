#!/usr/bin/env python3
"""Script para verificar permisos de usuario"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from app.auth_system import AuthSystem
    print("✅ Importación exitosa")

    auth = AuthSystem()

    # Verificar permisos del usuario Yahir
    username = "Yahir"
    print(f"🔍 Verificando permisos para usuario: {username}")

    # Obtener información del usuario
    info = auth.obtener_informacion_usuario(username)
    print(f"👤 Información del usuario: {info}")

    # Obtener permisos
    permisos, nivel = auth.obtener_permisos_usuario(username)
    print(f"🔐 Permisos: {permisos}")
    print(f"📊 Nivel máximo: {nivel}")

    # Verificar permisos de botones específicos
    paginas = ['inventario', 'produccion', 'smd', 'main']
    secciones = ['general', 'botones', 'controles']
    botones = ['agregar', 'editar', 'eliminar', 'ver', 'exportar']

    print("\n🔘 Verificando permisos de botones:")
    for pagina in paginas:
        for seccion in secciones:
            for boton in botones:
                tiene_permiso = auth.verificar_permiso_boton(username, pagina, seccion, boton)
                if tiene_permiso:
                    print(f"  ✅ {pagina}.{seccion}.{boton}")

    # Verificar roles del usuario
    print("\n👥 Verificando roles del usuario...")
    from app.db_mysql import get_db_connection
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT r.nombre, r.descripcion
            FROM usuario_roles ur
            JOIN roles r ON ur.rol_id = r.id
            WHERE ur.usuario_id = (SELECT id FROM usuarios_sistema WHERE username = %s)
        """, (username,))
        roles = cursor.fetchall()
        print(f"🎭 Roles asignados: {[role[0] for role in roles]}")
        conn.close()

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()