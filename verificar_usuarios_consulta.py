#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para verificar usuarios con rol 'consulta' y sus permisos
"""

import pymysql
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración de MySQL
MYSQL_CONFIG = {
    'host': os.getenv('MYSQL_HOST', 'localhost'),
    'user': os.getenv('MYSQL_USERNAME', 'root'),
    'password': os.getenv('MYSQL_PASSWORD', ''),
    'database': os.getenv('MYSQL_DATABASE', 'isemm_mes'),
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

def conectar_mysql():
    """Conectar a MySQL"""
    try:
        return pymysql.connect(**MYSQL_CONFIG)
    except Exception as e:
        print(f"❌ Error conectando a MySQL: {e}")
        return None

def verificar_usuarios_consulta():
    """Verificar usuarios con rol consulta y sus permisos"""
    conn = conectar_mysql()
    if not conn:
        return
    
    try:
        cursor = conn.cursor()
        
        print("=== VERIFICACIÓN DE USUARIOS CON ROL CONSULTA ===")
        print()
        
        # 1. Buscar usuarios con rol consulta
        cursor.execute("""
            SELECT u.id, u.username, u.nombre_completo, u.activo, r.nombre as rol_nombre
            FROM usuarios_sistema u
            JOIN usuario_roles ur ON u.id = ur.usuario_id
            JOIN roles r ON ur.rol_id = r.id
            WHERE r.nombre = 'consulta'
            ORDER BY u.username
        """)
        
        usuarios_consulta = cursor.fetchall()
        
        if not usuarios_consulta:
            print("❌ No se encontraron usuarios con rol 'consulta'")
            
            # Verificar si existe el rol consulta
            cursor.execute("SELECT id, nombre, descripcion FROM roles WHERE nombre = 'consulta'")
            rol_consulta = cursor.fetchone()
            
            if rol_consulta:
                print(f"✓ El rol 'consulta' existe (ID: {rol_consulta['id']})")
                print(f"  Descripción: {rol_consulta['descripcion']}")
            else:
                print("❌ El rol 'consulta' no existe en la base de datos")
            return
        
        print(f"📋 Usuarios con rol 'consulta' encontrados: {len(usuarios_consulta)}")
        print()
        
        for usuario in usuarios_consulta:
            print(f"👤 Usuario: {usuario['username']} ({usuario['nombre_completo']})")
            print(f"   ID: {usuario['id']}, Activo: {usuario['activo']}")
            
            # Verificar permisos específicos del usuario
            cursor.execute("""
                SELECT pb.pagina, pb.seccion, pb.boton, pb.descripcion
                FROM permisos_botones pb
                JOIN rol_permisos_botones rpb ON pb.id = rpb.permiso_boton_id
                JOIN roles r ON rpb.rol_id = r.id
                JOIN usuario_roles ur ON r.id = ur.rol_id
                WHERE ur.usuario_id = %s AND pb.activo = 1
                ORDER BY pb.pagina, pb.seccion, pb.boton
            """, (usuario['id'],))
            
            permisos = cursor.fetchall()
            
            print(f"   🔐 Permisos asignados: {len(permisos)}")
            
            if permisos:
                pagina_actual = None
                for permiso in permisos:
                    if permiso['pagina'] != pagina_actual:
                        print(f"\n     📄 {permiso['pagina']}:")
                        pagina_actual = permiso['pagina']
                    print(f"       - {permiso['seccion']} > {permiso['boton']}")
            else:
                print("     ❌ Sin permisos asignados")
            
            print()
        
        # 2. Verificar permisos del rol consulta en general
        print("\n=== PERMISOS DEL ROL CONSULTA ===")
        cursor.execute("""
            SELECT pb.pagina, pb.seccion, pb.boton, pb.descripcion
            FROM permisos_botones pb
            JOIN rol_permisos_botones rpb ON pb.id = rpb.permiso_boton_id
            JOIN roles r ON rpb.rol_id = r.id
            WHERE r.nombre = 'consulta' AND pb.activo = 1
            ORDER BY pb.pagina, pb.seccion, pb.boton
        """)
        
        permisos_rol = cursor.fetchall()
        
        if permisos_rol:
            print(f"🔐 Total de permisos del rol 'consulta': {len(permisos_rol)}")
            pagina_actual = None
            for permiso in permisos_rol:
                if permiso['pagina'] != pagina_actual:
                    print(f"\n📄 {permiso['pagina']}:")
                    pagina_actual = permiso['pagina']
                print(f"  - {permiso['seccion']} > {permiso['boton']}")
        else:
            print("❌ El rol 'consulta' no tiene permisos asignados")
        
        # 3. Sugerir permisos adicionales que podrían necesitar
        print("\n=== PERMISOS SUGERIDOS PARA CONSULTA ===")
        cursor.execute("""
            SELECT DISTINCT pagina, seccion, boton
            FROM permisos_botones
            WHERE (boton LIKE '%ver%' OR boton LIKE '%consultar%' OR boton LIKE '%listar%' 
                   OR boton LIKE '%exportar%' OR boton LIKE '%historial%')
            AND activo = 1
            AND id NOT IN (
                SELECT rpb.permiso_boton_id
                FROM rol_permisos_botones rpb
                JOIN roles r ON rpb.rol_id = r.id
                WHERE r.nombre = 'consulta'
            )
            ORDER BY pagina, seccion, boton
        """)
        
        permisos_sugeridos = cursor.fetchall()
        
        if permisos_sugeridos:
            print(f"💡 Permisos de solo lectura que podrían agregarse ({len(permisos_sugeridos)}):")
            pagina_actual = None
            for permiso in permisos_sugeridos:
                if permiso['pagina'] != pagina_actual:
                    print(f"\n📄 {permiso['pagina']}:")
                    pagina_actual = permiso['pagina']
                print(f"  - {permiso['seccion']} > {permiso['boton']}")
        
    except Exception as e:
        print(f"❌ Error verificando usuarios consulta: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

def asignar_permiso_consulta(pagina, seccion, boton):
    """Asignar un permiso específico al rol consulta"""
    conn = conectar_mysql()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Buscar el permiso
        cursor.execute("""
            SELECT id FROM permisos_botones
            WHERE pagina = %s AND seccion = %s AND boton = %s AND activo = 1
        """, (pagina, seccion, boton))
        
        permiso = cursor.fetchone()
        if not permiso:
            print(f"❌ Permiso no encontrado: {pagina} > {seccion} > {boton}")
            return False
        
        # Buscar el rol consulta
        cursor.execute("SELECT id FROM roles WHERE nombre = 'consulta'")
        rol = cursor.fetchone()
        if not rol:
            print("❌ Rol 'consulta' no encontrado")
            return False
        
        # Asignar el permiso
        cursor.execute("""
            INSERT IGNORE INTO rol_permisos_botones (rol_id, permiso_boton_id)
            VALUES (%s, %s)
        """, (rol['id'], permiso['id']))
        
        conn.commit()
        
        if cursor.rowcount > 0:
            print(f"✅ Permiso asignado: {pagina} > {seccion} > {boton}")
            return True
        else:
            print(f"ℹ️  Permiso ya estaba asignado: {pagina} > {seccion} > {boton}")
            return True
        
    except Exception as e:
        print(f"❌ Error asignando permiso: {e}")
        return False
    finally:
        conn.close()

def main():
    print("🔍 Verificando usuarios con rol 'consulta'...\n")
    verificar_usuarios_consulta()
    
    print("\n" + "="*60)
    print("¿Desea asignar algún permiso adicional al rol 'consulta'? (s/n): ", end="")
    respuesta = input().strip().lower()
    
    if respuesta == 's':
        print("\nIngrese los datos del permiso a asignar:")
        pagina = input("Página: ").strip()
        seccion = input("Sección: ").strip()
        boton = input("Botón: ").strip()
        
        if pagina and seccion and boton:
            asignar_permiso_consulta(pagina, seccion, boton)
            print("\n🔄 Verificando cambios...")
            verificar_usuarios_consulta()
        else:
            print("❌ Todos los campos son requeridos")

if __name__ == '__main__':
    main()