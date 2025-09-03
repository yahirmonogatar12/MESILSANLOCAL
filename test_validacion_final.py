#!/usr/bin/env python3
"""
Script final para validar que las correcciones funcionen
"""

import requests
import json

def test_flujo_corregido():
    """Probar si las correcciones solucionan el problema"""
    
    print("=== VALIDACIÓN DE CORRECCIONES ===")
    
    codigo_original = "1E1621020519206225110301102000008"
    numero_parte_esperado = "0CE106AH638"
    
    print(f"\n1. CÓDIGO ORIGINAL: {codigo_original}")
    print(f"2. NÚMERO DE PARTE ESPERADO: {numero_parte_esperado}")
    
    # Probar el endpoint nuevamente
    try:
        response = requests.get(f"http://localhost:5000/obtener_siguiente_secuencial?codigo_material={codigo_original}")
        
        if response.status_code == 200:
            data = response.json()
            proximo_codigo = data.get('proximo_codigo_completo', '')
            numero_parte = data.get('numero_parte', '')
            
            print(f"\n3. RESPUESTA DEL ENDPOINT:")
            print(f"   ✅ Próximo código completo: {proximo_codigo}")
            print(f"   ✅ Número de parte: {numero_parte}")
            
            # Verificar que sea correcto
            if numero_parte == numero_parte_esperado:
                print(f"\n4. VERIFICACIÓN:")
                print(f"   ✅ El endpoint devuelve el número de parte correcto")
                
                if proximo_codigo == f"{numero_parte_esperado},202509030001":
                    print(f"   ✅ El código completo tiene el formato correcto")
                    
                    print(f"\n5. RESULTADO ESPERADO EN EL FRONTEND:")
                    print(f"   Campo 'Código de material recibido': {proximo_codigo}")
                    print(f"   Campo 'Código de material': {numero_parte}")
                    print(f"   Campo 'Número de parte': {numero_parte}")
                    
                    print(f"\n🎉 CORRECCIONES VALIDADAS:")
                    print(f"   - El backend devuelve el número de parte correcto")
                    print(f"   - El código recibido usa el número de parte")
                    print(f"   - El formato es: [NUMERO_PARTE],[FECHA][SECUENCIAL]")
                    
                    print(f"\n📋 PASOS PARA VERIFICAR EN EL FRONTEND:")
                    print(f"   1. Abrir la página en el navegador")
                    print(f"   2. Escanear o escribir: {codigo_original}")
                    print(f"   3. Verificar que los campos se llenen con:")
                    print(f"      - Código material recibido: {proximo_codigo}")
                    print(f"      - Código de material: {numero_parte}")
                    print(f"      - Número de parte: {numero_parte}")
                    
                else:
                    print(f"   ❌ El código completo no tiene el formato esperado")
            else:
                print(f"   ❌ El número de parte no coincide")
                
        else:
            print(f"   ❌ Error en endpoint: {response.status_code}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_flujo_corregido()
