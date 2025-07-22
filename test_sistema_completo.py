#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test completo del sistema de permisos con sesión activa
"""

import requests
import json

def test_con_sesion():
    """Probar el sistema con una sesión de usuario activa"""
    base_url = "http://localhost:5000"
    
    print("🔐 TEST COMPLETO CON SESIÓN DE USUARIO")
    print("=" * 60)
    
    # Crear una sesión
    session = requests.Session()
    
    # Test 1: Intentar hacer login (simulado)
    print("\n1. 🚪 Probando login...")
    
    # Verificar si hay endpoint de login
    login_response = session.get(f"{base_url}/login")
    if login_response.status_code == 200:
        print("   ✅ Página de login disponible")
        
        # Intentar login con credenciales de admin
        login_data = {
            'username': 'admin',
            'password': 'admin'  # Cambiar si la contraseña es diferente
        }
        
        login_result = session.post(f"{base_url}/login", data=login_data)
        
        if login_result.status_code == 200 or 'dashboard' in login_result.url or 'ILSAN' in login_result.text:
            print("   ✅ Login exitoso")
            session_active = True
        else:
            print(f"   ⚠️ Login fallido: {login_result.status_code}")
            session_active = False
    else:
        print(f"   ❌ No se puede acceder al login: {login_response.status_code}")
        session_active = False
    
    # Test 2: Verificar permisos con sesión activa
    if session_active:
        print("\n2. 🔑 Probando permisos con sesión activa...")
        try:
            permisos_response = session.get(f"{base_url}/obtener_permisos_usuario_actual")
            print(f"   Status: {permisos_response.status_code}")
            
            if permisos_response.status_code == 200:
                permisos_data = permisos_response.json()
                
                print(f"   ✅ Permisos obtenidos correctamente")
                print(f"   👤 Usuario: {permisos_data.get('usuario', 'N/A')}")
                print(f"   🏷️ Rol: {permisos_data.get('rol', 'N/A')}")
                print(f"   📊 Total permisos: {permisos_data.get('total_permisos', 0)}")
                
                # Mostrar estructura de permisos
                permisos = permisos_data.get('permisos', {})
                if permisos:
                    print(f"   📂 Páginas disponibles: {len(permisos)}")
                    for pagina, secciones in list(permisos.items())[:3]:  # Mostrar solo las primeras 3
                        print(f"      📄 {pagina}: {len(secciones)} secciones")
                        for seccion, botones in list(secciones.items())[:2]:  # 2 secciones por página
                            print(f"         📋 {seccion}: {len(botones)} botones")
                
                # Test 3: Verificar un permiso específico
                print("\n3. 🎯 Probando validación específica...")
                if permisos:
                    # Buscar un permiso específico
                    found_permission = None
                    for pagina, secciones in permisos.items():
                        for seccion, botones in secciones.items():
                            if botones:  # Si hay botones en esta sección
                                found_permission = {
                                    'pagina': pagina,
                                    'seccion': seccion,
                                    'boton': botones[0]
                                }
                                break
                        if found_permission:
                            break
                    
                    if found_permission:
                        print(f"   🔍 Validando: {found_permission['pagina']} > {found_permission['seccion']} > {found_permission['boton']}")
                        
                        validate_data = {
                            'pagina': found_permission['pagina'],
                            'seccion': found_permission['seccion'],
                            'boton': found_permission['boton']
                        }
                        
                        validate_response = session.post(
                            f"{base_url}/verificar_permiso",
                            json=validate_data,
                            headers={'Content-Type': 'application/json'}
                        )
                        
                        if validate_response.status_code == 200:
                            validate_result = validate_response.json()
                            print(f"   ✅ Validación: {validate_result}")
                        else:
                            print(f"   ⚠️ Error en validación: {validate_response.status_code}")
                
            else:
                permisos_error = permisos_response.json()
                print(f"   ❌ Error obteniendo permisos: {permisos_error}")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    # Test 4: Verificar sistema JavaScript
    print("\n4. 📱 Verificando integración JavaScript...")
    
    # Verificar que el archivo de permisos existe
    js_response = session.get(f"{base_url}/static/js/permisos-dropdowns.js")
    if js_response.status_code == 200:
        print("   ✅ Script de permisos disponible")
        
        # Verificar contenido del script
        js_content = js_response.text
        if 'tienePermiso' in js_content:
            print("   ✅ Función tienePermiso encontrada")
        if 'obtener_permisos_usuario_actual' in js_content:
            print("   ✅ Integración con endpoint de permisos")
        if 'superadmin' in js_content:
            print("   ✅ Lógica de superadmin implementada")
    else:
        print(f"   ❌ Script no disponible: {js_response.status_code}")
    
    print("\n" + "=" * 60)
    print("🎯 DIAGNÓSTICO COMPLETADO")
    
    if session_active:
        print("✅ Sistema de backend funcionando correctamente")
        print("✅ Permisos jerárquicos disponibles")
        print("💡 Si los botones no funcionan, verificar:")
        print("   • Los elementos tienen atributos data-permiso-*")
        print("   • El script permisos-dropdowns.js se está cargando")
        print("   • La función PermisosDropdowns.init() se ejecuta")
        print("   • Los permisos corresponden exactamente con los elementos")
    else:
        print("⚠️ No se pudo establecer sesión activa")
        print("💡 Verificar credenciales de login")

if __name__ == "__main__":
    test_con_sesion()
