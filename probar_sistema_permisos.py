#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para probar el sistema completo de permisos de dropdowns
"""

import requests
import json
import time

def probar_sistema_permisos():
    """
    Prueba completa del sistema de permisos
    """
    print("=== PRUEBA DEL SISTEMA DE PERMISOS DROPDOWNS ===\n")
    
    base_url = "http://127.0.0.1:5000"
    
    # Test 1: Verificar que la aplicación esté ejecutándose
    print("1. Verificando que la aplicación esté activa...")
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        if response.status_code in [200, 302]:
            print("   ✅ Aplicación respondiendo correctamente")
        else:
            print(f"   ⚠️  Aplicación responde con código: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Error conectando con la aplicación: {e}")
        return False
    
    # Test 2: Verificar endpoint de permisos
    print("\n2. Probando endpoint de verificación de permisos...")
    try:
        # Crear una sesión para mantener cookies
        session = requests.Session()
        
        # Probar endpoint de verificación de permiso
        test_data = {
            'pagina': 'LISTA_DE_MATERIALES',
            'seccion': 'Control de material',
            'boton': 'Control de material de almacén'
        }
        
        response = session.post(
            f"{base_url}/verificar_permiso_dropdown", 
            data=test_data,
            timeout=5
        )
        
        if response.status_code == 200:
            resultado = response.json()
            print(f"   ✅ Endpoint responde: {resultado}")
        else:
            print(f"   ⚠️  Endpoint responde con código: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Error probando endpoint: {e}")
    
    # Test 3: Verificar endpoint de obtener permisos de usuario
    print("\n3. Probando endpoint de obtener permisos de usuario...")
    try:
        response = session.get(f"{base_url}/obtener_permisos_usuario_actual", timeout=5)
        
        if response.status_code == 200:
            resultado = response.json()
            print(f"   ✅ Endpoint responde con {len(resultado.get('permisos', []))} permisos")
        else:
            print(f"   ⚠️  Endpoint responde con código: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Error probando endpoint: {e}")
    
    # Test 4: Verificar que los archivos JavaScript existan
    print("\n4. Verificando archivo JavaScript de permisos...")
    try:
        response = requests.get(f"{base_url}/static/js/permisos-dropdowns.js", timeout=5)
        
        if response.status_code == 200:
            contenido = response.text
            if "PermisosDropdowns" in contenido:
                print("   ✅ Archivo JavaScript cargado correctamente")
            else:
                print("   ⚠️  Archivo JavaScript no contiene objeto PermisosDropdowns")
        else:
            print(f"   ❌ Archivo JavaScript no encontrado (código: {response.status_code})")
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Error cargando JavaScript: {e}")
    
    # Test 5: Verificar una página LISTA
    print("\n5. Verificando página de LISTA...")
    try:
        # Primero hacer login si es necesario
        login_response = session.get(f"{base_url}/login", timeout=5)
        
        # Intentar acceder a una página del sistema
        response = session.get(f"{base_url}/", timeout=5)
        
        if response.status_code == 200:
            contenido = response.text
            if "data-permiso-pagina" in contenido:
                print("   ✅ Página contiene atributos de permisos")
            else:
                print("   ⚠️  Página no contiene atributos de permisos")
                
            if "permisos-dropdowns.js" in contenido:
                print("   ✅ Página incluye script de permisos")
            else:
                print("   ⚠️  Página no incluye script de permisos")
        else:
            print(f"   ❌ Error cargando página (código: {response.status_code})")
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Error accediendo a la página: {e}")
    
    print("\n=== PRUEBA COMPLETADA ===")
    print("\n💡 Para probar completamente:")
    print("   1. Abra http://127.0.0.1:5000 en su navegador")
    print("   2. Inicie sesión con un usuario")
    print("   3. Vaya al Panel de Administración de Usuarios")
    print("   4. Configure permisos para un rol específico")
    print("   5. Inicie sesión con ese usuario para verificar restricciones")
    
    return True

if __name__ == "__main__":
    probar_sistema_permisos()
