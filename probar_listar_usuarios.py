#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para probar la función listar_usuarios después de las correcciones
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

import requests
import json
from datetime import datetime

def probar_endpoint_usuarios():
    """Probar el endpoint /listar_usuarios directamente"""
    print("🧪 Probando endpoint /listar_usuarios")
    print("="*50)
    
    try:
        # Hacer petición al endpoint (con prefijo /admin)
        url = "http://127.0.0.1:5000/admin/listar_usuarios"
        response = requests.get(url, timeout=10)
        
        print(f"📡 Status Code: {response.status_code}")
        print(f"📡 Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
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
                
        elif response.status_code == 401:
            print("🔒 Error 401: No autorizado - Se requiere login")
            print("📄 Respuesta:", response.text)
            
        elif response.status_code == 403:
            print("🚫 Error 403: Prohibido - Sin permisos")
            print("📄 Respuesta:", response.text)
            
        elif response.status_code == 500:
            print("💥 Error 500: Error interno del servidor")
            print("📄 Respuesta:", response.text)
            
        else:
            print(f"❓ Status code inesperado: {response.status_code}")
            print("📄 Respuesta:", response.text)
            
    except requests.exceptions.ConnectionError:
        print("❌ Error de conexión: No se pudo conectar al servidor")
        print("💡 Asegúrate de que la aplicación Flask esté corriendo en http://127.0.0.1:5000")
        
    except requests.exceptions.Timeout:
        print("⏰ Error de timeout: El servidor tardó demasiado en responder")
        
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()

def probar_funcion_directa():
    """Probar la función listar_usuarios directamente"""
    print("\n🔧 Probando función listar_usuarios directamente")
    print("="*50)
    
    try:
        from user_admin import listar_usuarios
        from flask import Flask
        
        # Crear una aplicación Flask temporal
        app = Flask(__name__)
        app.config['SECRET_KEY'] = 'test_key'
        
        with app.app_context():
            # Simular una petición
            with app.test_request_context():
                resultado = listar_usuarios()
                
                if hasattr(resultado, 'get_json'):
                    data = resultado.get_json()
                    print(f"✅ Función ejecutada correctamente")
                    print(f"👥 Total usuarios: {len(data) if data else 0}")
                    
                    if data:
                        print("\n📋 Usuarios (función directa):")
                        for usuario in data:
                            print(f"  • {usuario.get('username')} - {usuario.get('nombre_completo')}")
                else:
                    print(f"❌ Resultado inesperado: {type(resultado)}")
                    print(f"📄 Contenido: {resultado}")
                    
    except ImportError as e:
        print(f"❌ Error importando módulo: {e}")
    except Exception as e:
        print(f"❌ Error ejecutando función: {e}")
        import traceback
        traceback.print_exc()

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
    print(f"🧪 PRUEBA DE CARGA DE USUARIOS - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    # 1. Verificar servidor
    servidor_activo = verificar_servidor_activo()
    
    if servidor_activo:
        # 2. Probar endpoint
        probar_endpoint_usuarios()
    else:
        print("⚠️ Saltando prueba de endpoint - servidor no disponible")
    
    # 3. Probar función directa
    probar_funcion_directa()
    
    print("\n" + "="*70)
    print("🏁 PRUEBA COMPLETADA")
    
    if servidor_activo:
        print("💡 Si los usuarios no aparecen en la interfaz web pero sí en estas pruebas,")
        print("   el problema podría estar en el frontend (JavaScript) o en la autenticación.")
    else:
        print("💡 Inicia la aplicación Flask con 'python run.py' y vuelve a ejecutar esta prueba.")

if __name__ == "__main__":
    main()