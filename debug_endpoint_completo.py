#!/usr/bin/env python3
"""
Script para verificar el problema del código recibido
"""

import requests
import json

def debug_endpoint_completo():
    """Debug completo del endpoint y la respuesta"""
    
    print("=== DEBUG COMPLETO DEL ENDPOINT ===")
    
    # Usar el código que se ve en la imagen
    codigo_material = "1E1621020519206225110301102000008"
    
    try:
        url = f"http://localhost:5000/obtener_siguiente_secuencial?codigo_material={codigo_material}"
        print(f"\n1. URL COMPLETA:")
        print(f"   {url}")
        
        response = requests.get(url)
        print(f"\n2. RESPUESTA HTTP:")
        print(f"   Status: {response.status_code}")
        print(f"   Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n3. DATOS JSON COMPLETOS:")
            print(json.dumps(data, indent=2))
            
            print(f"\n4. ANÁLISIS ESPECÍFICO:")
            proximo_codigo = data.get('proximo_codigo_completo', '')
            print(f"   proximo_codigo_completo: '{proximo_codigo}'")
            print(f"   Longitud: {len(proximo_codigo)}")
            
            if proximo_codigo:
                partes = proximo_codigo.split(',')
                print(f"   Partes separadas por coma:")
                for i, parte in enumerate(partes):
                    print(f"     Parte {i+1}: '{parte}' (longitud: {len(parte)})")
                    
            # Verificar si la respuesta contiene lo esperado
            numero_parte_esperado = "0CE106AH638"
            print(f"\n5. VERIFICACIÓN:")
            if numero_parte_esperado in proximo_codigo:
                print(f"   ✅ Contiene número de parte esperado: {numero_parte_esperado}")
            else:
                print(f"   ❌ NO contiene número de parte esperado: {numero_parte_esperado}")
                
            if codigo_material in proximo_codigo:
                print(f"   ❌ Aún contiene código de material: {codigo_material}")
            else:
                print(f"   ✅ NO contiene código de material: {codigo_material}")
                
        else:
            print(f"   Error: {response.text}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_endpoint_completo()
