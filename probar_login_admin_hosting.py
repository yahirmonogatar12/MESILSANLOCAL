#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import pymysql
import hashlib
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

def hash_password(password):
    """Generar hash de contraseña"""
    return hashlib.sha256(password.encode()).hexdigest()

def probar_login(conn, username, password):
    """Probar login con credenciales"""
    try:
        cursor = conn.cursor()
        password_hash = hash_password(password)
        
        print(f"\n🔍 Probando login para usuario: {username}")
        print(f"🔑 Password hash: {password_hash[:20]}...")
        
        # Verificar usuario en usuarios_sistema
        cursor.execute("""
            SELECT id, username, password_hash, activo, departamento, cargo
            FROM usuarios_sistema 
            WHERE username = %s AND password_hash = %s AND activo = 1
        """, (username, password_hash))
        
        usuario = cursor.fetchone()
        
        if usuario:
            print(f"✅ Login exitoso:")
            print(f"   👤 ID: {usuario['id']}")
            print(f"   👤 Username: {usuario['username']}")
            print(f"   🏢 Departamento: {usuario['departamento']}")
            print(f"   💼 Cargo: {usuario['cargo']}")
            print(f"   ✅ Activo: {usuario['activo']}")
            
            # Verificar roles asignados
            cursor.execute("""
                SELECT r.id, r.nombre, r.descripcion, r.nivel
                FROM usuario_roles ur
                JOIN roles r ON ur.rol_id = r.id
                WHERE ur.usuario_id = %s
            """, (usuario['id'],))
            
            roles = cursor.fetchall()
            
            if roles:
                print(f"\n🎭 Roles asignados ({len(roles)}):")
                for rol in roles:
                    print(f"   - {rol['nombre']} (Nivel {rol['nivel']}): {rol['descripcion']}")
            else:
                print(f"\n⚠️  No se encontraron roles asignados")
            
            return True
        else:
            print(f"❌ Login fallido: Usuario no encontrado o credenciales incorrectas")
            
            # Verificar si el usuario existe
            cursor.execute("SELECT id, username, activo FROM usuarios_sistema WHERE username = %s", (username,))
            usuario_existe = cursor.fetchone()
            
            if usuario_existe:
                print(f"   ℹ️  Usuario existe pero credenciales no coinciden")
                print(f"   👤 ID: {usuario_existe['id']}")
                print(f"   ✅ Activo: {usuario_existe['activo']}")
            else:
                print(f"   ℹ️  Usuario no existe en la base de datos")
            
            return False
            
    except Exception as e:
        print(f"❌ Error durante el login: {e}")
        return False

def verificar_estructura_login(conn):
    """Verificar que las tablas necesarias para login existan"""
    try:
        cursor = conn.cursor()
        
        # Verificar tabla usuarios_sistema
        cursor.execute("SELECT COUNT(*) as total FROM usuarios_sistema")
        total_usuarios = cursor.fetchone()['total']
        print(f"\n📊 Total usuarios en usuarios_sistema: {total_usuarios}")
        
        # Verificar tabla roles
        cursor.execute("SELECT COUNT(*) as total FROM roles")
        total_roles = cursor.fetchone()['total']
        print(f"📊 Total roles: {total_roles}")
        
        # Verificar tabla usuario_roles
        cursor.execute("SELECT COUNT(*) as total FROM usuario_roles")
        total_usuario_roles = cursor.fetchone()['total']
        print(f"📊 Total asignaciones usuario-rol: {total_usuario_roles}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error verificando estructura: {e}")
        return False

def main():
    print("🧪 Probando login del administrador en el hosting...\n")
    
    # Conectar al hosting
    conn = conectar_hosting()
    if not conn:
        return
    
    try:
        # Verificar estructura
        verificar_estructura_login(conn)
        
        # Probar login con admin
        print("\n" + "="*50)
        print("🔐 PRUEBA DE LOGIN - ADMINISTRADOR")
        print("="*50)
        
        success = probar_login(conn, 'admin', 'admin123')
        
        if success:
            print("\n🎉 ¡Login del administrador funciona correctamente!")
            print("✅ La aplicación debería permitir el acceso en el hosting")
        else:
            print("\n❌ Problema con el login del administrador")
            print("⚠️  Revisar configuración de la aplicación")
        
        # También probar con otros usuarios existentes
        print("\n" + "="*50)
        print("🔐 PRUEBA DE LOGIN - OTROS USUARIOS")
        print("="*50)
        
        # Obtener lista de usuarios
        cursor = conn.cursor()
        cursor.execute("SELECT username FROM usuarios_sistema WHERE username != 'admin' LIMIT 3")
        otros_usuarios = cursor.fetchall()
        
        for usuario in otros_usuarios:
            print(f"\n🧪 Probando usuario: {usuario['username']}")
            # Nota: No sabemos las contraseñas de otros usuarios, solo verificamos que existan
            cursor.execute("SELECT id, activo FROM usuarios_sistema WHERE username = %s", (usuario['username'],))
            info = cursor.fetchone()
            if info:
                print(f"   ✅ Usuario existe (ID: {info['id']}, Activo: {info['activo']})")
        
        print("\n✅ Verificación completada")
        
    except Exception as e:
        print(f"❌ Error durante la verificación: {e}")
    finally:
        conn.close()
        print("\n🔌 Conexión cerrada")

if __name__ == "__main__":
    main()