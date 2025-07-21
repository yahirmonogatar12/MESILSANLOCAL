#!/usr/bin/env python3
"""
Script para verificar el comportamiento de redirecciones
"""

import requests

# Session para mantener cookies
session = requests.Session()

def test_redirect_behavior():
    """Test específico del comportamiento de redirecciones"""
    
    print("🔍 Probando comportamiento de redirecciones...")
    
    # Login
    login_data = {
        'username': 'admin',  # ¡CAMBIÉ a username en lugar de usuario!
        'password': 'admin123'
    }
    
    print("1️⃣ Haciendo login...")
    response = session.post("http://localhost:5000/login", data=login_data, allow_redirects=False)
    print(f"   Status: {response.status_code}")
    print(f"   Headers: {dict(response.headers)}")
    
    if 'Location' in response.headers:
        redirect_url = response.headers['Location']
        print(f"   🔄 Redirigiendo a: {redirect_url}")
        
        # Seguir la redirección
        print("2️⃣ Siguiendo redirección...")
        response2 = session.get("http://localhost:5000" + redirect_url, allow_redirects=False)
        print(f"   Status: {response2.status_code}")
        print(f"   Headers: {dict(response2.headers)}")
        
        if response2.status_code == 200:
            print(f"   📄 Contenido recibido: {len(response2.text)} caracteres")
            if "Panel de Administración" in response2.text:
                print("   ✅ ¡Página del panel de administración!")
            else:
                print("   ❌ No es la página esperada")
    
    print("\n3️⃣ Probando acceso directo a /ILSAN-ELECTRONICS...")
    material_response = session.get("http://localhost:5000/ILSAN-ELECTRONICS", allow_redirects=False)
    print(f"   Status: {material_response.status_code}")
    print(f"   Headers: {dict(material_response.headers)}")
    
    if material_response.status_code == 200:
        content = material_response.text
        print(f"   📄 Contenido recibido: {len(content)} caracteres")
        
        if "MaterialTemplate" in content or "Configuración de programa" in content:
            print("   ✅ ¡Página MaterialTemplate cargada!")
            
            # Ahora buscar el botón
            if "Panel de Administración" in content:
                print("   ✅ ¡Botón de administración encontrado!")
            else:
                print("   ❌ Botón de administración NO encontrado")
                # Buscar pistas
                if "tiene_permisos_usuarios" in content:
                    print("   🔍 Variable 'tiene_permisos_usuarios' presente")
                else:
                    print("   ❌ Variable 'tiene_permisos_usuarios' ausente")
        else:
            print("   ❌ No es MaterialTemplate")
            if "login" in content.lower():
                print("   📝 Parece ser página de login")
    elif material_response.status_code in [301, 302]:
        print(f"   🔄 Redirigiendo a: {material_response.headers.get('Location')}")

if __name__ == "__main__":
    try:
        test_redirect_behavior()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
