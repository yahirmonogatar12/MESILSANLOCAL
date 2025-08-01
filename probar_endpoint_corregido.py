#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para probar el endpoint /verificar_permisos_usuario corregido
"""

import requests
import json

def probar_endpoint():
    """Probar el endpoint de verificación de permisos"""
    try:
        # URL del endpoint
        url = 'http://localhost:5000/admin/verificar_permisos_usuario'
        
        print("🔍 Probando endpoint /admin/verificar_permisos_usuario...")
        print("=" * 60)
        
        # Hacer la petición
        response = requests.get(url)
        
        print(f"📊 Status Code: {response.status_code}")
        print(f"📋 Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print("\n✅ Respuesta exitosa:")
                print(json.dumps(data, indent=2, ensure_ascii=False))
                
                # Verificar estructura
                if isinstance(data, dict):
                    print(f"\n📈 Estadísticas:")
                    print(f"   - Páginas con permisos: {len(data)}")
                    
                    total_permisos = 0
                    for pagina, secciones in data.items():
                        if isinstance(secciones, dict):
                            for seccion, botones in secciones.items():
                                if isinstance(botones, list):
                                    total_permisos += len(botones)
                    
                    print(f"   - Total de permisos: {total_permisos}")
                    
                    return True
                else:
                    print("⚠️ La respuesta no tiene la estructura esperada")
                    return False
                    
            except json.JSONDecodeError as e:
                print(f"❌ Error decodificando JSON: {e}")
                print(f"Respuesta raw: {response.text}")
                return False
                
        elif response.status_code == 401:
            print("🔐 Usuario no autenticado (esperado si no hay sesión activa)")
            print(f"Respuesta: {response.text}")
            return True  # Es un comportamiento esperado
            
        else:
            print(f"❌ Error en la petición: {response.status_code}")
            print(f"Respuesta: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ No se pudo conectar al servidor. ¿Está ejecutándose Flask?")
        return False
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return False

def probar_endpoint_debug():
    """Probar el endpoint de debug"""
    try:
        # URL del endpoint de debug
        url = 'http://localhost:5000/admin/test_permisos_debug'
        
        print("\n🔍 Probando endpoint /admin/test_permisos_debug...")
        print("=" * 60)
        
        # Hacer la petición
        response = requests.get(url)
        
        print(f"📊 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print("\n✅ Respuesta exitosa del endpoint de debug:")
                print(json.dumps(data, indent=2, ensure_ascii=False))
                return True
            except json.JSONDecodeError as e:
                print(f"❌ Error decodificando JSON: {e}")
                print(f"Respuesta raw: {response.text}")
                return False
        else:
            print(f"❌ Error en la petición: {response.status_code}")
            print(f"Respuesta: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ No se pudo conectar al servidor. ¿Está ejecutándose Flask?")
        return False
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return False

def main():
    print("🚀 Iniciando pruebas de endpoints de permisos...")
    print("=" * 60)
    
    # Probar endpoint principal
    resultado1 = probar_endpoint()
    
    # Probar endpoint de debug
    resultado2 = probar_endpoint_debug()
    
    print("\n📊 RESUMEN DE PRUEBAS:")
    print("=" * 60)
    print(f"   - verificar_permisos_usuario: {'✅ OK' if resultado1 else '❌ FAIL'}")
    print(f"   - test_permisos_debug: {'✅ OK' if resultado2 else '❌ FAIL'}")
    
    if resultado1 and resultado2:
        print("\n🎉 Todos los endpoints funcionan correctamente")
    else:
        print("\n⚠️ Algunos endpoints tienen problemas")
    
    print("\n🔚 Pruebas completadas")

if __name__ == "__main__":
    main()