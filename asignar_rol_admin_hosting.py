#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import pymysql
from datetime import datetime
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv('hosting_config_mysql_directo.env')

def conectar_hosting():
    """Conectar a la base de datos del hosting"""
    try:
        conn = pymysql.connect(
            host=os.getenv('MYSQL_HOST'),
            port=int(os.getenv('MYSQL_PORT')),
            user=os.getenv('MYSQL_USERNAME'),
            password=os.getenv('MYSQL_PASSWORD'),
            database=os.getenv('MYSQL_DATABASE'),
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        print(f"✅ Conectado a la base de datos del hosting: {os.getenv('MYSQL_HOST')}")
        return conn
    except Exception as e:
        print(f"❌ Error conectando al hosting: {e}")
        return None

def asignar_rol_superadmin(conn, username='admin'):
    """Asignar rol de superadmin al usuario"""
    try:
        cursor = conn.cursor()
        
        # Obtener ID del usuario
        cursor.execute("SELECT id FROM usuarios_sistema WHERE username = %s", (username,))
        usuario = cursor.fetchone()
        
        if not usuario:
            print(f"❌ Usuario '{username}' no encontrado")
            return False
        
        usuario_id = usuario['id']
        print(f"👤 Usuario encontrado: {username} (ID: {usuario_id})")
        
        # Obtener ID del rol superadmin
        cursor.execute("SELECT id, nombre, descripcion FROM roles WHERE nombre = 'superadmin'")
        rol = cursor.fetchone()
        
        if not rol:
            print(f"❌ Rol 'superadmin' no encontrado")
            return False
        
        rol_id = rol['id']
        print(f"🎭 Rol encontrado: {rol['nombre']} (ID: {rol_id}) - {rol['descripcion']}")
        
        # Verificar si ya tiene el rol asignado
        cursor.execute("""
            SELECT id FROM usuario_roles 
            WHERE usuario_id = %s AND rol_id = %s
        """, (usuario_id, rol_id))
        
        asignacion_existente = cursor.fetchone()
        
        if asignacion_existente:
            print(f"⚠️  El usuario '{username}' ya tiene el rol 'superadmin' asignado")
            return True
        
        # Asignar el rol
        fecha_actual = datetime.now()
        cursor.execute("""
            INSERT INTO usuario_roles (usuario_id, rol_id, fecha_asignacion, asignado_por)
            VALUES (%s, %s, %s, %s)
        """, (usuario_id, rol_id, fecha_actual, 'sistema'))
        
        conn.commit()
        
        print(f"✅ Rol 'superadmin' asignado exitosamente al usuario '{username}'")
        print(f"📅 Fecha de asignación: {fecha_actual}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error asignando rol: {e}")
        conn.rollback()
        return False

def verificar_permisos_usuario(conn, username='admin'):
    """Verificar los permisos del usuario"""
    try:
        cursor = conn.cursor()
        
        # Obtener roles del usuario
        cursor.execute("""
            SELECT r.id, r.nombre, r.descripcion, r.nivel, ur.fecha_asignacion
            FROM usuario_roles ur
            JOIN roles r ON ur.rol_id = r.id
            JOIN usuarios_sistema u ON ur.usuario_id = u.id
            WHERE u.username = %s
            ORDER BY r.nivel DESC
        """, (username,))
        
        roles = cursor.fetchall()
        
        if roles:
            print(f"\n🎭 Roles asignados al usuario '{username}':")
            for rol in roles:
                print(f"   - {rol['nombre']} (Nivel {rol['nivel']})")
                print(f"     📝 {rol['descripcion']}")
                print(f"     📅 Asignado: {rol['fecha_asignacion']}")
                print()
        else:
            print(f"\n⚠️  No se encontraron roles asignados al usuario '{username}'")
        
        # Verificar permisos de botones
        cursor.execute("""
            SELECT COUNT(*) as total_permisos
            FROM usuario_roles ur
            JOIN roles r ON ur.rol_id = r.id
            JOIN rol_permisos_botones rpb ON r.id = rpb.rol_id
            JOIN permisos_botones pb ON rpb.permiso_boton_id = pb.id
            JOIN usuarios_sistema u ON ur.usuario_id = u.id
            WHERE u.username = %s AND pb.activo = 1
        """, (username,))
        
        permisos = cursor.fetchone()
        
        if permisos:
            print(f"🔐 Total de permisos de botones: {permisos['total_permisos']}")
        
        return len(roles) > 0
        
    except Exception as e:
        print(f"❌ Error verificando permisos: {e}")
        return False

def main():
    print("🎭 Asignando rol de superadmin al usuario admin...\n")
    
    # Conectar al hosting
    conn = conectar_hosting()
    if not conn:
        return
    
    try:
        # Asignar rol de superadmin
        print("\n" + "="*50)
        print("🎭 ASIGNACIÓN DE ROL SUPERADMIN")
        print("="*50)
        
        success = asignar_rol_superadmin(conn, 'admin')
        
        if success:
            print("\n✅ Rol asignado correctamente")
        else:
            print("\n❌ Error asignando rol")
            return
        
        # Verificar permisos
        print("\n" + "="*50)
        print("🔍 VERIFICACIÓN DE PERMISOS")
        print("="*50)
        
        verificar_permisos_usuario(conn, 'admin')
        
        print("\n🎉 ¡Configuración completada!")
        print("✅ El usuario 'admin' ahora tiene acceso completo al sistema")
        print("🔑 Credenciales: admin / admin123")
        
    except Exception as e:
        print(f"❌ Error durante la configuración: {e}")
    finally:
        conn.close()
        print("\n🔌 Conexión cerrada")

if __name__ == "__main__":
    main()