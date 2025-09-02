#!/usr/bin/env python3
"""
Script de prueba para el API de historial de cambio de material
"""

import requests
import json

def test_historial_api():
    """Prueba el API de historial de cambio de material"""
    
    # URL base
    base_url = "http://127.0.0.1:5000"
    
    # Crear sesión para mantener cookies
    session = requests.Session()
    
    print("🔐 Iniciando sesión...")
    
    # Datos de login (usa credenciales válidas de tu sistema)
    login_data = {
        'username': '1111',   # Usuario Sr. Kim
        'password': '1111'    # Contraseña correcta
    }
    
    # Hacer login
    login_response = session.post(f"{base_url}/login", data=login_data)
    
    if login_response.status_code == 200 and ("dashboard" in login_response.url or "ILSAN-ELECTRONICS" in login_response.url):
        print("✅ Login exitoso")
        
        # Probar el API endpoint
        print("\n📊 Probando API de historial...")
        
        api_url = f"{base_url}/api/historial-cambio-material-maquina"
        
        # Parámetros de prueba
        params = {
            'equipment': '',
            'slot_no': '',
            'part_name': '',
            'date_from': '2025-08-01',
            'date_to': '2025-09-01'
        }
        
        api_response = session.get(api_url, params=params)
        
        print(f"Status Code: {api_response.status_code}")
        
        if api_response.status_code == 200:
            try:
                data = api_response.json()
                print(f"✅ Respuesta exitosa")
                print(f"📈 Total de registros: {len(data.get('data', []))}")
                
                if data.get('data'):
                    print("\n📋 Primer registro:")
                    print(json.dumps(data['data'][0], indent=2, ensure_ascii=False))
                else:
                    print("⚠️  No hay datos disponibles")
                    
            except json.JSONDecodeError:
                print("❌ Error: Respuesta no es JSON válido")
                print(f"Contenido: {api_response.text[:200]}...")
        else:
            print(f"❌ Error en API: {api_response.status_code}")
            print(f"Contenido: {api_response.text[:200]}...")
            
    else:
        print("❌ Error en login")
        print(f"Status: {login_response.status_code}")
        print(f"URL: {login_response.url}")

if __name__ == "__main__":
    test_historial_api()
