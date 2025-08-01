#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para verificar específicamente el permiso de "Control de BOM" para el usuario Problema
"""

import pymysql
from app.config_mysql import get_mysql_connection_string

def get_db_connection():
    """Crear conexión a MySQL"""
    try:
        config = get_mysql_connection_string()
        if not config:
            print("Error: No se pudo obtener configuración de MySQL")
            return None
            
        connection = pymysql.connect(
            host=config['host'],
            user=config['user'],
            password=config['passwd'],
            database=config['db'],
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        return connection
    except Exception as e:
        print(f"Error conectando a MySQL: {e}")
        return None

def verificar_permiso_control_bom():
    """Verificar si el usuario Problema tiene permiso para Control de BOM"""
    conn = get_db_connection()
    if not conn:
        return
    
    try:
        cursor = conn.cursor()
        
        print("=== Verificación de Permiso: Control de BOM ===")
        print("Usuario: Problema")
        print("Permiso: LISTA_INFORMACIONBASICA > Control de produccion > Control de BOM")
        print()
        
        # 1. Verificar que el usuario existe
        cursor.execute("SELECT id, username, activo FROM usuarios_sistema WHERE username = %s", ('Problema',))
        usuario = cursor.fetchone()
        
        if not usuario:
            print("❌ Usuario 'Problema' no encontrado")
            return
        
        print(f"✓ Usuario encontrado: ID {usuario['id']}, Activo: {usuario['activo']}")
        
        # 2. Verificar roles del usuario
        cursor.execute("""
            SELECT r.id, r.nombre, r.descripcion
            FROM roles r
            JOIN usuario_roles ur ON r.id = ur.rol_id
            WHERE ur.usuario_id = %s
        """, (usuario['id'],))
        
        roles = cursor.fetchall()
        print(f"\n📋 Roles del usuario ({len(roles)}):")
        for rol in roles:
            print(f"  - {rol['nombre']} (ID: {rol['id']}) - {rol['descripcion']}")
        
        # 3. Verificar si existe el permiso específico
        cursor.execute("""
            SELECT id, pagina, seccion, boton, descripcion, activo
            FROM permisos_botones 
            WHERE pagina = %s AND seccion = %s AND boton = %s
        """, ('LISTA_INFORMACIONBASICA', 'Control de produccion', 'Control de BOM'))
        
        permiso_bom = cursor.fetchone()
        
        if not permiso_bom:
            print("\n❌ Permiso 'Control de BOM' no encontrado en la base de datos")
            
            # Buscar permisos similares
            cursor.execute("""
                SELECT pagina, seccion, boton
                FROM permisos_botones 
                WHERE boton LIKE '%BOM%' OR boton LIKE '%bom%'
            """)
            permisos_similares = cursor.fetchall()
            
            if permisos_similares:
                print("\n🔍 Permisos similares encontrados:")
                for p in permisos_similares:
                    print(f"  - {p['pagina']} > {p['seccion']} > {p['boton']}")
            return
        
        print(f"\n✓ Permiso encontrado: ID {permiso_bom['id']}, Activo: {permiso_bom['activo']}")
        print(f"  Descripción: {permiso_bom['descripcion']}")
        
        # 4. Verificar si algún rol del usuario tiene este permiso
        cursor.execute("""
            SELECT r.nombre as rol_nombre, pb.boton
            FROM roles r
            JOIN usuario_roles ur ON r.id = ur.rol_id
            JOIN rol_permisos_botones rpb ON r.id = rpb.rol_id
            JOIN permisos_botones pb ON rpb.permiso_boton_id = pb.id
            WHERE ur.usuario_id = %s AND pb.id = %s
        """, (usuario['id'], permiso_bom['id']))
        
        permisos_asignados = cursor.fetchall()
        
        if permisos_asignados:
            print(f"\n✅ Usuario TIENE el permiso 'Control de BOM'")
            print("📝 Asignado a través de los roles:")
            for p in permisos_asignados:
                print(f"  - {p['rol_nombre']}")
        else:
            print(f"\n❌ Usuario NO TIENE el permiso 'Control de BOM'")
            
            # Verificar qué permisos SÍ tiene el usuario
            cursor.execute("""
                SELECT pb.pagina, pb.seccion, pb.boton, r.nombre as rol_nombre
                FROM permisos_botones pb
                JOIN rol_permisos_botones rpb ON pb.id = rpb.permiso_boton_id
                JOIN roles r ON rpb.rol_id = r.id
                JOIN usuario_roles ur ON r.id = ur.rol_id
                WHERE ur.usuario_id = %s AND pb.activo = 1
                ORDER BY pb.pagina, pb.seccion, pb.boton
            """, (usuario['id'],))
            
            todos_permisos = cursor.fetchall()
            
            print(f"\n📊 Permisos que SÍ tiene el usuario ({len(todos_permisos)}):")
            pagina_actual = None
            for p in todos_permisos:
                if p['pagina'] != pagina_actual:
                    print(f"\n  📄 {p['pagina']}:")
                    pagina_actual = p['pagina']
                print(f"    - {p['seccion']} > {p['boton']} (rol: {p['rol_nombre']})")
        
        # 5. Verificar si el rol superadmin tiene todos los permisos
        cursor.execute("""
            SELECT r.nombre
            FROM roles r
            JOIN usuario_roles ur ON r.id = ur.rol_id
            WHERE ur.usuario_id = %s AND r.nombre IN ('superadmin', 'admin')
        """, (usuario['id'],))
        
        roles_admin = cursor.fetchall()
        
        if roles_admin:
            print(f"\n🔑 Usuario tiene roles administrativos:")
            for rol in roles_admin:
                print(f"  - {rol['nombre']} (debería tener acceso automático)")
        
    except Exception as e:
        print(f"Error verificando permiso: {e}")
    finally:
        conn.close()

def main():
    print("Verificando permiso específico para Control de BOM...\n")
    verificar_permiso_control_bom()

if __name__ == '__main__':
    main()