#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🔧 TEST DE SALIDA MATERIAL VIA API - POST CORRECCIÓN FETCH_ONE
===========================================================

Test para verificar que la corrección fetch_one → fetch='one' 
permite ejecutar salidas de material correctamente usando la API.
"""

import requests
import json

def test_salida_via_api():
    """
    Prueba el endpoint de salida de material después de la corrección
    """
    
    print("🔧 TEST DE SALIDA MATERIAL VIA API")
    print("=" * 50)
    
    # URL del endpoint (asumiendo que el servidor está corriendo en localhost:5000)
    url = "http://localhost:5000/api/material/salida"
    
    # Datos de prueba para el material que sabemos que existe
    data = {
        'codigo_material_recibido': '0RH5602C622,202508130004',
        'cantidad_salida': 500.0,  # Cantidad menor para prueba
        'numero_lote': 'LOTE_TEST_API',
        'modelo': 'MODELO_TEST_API',
        'depto_salida': 'PRUEBAS_API',
        'proceso_salida': 'AUTO',  # Usar AUTO para activar lógica automática
        'fecha_salida': '2025-08-13',
        'especificacion_material': ''
    }
    
    print(f"📊 DATOS DE PRUEBA:")
    print(f"   - Material: {data['codigo_material_recibido']}")
    print(f"   - Cantidad: {data['cantidad_salida']}")
    print(f"   - Proceso: {data['proceso_salida']} (AUTO)")
    print(f"   - URL: {url}")
    
    try:
        print(f"\n🌐 ENVIANDO REQUEST POST...")
        
        # Headers
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        # Hacer el request
        response = requests.post(url, json=data, headers=headers, timeout=30)
        
        print(f"📡 RESPONSE RECIBIDA:")
        print(f"   - Status Code: {response.status_code}")
        print(f"   - Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            try:
                resultado = response.json()
                print(f"✅ RESPUESTA JSON:")
                print(f"   - Success: {resultado.get('success', False)}")
                print(f"   - Proceso destino: {resultado.get('proceso_destino', 'N/A')}")
                print(f"   - Especificación usada: {resultado.get('especificacion_usada', 'N/A')}")
                print(f"   - Mensaje: {resultado.get('message', 'N/A')}")
                
                if resultado.get('success'):
                    print("🎯 SALIDA EXITOSA - ERROR fetch_one SOLUCIONADO")
                    
                    # Verificar que el proceso sea SMD
                    if resultado.get('proceso_destino') == 'SMD':
                        print("✅ CORRECTO: Material SMD procesado correctamente")
                    else:
                        print(f"⚠️  PROCESO: {resultado.get('proceso_destino')}")
                else:
                    print(f"❌ ERROR EN SALIDA: {resultado.get('error', 'Error desconocido')}")
                    
            except json.JSONDecodeError:
                print(f"❌ ERROR: Response no es JSON válido")
                print(f"   Response text: {response.text}")
                
        else:
            print(f"❌ ERROR HTTP: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ ERROR: No se puede conectar al servidor")
        print("   ℹ️  Asegúrate de que el servidor Flask esté corriendo en localhost:5000")
        print("   ℹ️  Ejecuta: python application.py")
        
    except requests.exceptions.Timeout:
        print("❌ ERROR: Timeout en la request")
        
    except Exception as e:
        print(f"❌ ERROR INESPERADO: {str(e)}")
        
    print("\n" + "=" * 50)
    print("🔧 FIN DEL TEST")

if __name__ == "__main__":
    test_salida_via_api()
