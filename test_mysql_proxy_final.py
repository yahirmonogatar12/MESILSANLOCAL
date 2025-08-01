#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prueba final del sistema MySQL Proxy HTTP
Verifica que todo funcione correctamente
"""

import requests
import time
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def test_proxy_health():
    """Probar salud del proxy"""
    print("🏥 Probando salud del proxy...")
    try:
        response = requests.get('http://localhost:5001/health', timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Proxy saludable: {data.get('status')}")
            print(f"📊 MySQL: {data.get('mysql')}")
            print(f"⏰ Timestamp: {data.get('timestamp')}")
            return True
        else:
            print(f"❌ Proxy no saludable: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error conectando al proxy: {e}")
        return False

def test_proxy_info():
    """Obtener información del proxy"""
    print("\n📋 Obteniendo información del proxy...")
    try:
        response = requests.get('http://localhost:5001/info', timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"📛 Nombre: {data.get('name')}")
            print(f"🔢 Versión: {data.get('version')}")
            print(f"🖥️ MySQL Host: {data.get('mysql_host')}")
            print(f"🔌 MySQL Puerto: {data.get('mysql_port')}")
            print(f"🗄️ Base de datos: {data.get('mysql_database')}")
            return True
        else:
            print(f"❌ Error obteniendo info: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_simple_query():
    """Probar consulta simple"""
    print("\n🔍 Probando consulta simple...")
    try:
        api_key = os.getenv('PROXY_API_KEY', 'ISEMM_PROXY_2024_SUPER_SECRETO')
        
        data = {
            'query': 'SELECT 1 as test, NOW() as timestamp',
            'fetch': 'one',
            'api_key': api_key
        }
        
        response = requests.post(
            'http://localhost:5001/execute',
            json=data,
            headers={'X-API-Key': api_key},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                query_result = result.get('result', {})
                print(f"✅ Consulta exitosa")
                print(f"📊 Test: {query_result.get('test')}")
                print(f"⏰ Timestamp: {query_result.get('timestamp')}")
                return True
            else:
                print(f"❌ Error en consulta: {result.get('error')}")
                return False
        else:
            print(f"❌ Error HTTP: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_database_query():
    """Probar consulta a la base de datos real"""
    print("\n🗄️ Probando consulta a base de datos real...")
    try:
        api_key = os.getenv('PROXY_API_KEY', 'ISEMM_PROXY_2024_SUPER_SECRETO')
        
        data = {
            'query': 'SELECT COUNT(*) as total_usuarios FROM usuarios_sistema',
            'fetch': 'one',
            'api_key': api_key
        }
        
        response = requests.post(
            'http://localhost:5001/execute',
            json=data,
            headers={'X-API-Key': api_key},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                query_result = result.get('result', {})
                print(f"✅ Consulta a BD exitosa")
                print(f"👥 Total usuarios: {query_result.get('total_usuarios')}")
                return True
            else:
                print(f"❌ Error en consulta: {result.get('error')}")
                return False
        else:
            print(f"❌ Error HTTP: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_hybrid_config():
    """Probar configuración híbrida"""
    print("\n🔄 Probando configuración híbrida...")
    try:
        import sys
        sys.path.append(os.path.join(os.getcwd(), 'app'))
        
        from config_mysql_hybrid import get_connection_info, execute_query
        
        info = get_connection_info()
        print(f"📊 Modo: {info['mode']}")
        print(f"🔗 Directo disponible: {info['direct_available']}")
        print(f"🌐 HTTP disponible: {info['http_available']}")
        
        # Probar consulta
        result = execute_query('SELECT 1 as test', fetch='one')
        if result and result.get('test') == 1:
            print(f"✅ Configuración híbrida funcionando")
            return True
        else:
            print(f"❌ Error en configuración híbrida")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def show_connection_instructions():
    """Mostrar instrucciones de conexión"""
    print("\n" + "="*60)
    print("📋 INSTRUCCIONES PARA HOSTING")
    print("="*60)
    
    print("\n1. 📁 ARCHIVOS A SUBIR AL HOSTING:")
    print("   - app/mysql_http_client.py")
    print("   - app/config_mysql_hybrid.py")
    print("   - hosting_config.env (renombrar a .env)")
    
    print("\n2. 📦 DEPENDENCIAS A INSTALAR EN HOSTING:")
    print("   pip install flask flask-cors requests python-dotenv pymysql")
    
    print("\n3. 🔧 CONFIGURACIÓN EN HOSTING:")
    print("   - Copia hosting_config.env como .env")
    print("   - Modifica MYSQL_PROXY_URL si usas dominio")
    print("   - Asegúrate de que el puerto 5001 esté abierto")
    
    print("\n4. 🔒 SEGURIDAD:")
    print("   - Cambia PROXY_API_KEY por una clave única")
    print("   - Configura firewall para permitir solo tu hosting")
    print("   - Considera usar HTTPS en producción")
    
    print("\n5. 🧪 PRUEBAS EN HOSTING:")
    print("   - Sube test_mysql_proxy_final.py al hosting")
    print("   - Ejecuta: python test_mysql_proxy_final.py")
    print("   - Verifica que todas las pruebas pasen")

def show_local_info():
    """Mostrar información local"""
    print("\n" + "="*60)
    print("📊 INFORMACIÓN LOCAL")
    print("="*60)
    
    try:
        # IP pública
        response = requests.get('https://api.ipify.org', timeout=10)
        public_ip = response.text.strip()
        print(f"🌐 IP pública: {public_ip}")
    except:
        print(f"🌐 IP pública: No detectada")
    
    print(f"🔗 MySQL Host: {os.getenv('MYSQL_HOST', 'localhost')}")
    print(f"🗄️ Base de datos: {os.getenv('MYSQL_DATABASE', 'N/A')}")
    print(f"🔑 API Key: {os.getenv('PROXY_API_KEY', 'N/A')[:10]}...")
    print(f"🚪 Puerto proxy: 5001")
    
    print("\n🔧 URLs importantes:")
    print(f"   - Health: http://localhost:5001/health")
    print(f"   - Info: http://localhost:5001/info")
    print(f"   - Execute: http://localhost:5001/execute")

def main():
    """Función principal"""
    print("🚀 PRUEBA FINAL DEL SISTEMA MYSQL PROXY HTTP")
    print("=" * 60)
    
    tests = [
        ("Salud del proxy", test_proxy_health),
        ("Información del proxy", test_proxy_info),
        ("Consulta simple", test_simple_query),
        ("Consulta a BD real", test_database_query),
        ("Configuración híbrida", test_hybrid_config)
    ]
    
    passed = 0
    total = len(tests)
    
    for name, test_func in tests:
        print(f"\n🧪 Ejecutando: {name}")
        print("-" * 40)
        
        try:
            if test_func():
                passed += 1
                print(f"✅ {name} - PASÓ")
            else:
                print(f"❌ {name} - FALLÓ")
        except Exception as e:
            print(f"❌ {name} - ERROR: {e}")
        
        time.sleep(1)
    
    # Resumen
    print("\n" + "="*60)
    print("📊 RESUMEN DE PRUEBAS")
    print("="*60)
    print(f"✅ Pruebas pasadas: {passed}/{total}")
    print(f"❌ Pruebas fallidas: {total - passed}/{total}")
    
    if passed == total:
        print("\n🎉 ¡TODAS LAS PRUEBAS PASARON!")
        print("✅ El sistema está listo para usar")
        
        show_local_info()
        show_connection_instructions()
        
        print("\n🚀 SISTEMA LISTO PARA PRODUCCIÓN")
    else:
        print("\n⚠️ ALGUNAS PRUEBAS FALLARON")
        print("🔧 Revisa los errores arriba y corrige antes de continuar")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️ Pruebas canceladas por el usuario")
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")