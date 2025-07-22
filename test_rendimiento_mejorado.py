#!/usr/bin/env python3
"""
Script para verificar que el problema de rendimiento se ha solucionado
"""

import requests
import time

def test_performance_mejorado():
    """Probar que la página ya no se atore"""
    print("🔧 Probando rendimiento mejorado del sistema...")
    print("=" * 50)
    
    endpoints = [
        ("Página principal", "http://localhost:5000/"),
        ("Debug permisos", "http://localhost:5000/admin/test_permisos_debug"),
        ("Endpoint permisos", "http://localhost:5000/admin/verificar_permisos_usuario")
    ]
    
    for nombre, url in endpoints:
        print(f"\n📡 Probando: {nombre}")
        
        try:
            start_time = time.time()
            response = requests.get(url, timeout=5)
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"   Status: {response.status_code}")
            print(f"   Tiempo: {duration:.2f}s")
            
            if duration < 2.0:
                print("   ✅ Rendimiento bueno (< 2s)")
            elif duration < 5.0:
                print("   ⚠️ Rendimiento aceptable (< 5s)")
            else:
                print("   ❌ Rendimiento lento (> 5s)")
                
            # Verificar si retorna JSON para endpoints de API
            if "admin" in url:
                try:
                    data = response.json()
                    print(f"   ✅ JSON válido: {type(data)}")
                    if isinstance(data, dict) and 'permisos' in data:
                        print(f"   📊 Permisos encontrados: {len(data.get('permisos', []))}")
                except:
                    if response.status_code == 401:
                        print("   ℹ️ Requiere autenticación (esperado)")
                    else:
                        print("   ⚠️ Respuesta no es JSON")
                        
        except requests.exceptions.Timeout:
            print("   ❌ TIMEOUT - Servidor no responde en 5s")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print("\n" + "=" * 50)
    print("📋 Diagnóstico:")
    print("✅ Si todos los tiempos son < 2s: Problema resuelto")
    print("⚠️ Si hay timeouts: Revisar bucles infinitos en JavaScript")
    print("💡 Si funciona: Probar en navegador web")
    
    print(f"\n🌐 URLs para probar en navegador:")
    print(f"   Página principal: http://localhost:5000/")
    print(f"   Login: http://localhost:5000/login")
    print(f"   Debug permisos: http://localhost:5000/admin/test_permisos_debug")

if __name__ == "__main__":
    test_performance_mejorado()
