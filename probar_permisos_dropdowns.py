#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para probar los permisos de dropdowns después de las correcciones
"""

import requests
import json
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def crear_sesion():
    """Crear sesión con reintentos"""
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

def verificar_servidor():
    """Verificar que el servidor Flask esté activo"""
    try:
        response = requests.get('http://127.0.0.1:5000', timeout=5)
        print(f"✓ Servidor Flask activo (código: {response.status_code})")
        return True
    except Exception as e:
        print(f"✗ Error conectando al servidor: {e}")
        return False

def hacer_login(session, usuario, password):
    """Realizar login en la aplicación"""
    try:
        # Primero obtener la página de login para cualquier token CSRF
        login_page = session.get('http://127.0.0.1:5000/login')
        
        # Realizar login
        login_data = {
            'username': usuario,
            'password': password
        }
        
        response = session.post(
            'http://127.0.0.1:5000/login',
            data=login_data,
            allow_redirects=False
        )
        
        print(f"Login {usuario}: código {response.status_code}")
        
        if response.status_code == 302:  # Redirección exitosa
            print(f"✓ Login exitoso para {usuario}")
            return True
        else:
            print(f"✗ Login fallido para {usuario}")
            return False
            
    except Exception as e:
        print(f"✗ Error en login para {usuario}: {e}")
        return False

def probar_obtener_permisos_usuario(session):
    """Probar el endpoint /admin/obtener_permisos_usuario_actual"""
    try:
        response = session.get('http://127.0.0.1:5000/admin/obtener_permisos_usuario_actual')
        print(f"\nEndpoint obtener_permisos_usuario_actual: código {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Permisos obtenidos exitosamente")
            print(f"  - Tipo de respuesta: {type(data)}")
            if isinstance(data, dict):
                if 'permisos' in data:
                    print(f"  - Cantidad de permisos: {len(data['permisos'])}")
                    print(f"  - Primeros 3 permisos: {list(data['permisos'].keys())[:3]}")
                elif 'error' in data:
                    print(f"  - Error en respuesta: {data['error']}")
                else:
                    print(f"  - Estructura de respuesta: {list(data.keys())}")
            return True
        else:
            print(f"✗ Error obteniendo permisos: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Error probando obtener_permisos_usuario_actual: {e}")
        return False

def probar_verificar_permiso_dropdown(session):
    """Probar el endpoint /admin/verificar_permiso_dropdown"""
    try:
        # Probar con un permiso común
        test_data = {
            'pagina': 'LISTA_CONTROLDEPRODUCCION',
            'seccion': 'Control de plan de produccion',
            'boton': 'Control de embarque'
        }
        
        response = session.post(
            'http://127.0.0.1:5000/admin/verificar_permiso_dropdown',
            json=test_data,
            headers={'Content-Type': 'application/json'}
        )
        
        print(f"\nEndpoint verificar_permiso_dropdown: código {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Verificación de permiso exitosa")
            print(f"  - Respuesta: {data}")
            return True
        else:
            print(f"✗ Error verificando permiso: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Error probando verificar_permiso_dropdown: {e}")
        return False

def main():
    print("=== Prueba de Permisos de Dropdowns ===")
    
    # Verificar servidor
    if not verificar_servidor():
        return
    
    # Crear sesión
    session = crear_sesion()
    
    # Probar login con usuario Problema
    if hacer_login(session, 'Problema', 'Problema'):
        print("\n--- Probando endpoints de permisos ---")
        
        # Probar obtener permisos
        permisos_ok = probar_obtener_permisos_usuario(session)
        
        # Probar verificar permiso
        verificar_ok = probar_verificar_permiso_dropdown(session)
        
        print("\n=== Resumen ===")
        print(f"✓ Login: Exitoso")
        print(f"{'✓' if permisos_ok else '✗'} Obtener permisos: {'Exitoso' if permisos_ok else 'Fallido'}")
        print(f"{'✓' if verificar_ok else '✗'} Verificar permiso: {'Exitoso' if verificar_ok else 'Fallido'}")
        
        if permisos_ok and verificar_ok:
            print("\n🎉 Todos los endpoints de permisos funcionan correctamente")
        else:
            print("\n⚠️ Algunos endpoints tienen problemas")
    else:
        print("\n✗ No se pudo realizar login, verificar credenciales")

if __name__ == '__main__':
    main()