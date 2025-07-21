#!/usr/bin/env python3
"""
Test script para verificar el login del administrador
"""
import requests
import sys

def test_admin_login():
    """Prueba el login del administrador y verifica la redirección"""
    
    # Configuración
    base_url = "http://localhost:5000"
    login_data = {
        'username': 'admin',
        'password': 'admin123'
    }
    
    print("🔐 Probando login del administrador...")
    print(f"📍 Base URL: {base_url}")
    print(f"👤 Usuario: {login_data['username']}")
    
    # Crear sesión para mantener cookies
    session = requests.Session()
    
    try:
        # 1. Realizar login
        print("\n1️⃣ Enviando credenciales de login...")
        login_response = session.post(f"{base_url}/login", data=login_data, allow_redirects=False)
        
        print(f"📊 Status Code: {login_response.status_code}")
        print(f"📍 Location Header: {login_response.headers.get('Location', 'Sin redirección')}")
        
        # 2. Verificar redirección
        if login_response.status_code == 302:
            redirect_url = login_response.headers.get('Location', '')
            print(f"✅ Login exitoso - Redirección a: {redirect_url}")
            
            # Verificar si es admin panel
            if '/admin/panel' in redirect_url:
                print("🎯 ¡CORRECTO! Se redirige al panel de administración")
                
                # 3. Seguir la redirección para verificar acceso
                print("\n2️⃣ Siguiendo redirección al panel admin...")
                panel_response = session.get(f"{base_url}/admin/panel", allow_redirects=False)
                print(f"📊 Panel Status: {panel_response.status_code}")
                
                if panel_response.status_code == 200:
                    print("✅ ¡PERFECTO! Acceso exitoso al panel de administración")
                    return True
                else:
                    print(f"❌ Error al acceder al panel: {panel_response.status_code}")
                    return False
                    
            else:
                print(f"❌ ERROR: Se redirige a {redirect_url} en lugar del panel admin")
                return False
        else:
            print(f"❌ Login falló - Status: {login_response.status_code}")
            print(f"📝 Response: {login_response.text[:200]}...")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ ERROR: No se puede conectar al servidor")
        print("💡 Asegúrate de que Flask esté ejecutándose en http://localhost:5000")
        return False
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 TEST: LOGIN ADMINISTRADOR")
    print("=" * 60)
    
    success = test_admin_login()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ RESULTADO: TODAS LAS PRUEBAS PASARON")
        print("🚀 El administrador puede acceder correctamente al panel")
    else:
        print("❌ RESULTADO: ALGUNAS PRUEBAS FALLARON")
        print("🔧 Revisar la configuración del servidor")
    print("=" * 60)
    
    sys.exit(0 if success else 1)
