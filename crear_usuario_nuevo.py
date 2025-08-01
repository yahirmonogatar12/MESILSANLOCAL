#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para crear un nuevo usuario en el sistema ISEMM_MES
Resuelve el problema de contraseñas hasheadas
"""

import pymysql
import os
import hashlib
from datetime import datetime
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
    """Conecta a la base de datos MySQL"""
    try:
        conn = pymysql.connect(**MYSQL_CONFIG)
        print(f"✅ Conectado a MySQL: {MYSQL_CONFIG['host']}:{MYSQL_CONFIG['database']}")
        return conn
    except Exception as e:
        print(f"❌ Error conectando a MySQL: {e}")
        return None

def hash_password(password):
    """Hashear contraseña usando SHA256 (mismo método que el sistema)"""
    return hashlib.sha256(password.encode()).hexdigest()

def crear_usuario_nuevo(username, password, nombre_completo, email="", departamento="", cargo="", rol="admin"):
    """Crear un nuevo usuario en el sistema"""
    print(f"\n🔧 Creando usuario: {username}")
    
    conn = conectar_mysql()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Verificar si el usuario ya existe
        cursor.execute("SELECT id FROM usuarios_sistema WHERE username = %s", (username,))
        if cursor.fetchone():
            print(f"⚠️ El usuario '{username}' ya existe")
            
            # Preguntar si actualizar
            respuesta = input("¿Desea actualizar la contraseña? (s/N): ")
            if respuesta.lower() in ['s', 'si', 'sí', 'y', 'yes']:
                password_hash = hash_password(password)
                cursor.execute("""
                    UPDATE usuarios_sistema 
                    SET password_hash = %s, 
                        nombre_completo = %s,
                        email = %s,
                        departamento = %s,
                        cargo = %s,
                        activo = 1,
                        intentos_fallidos = 0,
                        bloqueado_hasta = NULL,
                        fecha_modificacion = NOW()
                    WHERE username = %s
                """, (password_hash, nombre_completo, email, departamento, cargo, username))
                
                conn.commit()
                print(f"✅ Usuario '{username}' actualizado exitosamente")
                print(f"   Contraseña: {password}")
                return True
            else:
                print("❌ Operación cancelada")
                return False
        
        # Crear nuevo usuario
        password_hash = hash_password(password)
        
        cursor.execute("""
            INSERT INTO usuarios_sistema (
                username, password_hash, nombre_completo, email,
                departamento, cargo, activo, creado_por
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            username, password_hash, nombre_completo, email,
            departamento, cargo, 1, 'sistema'
        ))
        
        usuario_id = cursor.lastrowid
        print(f"✅ Usuario creado con ID: {usuario_id}")
        
        # Asignar rol
        cursor.execute("SELECT id FROM roles WHERE nombre = %s", (rol,))
        rol_data = cursor.fetchone()
        
        if rol_data:
            cursor.execute("""
                INSERT INTO usuario_roles (usuario_id, rol_id, asignado_por)
                VALUES (%s, %s, %s)
            """, (usuario_id, rol_data['id'], 'sistema'))
            
            print(f"✅ Rol '{rol}' asignado al usuario")
        else:
            print(f"⚠️ Rol '{rol}' no encontrado, usuario creado sin rol")
        
        conn.commit()
        
        print(f"\n🎉 Usuario '{username}' creado exitosamente")
        print(f"   Contraseña: {password}")
        print(f"   Hash: {password_hash}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creando usuario: {e}")
        conn.rollback()
        return False
    
    finally:
        conn.close()

