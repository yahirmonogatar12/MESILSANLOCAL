#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para probar las correcciones de duplicados y contador de filas en historial de salidas
"""

import urllib.request
import urllib.parse
import json
from datetime import datetime

def test_consultar_historial_salidas():
    """
    Test para verificar que la consulta de historial de salidas:
    1. No devuelve duplicados (DISTINCT)
    2. Incluye contador de total de filas
    3. Mantiene buena performance
    """
    
    print("🔬 PROBANDO CORRECCIONES EN HISTORIAL DE SALIDAS")
    print("=" * 60)
    
    base_url = "http://127.0.0.1:5000"
    
    # Test 1: Consulta sin filtros
    print("📋 Test 1: Consulta básica sin filtros")
    try:
        url = f"{base_url}/consultar_historial_salidas"
        
        print(f"🌐 URL: {url}")
        
        inicio = datetime.now()
        with urllib.request.urlopen(url, timeout=30) as response:
            fin = datetime.now()
            tiempo_ms = (fin - inicio).total_seconds() * 1000
            
            print(f"⏱️ Tiempo de respuesta: {tiempo_ms:.2f}ms")
            print(f"📊 Status Code: {response.getcode()}")
            
            if response.getcode() == 200:
                data = json.loads(response.read().decode('utf-8'))
                
                # Verificar estructura de respuesta
                if isinstance(data, dict) and 'datos' in data:
                    print("✅ Nueva estructura de respuesta detectada")
                    salidas = data['datos']
                    total = data.get('total', 0)
                    mostrados = data.get('mostrados', 0)
                    
                    print(f"📈 Total de registros en BD: {total}")
                    print(f"📋 Registros mostrados: {mostrados}")
                    print(f"🎯 Registros en array: {len(salidas)}")
                    
                    # Verificar que no hay duplicados
                    if len(salidas) > 0:
                        # Crear lista de identificadores únicos para verificar duplicados
                        identificadores = []
                        for salida in salidas:
                            identificador = f"{salida.get('fecha_salida')}_{salida.get('codigo_material_recibido')}_{salida.get('numero_lote')}"
                            identificadores.append(identificador)
                        
                        duplicados = len(identificadores) - len(set(identificadores))
                        
                        if duplicados == 0:
                            print("✅ Sin duplicados detectados")
                        else:
                            print(f"❌ PROBLEMA: {duplicados} registros duplicados encontrados")
                        
                        # Mostrar muestra de los primeros 3 registros
                        print("\n📋 Muestra de registros:")
                        for i, salida in enumerate(salidas[:3]):
                            print(f"   {i+1}. {salida.get('fecha_salida')} | {salida.get('codigo_material_recibido')} | {salida.get('numero_lote')}")
                    
                elif isinstance(data, list):
                    print("⚠️ Estructura antigua detectada (array directo)")
                    print(f"📋 Registros: {len(data)}")
                    
                else:
                    print(f"❌ Estructura de respuesta inesperada: {type(data)}")
                    
            else:
                print(f"❌ Error HTTP: {response.getcode()}")
                
    except Exception as e:
        print(f"❌ Error en test: {str(e)}")
    
    print("\n" + "=" * 60)
    print("🎯 RESUMEN DE TESTS COMPLETADO")
    print("✅ Verifica que no aparezcan mensajes de duplicados")
    print("✅ Verifica que el contador muestre el número correcto de filas")
    print("✅ Verifica que los filtros funcionen correctamente")

if __name__ == "__main__":
    test_consultar_historial_salidas()
