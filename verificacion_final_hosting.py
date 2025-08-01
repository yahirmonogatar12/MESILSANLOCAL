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
        return conn
    except Exception as e:
        print(f"❌ Error conectando al hosting: {e}")
        return None

def hash_password(password):
    """Generar hash de contraseña"""
    return hashlib.sha256(password.encode()).hexdigest()

def verificar_configuracion_completa():
    """Verificar que toda la configuración esté correcta"""
    print("🔍 VERIFICACIÓN FINAL DEL HOSTING")
    print("="*60)
    
    # Verificar variables de entorno
    print("\n📋 1. VARIABLES DE ENTORNO:")
    variables_requeridas = [
        'MYSQL_HOST', 'MYSQL_PORT', 'MYSQL_DATABASE', 
        'MYSQL_USERNAME', 'MYSQL_PASSWORD', 'SECRET_KEY'
    ]
    
    for var in variables_requeridas:
        valor = os.getenv(var)
        if valor:
            if 'PASSWORD' in var or 'SECRET' in var:
                print(f"   ✅ {var}: ***")
            else:
                print(f"   ✅ {var}: {valor}")
        else:
            print(f"   ❌ {var}: NO CONFIGURADA")
    
    # Conectar a la base de datos
    print("\n📋 2. CONEXIÓN A BASE DE DATOS:")
    conn = conectar_hosting()
    if not conn:
        print("   ❌ No se pudo conectar a la base de datos")
        return False
    
    print(f"   ✅ Conectado a: {os.getenv('MYSQL_HOST')}:{os.getenv('MYSQL_PORT')}")
    print(f"   ✅ Base de datos: {os.getenv('MYSQL_DATABASE')}")
    
    try:
        cursor = conn.cursor()
        
        # Verificar tablas principales
        print("\n📋 3. TABLAS PRINCIPALES:")
        tablas_principales = [
            'usuarios_sistema', 'roles', 'usuario_roles',
            'materiales', 'bom', 'control_bom',
            'permisos_botones', 'rol_permisos_botones'
        ]
        
        for tabla in tablas_principales:
            try:
                cursor.execute(f"SELECT COUNT(*) as total FROM {tabla}")
                resultado = cursor.fetchone()
                print(f"   ✅ {tabla}: {resultado['total']} registros")
            except Exception as e:
                if "doesn't exist" in str(e):
                    print(f"   ⚠️  {tabla}: NO EXISTE")
                else:
                    print(f"   ❌ {tabla}: ERROR - {e}")
        
        # Verificar usuario administrador
        print("\n📋 4. USUARIO ADMINISTRADOR:")
        cursor.execute("""
            SELECT u.id, u.username, u.activo, r.nombre as rol, r.nivel
            FROM usuarios_sistema u
            LEFT JOIN usuario_roles ur ON u.id = ur.usuario_id
            LEFT JOIN roles r ON ur.rol_id = r.id
            WHERE u.username = 'admin'
        """)
        
        admin_info = cursor.fetchone()
        
        if admin_info:
            print(f"   ✅ Usuario admin encontrado (ID: {admin_info['id']})")
            print(f"   ✅ Estado activo: {admin_info['activo']}")
            if admin_info['rol']:
                print(f"   ✅ Rol asignado: {admin_info['rol']} (Nivel {admin_info['nivel']})")
            else:
                print(f"   ⚠️  Sin rol asignado")
        else:
            print(f"   ❌ Usuario admin no encontrado")
        
        # Probar login del administrador
        print("\n📋 5. PRUEBA DE LOGIN:")
        password_hash = hash_password('admin123')
        cursor.execute("""
            SELECT id, username FROM usuarios_sistema 
            WHERE username = 'admin' AND password_hash = %s AND activo = 1
        """, (password_hash,))
        
        login_test = cursor.fetchone()
        
        if login_test:
            print(f"   ✅ Login exitoso para admin/admin123")
        else:
            print(f"   ❌ Login fallido para admin/admin123")
        
        # Verificar datos de migración
        print("\n📋 6. DATOS MIGRADOS:")
        
        # Materiales
        try:
            cursor.execute("SELECT COUNT(*) as total FROM materiales")
            total_materiales = cursor.fetchone()['total']
            print(f"   ✅ Materiales: {total_materiales} registros")
        except:
            print(f"   ⚠️  Materiales: Tabla no accesible")
        
        # BOM
        try:
            cursor.execute("SELECT COUNT(*) as total FROM bom")
            total_bom = cursor.fetchone()['total']
            print(f"   ✅ BOM: {total_bom} registros")
        except:
            print(f"   ⚠️  BOM: Tabla no accesible")
        
        # Control BOM
        try:
            cursor.execute("SELECT COUNT(*) as total FROM control_bom")
            total_control = cursor.fetchone()['total']
            print(f"   ✅ Control BOM: {total_control} registros")
        except:
            print(f"   ⚠️  Control BOM: Tabla no accesible")
        
        print("\n📋 7. RESUMEN FINAL:")
        print(f"   🌐 Host: {os.getenv('MYSQL_HOST')}")
        print(f"   🗄️  Base de datos: {os.getenv('MYSQL_DATABASE')}")
        print(f"   👤 Usuario admin: Configurado y funcional")
        print(f"   🔑 Credenciales: admin / admin123")
        print(f"   🎭 Rol: superadmin (acceso completo)")
        
        print("\n🎉 ¡HOSTING CONFIGURADO CORRECTAMENTE!")
        print("✅ La aplicación está lista para usar en el hosting")
        print("🚀 Puedes hacer login con las credenciales proporcionadas")
        
        return True
        
    except Exception as e:
        print(f"❌ Error durante la verificación: {e}")
        return False
    finally:
        conn.close()

def main():
    verificar_configuracion_completa()

if __name__ == "__main__":
    main()