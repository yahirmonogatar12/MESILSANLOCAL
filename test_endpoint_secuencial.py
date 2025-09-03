#!/usr/bin/env python3
"""
Script para probar directamente el endpoint de obtener_siguiente_secuencial
con los cambios de número de parte
"""

import requests
import json

def test_endpoint_secuencial():
    """Probar el endpoint modificado"""
    
    print("=== PRUEBA DEL ENDPOINT obtener_siguiente_secuencial ===")
    
    # Usar un código de material conocido
    codigo_material = "1E162102051920622511030110200"  # Del ejemplo en la imagen
    
    print(f"\n1. ENVIANDO SOLICITUD AL ENDPOINT...")
    print(f"   Código de material: {codigo_material}")
    
    try:
        # Hacer la solicitud al endpoint
        url = f"http://localhost:5000/obtener_siguiente_secuencial?codigo_material={codigo_material}"
        
        print(f"   URL: {url}")
        
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"\n2. RESPUESTA DEL SERVIDOR:")
            print(f"   Status: {response.status_code}")
            print(f"   Success: {data.get('success')}")
            
            if data.get('success'):
                print(f"\n3. DATOS RETORNADOS:")
                print(f"   Código material:      {data.get('codigo_material')}")
                print(f"   Número de parte:      {data.get('numero_parte')}")
                print(f"   Siguiente secuencial: {data.get('siguiente_secuencial')}")
                print(f"   Próximo código:       {data.get('proximo_codigo_completo')}")
                
                # Verificar si el próximo código contiene el número de parte
                proximo_codigo = data.get('proximo_codigo_completo', '')
                numero_parte = data.get('numero_parte', '')
                codigo_material_usado = data.get('codigo_material', '')
                
                print(f"\n4. VALIDACIÓN:")
                
                if numero_parte and numero_parte in proximo_codigo:
                    print(f"   ✅ El próximo código contiene el número de parte: '{numero_parte}'")
                    
                    if codigo_material_usado not in proximo_codigo:
                        print(f"   ✅ El próximo código NO contiene el código de material: '{codigo_material_usado}'")
                        print(f"   🎉 CORRECCIÓN EXITOSA: Se usa número de parte en lugar de código de material")
                    else:
                        print(f"   ❌ El próximo código aún contiene el código de material: '{codigo_material_usado}'")
                        
                elif codigo_material_usado and codigo_material_usado in proximo_codigo:
                    print(f"   ❌ El próximo código aún usa el código de material: '{codigo_material_usado}'")
                    if numero_parte:
                        print(f"   ❌ Debería usar el número de parte: '{numero_parte}'")
                    else:
                        print(f"   ⚠️ No se encontró número de parte para este código")
                else:
                    print(f"   ⚠️ Resultado inesperado en el próximo código: '{proximo_codigo}'")
                    
            else:
                print(f"   ❌ Error en la respuesta: {data.get('error')}")
                
        else:
            print(f"\n   ❌ Error HTTP: {response.status_code}")
            print(f"   Respuesta: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print(f"\n   ❌ Error: No se pudo conectar al servidor en localhost:5000")
        print(f"   💡 Asegúrate de que el servidor Flask esté ejecutándose con 'python run.py'")
        
    except Exception as e:
        print(f"\n   ❌ Error inesperado: {e}")

if __name__ == "__main__":
    test_endpoint_secuencial()
