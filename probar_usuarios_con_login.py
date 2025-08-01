#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para probar la carga de usuarios con autenticación
"""

import requests
import json
from datetime import datetime

def hacer_login(session, username="Problema", password="Problema"):
    """Hacer login en la aplicación"""
    print(f"🔐 Intentando login con usuario: {username}")
    
    try:
        # Hacer petición de login
        login_url = "http://127.0.0.1:5000/login"
        login_data = {
            'username': username,
            'password': password
        }
        
        response = session.post(login_url, data=login_data, allow_redirects=False)
        
        print(f"📡 Login Status Code: {response.status_code}")
        
        if response.status_code == 302:  # Redirección = login exitoso
            print("✅ Login exitoso")
            return True
        elif response.status_code == 200:
            if "error" in response.text.lower() or "incorrectos" in response.text.lower():
                print("❌ Login fallido - credenciales incorrectas")
                return False
            else:
                print("⚠️ Login posiblemente exitoso (status 200)")
                return True
        else:
            print(f"❌ Login fallido - Status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error durante login: {e}")
        return False

def probar_endpoint_usuarios_autenticado():
    """Probar el endpoint /admin/listar_usuarios con autenticación"""
    print("🧪 Probando endpoint /admin/listar_usuarios con autenticación")
    print("="*60)
    
    # Crear sesión para mantener cookies
    session = requests.Session()
    
    try:
        # 1. Hacer login
        if not hacer_login(session):
            print("❌ No se pudo hacer login, abortando prueba")
            return
        
        # 2. Acceder al endpoint de usuarios
        print("\n📋 Accediendo al endpoint de usuarios...")
        url = "http://127.0.0.1:5000/admin/listar_usuarios"
        response = session.get(url, timeout=10)
        
        print(f"📡 Status Code: {response.status_code}")
        print(f"📡 Content-Type: {response.headers.get('Content-Type', 'N/A')}")
        
        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', '')
            
            if 'application/json' in content_type:
                try:
                    usuarios = response.json()
                    print(f"✅ Respuesta JSON válida")
                    print(f"👥 Total usuarios: {len(usuarios)}")
                    
                    if usuarios:
                        print("\n📋 Usuarios encontrados:")
                        for i, usuario in enumerate(usuarios, 1):
                            print(f"\n  {i}. Usuario:")
                            print(f"     • ID: {usuario.get('id', 'N/A')}")
                            print(f"     • Username: {usuario.get('username', 'N/A')}")
                            print(f"     • Nombre: {usuario.get('nombre_completo', 'N/A')}")
                            print(f"     • Email: {usuario.get('email', 'N/A')}")
                            print(f"     • Departamento: {usuario.get('departamento', 'N/A')}")
                            print(f"     • Activo: {usuario.get('activo', 'N/A')}")
                            print(f"     • Roles: {usuario.get('roles', [])}")
                            print(f"     • Bloqueado: {usuario.get('bloqueado', 'N/A')}")
                            print(f"     • Último acceso: {usuario.get('ultimo_acceso', 'N/A')}")
                    else:
                        print("⚠️ Lista de usuarios vacía")
                        
                except json.JSONDecodeError as e:
                    print(f"❌ Error decodificando JSON: {e}")
                    print(f"📄 Contenido de respuesta: {response.text[:500]}")
            else:
                print(f"⚠️ Respuesta no es JSON: {content_type}")
                if "login" in response.text.lower():
                    print("🔒 Parece que se requiere autenticación adicional")
                print(f"📄 Contenido: {response.text[:300]}...")
                
        elif response.status_code == 401:
            print("🔒 Error 401: No autorizado")
            
        elif response.status_code == 403:
            print("🚫 Error 403: Sin permisos")
            
        elif response.status_code == 500:
            print("💥 Error 500: Error interno del servidor")
            print("📄 Respuesta:", response.text[:500])
            
        else:
            print(f"❓ Status code inesperado: {response.status_code}")
            print("📄 Respuesta:", response.text[:300])
            
    except requests.exceptions.ConnectionError:
        print("❌ Error de conexión: No se pudo conectar al servidor")
        
    except requests.exceptions.Timeout:
        print("⏰ Error de timeout: El servidor tardó demasiado en responder")
        
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()

def probar_otros_usuarios():
    """Probar con diferentes credenciales"""
    print("\n🔄 Probando con diferentes credenciales...")
    print("="*50)
    
    credenciales = [
        ("admin", "admin123"),
        ("Problema", "Problema"),
        ("admin", "admin")
    ]
    
    for username, password in credenciales:
        print(f"\n🧪 Probando: {username}/{password}")
        session = requests.Session()
        
        if hacer_login(session, username, password):
            print(f"✅ Login exitoso con {username}")
            
            # Probar acceso al endpoint
            try:
                url = "http://127.0.0.1:5000/admin/listar_usuarios"
                response = session.get(url, timeout=5)
                
                if response.status_code == 200 and 'application/json' in response.headers.get('Content-Type', ''):
                    usuarios = response.json()
                    print(f"✅ Endpoint funciona - {len(usuarios)} usuarios")
                    return True
                else:
                    print(f"⚠️ Endpoint no funciona - Status: {response.status_code}")
            except:
                print("❌ Error accediendo al endpoint")
        else:
            print(f"❌ Login fallido con {username}")
    
    return False

def verificar_servidor_activo():
    """Verificar que el servidor Flask esté activo"""
    print("🌐 Verificando servidor Flask")
    print("="*30)
    
    try:
        response = requests.get("http://127.0.0.1:5000", timeout=5)
        print(f"✅ Servidor activo - Status: {response.status_code}")
        return True
    except:
        print("❌ Servidor no disponible")
        return False

def main():
    """Función principal"""
    print(f"🧪 PRUEBA DE USUARIOS CON AUTENTICACIÓN - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # 1. Verificar servidor
    if not verificar_servidor_activo():
        print("❌ Servidor no disponible, abortando")
        return
    
    # 2. Probar con usuario conocido
    probar_endpoint_usuarios_autenticado()
    
    # 3. Probar con diferentes credenciales
    if not probar_otros_usuarios():
        print("\n❌ No se pudo acceder al endpoint con ninguna credencial")
    
    print("\n" + "="*80)
    print("🏁 PRUEBA COMPLETADA")
    print("\n💡 DIAGNÓSTICO:")
    print("   • Si el login es exitoso pero el endpoint no funciona:")
    print("     - Verificar permisos del usuario")
    print("     - Revisar logs de la aplicación Flask")
    print("   • Si el login falla:")
    print("     - Verificar credenciales en la base de datos")
    print("     - Usar el script verificar_usuarios_mysql.py")

if __name__ == "__main__":
    main()