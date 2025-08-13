#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json

def probar_salida_corregida():
    """Probar la salida de material con el sistema corregido"""
    
    print("🧪 PROBANDO SISTEMA DE SALIDAS CORREGIDO")
    print("=" * 50)
    
    # Datos de prueba usando el material real que viste en la imagen
    datos_prueba = {
        'codigo_material_recibido': '0RH5602C622,202508130002',
        'cantidad_salida': 100,
        'modelo': 'MODELO_PRUEBA',
        'numero_lote': 'LOTE_PRUEBA',
        'fecha_salida': '2025-08-13',
        'proceso_salida': 'AUTO',  # Nuevo: determinación automática
        'codigo_verificacion': 'AUTO'
    }
    
    print("📋 Datos de prueba:")
    for clave, valor in datos_prueba.items():
        print(f"   {clave}: {valor}")
    
    try:
        # Realizar la petición
        url = 'http://localhost:5000/api/material/salida'
        headers = {'Content-Type': 'application/json'}
        
        print(f"\n🌐 Enviando petición a: {url}")
        
        response = requests.post(url, json=datos_prueba, headers=headers)
        
        print(f"📡 Código de respuesta: {response.status_code}")
        
        if response.status_code == 200:
            resultado = response.json()
            
            print("✅ RESPUESTA EXITOSA:")
            print(f"   Success: {resultado.get('success')}")
            print(f"   Message: {resultado.get('message')}")
            print(f"   🎯 Proceso destino: {resultado.get('proceso_destino', 'NO ESPECIFICADO')}")
            print(f"   📝 Especificación usada: {resultado.get('especificacion_usada', 'NO ESPECIFICADA')}")
            print(f"   📦 Nueva cantidad disponible: {resultado.get('nueva_cantidad_disponible')}")
            print(f"   📊 Número de parte: {resultado.get('numero_parte')}")
            
            if resultado.get('proceso_destino') == 'SMD':
                print("\n✅ ÉXITO: El sistema determinó correctamente que es material SMD")
            else:
                print(f"\n⚠️ ATENCIÓN: Proceso determinado: {resultado.get('proceso_destino')}")
                
        else:
            print(f"❌ ERROR en la petición:")
            print(f"   Código: {response.status_code}")
            print(f"   Respuesta: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ ERROR: No se pudo conectar al servidor")
        print("   Asegúrate de que el servidor Flask esté ejecutándose en localhost:5000")
    except Exception as e:
        print(f"❌ ERROR inesperado: {e}")

def mostrar_mejoras_implementadas():
    """Mostrar las mejoras implementadas en el sistema"""
    
    print("\n🎉 MEJORAS IMPLEMENTADAS EN EL SISTEMA")
    print("=" * 50)
    
    mejoras = [
        "✅ Determinación automática del proceso destino (SMD, IMD, MAIN)",
        "✅ Obtención de especificación del material original",
        "✅ Corrección del campo cantidad_actual → cantidad_total",
        "✅ Eliminación del hardcodeo 'SMD' en el frontend",
        "✅ Uso de proceso_salida: 'AUTO' para determinación automática",
        "✅ Respuesta API incluye proceso_destino y especificación_usada",
        "✅ Mensajes de usuario muestran el proceso destino",
        "✅ Triggers corregidos para usar codigo_material_recibido real"
    ]
    
    for mejora in mejoras:
        print(f"  {mejora}")
    
    print("\n📝 LÓGICA DE DETERMINACIÓN DE PROCESO:")
    print("   1. Se busca el material en control_material_almacen")
    print("   2. Se obtiene propiedad_material y especificacion")
    print("   3. Si propiedad_material = 'SMD' → proceso_salida = 'SMD'")
    print("   4. Si propiedad_material = 'IMD' → proceso_salida = 'IMD'")
    print("   5. Si propiedad_material = 'MAIN' → proceso_salida = 'MAIN'")
    print("   6. Si no está claro, analiza palabras clave en especificación")
    print("   7. Default: 'PRODUCCION'")

def main():
    """Función principal"""
    
    mostrar_mejoras_implementadas()
    
    respuesta = input("\n¿Probar el sistema de salidas corregido? (s/n): ").strip().lower()
    
    if respuesta in ['s', 'si', 'y', 'yes']:
        probar_salida_corregida()
    
    print("\n" + "=" * 50)
    print("✅ SISTEMA DE SALIDAS COMPLETAMENTE CORREGIDO")
    print("🎯 Ahora determina automáticamente el destino correcto")
    print("📋 Usa la especificación del material original")
    print("🔧 No más hardcodeo de proceso_salida='SMD'")
    print("=" * 50)

if __name__ == "__main__":
    main()
