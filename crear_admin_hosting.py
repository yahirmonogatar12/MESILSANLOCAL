#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para crear usuario administrador en la base de datos del hosting
Autor: Asistente AI
Fecha: 2025-07-31
"""

import pymysql
import hashlib
from datetime import datetime

# Configuración de la base de datos del hosting
HOSTING_CONFIG = {
    'host': 'up-de-fra1-mysql-1.db.run-on-seenode.com',
    'port': 11550,
    'database': 'db_rrpq0erbdujn',
    'username': 'db_rrpq0erbdujn',
    'password': '5fUNbSRcPP3LN9K2I33Pr0ge'
}

def hash_password(password):
    """Crear hash de contraseña usando SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def conectar_hosting():
    """Conectar a la base de datos del hosting"""
    try:
        conexion = pymysql.connect(
            host=HOSTING_CONFIG['host'],
            port=HOSTING_CONFIG['port'],
            user=HOSTING_CONFIG['username'],
            password=HOSTING_CONFIG['password'],
            database=HOSTING_CONFIG['database'],
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        print(f"✅ Conectado a hosting: {HOSTING_CONFIG['host']}:{HOSTING_CONFIG['port']}")
        return conexion
    except Exception as e:
        print(f"❌ Error conectando al hosting: {e}")
        return None

def verificar_estructura_tabla(cursor):
    """Verificar la estructura de la tabla usuarios_sistema"""
    try:
        cursor.execute("DESCRIBE usuarios_sistema")
        campos = cursor.fetchall()
        
        print(f"\n📋 Estructura de tabla usuarios_sistema:")
        print("   Campo | Tipo | Null | Key | Default")
        print("   " + "-" * 50)
        for campo in campos:
            print(f"   {campo['Field']:15} | {campo['Type']:10} | {campo['Null']:4} | {campo['Key']:3} | {campo.get('Default', 'NULL')}")
        
        return [campo['Field'] for campo in campos]
    except Exception as e:
        print(f"❌ Error verificando estructura: {e}")
        return []

def verificar_usuarios_existentes(cursor, campos_disponibles):
    """Verificar qué usuarios ya existen"""
    try:
        # Usar solo campos que existen
        campos_select = ['id', 'username']
        if 'area' in campos_disponibles:
            campos_select.append('area')
        
        query = f"SELECT {', '.join(campos_select)} FROM usuarios_sistema"
        cursor.execute(query)
        usuarios = cursor.fetchall()
        
        print(f"\n📋 Usuarios existentes en hosting: {len(usuarios)}")
        if usuarios:
            print("   ID | Username | Área")
            print("   " + "-" * 30)
            for user in usuarios:
                area = user.get('area', 'N/A')
                print(f"   {user['id']:2} | {user['username']:10} | {area}")
        else:
            print("   ⚠️  No hay usuarios en la base de datos del hosting")
        
        return usuarios
    except Exception as e:
        print(f"❌ Error verificando usuarios: {e}")
        return []

def crear_usuario_admin(cursor, conexion, campos_disponibles):
    """Crear usuario administrador usando solo campos disponibles"""
    print("\n🔧 Creando usuario administrador para el hosting...")
    
    # Datos básicos del usuario admin
    username = "admin"
    password = "admin123"
    password_hash = hash_password(password)
    
    try:
        # Verificar si el usuario ya existe
        cursor.execute("SELECT id FROM usuarios_sistema WHERE username = %s", (username,))
        if cursor.fetchone():
            print(f"⚠️  El usuario '{username}' ya existe")
            return False
        
        # Construir query dinámicamente según campos disponibles
        campos_insert = ['username', 'password_hash']
        valores_insert = [username, password_hash]
        
        # Agregar campos opcionales si existen
        if 'area' in campos_disponibles:
            campos_insert.append('area')
            valores_insert.append('superadmin')
        
        # Crear query de inserción
        placeholders = ', '.join(['%s'] * len(campos_insert))
        campos_str = ', '.join(campos_insert)
        query = f"INSERT INTO usuarios_sistema ({campos_str}) VALUES ({placeholders})"
        
        cursor.execute(query, valores_insert)
        user_id = cursor.lastrowid
        
        # Intentar asignar rol si existe la tabla usuario_roles
        try:
            cursor.execute("SHOW TABLES LIKE 'usuario_roles'")
            if cursor.fetchone():
                cursor.execute("""
                INSERT INTO usuario_roles (usuario_id, rol) 
                VALUES (%s, 'superadmin')
                """, (user_id,))
                print(f"✅ Rol 'superadmin' asignado")
        except:
            print(f"⚠️  No se pudo asignar rol (tabla usuario_roles no existe)")
        
        conexion.commit()
        
        print(f"✅ Usuario administrador creado exitosamente:")
        print(f"   👤 Username: {username}")
        print(f"   🔑 Password: {password}")
        print(f"   🆔 ID: {user_id}")
        print(f"   📋 Campos usados: {', '.join(campos_insert)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creando usuario: {e}")
        conexion.rollback()
        return False

def verificar_login(cursor, username, password):
    """Verificar que el login funcione"""
    try:
        password_hash = hash_password(password)
        
        cursor.execute("""
        SELECT u.id, u.username
        FROM usuarios_sistema u
        WHERE u.username = %s AND u.password_hash = %s
        """, (username, password_hash))
        
        user = cursor.fetchone()
        
        if user:
            print(f"\n✅ Login verificado exitosamente:")
            print(f"   👤 Usuario: {user['username']}")
            print(f"   🆔 ID: {user['id']}")
            return True
        else:
            print(f"\n❌ Login falló para usuario: {username}")
            return False
            
    except Exception as e:
        print(f"❌ Error verificando login: {e}")
        return False

def main():
    """Función principal"""
    print("🚀 CREAR USUARIO ADMINISTRADOR PARA HOSTING")
    print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    # Conectar a la base de datos del hosting
    conexion = conectar_hosting()
    if not conexion:
        print("❌ No se pudo conectar al hosting")
        return False
    
    try:
        cursor = conexion.cursor()
        
        # 1. Verificar estructura de la tabla
        campos_disponibles = verificar_estructura_tabla(cursor)
        if not campos_disponibles:
            print("❌ No se pudo verificar la estructura de la tabla")
            return False
        
        # 2. Verificar usuarios existentes
        usuarios_existentes = verificar_usuarios_existentes(cursor, campos_disponibles)
        
        # 3. Crear usuario admin si no existe
        if crear_usuario_admin(cursor, conexion, campos_disponibles):
            # 4. Verificar que el login funcione
            verificar_login(cursor, "admin", "admin123")
            
            print("\n" + "=" * 50)
            print("🎉 ¡USUARIO ADMINISTRADOR CREADO EXITOSAMENTE!")
            print("=" * 50)
            print("\n📋 Credenciales para el hosting:")
            print("   👤 Username: admin")
            print("   🔑 Password: admin123")
            print("\n🚀 Ahora puedes hacer login en tu aplicación del hosting")
            print("\n⚠️  IMPORTANTE: Cambia la contraseña después del primer login")
            
        else:
            print("\n⚠️  No se pudo crear el usuario administrador")
            
    except Exception as e:
        print(f"❌ Error durante la ejecución: {e}")
        return False
        
    finally:
        conexion.close()
        print("\n🔌 Conexión cerrada")
    
    return True

if __name__ == "__main__":
    print("🔧 CONFIGURACIÓN DE USUARIO ADMINISTRADOR HOSTING")
    print("\n⚠️  Este script creará un usuario 'admin' con contraseña 'admin123'")
    print("\nPresiona Enter para continuar o Ctrl+C para cancelar...")
    
    try:
        input()
        exito = main()
        if exito:
            print("\n🎯 ¡Configuración completada! Tu hosting está listo para usar.")
        else:
            print("\n⚠️  Configuración incompleta. Revisa los errores arriba.")
    except KeyboardInterrupt:
        print("\n❌ Operación cancelada por el usuario")
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")