def listar_usuarios_existentes():
    """Listar usuarios existentes en el sistema"""
    print("\n📋 Usuarios existentes en el sistema:")
    
    conn = conectar_mysql()
    if not conn:
        return
    
    try:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT u.username, u.nombre_completo, u.activo, 
                   GROUP_CONCAT(r.nombre) as roles
            FROM usuarios_sistema u
            LEFT JOIN usuario_roles ur ON u.id = ur.usuario_id
            LEFT JOIN roles r ON ur.rol_id = r.id
            GROUP BY u.id
            ORDER BY u.username
        """)
        
        usuarios = cursor.fetchall()
        
        if usuarios:
            print(f"{'Username':<15} {'Nombre':<25} {'Activo':<8} {'Roles':<20}")
            print("-" * 70)
            
            for usuario in usuarios:
                activo = "✅ Sí" if usuario['activo'] else "❌ No"
                roles = usuario['roles'] if usuario['roles'] else "Sin roles"
                print(f"{usuario['username']:<15} {usuario['nombre_completo']:<25} {activo:<8} {roles:<20}")
        else:
            print("No hay usuarios en el sistema")
        
    except Exception as e:
        print(f"❌ Error listando usuarios: {e}")
    
    finally:
        conn.close()

def verificar_login(username, password):
    """Verificar si las credenciales funcionan"""
    print(f"\n🔍 Verificando login para: {username}")
    
    conn = conectar_mysql()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Obtener usuario
        cursor.execute("""
            SELECT id, username, password_hash, activo, nombre_completo
            FROM usuarios_sistema 
            WHERE username = %s
        """, (username,))
        
        usuario = cursor.fetchone()
        
        if not usuario:
            print(f"❌ Usuario '{username}' no encontrado")
            return False
        
        if not usuario['activo']:
            print(f"❌ Usuario '{username}' está inactivo")
            return False
        
        # Verificar contraseña
        password_hash = hash_password(password)
        
        print(f"   Hash esperado: {password_hash}")
        print(f"   Hash en BD:    {usuario['password_hash']}")
        
        if usuario['password_hash'] == password_hash:
            print(f"✅ Login exitoso para '{username}'")
            return True
        else:
            print(f"❌ Contraseña incorrecta para '{username}'")
            return False
        
    except Exception as e:
        print(f"❌ Error verificando login: {e}")
        return False
    
    finally:
        conn.close()

def main():
    """Función principal"""
    print("🚀 CREADOR DE USUARIOS - ISEMM MES")
    print("=" * 50)
    
    while True:
        print("\n📋 Opciones disponibles:")
        print("1. Listar usuarios existentes")
        print("2. Crear nuevo usuario")
        print("3. Verificar login")
        print("4. Crear usuario admin rápido")
        print("5. Salir")
        
        opcion = input("\nSeleccione una opción (1-5): ").strip()
        
        if opcion == "1":
            listar_usuarios_existentes()
        
        elif opcion == "2":
            print("\n📝 Crear nuevo usuario:")
            username = input("Username: ").strip()
            if not username:
                print("❌ Username es requerido")
                continue
            
            password = input("Contraseña: ").strip()
            if not password:
                print("❌ Contraseña es requerida")
                continue
            
            nombre_completo = input("Nombre completo: ").strip()
            if not nombre_completo:
                print("❌ Nombre completo es requerido")
                continue
            
            email = input("Email (opcional): ").strip()
            departamento = input("Departamento (opcional): ").strip()
            cargo = input("Cargo (opcional): ").strip()
            
            print("\nRoles disponibles: superadmin, admin, supervisor_almacen, operador_almacen, consulta")
            rol = input("Rol (default: admin): ").strip() or "admin"
            
            crear_usuario_nuevo(username, password, nombre_completo, email, departamento, cargo, rol)
        
        elif opcion == "3":
            print("\n🔍 Verificar login:")
            username = input("Username: ").strip()
            password = input("Contraseña: ").strip()
            
            if username and password:
                verificar_login(username, password)
            else:
                print("❌ Username y contraseña son requeridos")
        
        elif opcion == "4":
            print("\n⚡ Creando usuario admin rápido...")
            crear_usuario_nuevo(
                username="nuevo_admin",
                password="admin123",
                nombre_completo="Nuevo Administrador",
                email="admin@isemm.com",
                departamento="Sistemas",
                cargo="Administrador",
                rol="superadmin"
            )
        
        elif opcion == "5":
            print("\n👋 ¡Hasta luego!")
            break
        
        else:
            print("❌ Opción inválida")

if __name__ == "__main__":
    main()