#!/usr/bin/env python3
"""
Script para probar que el endpoint de permisos no causa bucles o problemas
"""

import requests
import time

def test_endpoint_permisos():
    """Probar el endpoint de permisos"""
    url = "http://localhost:5000/admin/verificar_permisos_usuario"
    
    print("🔍 Probando endpoint de permisos...")
    
    try:
        # Probar múltiples requests para ver si hay problemas
        for i in range(3):
            print(f"   📡 Request {i+1}/3...")
            start_time = time.time()
            
            response = requests.get(url, timeout=10)
            
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"      Status: {response.status_code}")
            print(f"      Tiempo: {duration:.2f}s")
            
            if response.status_code == 401:
                print("      ✅ Requiere autenticación (esperado)")
            elif response.status_code == 200:
                print("      ✅ Respuesta exitosa")
                try:
                    data = response.json()
                    print(f"      📊 Datos: {len(data)} páginas de permisos")
                except:
                    print("      ⚠️ Respuesta no es JSON válido")
            else:
                print(f"      ❌ Estado inesperado: {response.status_code}")
            
            time.sleep(1)  # Esperar 1 segundo entre requests
            
    except requests.exceptions.Timeout:
        print("❌ Timeout - El servidor no responde en 10 segundos")
    except requests.exceptions.ConnectionError:
        print("❌ Error de conexión - ¿Está el servidor ejecutándose?")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")

def test_login_page():
    """Probar que la página de login se carga"""
    url = "http://localhost:5000/"
    
    print("\n🏠 Probando página principal...")
    
    try:
        response = requests.get(url, timeout=10)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            print("   ✅ Página principal carga correctamente")
        else:
            print(f"   ⚠️ Redirección o error: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    test_login_page()
    test_endpoint_permisos()
    
    print("\n📋 Si el servidor responde lentamente o se cuelga:")
    print("1. El problema puede estar en el JavaScript MutationObserver")
    print("2. Revisa la consola del navegador para errores JavaScript")
    print("3. Prueba deshabilitando temporalmente el sistema de permisos")
    print("4. Verifica que no haya bucles infinitos en los event listeners")
