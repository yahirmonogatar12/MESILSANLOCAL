#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para probar que Control de BOM funcione correctamente después de las correcciones
"""

import requests
import time

def verificar_servidor():
    """Verificar que el servidor Flask esté activo"""
    try:
        response = requests.get('http://127.0.0.1:5000/', timeout=5)
        print(f"✓ Servidor Flask activo (código {response.status_code})")
        return True
    except requests.exceptions.RequestException as e:
        print(f"✗ Servidor Flask no disponible: {e}")
        return False

def hacer_login():
    """Hacer login con el usuario Problema"""
    try:
        session = requests.Session()
        
        # Datos de login
        login_data = {
            'username': 'Problema',
            'password': 'Problema123'
        }
        
        response = session.post(
            'http://127.0.0.1:5000/login',
            data=login_data,
            allow_redirects=False
        )
        
        print(f"Login: código {response.status_code}")
        
        if response.status_code == 302:
            print(f"✓ Login exitoso")
            return session
        else:
            print(f"✗ Login falló: {response.text}")
            return None
            
    except Exception as e:
        print(f"✗ Error en login: {e}")
        return None

def probar_endpoint_control_bom(session):
    """Probar el endpoint de Control de BOM"""
    try:
        response = session.get('http://127.0.0.1:5000/informacion_basica/control_de_bom')
        
        print(f"\nEndpoint Control de BOM: código {response.status_code}")
        
        if response.status_code == 200:
            print(f"✅ Control de BOM carga correctamente")
            
            # Verificar que el contenido incluya elementos esperados
            content = response.text
            if 'Control de BOM' in content and 'bomModeloSearch' in content:
                print(f"✓ Contenido HTML válido encontrado")
                return True
            else:
                print(f"⚠️ Contenido HTML incompleto")
                return False
        else:
            print(f"❌ Error cargando Control de BOM: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Error probando Control de BOM: {e}")
        return False

def probar_endpoint_modelos_bom(session):
    """Probar el endpoint de listar modelos BOM"""
    try:
        response = session.get('http://127.0.0.1:5000/listar_modelos_bom')
        
        print(f"\nEndpoint listar modelos BOM: código {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Modelos BOM obtenidos: {len(data)} modelos")
            if len(data) > 0:
                print(f"  Ejemplos: {data[:3]}")
            return True
        else:
            print(f"✗ Error obteniendo modelos BOM: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Error probando modelos BOM: {e}")
        return False

def main():
    print("=== Prueba Final de Control de BOM ===")
    print("Verificando que todas las funciones estén disponibles...\n")
    
    # 1. Verificar servidor
    if not verificar_servidor():
        print("❌ No se puede continuar sin el servidor Flask")
        return
    
    # 2. Hacer login
    session = hacer_login()
    if not session:
        print("❌ No se puede continuar sin login")
        return
    
    # 3. Probar endpoint de Control de BOM
    bom_ok = probar_endpoint_control_bom(session)
    
    # 4. Probar endpoint de modelos BOM
    modelos_ok = probar_endpoint_modelos_bom(session)
    
    # Resumen
    print("\n=== RESUMEN ===")
    if bom_ok and modelos_ok:
        print("🎉 ¡Control de BOM funciona correctamente!")
        print("✅ Todas las funciones están disponibles")
        print("✅ No hay errores de funciones no definidas")
    else:
        print("❌ Aún hay problemas con Control de BOM")
        if not bom_ok:
            print("  - Problema cargando la página de Control de BOM")
        if not modelos_ok:
            print("  - Problema obteniendo modelos BOM")

if __name__ == '__main__':
    main()