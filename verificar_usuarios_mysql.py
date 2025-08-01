#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para verificar usuarios en MySQL y diagnosticar el problema
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

try:
    from config_mysql import get_mysql_connection
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False
    print("⚠️ No se pudo importar configuración MySQL")

def verificar_conexion():
    """Verificar conexión a MySQL"""
    if not MYSQL_AVAILABLE:
        print("❌ MySQL no disponible")
        return None
    
    try:
        conn = get_mysql_connection()
        if conn:
            print("✅ Conexión MySQL exitosa")
            return conn
        else:
            print("❌ No se pudo obtener conexión MySQL")
            return None
    except Exception as e:
        print(f"❌ Error conectando a MySQL: {e}")
        return None

def verificar_tablas(conn):
    """Verificar que las tablas necesarias existan"""
    cursor = conn.cursor()
    
    tablas_necesarias = ['usuarios_sistema', 'roles', 'usuario_roles']
    
    for tabla in tablas_necesarias:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {tabla}")
            count = cursor.fetchone()[0]
            print(f"✅ Tabla {tabla}: {count} registros")
        except Exception as e:
            print(f"❌ Error en tabla {tabla}: {e}")
            return False
    
    return True

def listar_usuarios_detallado(conn):
    """Listar usuarios con detalles completos"""
    cursor = conn.cursor()
    
    try:
        # Consulta simple primero
        cursor.execute("SELECT id, username, activo FROM usuarios_sistema")
        usuarios_basicos = cursor.fetchall()
        
        print(f"\n👥 Usuarios básicos ({len(usuarios_basicos)}):")
        for usuario in usuarios_basicos:
            print(f"  - ID: {usuario[0]}, Username: {usuario[1]}, Activo: {usuario[2]}")
        
        # Consulta completa como en la aplicación
        cursor.execute('''
            SELECT 
                u.id, u.username, u.email, u.nombre_completo,
                u.departamento, u.cargo, u.activo, u.ultimo_acceso,
                u.fecha_creacion, u.intentos_fallidos, u.bloqueado_hasta,
                GROUP_CONCAT(r.nombre) as roles
            FROM usuarios_sistema u
            LEFT JOIN usuario_roles ur ON u.id = ur.usuario_id
            LEFT JOIN roles r ON ur.rol_id = r.id AND r.activo = 1
            GROUP BY u.id
            ORDER BY u.fecha_creacion DESC
        ''')
        
        usuarios_completos = cursor.fetchall()
        
        print(f"\n📋 Usuarios completos ({len(usuarios_completos)}):")
        for usuario in usuarios_completos:
            print(f"  - ID: {usuario[0]}")
            print(f"    Username: {usuario[1]}")
            print(f"    Nombre: {usuario[3]}")
            print(f"    Activo: {usuario[6]}")
            print(f"    Roles: {usuario[11] if usuario[11] else 'Sin roles'}")
            print("    ---")
        
        return len(usuarios_completos)
        
    except Exception as e:
        print(f"❌ Error listando usuarios: {e}")
        import traceback
        traceback.print_exc()
        return 0

def verificar_roles(conn):
    """Verificar roles disponibles"""
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT id, nombre, activo FROM roles ORDER BY nombre")
        roles = cursor.fetchall()
        
        print(f"\n🎭 Roles disponibles ({len(roles)}):")
        for rol in roles:
            estado = "✅ Activo" if rol[2] else "❌ Inactivo"
            print(f"  - ID: {rol[0]}, Nombre: {rol[1]}, Estado: {estado}")
        
        return len(roles)
        
    except Exception as e:
        print(f"❌ Error verificando roles: {e}")
        return 0

