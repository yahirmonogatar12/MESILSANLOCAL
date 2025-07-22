#!/usr/bin/env python3
"""
Script para probar el sistema de permisos de botones
"""

import sqlite3
import os

def probar_permisos_sistema():
    """Probar el sistema de permisos"""
    # Conectar a la base de datos
    db_path = os.path.join('app', 'database', 'ISEMM_MES.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("🔍 Verificando sistema de permisos...")
        
        # Verificar que no hay permisos generales
        cursor.execute('SELECT COUNT(*) FROM permisos')
        count_permisos = cursor.fetchone()[0]
        print(f"📊 Permisos generales: {count_permisos} (debe ser 0)")
        
        # Verificar permisos de botones
        cursor.execute('SELECT COUNT(*) FROM permisos_botones WHERE activo = 1')
        count_botones = cursor.fetchone()[0]
        print(f"📊 Permisos de botones: {count_botones}")
        
        # Verificar estructura de permisos de botones para LISTA_INFORMACIONBASICA
        cursor.execute('''
            SELECT pagina, seccion, boton
            FROM permisos_botones 
            WHERE pagina = 'LISTA_INFORMACIONBASICA' AND activo = 1
            ORDER BY seccion, boton
        ''')
        
        permisos_info_basica = cursor.fetchall()
        print(f"\n📋 Permisos disponibles para LISTA_INFORMACIONBASICA ({len(permisos_info_basica)}):")
        
        seccion_actual = None
        for permiso in permisos_info_basica:
            pagina, seccion, boton = permiso
            if seccion != seccion_actual:
                print(f"   📁 {seccion}")
                seccion_actual = seccion
            print(f"      ✅ {boton}")
        
        # Verificar usuarios y sus roles
        cursor.execute('''
            SELECT u.username, GROUP_CONCAT(r.nombre) as roles
            FROM usuarios_sistema u
            LEFT JOIN usuario_roles ur ON u.id = ur.usuario_id
            LEFT JOIN roles r ON ur.rol_id = r.id
            WHERE u.activo = 1
            GROUP BY u.id
        ''')
        
        usuarios = cursor.fetchall()
        print(f"\n👥 Usuarios activos ({len(usuarios)}):")
        for usuario in usuarios:
            username, roles = usuario
            roles_str = roles if roles else "Sin roles"
            print(f"   👤 {username}: {roles_str}")
        
        # Verificar permisos de superadmin (si existe)
        cursor.execute('''
            SELECT DISTINCT pb.pagina, pb.seccion, pb.boton
            FROM permisos_botones pb
            JOIN rol_permisos_botones rpb ON pb.id = rpb.permiso_boton_id
            JOIN usuario_roles ur ON rpb.rol_id = ur.rol_id
            JOIN usuarios_sistema u ON ur.usuario_id = u.id
            WHERE u.username = 'superadmin' AND pb.activo = 1
            ORDER BY pb.pagina, pb.seccion, pb.boton
        ''')
        
        permisos_superadmin = cursor.fetchall()
        print(f"\n🛡️ Permisos de superadmin ({len(permisos_superadmin)}):")
        if permisos_superadmin:
            pagina_actual = None
            seccion_actual = None
            for permiso in permisos_superadmin[:10]:  # Mostrar solo los primeros 10
                pagina, seccion, boton = permiso
                if pagina != pagina_actual:
                    print(f"   🗂️ {pagina}")
                    pagina_actual = pagina
                    seccion_actual = None
                if seccion != seccion_actual:
                    print(f"      📁 {seccion}")
                    seccion_actual = seccion
                print(f"         ✅ {boton}")
            
            if len(permisos_superadmin) > 10:
                print(f"         ... y {len(permisos_superadmin) - 10} más")
        else:
            print("   ⚠️ Superadmin no tiene permisos asignados")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        conn.close()

def verificar_endpoint():
    """Verificar que el endpoint de permisos funciona"""
    try:
        import requests
        
        print("\n🌐 Probando endpoint de permisos...")
        
        # Intentar conectarse al endpoint (necesitará autenticación)
        response = requests.get('http://localhost:5000/admin/verificar_permisos_usuario')
        print(f"📡 Respuesta del servidor: {response.status_code}")
        
        if response.status_code == 401:
            print("   ℹ️ Endpoint requiere autenticación (correcto)")
        elif response.status_code == 200:
            print("   ✅ Endpoint responde correctamente")
        else:
            print(f"   ⚠️ Estado inesperado: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("   ⚠️ Servidor no está ejecutándose en localhost:5000")
    except ImportError:
        print("   ℹ️ requests no está disponible, saltando prueba de endpoint")
    except Exception as e:
        print(f"   ❌ Error probando endpoint: {e}")

if __name__ == "__main__":
    probar_permisos_sistema()
    verificar_endpoint()
    
    print("\n✅ Pruebas completadas")
    print("\n📋 Instrucciones de uso:")
    print("1. Inicia el servidor: python run.py")
    print("2. Inicia sesión con un usuario")
    print("3. Ve a las listas (Información Básica o Materiales)")
    print("4. Los botones sin permisos aparecerán deshabilitados")
    print("5. Abre la consola del navegador para ver los logs de permisos")
