#!/usr/bin/env python3
"""
Script simple para probar la página directamente
"""

import requests
import re

# Session para mantener cookies
session = requests.Session()

def test_login_and_check_button():
    """Test completo de login y verificación del botón"""
    
    print("🔍 Probando login y botón de administración...")
    
    # Primero obtener la página de login para cualquier CSRF o tokens
    login_page = session.get("http://localhost:5000/login")
    print(f"✅ Página de login obtenida: {login_page.status_code}")
    
    # Hacer login
    login_data = {
        'usuario': 'admin',
        'password': 'admin123'
    }
    
    response = session.post("http://localhost:5000/login", data=login_data, allow_redirects=False)
    print(f"📤 Login response status: {response.status_code}")
    print(f"📤 Login response headers: {dict(response.headers)}")
    
    # Si hay redirección, seguirla manualmente
    if response.status_code in [302, 301]:
        redirect_url = response.headers.get('Location')
        print(f"🔄 Redirigiendo a: {redirect_url}")
        
        if redirect_url:
            # Manejar URLs relativas
            if redirect_url.startswith('/'):
                redirect_url = "http://localhost:5000" + redirect_url
            
            response = session.get(redirect_url)
            print(f"✅ Página después de login: {response.status_code}")
        else:
            print("❌ No se encontró URL de redirección")
            return
    
    # Ahora obtener la página principal
    main_page = session.get("http://localhost:5000/ILSAN-ELECTRONICS")
    print(f"📄 Página principal obtenida: {main_page.status_code}")
    
    if main_page.status_code == 200:
        content = main_page.text
        
        # Buscar el botón de administración
        if "Panel de Administración" in content:
            print("✅ ¡BOTÓN DE ADMINISTRACIÓN ENCONTRADO!")
            
            # Buscar también la clase admin-only
            if "admin-only" in content:
                print("✅ Clase admin-only también encontrada")
            else:
                print("⚠️ Clase admin-only NO encontrada (extraño)")
                
        else:
            print("❌ Botón de administración NO encontrado")
            
            # Buscar pistas en el HTML
            if "tiene_permisos_usuarios" in content:
                print("🔍 La variable tiene_permisos_usuarios está en el HTML")
            else:
                print("❌ La variable tiene_permisos_usuarios NO está en el HTML")
            
            # Buscar si hay algún bloque condicional
            if_blocks = re.findall(r'{%\s*if\s+[^%]+\s*%}', content)
            print(f"🔍 Bloques condicionales encontrados: {len(if_blocks)}")
            for block in if_blocks[:3]:  # Mostrar solo los primeros 3
                print(f"   - {block}")
        
        # Verificar si el usuario está logueado correctamente
        if "usuario" in content.lower() or "admin" in content.lower():
            print("✅ Usuario parece estar logueado")
        else:
            print("❌ No se detecta usuario logueado")
            
    else:
        print(f"❌ Error al obtener página principal: {main_page.status_code}")
        print(f"❌ Contenido: {main_page.text[:200]}")

if __name__ == "__main__":
    try:
        test_login_and_check_button()
    except Exception as e:
        print(f"❌ Error durante la prueba: {e}")
        import traceback
        traceback.print_exc()
