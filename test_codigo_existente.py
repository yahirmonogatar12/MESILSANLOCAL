#!/usr/bin/env python3
"""
Script para probar el endpoint con un código que existe en la tabla
"""

import requests
import json

def test_endpoint_codigo_existente():
    """Probar el endpoint con código de material que existe en la tabla"""
    
    print("=== PRUEBA CON CÓDIGO EXISTENTE ===")
    
    # Usar el código que encontramos en la tabla
    codigo_material = "1E1621020519206225110301102000008"
    
    try:
        # Hacer solicitud al endpoint
        url = f"http://localhost:5000/obtener_siguiente_secuencial?codigo_material={codigo_material}"
        print(f"\n1. ENVIANDO SOLICITUD:")
        print(f"   URL: {url}")
        
        response = requests.get(url)
        
        print(f"\n2. RESPUESTA:")
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Success: {data.get('success', False)}")
            
            print(f"\n3. DATOS RETORNADOS:")
            print(f"   Código material:      {data.get('codigo_material', '')}")
            print(f"   Número de parte:      {data.get('numero_parte', '')}")
            print(f"   Siguiente secuencial: {data.get('siguiente_secuencial', '')}")
            print(f"   Próximo código:       {data.get('proximo_codigo_completo', '')}")
            
            # Verificar que ahora use el número de parte correcto
            numero_parte_esperado = "0CE106AH638"
            proximo_codigo = data.get('proximo_codigo_completo', '')
            
            print(f"\n4. VALIDACIÓN:")
            if numero_parte_esperado in proximo_codigo:
                print(f"   ✅ El próximo código contiene el número de parte correcto: '{numero_parte_esperado}'")
            else:
                print(f"   ❌ El próximo código NO contiene el número de parte esperado: '{numero_parte_esperado}'")
                print(f"      Código generado: '{proximo_codigo}'")
                
            if codigo_material not in proximo_codigo:
                print(f"   ✅ El próximo código ya NO contiene el código de material: '{codigo_material}'")
            else:
                print(f"   ❌ El próximo código aún contiene el código de material: '{codigo_material}'")
                
        else:
            print(f"   Error: {response.text}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_endpoint_codigo_existente()
