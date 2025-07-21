#!/usr/bin/env python3
"""
Script final para probar que solo los usuarios con permisos ven el botón
"""

import requests

def test_user_permissions(username, password, expected_button):
    """Test permisos de un usuario específico"""
    
    session = requests.Session()
    
    print(f"🔍 Probando usuario: {username}")
    
    # Login
    login_data = {
        'username': username,
        'password': password
    }
    
    response = session.post("http://localhost:5000/login", data=login_data, allow_redirects=False)
    
    if response.status_code in [302, 301]:
        print(f"   ✅ Login exitoso (redirect: {response.headers.get('Location')})")
    elif response.status_code == 200:
        print("   ✅ Login exitoso (sin redirect)")
    else:
        print(f"   ❌ Login falló: {response.status_code}")
        return
    
    # Probar acceso a MaterialTemplate
    material_response = session.get("http://localhost:5000/ILSAN-ELECTRONICS")
    
    if material_response.status_code == 200:
        content = material_response.text
        
        # Verificar si el botón de administración aparece
        if "Panel de Administración" in content:
            result = "✅ VISIBLE"
        else:
            result = "❌ NO VISIBLE"
            
        expected_str = "✅ ESPERADO" if expected_button else "❌ NO ESPERADO"
        correct = (expected_button and "VISIBLE" in result) or (not expected_button and "NO VISIBLE" in result)
        
        print(f"   Botón Admin: {result} ({expected_str}) {'✅ CORRECTO' if correct else '❌ INCORRECTO'}")
        
        # También verificar la clase admin-only
        if "admin-only" in content:
            print(f"   Clase admin-only: ✅ PRESENTE")
        else:
            print(f"   Clase admin-only: ❌ AUSENTE")
            
    else:
        print(f"   ❌ Error accediendo a MaterialTemplate: {material_response.status_code}")

def main():
    print("🧪 PRUEBA FINAL DE PERMISOS")
    print("=" * 50)
    
    # Usuario admin - DEBE ver el botón
    test_user_permissions("admin", "admin123", expected_button=True)
    print()
    
    # Usuario 1111 (fallback JSON) - NO debe ver el botón
    test_user_permissions("1111", "1111", expected_button=False)
    print()
    
    # Usuario Yahir (que el usuario cambió a operador) - NO debe ver el botón
    test_user_permissions("Yahir", "Yahir123", expected_button=False)
    print()
    
    print("✅ Pruebas completadas")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
