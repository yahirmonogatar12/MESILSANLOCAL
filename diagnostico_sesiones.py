#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test de diagnóstico de sesiones y autenticación
Verifica si el problema está en la persistencia de sesiones o en la configuración
"""

import requests
import json
import sys
import os

# Configuración del servidor
BASE_URL = "http://localhost:5000"
TEST_USER = "admin"
TEST_PASS = ".ISEMM2025."

def test_session_persistence():
    """Test completo de persistencia de sesiones"""
    print("🔍 TEST DE PERSISTENCIA DE SESIONES")
    print("=" * 50)
    
    # Crear una sesión persistente
    session = requests.Session()
    
    # 1. Verificar que el servidor esté funcionando
    print("\n1️⃣ Verificando servidor...")
    try:
        response = session.get(f"{BASE_URL}/")
        print(f"   ✅ Servidor activo - Status: {response.status_code}")
        print(f"   🍪 Cookies iniciales: {session.cookies}")
    except Exception as e:
        print(f"   ❌ Error conectando al servidor: {e}")
        return False
    
    # 2. Hacer login y capturar cookies
    print("\n2️⃣ Realizando login...")
    login_data = {
        'username': TEST_USER,
        'password': TEST_PASS
    }
    
    try:
        response = session.post(f"{BASE_URL}/login", data=login_data, allow_redirects=False)
        print(f"   📡 Status del login: {response.status_code}")
        print(f"   🍪 Cookies después del login: {session.cookies}")
        print(f"   📍 Redirect location: {response.headers.get('Location', 'No redirect')}")
        
        # Verificar si el login fue exitoso (debe ser redirect 302)
        if response.status_code in [302, 200]:
            print("   ✅ Login aparentemente exitoso")
        else:
            print(f"   ❌ Login falló - Status: {response.status_code}")
            print(f"   📄 Response text: {response.text[:500]}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error en login: {e}")
        return False
    
    # 3. Seguir el redirect si existe
    if response.status_code == 302:
        print("\n3️⃣ Siguiendo redirect...")
        try:
            redirect_url = response.headers.get('Location')
            if redirect_url and redirect_url.startswith('/'):
                redirect_url = BASE_URL + redirect_url
            
            if redirect_url:
                response = session.get(redirect_url)
                print(f"   📡 Status del redirect: {response.status_code}")
                print(f"   🍪 Cookies después del redirect: {session.cookies}")
            else:
                print("   ⚠️ No se encontró URL de redirect")
            
        except Exception as e:
            print(f"   ⚠️ Error siguiendo redirect: {e}")
    
    # 4. Test directo del endpoint de permisos
    print("\n4️⃣ Probando endpoint de permisos...")
    try:
        response = session.get(f"{BASE_URL}/obtener_permisos_usuario_actual")
        print(f"   📡 Status del endpoint permisos: {response.status_code}")
        print(f"   🍪 Cookies enviadas: {session.cookies}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"   ✅ Permisos obtenidos exitosamente")
                print(f"   👤 Usuario: {data.get('usuario', 'No especificado')}")
                print(f"   🎭 Rol: {data.get('rol', 'No especificado')}")
                print(f"   🔑 Total permisos: {data.get('total_permisos', 0)}")
                
                # Mostrar primeros permisos como muestra
                permisos = data.get('permisos', {})
                if permisos:
                    print(f"   📋 Primeras páginas con permisos: {list(permisos.keys())[:3]}")
                
                return True
            except Exception as e:
                print(f"   ❌ Error parseando JSON: {e}")
                print(f"   📄 Response text: {response.text[:500]}")
                return False
        else:
            print(f"   ❌ Error en endpoint permisos - Status: {response.status_code}")
            print(f"   📄 Response text: {response.text[:500]}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error consultando permisos: {e}")
        return False

def test_cookie_configuration():
    """Test de configuración de cookies"""
    print("\n\n🍪 TEST DE CONFIGURACIÓN DE COOKIES")
    print("=" * 50)
    
    session = requests.Session()
    
    # Test básico de cookies
    try:
        response = session.get(f"{BASE_URL}/")
        print(f"Cookies del servidor: {session.cookies}")
        
        # Verificar headers de seguridad
        print(f"Headers de seguridad:")
        for header in ['Set-Cookie', 'Secure', 'HttpOnly', 'SameSite']:
            if header in response.headers:
                print(f"  {header}: {response.headers[header]}")
                
    except Exception as e:
        print(f"Error verificando cookies: {e}")

def test_manual_session():
    """Test manual de verificación de sesión"""
    print("\n\n🔧 TEST MANUAL DE SESIÓN")
    print("=" * 50)
    
    # Hacer requests individuales para ver el flujo
    print("1. GET inicial...")
    response1 = requests.get(f"{BASE_URL}/")
    print(f"   Status: {response1.status_code}")
    
    print("2. POST login...")
    login_data = {'username': TEST_USER, 'password': TEST_PASS}
    response2 = requests.post(f"{BASE_URL}/login", data=login_data, allow_redirects=False)
    print(f"   Status: {response2.status_code}")
    print(f"   Set-Cookie: {response2.headers.get('Set-Cookie', 'None')}")
    
    print("3. GET permisos (sin sesión persistente)...")
    response3 = requests.get(f"{BASE_URL}/obtener_permisos_usuario_actual")
    print(f"   Status: {response3.status_code}")
    print(f"   Response: {response3.text[:200]}")

if __name__ == "__main__":
    print("🧪 DIAGNÓSTICO COMPLETO DE SESIONES Y AUTENTICACIÓN")
    print("=" * 60)
    
    # Test principal
    resultado = test_session_persistence()
    
    # Tests adicionales
    test_cookie_configuration()
    test_manual_session()
    
    print("\n\n📊 RESUMEN")
    print("=" * 30)
    if resultado:
        print("✅ Las sesiones funcionan correctamente")
        print("   El problema puede estar en el frontend (JavaScript)")
    else:
        print("❌ Hay problemas con la persistencia de sesiones")
        print("   El problema está en el backend (Flask/configuración)")
    
    print("\n🔍 PRÓXIMOS PASOS:")
    if resultado:
        print("1. Verificar JavaScript en el frontend")
        print("2. Revisar llamadas AJAX y headers")
        print("3. Verificar que el frontend use la misma sesión")
    else:
        print("1. Verificar configuración de Flask")
        print("2. Revisar secret_key y configuración de sesiones")
        print("3. Verificar decoradores y manejo de sesiones")
