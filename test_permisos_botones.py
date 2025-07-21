#!/usr/bin/env python3
"""
Script para probar que los botones de administración solo aparecen para usuarios con permisos
"""

import requests
import time

# Configuración
BASE_URL = "http://localhost:5000"

def test_admin_con_permisos():
    """Probar que el usuario admin VE el botón de administración"""
    print("🔍 Probando usuario ADMIN (con permisos)...")
    
    session = requests.Session()
    
    # Login
    login_data = {
        'usuario': 'admin',
        'password': 'admin123'
    }
    
    response = session.post(f"{BASE_URL}/login", data=login_data)
    if response.status_code == 200 and "login.html" in response.url:
        print("❌ Login falló")
        return
    
    print("✅ Login exitoso")
    
    # Obtener página principal
    response = session.get(f"{BASE_URL}/ILSAN-ELECTRONICS")
    content = response.text
    
    # Verificar que el botón de administración aparece
    if "Panel de Administración" in content and "admin-only" in content:
        print("✅ Botón de administración VISIBLE para admin (correcto)")
    else:
        print("❌ Botón de administración NO VISIBLE para admin (incorrecto)")
    
    # Verificar página de auditoría
    response = session.get(f"{BASE_URL}/admin/auditoria")
    if response.status_code == 200:
        audit_content = response.text
        if "Panel Usuarios" in audit_content:
            print("✅ Botón 'Panel Usuarios' VISIBLE en auditoría para admin (correcto)")
        else:
            print("❌ Botón 'Panel Usuarios' NO VISIBLE en auditoría para admin (incorrecto)")
    else:
        print(f"❌ No pudo acceder a auditoría: {response.status_code}")
    
    print()

def test_usuario_sin_permisos():
    """Probar que un usuario sin permisos NO ve el botón"""
    print("🔍 Probando usuario SIN PERMISOS...")
    
    session = requests.Session()
    
    # Login con usuario sin permisos (1111 - JSON fallback)
    login_data = {
        'usuario': '1111',
        'password': '1111'
    }
    
    response = session.post(f"{BASE_URL}/login", data=login_data)
    if response.status_code == 200 and "login.html" in response.url:
        print("❌ Login falló")
        return
    
    print("✅ Login exitoso")
    
    # Obtener página principal
    response = session.get(f"{BASE_URL}/ILSAN-ELECTRONICS")
    content = response.text
    
    # Verificar que el botón de administración NO aparece
    if "Panel de Administración" in content or "admin-only" in content:
        print("❌ Botón de administración VISIBLE para usuario sin permisos (incorrecto)")
    else:
        print("✅ Botón de administración NO VISIBLE para usuario sin permisos (correcto)")
    
    print()

def test_usuario_con_rol_operador():
    """Probar que un usuario con rol operador NO ve el botón"""
    print("🔍 Probando usuario con ROL OPERADOR...")
    
    session = requests.Session()
    
    # Login con Yahir (que cambió a operador según el usuario)
    login_data = {
        'usuario': 'Yahir',
        'password': 'Yahir123'
    }
    
    response = session.post(f"{BASE_URL}/login", data=login_data)
    if response.status_code == 200 and "login.html" in response.url:
        print("❌ Login falló")
        return
    
    print("✅ Login exitoso")
    
    # Obtener página principal
    response = session.get(f"{BASE_URL}/ILSAN-ELECTRONICS")
    content = response.text
    
    # Verificar que el botón de administración NO aparece
    if "Panel de Administración" in content or "admin-only" in content:
        print("❌ Botón de administración VISIBLE para operador (incorrecto)")
    else:
        print("✅ Botón de administración NO VISIBLE para operador (correcto)")
    
    print()

if __name__ == "__main__":
    print("🧪 PRUEBAS DE PERMISOS PARA BOTONES DE ADMINISTRACIÓN")
    print("=" * 60)
    
    try:
        test_admin_con_permisos()
        test_usuario_sin_permisos()
        test_usuario_con_rol_operador()
        
        print("✅ Pruebas completadas")
        
    except Exception as e:
        print(f"❌ Error durante las pruebas: {e}")
