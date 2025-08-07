#!/usr/bin/env python3
"""
Script de verificación rápida para la consulta de salidas optimizada
"""

import requests
import time
import json

def probar_consulta_optimizada():
    print("🚀 PROBANDO CONSULTA ULTRA-OPTIMIZADA DE SALIDAS")
    print("=" * 60)
    
    base_url = "http://127.0.0.1:5000"
    
    # Casos de prueba para velocidad
    casos_prueba = [
        {
            'nombre': 'Solo fecha de hoy',
            'params': {
                'fecha_desde': '2025-08-07',
                'fecha_hasta': '2025-08-07'
            }
        },
        {
            'nombre': 'Fecha + código específico',
            'params': {
                'fecha_desde': '2025-08-07',
                'fecha_hasta': '2025-08-07',
                'codigo_material': '0RH5602C622'
            }
        },
        {
            'nombre': 'Solo código (sin fecha)',
            'params': {
                'codigo_material': '0RH5602C622'
            }
        },
        {
            'nombre': 'Últimos 3 días',
            'params': {
                'fecha_desde': '2025-08-05',
                'fecha_hasta': '2025-08-07'
            }
        }
    ]
    
    for i, caso in enumerate(casos_prueba, 1):
        print(f"\n{i}. {caso['nombre']}")
        print("-" * 40)
        
        try:
            # Preparar URL
            url = f"{base_url}/consultar_historial_salidas"
            params = caso['params']
            
            # Medir tiempo de inicio
            inicio = time.time()
            
            # Hacer petición
            response = requests.get(url, params=params, timeout=10)
            
            # Medir tiempo final
            fin = time.time()
            tiempo_ms = (fin - inicio) * 1000
            
            if response.status_code == 200:
                try:
                    datos = response.json()
                    if isinstance(datos, list):
                        print(f"✅ {len(datos)} registros en {tiempo_ms:.1f}ms")
                        
                        # Mostrar algunos resultados de ejemplo
                        if datos:
                            ejemplo = datos[0]
                            print(f"   📄 Ejemplo: {ejemplo.get('codigo_material', 'N/A')} | {ejemplo.get('fecha_salida', 'N/A')}")
                        
                        # Evaluar velocidad
                        if tiempo_ms < 100:
                            print("   🚀 ULTRA-RÁPIDO")
                        elif tiempo_ms < 500:
                            print("    RÁPIDO")
                        elif tiempo_ms < 1000:
                            print("    ACEPTABLE")
                        else:
                            print("    LENTO")
                            
                    else:
                        print(f"❌ Respuesta no es array: {datos}")
                        
                except json.JSONDecodeError:
                    print(f"❌ Error JSON en respuesta")
                    
            else:
                print(f"❌ Error HTTP {response.status_code}: {response.text[:100]}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Error de conexión: {e}")
        except Exception as e:
            print(f"❌ Error inesperado: {e}")
    
    print("\n" + "=" * 60)
    print("🏁 Pruebas de velocidad completadas")
    
    # Mostrar recomendaciones
    print("\n💡 RECOMENDACIONES DE OPTIMIZACIÓN:")
    print("✅ Query SQL optimizado con LIMIT 500")
    print("✅ COALESCE para valores nulos")
    print("✅ ORDER BY solo por fecha_salida")
    print("✅ LEFT JOIN eficiente")
    print("✅ Mensajes molestos eliminados")
    print("✅ DISTINCT removido para velocidad")

if __name__ == "__main__":
    probar_consulta_optimizada()