def verificar_relaciones_usuario_rol(conn):
    """Verificar relaciones usuario-rol"""
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT ur.usuario_id, u.username, ur.rol_id, r.nombre as rol_nombre
            FROM usuario_roles ur
            JOIN usuarios_sistema u ON ur.usuario_id = u.id
            JOIN roles r ON ur.rol_id = r.id
            ORDER BY u.username
        """)
        
        relaciones = cursor.fetchall()
        
        print(f"\n🔗 Relaciones Usuario-Rol ({len(relaciones)}):")
        for rel in relaciones:
            print(f"  - Usuario: {rel[1]} (ID: {rel[0]}) -> Rol: {rel[3]} (ID: {rel[2]})")
        
        return len(relaciones)
        
    except Exception as e:
        print(f"❌ Error verificando relaciones: {e}")
        return 0

def crear_usuario_admin_si_no_existe(conn):
    """Crear usuario admin si no existe"""
    cursor = conn.cursor()
    
    try:
        # Verificar si admin existe
        cursor.execute("SELECT COUNT(*) FROM usuarios_sistema WHERE username = 'admin'")
        existe_admin = cursor.fetchone()[0]
        
        if existe_admin == 0:
            print("\n🔧 Creando usuario admin...")
            
            # Crear usuario admin
            import hashlib
            password_hash = hashlib.sha256('admin123'.encode()).hexdigest()
            
            cursor.execute("""
                INSERT INTO usuarios_sistema 
                (username, password_hash, nombre_completo, departamento, cargo, activo, creado_por)
                VALUES ('admin', %s, 'Administrador Sistema', 'Sistemas', 'Administrador', 1, 'sistema')
            """, (password_hash,))
            
            admin_id = cursor.lastrowid
            
            # Verificar si existe rol superadmin
            cursor.execute("SELECT id FROM roles WHERE nombre = 'superadmin'")
            rol_superadmin = cursor.fetchone()
            
            if rol_superadmin:
                cursor.execute("""
                    INSERT INTO usuario_roles (usuario_id, rol_id, asignado_por)
                    VALUES (%s, %s, 'sistema')
                """, (admin_id, rol_superadmin[0]))
                print(f"✅ Usuario admin creado con rol superadmin")
            else:
                print(f"⚠️ Usuario admin creado pero sin rol (rol superadmin no existe)")
            
            conn.commit()
            return True
        else:
            print(f"ℹ️ Usuario admin ya existe")
            return False
            
    except Exception as e:
        print(f"❌ Error creando usuario admin: {e}")
        return False

def main():
    """Función principal"""
    print("🔍 Verificando usuarios en MySQL")
    print("="*50)
    
    # 1. Verificar conexión
    conn = verificar_conexion()
    if not conn:
        return
    
    try:
        # 2. Verificar tablas
        if not verificar_tablas(conn):
            print("❌ Error en las tablas")
            return
        
        # 3. Verificar roles
        total_roles = verificar_roles(conn)
        
        # 4. Verificar usuarios
        total_usuarios = listar_usuarios_detallado(conn)
        
        # 5. Verificar relaciones
        total_relaciones = verificar_relaciones_usuario_rol(conn)
        
        # 6. Crear admin si no existe
        if total_usuarios == 0:
            print("\n⚠️ No hay usuarios en el sistema")
            crear_usuario_admin_si_no_existe(conn)
            # Verificar nuevamente
            total_usuarios = listar_usuarios_detallado(conn)
        
        print("\n" + "="*50)
        print(f"📊 RESUMEN:")
        print(f"  • Roles: {total_roles}")
        print(f"  • Usuarios: {total_usuarios}")
        print(f"  • Relaciones: {total_relaciones}")
        
        if total_usuarios > 0:
            print("\n✅ El sistema tiene usuarios. El problema podría ser:")
            print("  1. Error en la función listar_usuarios de la aplicación")
            print("  2. Problema de permisos o autenticación")
            print("  3. Error en el frontend al cargar los datos")
        else:
            print("\n❌ No hay usuarios en el sistema")
        
    finally:
        conn.close()

if __name__ == "__main__":
    main()