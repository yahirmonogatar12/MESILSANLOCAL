#!/usr/bin/env python3
"""
Test script para verificar el acceso a la página de auditoría
"""
import requests
import sys

def test_auditoria_access():
    """Prueba el acceso a la página de auditoría"""
    
    # Configuración
    base_url = "http://localhost:5000"
    login_data = {
        'username': 'admin',
        'password': 'admin123'
    }
    
    print("🔍 Probando acceso a la página de auditoría...")
    print(f"📍 Base URL: {base_url}")
    print(f"👤 Usuario: {login_data['username']}")
    
    # Crear sesión para mantener cookies
    session = requests.Session()
    
    try:
        # 1. Realizar login
        print("\n1️⃣ Realizando login...")
        login_response = session.post(f"{base_url}/login", data=login_data, allow_redirects=False)
        
        if login_response.status_code != 302:
            print(f"❌ Login falló - Status: {login_response.status_code}")
            return False
        
        print(f"✅ Login exitoso - Redirección a: {login_response.headers.get('Location')}")
        
        # 2. Acceder a la página de auditoría
        print("\n2️⃣ Accediendo a /admin/auditoria...")
        auditoria_response = session.get(f"{base_url}/admin/auditoria", allow_redirects=False)
        
        print(f"📊 Status Code: {auditoria_response.status_code}")
        
        if auditoria_response.status_code == 200:
            print("✅ ¡ÉXITO! Página de auditoría cargada correctamente")
            print(f"📄 Tamaño de respuesta: {len(auditoria_response.text)} caracteres")
            return True
        elif auditoria_response.status_code == 302:
            redirect_url = auditoria_response.headers.get('Location', 'Sin redirección')
            print(f"🔄 Redirección a: {redirect_url}")
            return False
        elif auditoria_response.status_code == 500:
            print("💥 Error interno del servidor (500)")
            print("🔍 Esto sugiere un problema con el template o el código del endpoint")
            return False
        else:
            print(f"❌ Error inesperado: {auditoria_response.status_code}")
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
    print("🧪 TEST: ACCESO A PÁGINA DE AUDITORÍA")
    print("=" * 60)
    
    success = test_auditoria_access()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ RESULTADO: PÁGINA DE AUDITORÍA ACCESIBLE")
        print("🚀 La página de auditoría funciona correctamente")
    else:
        print("❌ RESULTADO: PROBLEMAS CON PÁGINA DE AUDITORÍA")
        print("🔧 Revisar configuración y templates")
    print("=" * 60)
    
    sys.exit(0 if success else 1)
