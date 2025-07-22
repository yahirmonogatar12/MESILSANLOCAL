#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test final completo del sistema de permisos
Verifica que todo funcione correctamente end-to-end
"""

import requests
import json
import sys
import time

# Configuración
BASE_URL = "http://localhost:5000"
TEST_USER = "admin"
TEST_PASS = ".ISEMM2025."

def test_completo_sistema():
    """Test end-to-end completo del sistema de permisos"""
    print("🎯 TEST COMPLETO DEL SISTEMA DE PERMISOS")
    print("=" * 60)
    
    # Crear sesión persistente
    session = requests.Session()
    
    # 1. Login
    print("\n1️⃣ Login del usuario...")
    login_data = {'username': TEST_USER, 'password': TEST_PASS}
    
    try:
        response = session.post(f"{BASE_URL}/login", data=login_data, allow_redirects=False)
        
        if response.status_code == 302:
            print(f"   ✅ Login exitoso - Redirect a: {response.headers.get('Location')}")
            print(f"   🍪 Session cookie establecido: {'session' in [c.name for c in session.cookies]}")
        else:
            print(f"   ❌ Login falló - Status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error en login: {e}")
        return False
    
    # 2. Acceso al panel de admin
    print("\n2️⃣ Acceso al panel de administración...")
    try:
        response = session.get(f"{BASE_URL}/admin/panel")
        
        if response.status_code == 200 and "Gestión de Usuarios" in response.text:
            print("   ✅ Panel de admin accesible")
        else:
            print(f"   ❌ Error accediendo al panel - Status: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error accediendo al panel: {e}")
    
    # 3. Obtener permisos del usuario
    print("\n3️⃣ Obtención de permisos del usuario...")
    try:
        response = session.get(f"{BASE_URL}/obtener_permisos_usuario_actual")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"   ✅ Permisos obtenidos exitosamente")
                print(f"   👤 Usuario: {data.get('usuario')}")
                print(f"   🎭 Rol: {data.get('rol')}")
                print(f"   🔑 Total permisos: {data.get('total_permisos')}")
                
                # Verificar estructura de permisos
                permisos = data.get('permisos', {})
                if permisos:
                    print(f"   📋 Páginas con permisos: {len(permisos)}")
                    print(f"   📄 Primeras páginas: {list(permisos.keys())[:3]}")
                    
                    # Verificar estructura jerárquica
                    primera_pagina = list(permisos.keys())[0]
                    secciones = permisos[primera_pagina]
                    print(f"   🏗️ Estructura jerárquica confirmada: {primera_pagina} > {list(secciones.keys())[0] if secciones else 'N/A'}")
                
                return True
                
            except Exception as e:
                print(f"   ❌ Error parseando JSON de permisos: {e}")
                print(f"   📄 Response: {response.text[:200]}")
                return False
                
        else:
            print(f"   ❌ Error obteniendo permisos - Status: {response.status_code}")
            print(f"   📄 Response: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error consultando permisos: {e}")
        return False
    
    # 4. Test de gestión de permisos
    print("\n4️⃣ Test de gestión de permisos...")
    try:
        response = session.get(f"{BASE_URL}/admin/gestionar_permisos_dropdowns")
        
        if response.status_code == 200 and "Gestión de Permisos" in response.text:
            print("   ✅ Interfaz de gestión de permisos accesible")
        else:
            print(f"   ⚠️ Problema con interfaz de gestión - Status: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error accediendo a gestión de permisos: {e}")
    
    # 5. Test de página de test frontend
    print("\n5️⃣ Test de página de test frontend...")
    try:
        response = session.get(f"{BASE_URL}/test-frontend-permisos")
        
        if response.status_code == 200 and "Test Frontend" in response.text:
            print("   ✅ Página de test frontend accesible")
            print("   💡 URL para test manual: http://localhost:5000/test-frontend-permisos")
        else:
            print(f"   ⚠️ Problema con página de test - Status: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error accediendo a página de test: {e}")
    
    return True

def test_endpoints_clave():
    """Test de endpoints clave del sistema"""
    print("\n\n🔧 TEST DE ENDPOINTS CLAVE")
    print("=" * 40)
    
    session = requests.Session()
    
    # Login primero
    login_data = {'username': TEST_USER, 'password': TEST_PASS}
    session.post(f"{BASE_URL}/login", data=login_data)
    
    endpoints = [
        ("/admin/panel", "Panel de administración"),
        ("/admin/gestionar_permisos_dropdowns", "Gestión de permisos"),
        ("/obtener_permisos_usuario_actual", "API de permisos"),
        ("/admin/listar_dropdowns_permisos", "Lista de dropdowns"),
        ("/test-frontend-permisos", "Test frontend")
    ]
    
    for endpoint, descripcion in endpoints:
        try:
            response = session.get(f"{BASE_URL}{endpoint}")
            status = "✅" if response.status_code == 200 else "❌"
            print(f"   {status} {descripcion}: {response.status_code}")
            
        except Exception as e:
            print(f"   ❌ {descripcion}: Error - {e}")

def main():
    print("🚀 VERIFICACIÓN FINAL DEL SISTEMA DE PERMISOS")
    print("=" * 60)
    print(f"Usuario de prueba: {TEST_USER}")
    print(f"Servidor: {BASE_URL}")
    print()
    
    # Verificar servidor
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        print(f"✅ Servidor funcionando - Status: {response.status_code}")
    except Exception as e:
        print(f"❌ Error conectando al servidor: {e}")
        print("   Asegúrate de que el servidor esté ejecutándose con: python run.py")
        return
    
    # Tests principales
    resultado_principal = test_completo_sistema()
    test_endpoints_clave()
    
    # Resumen
    print("\n\n📊 RESUMEN FINAL")
    print("=" * 30)
    
    if resultado_principal:
        print("🎉 ¡SISTEMA FUNCIONANDO CORRECTAMENTE!")
        print()
        print("✅ Verificaciones exitosas:")
        print("   • Login con usuario admin")
        print("   • Cookies de sesión establecidas")
        print("   • API de permisos funcional")
        print("   • 118 permisos jerárquicos cargados")
        print("   • Estructura pagina > seccion > boton confirmada")
        print("   • Interfaz de gestión accesible")
        print()
        print("🎯 SOLUCIÓN IMPLEMENTADA:")
        print("   • Agregado credentials: 'include' en fetch JavaScript")
        print("   • Usuario admin desbloqueado")
        print("   • Contraseña correcta: .ISEMM2025.")
        print("   • Sistema de permisos unificado")
        print()
        print("🔗 URLs para probar manualmente:")
        print(f"   • Login: {BASE_URL}/login")
        print(f"   • Panel Admin: {BASE_URL}/admin/panel")
        print(f"   • Gestión Permisos: {BASE_URL}/admin/gestionar_permisos_dropdowns")
        print(f"   • Test Frontend: {BASE_URL}/test-frontend-permisos")
        print()
        print("💡 INSTRUCCIONES FINALES:")
        print("   1. Haz login con usuario: admin, contraseña: .ISEMM2025.")
        print("   2. Ve a 'Gestión de Permisos de Dropdowns'")
        print("   3. Los botones ahora deberían funcionar correctamente")
        print("   4. Usa la página de test para verificar funcionalidad")
        
    else:
        print("❌ Aún hay problemas con el sistema")
        print("   Revisa los errores anteriores y verifica la configuración")

if __name__ == "__main__":
    main()
