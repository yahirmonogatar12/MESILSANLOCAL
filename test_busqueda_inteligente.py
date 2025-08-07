#!/usr/bin/env python3
"""
Script de prueba para la funcionalidad de búsqueda inteligente de materiales
Prueba diferentes escenarios de búsqueda parcial
"""

import requests
import json

def probar_busqueda_inteligente():
    base_url = "http://127.0.0.1:5000"
    
    print("🧪 PROBANDO BÚSQUEDA INTELIGENTE DE MATERIALES")
    print("=" * 60)
    
    # Casos de prueba
    casos_prueba = [
        "",  # Sin búsqueda (todos los materiales)
        "0RH5602C622",  # Búsqueda exacta del ejemplo
        "5602",  # Parte del medio
        "622",  # Parte del final  
        "0RH",  # Parte del inicio
        "M260",  # Otro código diferente
        "68F",  # Búsqueda en especificación
        "1608",  # Otra especificación
        "xyz123"  # Búsqueda que no debería encontrar nada
    ]
    
    for i, busqueda in enumerate(casos_prueba, 1):
        print(f"\n{i}. Probando búsqueda: '{busqueda}'")
        print("-" * 40)
        
        try:
            if busqueda:
                url = f"{base_url}/obtener_codigos_material?busqueda={busqueda}"
            else:
                url = f"{base_url}/obtener_codigos_material"
                
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                resultados = response.json()
                print(f"✅ Encontrados {len(resultados)} resultados")
                
                # Mostrar primeros 3 resultados
                for j, material in enumerate(resultados[:3]):
                    codigo = material.get('codigo', 'N/A')
                    nombre = material.get('nombre', 'N/A')
                    spec = material.get('spec', 'N/A')
                    coincidencia = material.get('coincidencia', False)
                    
                    marca = "🎯" if coincidencia else "📄"
                    print(f"  {marca} {codigo} | {nombre} | {spec}")
                
                if len(resultados) > 3:
                    print(f"  ... y {len(resultados) - 3} más")
                    
                # Verificar si encontró el código específico de ejemplo
                if busqueda == "0RH5602C622":
                    encontrado = any(busqueda in material.get('codigo', '') for material in resultados)
                    if encontrado:
                        print("  ✅ ¡Código de ejemplo encontrado correctamente!")
                    else:
                        print("  ⚠️ Código de ejemplo no encontrado")
                        
            else:
                print(f"❌ Error HTTP {response.status_code}: {response.text}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Error de conexión: {e}")
        except Exception as e:
            print(f"❌ Error inesperado: {e}")
    
    print("\n" + "=" * 60)
    print("🎉 Pruebas de búsqueda inteligente completadas")

if __name__ == "__main__":
    probar_busqueda_inteligente()
