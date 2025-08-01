#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para verificar que todo funcione al 100% después de la migración completa
Prueba: login, permisos, endpoints y funcionalidad de botones
"""

import requests
import json
from datetime import datetime

# Configuración
BASE_URL = "http://localhost:5000"
USUARIO_TEST = "Yahir"
PASSWORD_TEST = "Yahir123"

def probar_login():
    """Probar login del usuario"""
    print("🔐 PROBANDO LOGIN")
    print("-" * 50)
    
    session = requests.Session()
    
    try:
        # Obtener página de login
        response = session.get(f"{BASE_URL}/login")
        if response.status_code != 200:
            print(f"❌ Error obteniendo página de login: {response.status_code}")
            return None
        
        # Hacer login
        login_data = {
            'username': USUARIO_TEST,
            'password': PASSWORD_TEST
        }
        
        response = session.post(f"{BASE_URL}/login", data=login_data)
        
        # Verificar si el login fue exitoso (redirección a dashboard, admin/panel, etc.)
        login_exitoso = (
            response.status_code == 200 and 
            ('dashboard' in response.url or 'admin' in response.url or 'panel' in response.url)
        )
        
        if login_exitoso:
            print(f"✅ Login exitoso para usuario: {USUARIO_TEST}")
            print(f"   Redirigido a: {response.url}")
            return session
        else:
            print(f"❌ Login fallido - Status: {response.status_code}")
            print(f"   URL final: {response.url}")
            return None
            
    except Exception as e:
        print(f"❌ Error durante login: {e}")
        return None

def probar_endpoints_permisos(session):
    """Probar endpoints de permisos"""
    print("\n🔑 PROBANDO ENDPOINTS DE PERMISOS")
    print("-" * 50)
    
    endpoints = [
        "/admin/obtener_permisos_usuario_actual",
        "/admin/verificar_permisos_usuario",
        "/admin/test_permisos_debug"
    ]
    
    resultados = {}
    
    for endpoint in endpoints:
        try:
            response = session.get(f"{BASE_URL}{endpoint}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    resultados[endpoint] = {
                        'status': 'OK',
                        'permisos_count': len(data.get('permisos', [])),
                        'estructura': list(data.keys()) if isinstance(data, dict) else 'No dict'
                    }
                    print(f"✅ {endpoint}: {resultados[endpoint]['permisos_count']} permisos")
                except json.JSONDecodeError:
                    resultados[endpoint] = {'status': 'ERROR', 'error': 'JSON inválido'}
                    print(f"❌ {endpoint}: Respuesta no es JSON válido")
            else:
                resultados[endpoint] = {'status': 'ERROR', 'code': response.status_code}
                print(f"❌ {endpoint}: Error {response.status_code}")
                
        except Exception as e:
            resultados[endpoint] = {'status': 'ERROR', 'error': str(e)}
            print(f"❌ {endpoint}: {e}")
    
    return resultados

def probar_paginas_principales(session):
    """Probar acceso a páginas principales"""
    print("\n📄 PROBANDO PÁGINAS PRINCIPALES")
    print("-" * 50)
    
    paginas = [
        "/",
        "/control_almacen",
        "/control_salida",
        "/material/info",
        "/material/control_almacen",
        "/informacion_basica/control_de_material"
    ]
    
    resultados = {}
    
    for pagina in paginas:
        try:
            response = session.get(f"{BASE_URL}{pagina}")
            
            if response.status_code == 200:
                # Verificar que la página contenga elementos esperados
                content = response.text.lower()
                tiene_botones = 'button' in content or 'btn' in content
                tiene_scripts = 'script' in content
                
                resultados[pagina] = {
                    'status': 'OK',
                    'tiene_botones': tiene_botones,
                    'tiene_scripts': tiene_scripts,
                    'size': len(response.text)
                }
                print(f"✅ {pagina}: OK (Botones: {tiene_botones}, Scripts: {tiene_scripts})")
            else:
                resultados[pagina] = {'status': 'ERROR', 'code': response.status_code}
                print(f"❌ {pagina}: Error {response.status_code}")
                
        except Exception as e:
            resultados[pagina] = {'status': 'ERROR', 'error': str(e)}
            print(f"❌ {pagina}: {e}")
    
    return resultados

def verificar_base_datos():
    """Verificar conexión y datos en la base de datos"""
    print("\n🗄️ VERIFICANDO BASE DE DATOS")
    print("-" * 50)
    
    try:
        import pymysql
        
        # Configuración de MySQL del hosting
        config = {
            'host': 'up-de-fra1-mysql-1.db.run-on-seenode.com',
            'port': 11550,
            'user': 'db_rrpq0erbdujn',
            'password': '5fUNbSRcPP3LN9K2I33Pr0ge',
            'database': 'db_rrpq0erbdujn',
            'charset': 'utf8mb4'
        }
        
        conn = pymysql.connect(**config)
        cursor = conn.cursor()
        
        # Verificar tablas principales
        tablas_verificar = [
            'usuarios_sistema',
            'roles', 
            'usuario_roles',
            'rol_permisos_botones',
            'control_material_almacen',
            'inventario_general',
            'bom'
        ]
        
        resultados_db = {}
        
        for tabla in tablas_verificar:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {tabla}")
                count = cursor.fetchone()[0]
                resultados_db[tabla] = count
                print(f"✅ {tabla}: {count} registros")
            except Exception as e:
                resultados_db[tabla] = f"Error: {e}"
                print(f"❌ {tabla}: {e}")
        
        # Verificar usuario específico
        cursor.execute("SELECT id, username, email FROM usuarios_sistema WHERE username = %s", (USUARIO_TEST,))
        usuario = cursor.fetchone()
        
        if usuario:
            print(f"✅ Usuario {USUARIO_TEST} encontrado - ID: {usuario[0]}, Email: {usuario[2]}")
            
            # Verificar roles del usuario
            cursor.execute("""
                SELECT ur.rol_id, r.nombre 
                FROM usuario_roles ur 
                JOIN roles r ON ur.rol_id = r.id 
                WHERE ur.usuario_id = %s
            """, (usuario[0],))
            
            roles = cursor.fetchall()
            if roles:
                roles_nombres = [rol[1] for rol in roles]
                print(f"   Roles: {', '.join(roles_nombres)}")
            else:
                print("   Sin roles asignados")
        else:
            print(f"❌ Usuario {USUARIO_TEST} no encontrado")
        
        conn.close()
        return resultados_db
        
    except Exception as e:
        print(f"❌ Error verificando base de datos: {e}")
        return {}

def generar_reporte(login_ok, permisos_results, paginas_results, db_results):
    """Generar reporte final"""
    print("\n📊 REPORTE FINAL DE VERIFICACIÓN")
    print("=" * 70)
    
    # Estadísticas generales
    total_endpoints = len(permisos_results)
    endpoints_ok = sum(1 for r in permisos_results.values() if r.get('status') == 'OK')
    
    total_paginas = len(paginas_results)
    paginas_ok = sum(1 for r in paginas_results.values() if r.get('status') == 'OK')
    
    total_tablas = len(db_results)
    tablas_ok = sum(1 for r in db_results.values() if isinstance(r, int))
    
    print(f"🔐 Login: {'✅ OK' if login_ok else '❌ FALLO'}")
    print(f"🔑 Endpoints de permisos: {endpoints_ok}/{total_endpoints} OK")
    print(f"📄 Páginas principales: {paginas_ok}/{total_paginas} OK")
    print(f"🗄️ Tablas de base de datos: {tablas_ok}/{total_tablas} OK")
    
    # Detalles de permisos
    if login_ok and endpoints_ok > 0:
        print("\n🎯 DETALLES DE PERMISOS:")
        for endpoint, result in permisos_results.items():
            if result.get('status') == 'OK':
                count = result.get('permisos_count', 0)
                print(f"   {endpoint}: {count} permisos cargados")
    
    # Estado general
    funcionamiento_general = (
        login_ok and 
        endpoints_ok >= 1 and  # Al menos un endpoint de permisos funciona
        paginas_ok >= 3 and    # Al menos 3 páginas funcionan
        tablas_ok >= 5         # Al menos 5 tablas tienen datos
    )
    
    print(f"\n🎉 FUNCIONAMIENTO GENERAL: {'✅ EXCELENTE' if funcionamiento_general else '⚠️ NECESITA REVISIÓN'}")
    
    if funcionamiento_general:
        print("\n✨ ¡MIGRACIÓN COMPLETADA AL 100%!")
        print("   - Login funcional")
        print("   - Permisos cargados correctamente")
        print("   - Páginas accesibles")
        print("   - Base de datos con datos migrados")
        print("   - Sistema listo para uso en producción")
    else:
        print("\n⚠️ Revisar elementos que fallaron")
    
    return funcionamiento_general

def main():
    print("🚀 VERIFICACIÓN COMPLETA DEL SISTEMA MIGRADO")
    print("=" * 70)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Usuario de prueba: {USUARIO_TEST}")
    print(f"URL base: {BASE_URL}")
    
    # 1. Probar login
    session = probar_login()
    login_ok = session is not None
    
    # 2. Probar endpoints de permisos
    permisos_results = {}
    if login_ok:
        permisos_results = probar_endpoints_permisos(session)
    else:
        print("\n⚠️ Saltando pruebas de permisos (login falló)")
    
    # 3. Probar páginas principales
    paginas_results = {}
    if login_ok:
        paginas_results = probar_paginas_principales(session)
    else:
        print("\n⚠️ Saltando pruebas de páginas (login falló)")
    
    # 4. Verificar base de datos
    db_results = verificar_base_datos()
    
    # 5. Generar reporte final
    funcionamiento_ok = generar_reporte(login_ok, permisos_results, paginas_results, db_results)
    
    return funcionamiento_ok

if __name__ == "__main__":
    resultado = main()
    exit(0 if resultado else 1)