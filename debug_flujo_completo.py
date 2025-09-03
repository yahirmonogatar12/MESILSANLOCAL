#!/usr/bin/env python3
"""
Script para verificar todo el flujo de generación del código recibido
"""

import requests
import json

def test_flujo_completo():
    """Simular el flujo completo del frontend"""
    
    print("=== SIMULACIÓN DEL FLUJO COMPLETO ===")
    
    # Código que aparece en la imagen
    codigo_original = "1E1621020519206225110301102000008"
    
    print(f"\n1. CÓDIGO ORIGINAL ESCANEADO:")
    print(f"   {codigo_original}")
    
    # Paso 1: Obtener información del código (simular lo que hace /obtener_codigos_material)
    try:
        print(f"\n2. CONSULTANDO INFORMACIÓN DEL CÓDIGO...")
        
        response = requests.get(f"http://localhost:5000/obtener_codigos_material")
        
        if response.status_code == 200:
            codigos = response.json()
            
            # Buscar el código específico
            codigo_encontrado = None
            for codigo in codigos:
                if codigo.get('codigo') == codigo_original:
                    codigo_encontrado = codigo
                    break
                    
            if codigo_encontrado:
                print(f"   ✅ Código encontrado en base de datos:")
                print(f"      - Código: {codigo_encontrado.get('codigo', '')}")
                print(f"      - Número de parte: {codigo_encontrado.get('numero_parte', '')}")
                print(f"      - Especificación: {codigo_encontrado.get('especificacion', '')}")
            else:
                print(f"   ❌ Código NO encontrado en base de datos")
                return
                
        else:
            print(f"   ❌ Error al consultar códigos: {response.status_code}")
            return
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return
    
    # Paso 2: Obtener siguiente secuencial
    try:
        print(f"\n3. OBTENIENDO SIGUIENTE SECUENCIAL...")
        
        response = requests.get(f"http://localhost:5000/obtener_siguiente_secuencial?codigo_material={codigo_original}")
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"   ✅ Secuencial obtenido:")
            print(f"      - Código material: {data.get('codigo_material', '')}")
            print(f"      - Número de parte: {data.get('numero_parte', '')}")
            print(f"      - Siguiente secuencial: {data.get('siguiente_secuencial', '')}")
            print(f"      - Próximo código completo: {data.get('proximo_codigo_completo', '')}")
            
            proximo_codigo = data.get('proximo_codigo_completo', '')
            numero_parte = data.get('numero_parte', '')
            
        else:
            print(f"   ❌ Error al obtener secuencial: {response.status_code}")
            return
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return
    
    # Paso 3: Simular lo que debería pasar en el frontend
    print(f"\n4. SIMULACIÓN DEL FRONTEND:")
    print(f"   codigoCompleto.numero_parte: '{numero_parte}'")
    print(f"   proximoCodigoCompleto: '{proximo_codigo}'")
    
    # Lo que debería ir en cada campo
    print(f"\n5. CAMPOS QUE DEBERÍAN LLENARSE:")
    print(f"   Código de material original: {codigo_original}")
    print(f"   Número de parte: {numero_parte}")
    print(f"   Código de material: {numero_parte}")  # Campo "Código de material" debería ser número de parte
    print(f"   Código material recibido: {proximo_codigo}")  # Debería venir del endpoint
    
    # Verificar qué aparece realmente en la imagen vs lo esperado
    print(f"\n6. COMPARACIÓN CON LA IMAGEN:")
    codigo_recibido_imagen = "1E162102051920,202509030001"
    codigo_material_imagen = "1E162102051920"
    numero_parte_imagen = "0CE106AH638"
    
    print(f"   IMAGEN ACTUAL:")
    print(f"      - Código material recibido: {codigo_recibido_imagen}")
    print(f"      - Código de material: {codigo_material_imagen}")
    print(f"      - Número de parte: {numero_parte_imagen}")
    
    print(f"\n   DEBERÍA SER:")
    print(f"      - Código material recibido: {proximo_codigo}")
    print(f"      - Código de material: {numero_parte}")
    print(f"      - Número de parte: {numero_parte}")
    
    print(f"\n7. ANÁLISIS:")
    
    # Análisis del código recibido
    if codigo_recibido_imagen != proximo_codigo:
        print(f"   ❌ PROBLEMA DETECTADO en código recibido:")
        print(f"      Esperado: {proximo_codigo}")
        print(f"      Actual:   {codigo_recibido_imagen}")
        
        # Ver si el código en la imagen parece ser un truncamiento
        if codigo_original.startswith(codigo_material_imagen):
            longitud_truncado = len(codigo_material_imagen)
            print(f"      El código parece estar truncado a {longitud_truncado} caracteres")
            print(f"      '{codigo_original}' → '{codigo_original[:longitud_truncado]}'")
    
    # Análisis del código de material
    if codigo_material_imagen != numero_parte:
        print(f"   ❌ PROBLEMA DETECTADO en código de material:")
        print(f"      Esperado: {numero_parte}")
        print(f"      Actual:   {codigo_material_imagen}")

if __name__ == "__main__":
    test_flujo_completo()
