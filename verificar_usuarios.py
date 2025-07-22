#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verificar usuarios existentes en ambos sistemas
"""

import sqlite3
import json
import os

def verificar_usuario_bd():
    """Verificar usuario admin en base de datos"""
    print("🔍 VERIFICANDO USUARIO EN BASE DE DATOS")
    print("=" * 40)
    
    try:
        conn = sqlite3.connect('app/database/ISEMM_MES.db')
        cursor = conn.cursor()
        
        # Verificar si existe la tabla usuarios_sistema
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='usuarios_sistema'")
        if not cursor.fetchone():
            print("❌ Tabla usuarios_sistema no existe")
            return False
        
        # Buscar usuario admin
        cursor.execute("SELECT id, username, email, activo FROM usuarios_sistema WHERE username = ?", ('admin',))
        admin_user = cursor.fetchone()
        
        if admin_user:
            print(f"✅ Usuario admin encontrado en BD:")
            print(f"   ID: {admin_user[0]}")
            print(f"   Username: {admin_user[1]}")
            print(f"   Email: {admin_user[2]}")
            print(f"   Activo: {admin_user[3]}")
            
            # Verificar roles del usuario
            cursor.execute('''
                SELECT r.id, r.nombre, r.nivel
                FROM roles r
                JOIN usuario_roles ur ON r.id = ur.rol_id
                WHERE ur.usuario_id = ? AND r.activo = 1
            ''', (admin_user[0],))
            
            roles = cursor.fetchall()
            if roles:
                print(f"   Roles: {[f'{r[1]} (nivel {r[2]})' for r in roles]}")
            else:
                print("   ⚠️ Sin roles asignados")
            
            return True
        else:
            print("❌ Usuario admin NO encontrado en BD")
            return False
            
    except Exception as e:
        print(f"❌ Error verificando BD: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def verificar_usuario_json():
    """Verificar usuario admin en usuarios.json"""
    print("\n🔍 VERIFICANDO USUARIO EN JSON")
    print("=" * 40)
    
    try:
        json_path = 'app/database/usuarios.json'
        if not os.path.exists(json_path):
            print("❌ Archivo usuarios.json no existe")
            return False
        
        with open(json_path, 'r') as f:
            usuarios = json.load(f)
        
        if 'admin' in usuarios:
            print(f"✅ Usuario admin encontrado en JSON:")
            print(f"   Password: {usuarios['admin']}")
            return True
        else:
            print("❌ Usuario admin NO encontrado en JSON")
            print(f"   Usuarios disponibles: {list(usuarios.keys())}")
            return False
            
    except Exception as e:
        print(f"❌ Error verificando JSON: {e}")
        return False

def crear_usuario_admin():
    """Crear usuario admin si no existe"""
    print("\n🔧 CREANDO USUARIO ADMIN")
    print("=" * 40)
    
    try:
        # Importar el sistema de autenticación
        import sys
        sys.path.append('.')
        from app.auth_system import AuthSystem
        
        auth = AuthSystem()
        
        # Crear usuario admin
        resultado = auth.crear_usuario(
            username='admin',
            password='admin123',
            email='admin@example.com',
            nombre_completo='Administrador Sistema'
        )
        
        if isinstance(resultado, tuple):
            success, message = resultado
        else:
            success = resultado.get('success', False) if isinstance(resultado, dict) else False
            message = resultado.get('message', str(resultado)) if isinstance(resultado, dict) else str(resultado)
        
        if success:
            print(f"✅ Usuario admin creado: {message}")
            
            # Asignar rol de superadmin
            resultado_rol = auth.asignar_rol_usuario('admin', 'superadmin')
            if isinstance(resultado_rol, tuple):
                success_rol, message_rol = resultado_rol
            else:
                success_rol = resultado_rol.get('success', False) if isinstance(resultado_rol, dict) else False
                message_rol = resultado_rol.get('message', str(resultado_rol)) if isinstance(resultado_rol, dict) else str(resultado_rol)
            
            if success_rol:
                print(f"✅ Rol superadmin asignado: {message_rol}")
                return True
            else:
                print(f"⚠️ Error asignando rol: {message_rol}")
                return True  # Usuario creado aunque no se asignó rol
        else:
            print(f"❌ Error creando usuario: {message}")
            return False
            
    except Exception as e:
        print(f"❌ Error creando usuario admin: {e}")
        return False

def comparar_admin_vs_superadmin():
    """Comparar diferencias entre admin y superadmin"""
    print("\n🔍 COMPARANDO ADMIN VS SUPERADMIN")
    print("=" * 40)
    
    try:
        conn = sqlite3.connect('app/database/ISEMM_MES.db')
        cursor = conn.cursor()
        
        # Buscar usuarios admin y superadmin
        cursor.execute("""
            SELECT u.id, u.username, r.nombre as rol_nombre, r.nivel
            FROM usuarios_sistema u
            JOIN usuario_roles ur ON u.id = ur.usuario_id
            JOIN roles r ON ur.rol_id = r.id
            WHERE u.username IN ('admin', 'superadmin') AND r.activo = 1
        """)
        
        usuarios_roles = cursor.fetchall()
        
        if not usuarios_roles:
            print("❌ No se encontraron usuarios admin o superadmin")
            return False
        
        print("👥 USUARIOS Y ROLES ENCONTRADOS:")
        for usuario in usuarios_roles:
            print(f"   • {usuario[1]} -> Rol: {usuario[2]} (Nivel: {usuario[3]})")
        
        # Comparar permisos por usuario
        print("\n📋 PERMISOS POR USUARIO:")
        
        for usuario in usuarios_roles:
            usuario_id, username, rol_nombre, nivel = usuario
            
            # Contar permisos del usuario
            cursor.execute("""
                SELECT COUNT(*) as total_permisos
                FROM rol_permisos_botones rpb
                JOIN usuario_roles ur ON rpb.rol_id = ur.rol_id
                WHERE ur.usuario_id = ?
            """, (usuario_id,))
            
            total_permisos = cursor.fetchone()[0]
            
            print(f"\n   🔹 {username.upper()}:")
            print(f"      • Rol: {rol_nombre} (Nivel {nivel})")
            print(f"      • Total permisos: {total_permisos}")
            
            # Obtener algunos permisos específicos para comparar
            cursor.execute("""
                SELECT pb.pagina, pb.seccion, pb.boton, 1 as permitido
                FROM rol_permisos_botones rpb
                JOIN permisos_botones pb ON rpb.permiso_boton_id = pb.id
                JOIN usuario_roles ur ON rpb.rol_id = ur.rol_id
                WHERE ur.usuario_id = ?
                ORDER BY pb.pagina, pb.seccion, pb.boton
                LIMIT 10
            """, (usuario_id,))
            
            permisos_muestra = cursor.fetchall()
            
            if permisos_muestra:
                print(f"      • Muestra de permisos:")
                for permiso in permisos_muestra:
                    estado = "✅" if permiso[3] else "❌"
                    print(f"        {estado} {permiso[0]} -> {permiso[1]} -> {permiso[2]}")
        
        # Verificar diferencias específicas
        print("\n🔍 ANÁLISIS DE DIFERENCIAS:")
        
        # Verificar si superadmin tiene tratamiento especial en JavaScript
        js_permisos_path = 'app/static/js/permisos-dropdowns.js'
        if os.path.exists(js_permisos_path):
            with open(js_permisos_path, 'r', encoding='utf-8') as f:
                js_content = f.read()
                
            if 'superadmin' in js_content:
                print("   ⚠️ ENCONTRADO: El archivo JavaScript contiene referencias a 'superadmin'")
                
                # Buscar líneas específicas
                lines = js_content.split('\n')
                for i, line in enumerate(lines):
                    if 'superadmin' in line.lower():
                        print(f"      Línea {i+1}: {line.strip()}")
            else:
                print("   ✅ JavaScript no tiene referencias específicas a 'superadmin'")
        else:
            print("   ❌ Archivo permisos-dropdowns.js no encontrado")
        
        return True
        
    except Exception as e:
        print(f"❌ Error comparando usuarios: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    print("👤 VERIFICACIÓN Y CREACIÓN DE USUARIO ADMIN")
    print("=" * 50)
    
    # Verificar en ambos sistemas
    existe_bd = verificar_usuario_bd()
    existe_json = verificar_usuario_json()
    
    if not existe_bd and not existe_json:
        print("\n❌ Usuario admin no existe en ningún sistema")
        print("🔧 Intentando crear usuario admin...")
        if crear_usuario_admin():
            print("\n✅ Usuario admin creado correctamente")
            # Verificar nuevamente
            verificar_usuario_bd()
        else:
            print("\n❌ No se pudo crear el usuario admin")
    elif existe_bd:
        print("\n✅ Usuario admin existe en BD - el sistema debería funcionar")
    elif existe_json:
        print("\n✅ Usuario admin existe en JSON - el sistema debería funcionar")
    
    # Ejecutar análisis comparativo
    comparar_admin_vs_superadmin()
    
    print("\n🔍 PRÓXIMOS PASOS:")
    if existe_bd or existe_json:
        print("1. Verificar que las credenciales sean correctas")
        print("2. Verificar logs del servidor durante el login")
        print("3. El problema puede estar en la lógica del endpoint de login")
        print("4. Revisar las diferencias encontradas entre admin y superadmin")
    else:
        print("1. Ejecutar nuevamente después de crear el usuario")
        print("2. Verificar que el servidor tenga acceso a la base de datos")
