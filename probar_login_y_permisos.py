#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para hacer login con Yahir y probar los endpoints de permisos
"""

import requests
import json

def hacer_login():
    """Hacer login con el usuario Yahir"""
    try:
        # Crear sesión para mantener cookies
        session = requests.Session()
        
        # URL de login
        login_url = 'http://localhost:5000/login'
        
        # Datos de login
        login_data = {
            'username': 'Yahir',
            'password': 'Yahir123'
        }
        
        print("🔐 Intentando hacer login...")
        print(f"   Usuario: {login_data['username']}")
        print(f"   Contraseña: {'*' * len(login_data['password'])}")
        
        # Hacer login
        response = session.post(login_url, data=login_data, allow_redirects=False)
        
        print(f"📊 Status Code: {response.status_code}")
        print(f"📋 Headers: {dict(response.headers)}")
        
        if response.status_code == 302:  # Redirección exitosa
            print("✅ Login exitoso")
            return session
        elif response.status_code == 200:
            # Verificar si hay mensaje de error en la respuesta
            if 'error' in response.text.lower() or 'incorrecto' in response.text.lower():
                print("❌ Credenciales incorrectas")
                return None
            else:
                print("✅ Login exitoso (sin redirección)")
                return session
        else:
            print(f"❌ Error en login: {response.status_code}")
            print(f"Respuesta: {response.text[:500]}")
            return None
            
    except Exception as e:
        print(f"❌ Error en login: {e}")
        return None

def probar_endpoint_con_sesion(session, endpoint_url, nombre_endpoint):
    """Probar un endpoint con la sesión autenticada"""
    try:
        print(f"\n🔍 Probando {nombre_endpoint}...")
        print("-" * 50)
        
        response = session.get(endpoint_url)
        
        print(f"📊 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print("✅ Respuesta exitosa:")
                print(json.dumps(data, indent=2, ensure_ascii=False))
                
                # Estadísticas
                if isinstance(data, dict):
                    if 'permisos' in data or any(isinstance(v, dict) for v in data.values()):
                        total_permisos = 0
                        if 'permisos' in data:
                            # Formato del endpoint de debug
                            permisos = data['permisos']
                            if isinstance(permisos, dict):
                                for pagina, secciones in permisos.items():
                                    if isinstance(secciones, dict):
                                        for seccion, botones in secciones.items():
                                            if isinstance(botones, list):
                                                total_permisos += len(botones)
                        else:
                            # Formato del endpoint principal
                            for pagina, secciones in data.items():
                                if isinstance(secciones, dict):
                                    for seccion, botones in secciones.items():
                                        if isinstance(botones, list):
                                            total_permisos += len(botones)
                        
                        print(f"\n📈 Estadísticas:")
                        print(f"   - Páginas con permisos: {len(data)}")
                        print(f"   - Total de permisos: {total_permisos}")
                
                return True
                
            except json.JSONDecodeError as e:
                print(f"❌ Error decodificando JSON: {e}")
                print(f"Respuesta raw: {response.text[:500]}")
                return False
                
        elif response.status_code == 401:
            print("🔐 No autenticado")
            return False
        elif response.status_code == 403:
            print("🚫 Sin permisos")
            return False
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Respuesta: {response.text[:500]}")
            return False
            
    except Exception as e:
        print(f"❌ Error probando endpoint: {e}")
        return False

def main():
    print("🚀 Probando login y endpoints de permisos...")
    print("=" * 60)
    
    # Hacer login
    session = hacer_login()
    if not session:
        print("\n❌ No se pudo hacer login. Terminando.")
        return
    
    # Probar endpoints
    endpoints = [
        ('http://localhost:5000/admin/verificar_permisos_usuario', 'verificar_permisos_usuario'),
        ('http://localhost:5000/admin/test_permisos_debug', 'test_permisos_debug'),
        ('http://localhost:5000/admin/obtener_permisos_usuario_actual', 'obtener_permisos_usuario_actual')
    ]
    
    resultados = {}
    
    for url, nombre in endpoints:
        resultado = probar_endpoint_con_sesion(session, url, nombre)
        resultados[nombre] = resultado
    
    # Resumen
    print("\n📊 RESUMEN DE PRUEBAS:")
    print("=" * 60)
    
    for nombre, resultado in resultados.items():
        estado = "✅ OK" if resultado else "❌ FAIL"
        print(f"   - {nombre}: {estado}")
    
    exitosos = sum(1 for r in resultados.values() if r)
    total = len(resultados)
    
    if exitosos == total:
        print(f"\n🎉 Todos los endpoints funcionan correctamente ({exitosos}/{total})")
    else:
        print(f"\n⚠️ {exitosos}/{total} endpoints funcionan correctamente")
    
    print("\n🔚 Pruebas completadas")

if __name__ == "__main__":
    main()