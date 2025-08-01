#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para probar que el permiso de Control de BOM funcione correctamente después de la corrección
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

def hacer_login(session, usuario, password):
    """Realizar login en la aplicación"""
    try:
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

def probar_permiso_control_bom(session):
    """Probar el permiso específico de Control de BOM"""
    try:
        # Datos del permiso específico de Control de BOM
        test_data = {
            'pagina': 'LISTA_INFORMACIONBASICA',
            'seccion': 'Control de produccion',
            'boton': 'Control de BOM'
        }
        
        response = session.post(
            'http://127.0.0.1:5000/admin/verificar_permiso_dropdown',
            json=test_data,
            headers={'Content-Type': 'application/json'}
        )
        
        print(f"\nVerificación permiso Control de BOM: código {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            tiene_permiso = data.get('tiene_permiso', False)
            
            if tiene_permiso:
                print(f"✅ Usuario TIENE permiso para Control de BOM")
                print(f"  - Respuesta: {data}")
                return True
            else:
                print(f"❌ Usuario NO TIENE permiso para Control de BOM")
                print(f"  - Respuesta: {data}")
                return False
        else:
            print(f"✗ Error verificando permiso: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Error probando permiso Control de BOM: {e}")
        return False

def probar_obtener_permisos(session):
    """Probar obtener todos los permisos del usuario"""
    try:
        response = session.get('http://127.0.0.1:5000/admin/obtener_permisos_usuario_actual')
        print(f"\nObtener permisos usuario: código {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Permisos obtenidos exitosamente")
            
            # Buscar específicamente el permiso de Control de BOM
            permisos = data.get('permisos', {})
            
            if 'LISTA_INFORMACIONBASICA' in permisos:
                if 'Control de produccion' in permisos['LISTA_INFORMACIONBASICA']:
                    if 'Control de BOM' in permisos['LISTA_INFORMACIONBASICA']['Control de produccion']:
                        print(f"✅ Control de BOM encontrado en permisos del usuario")
                        return True
                    else:
                        print(f"❌ Control de BOM NO encontrado en 'Control de produccion'")
                        print(f"  Botones disponibles: {permisos['LISTA_INFORMACIONBASICA']['Control de produccion']}")
                else:
                    print(f"❌ Sección 'Control de produccion' NO encontrada")
                    print(f"  Secciones disponibles: {list(permisos['LISTA_INFORMACIONBASICA'].keys())}")
            else:
                print(f"❌ Página 'LISTA_INFORMACIONBASICA' NO encontrada")
                print(f"  Páginas disponibles: {list(permisos.keys())}")
            
            return False
        else:
            print(f"✗ Error obteniendo permisos: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Error probando obtener permisos: {e}")
        return False

def main():
    print("=== Prueba de Control de BOM Corregido ===")
    
    # Crear sesión
    session = crear_sesion()
    
    # Probar login con usuario Problema
    if hacer_login(session, 'Problema', 'Problema'):
        print("\n--- Probando permisos de Control de BOM ---")
        
        # Probar verificación específica del permiso
        permiso_especifico_ok = probar_permiso_control_bom(session)
        
        # Probar obtener todos los permisos
        permisos_generales_ok = probar_obtener_permisos(session)
        
        print("\n=== Resumen ===")
        print(f"✓ Login: Exitoso")
        print(f"{'✓' if permiso_especifico_ok else '✗'} Verificación específica: {'Exitoso' if permiso_especifico_ok else 'Fallido'}")
        print(f"{'✓' if permisos_generales_ok else '✗'} Permisos generales: {'Exitoso' if permisos_generales_ok else 'Fallido'}")
        
        if permiso_especifico_ok and permisos_generales_ok:
            print("\n🎉 Control de BOM funciona correctamente")
            print("💡 El usuario debería poder acceder sin problemas")
        else:
            print("\n⚠️ Aún hay problemas con los permisos de Control de BOM")
    else:
        print("\n✗ No se pudo realizar login, verificar credenciales")

if __name__ == '__main__':
    main()