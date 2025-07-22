#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test específico para superadmin
"""

import requests
import json

SERVER_URL = 'http://localhost:5000'

def test_superadmin_login():
    """Probar login del superadmin"""
    print("=== TEST SUPERADMIN ===")
    
    session = requests.Session()
    
    try:
        # Obtener página de login
        response = session.get(f"{SERVER_URL}/login")
        if response.status_code != 200:
            print(f"   ✗ Error obteniendo página de login: {response.status_code}")
            return None
            
        # Intentar login con Jesus (superadmin)
        login_data = {
            'username': 'Jesus',
            'password': 'admin123'  # Asumiendo contraseña común
        }
        
        response = session.post(f"{SERVER_URL}/login", data=login_data)
        
        print(f"Status code: {response.status_code}")
        print(f"URL final: {response.url}")
        
        if response.status_code == 200 and ('/ILSAN-ELECTRONICS' in response.url):
            print("✓ Login superadmin exitoso")
            
            # Probar endpoint de permisos
            print("\n=== PROBANDO ENDPOINT DE PERMISOS ===")
            response = session.get(f"{SERVER_URL}/obtener_permisos_usuario_actual")
            
            if response.status_code == 200:
                permisos_data = response.json()
                print(f"✓ Endpoint funciona")
                print(f"Usuario: {permisos_data.get('usuario')}")
                print(f"Rol: {permisos_data.get('rol')}")
                print(f"Total permisos: {permisos_data.get('total_permisos')}")
                
                permisos = permisos_data.get('permisos', {})
                
                print(f"\nCategorías de permisos:")
                for categoria in permisos.keys():
                    print(f"  - {categoria}")
                
                if 'informacion_basica' in permisos:
                    info_basica = permisos['informacion_basica']
                    print(f"\nPermisos de informacion_basica:")
                    for seccion, elementos in info_basica.items():
                        print(f"  {seccion}: {elementos}")
                else:
                    print("✗ No se encontró informacion_basica en permisos")
                
                # Probar una ruta específica
                print(f"\n=== PROBANDO RUTA ESPECÍFICA ===")
                response = session.get(f"{SERVER_URL}/informacion_basica/control_de_bom")
                print(f"control_de_bom: {response.status_code}")
                
                response = session.get(f"{SERVER_URL}/informacion_basica/control_de_material")
                print(f"control_de_material: {response.status_code}")
                
            else:
                print(f"✗ Error en endpoint de permisos: {response.status_code}")
                print(f"Response: {response.text}")
        else:
            print(f"✗ Login fallido")
            print(f"Response text: {response.text[:500]}")
            
    except Exception as e:
        print(f"✗ Error: {e}")

if __name__ == "__main__":
    test_superadmin_login()
