#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test de la nueva interfaz web de gestión de permisos
"""

import requests
import json

def test_nueva_interfaz():
    """Probar la nueva interfaz web de gestión de permisos"""
    base_url = "http://localhost:5000"
    
    print("🚀 PROBANDO NUEVA INTERFAZ WEB DE GESTIÓN DE PERMISOS")
    print("=" * 60)
    
    # Test 1: Cargar página principal
    print("\n1. 📄 Probando carga de página principal...")
    try:
        response = requests.get(f"{base_url}/admin/permisos-dropdowns")
        if response.status_code == 200:
            print("   ✅ Página principal carga correctamente")
        else:
            print(f"   ❌ Error {response.status_code}: {response.text}")
    except Exception as e:
        print(f"   ❌ Error de conexión: {e}")
    
    # Test 2: API de roles
    print("\n2. 👥 Probando API de roles...")
    try:
        response = requests.get(f"{base_url}/admin/api/roles")
        if response.status_code == 200:
            roles = response.json()
            print(f"   ✅ {len(roles)} roles encontrados:")
            for role in roles:
                print(f"      - {role['nombre']}: {role['descripcion']}")
        else:
            print(f"   ❌ Error {response.status_code}: {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 3: API de dropdowns
    print("\n3. 📋 Probando API de dropdowns...")
    try:
        response = requests.get(f"{base_url}/admin/api/dropdowns")
        if response.status_code == 200:
            dropdowns = response.json()
            print(f"   ✅ {len(dropdowns)} dropdowns disponibles:")
            for dropdown in dropdowns:
                print(f"      - {dropdown['boton']}: {dropdown['descripcion']}")
        else:
            print(f"   ❌ Error {response.status_code}: {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 4: Permisos de supervisor_almacen
    print("\n4. 🔐 Probando permisos de supervisor_almacen...")
    try:
        response = requests.get(f"{base_url}/admin/api/role-permissions/supervisor_almacen")
        if response.status_code == 200:
            permisos = response.json()
            print(f"   ✅ supervisor_almacen tiene {len(permisos)} permisos:")
            for permiso in permisos:
                print(f"      - {permiso['boton']}")
        else:
            print(f"   ❌ Error {response.status_code}: {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 5: Funcionalidad de toggle (simulación)
    print("\n5. 🔄 Probando funcionalidad de toggle...")
    try:
        # Primero obtener un permiso existente del supervisor_almacen
        permisos_response = requests.get(f"{base_url}/admin/api/role-permissions/supervisor_almacen")
        if permisos_response.status_code == 200:
            permisos = permisos_response.json()
            if permisos:
                # Usar el primer permiso encontrado
                primer_permiso = permisos[0]
                permission_key = primer_permiso['key']
                
                # Intentar remover el permiso
                test_data = {
                    "role": "supervisor_almacen",
                    "permission_key": permission_key, 
                    "action": "remove"
                }
                
                response = requests.post(
                    f"{base_url}/admin/api/toggle-permission",
                    json=test_data,
                    headers={'Content-Type': 'application/json'}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"   ✅ Toggle funcionando: {result.get('message', 'Sin mensaje')}")
                    
                    # Volver a agregar el permiso
                    test_data["action"] = "add"
                    response2 = requests.post(
                        f"{base_url}/admin/api/toggle-permission",
                        json=test_data,
                        headers={'Content-Type': 'application/json'}
                    )
                    
                    if response2.status_code == 200:
                        result2 = response2.json()
                        print(f"   ✅ Permiso restaurado: {result2.get('message', 'Sin mensaje')}")
                    else:
                        print(f"   ⚠️  Error restaurando permiso: {response2.status_code}")
                else:
                    print(f"   ❌ Error {response.status_code}: {response.text}")
            else:
                print("   ⚠️  No hay permisos para probar el toggle")
        else:
            print(f"   ❌ Error obteniendo permisos: {permisos_response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print("\n" + "=" * 60)
    print("🎉 PRUEBAS COMPLETADAS")
    print("\n📱 Interfaz disponible en: http://localhost:5000/admin/permisos-dropdowns")
    print("\n✨ CARACTERÍSTICAS DE LA NUEVA INTERFAZ:")
    print("   • 🎨 Diseño moderno con Bootstrap 5 y gradientes")
    print("   • ⚡ Interfaz reactiva en tiempo real")
    print("   • 🔄 Toggle individual de permisos")
    print("   • 📊 Contadores de permisos por rol")
    print("   • 🎯 Botones de habilitar/deshabilitar todos")
    print("   • 🔔 Notificaciones toast")
    print("   • 📱 Diseño responsive")
    print("   • 🔍 Búsqueda y filtrado de permisos")
    print("   • 📂 Filtros por categoría (info_, lista_, control_, etc.)")
    print(f"   • 📋 Gestión completa de {len(requests.get(f'{base_url}/admin/api/dropdowns').json())} dropdowns")

if __name__ == "__main__":
    test_nueva_interfaz()
