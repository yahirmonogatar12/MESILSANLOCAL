#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de configuración para MySQL Proxy HTTP
Configura automáticamente la conexión entre hosting y MySQL local vía Tailscale
"""

import os
import sys
import subprocess
import time
import requests
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def print_header(title):
    """Imprimir encabezado decorado"""
    print("\n" + "="*60)
    print(f"🚀 {title}")
    print("="*60)

def print_step(step, description):
    """Imprimir paso del proceso"""
    print(f"\n📋 Paso {step}: {description}")
    print("-" * 50)

def check_dependencies():
    """Verificar dependencias necesarias"""
    print_step(1, "Verificando dependencias")
    
    required_packages = [
        'flask',
        'flask-cors', 
        'pymysql',
        'requests',
        'python-dotenv'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package} - Instalado")
        except ImportError:
            print(f"❌ {package} - Faltante")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️ Instalando paquetes faltantes: {', '.join(missing_packages)}")
        try:
            subprocess.check_call([
                sys.executable, '-m', 'pip', 'install'
            ] + missing_packages)
            print("✅ Paquetes instalados exitosamente")
        except subprocess.CalledProcessError as e:
            print(f"❌ Error instalando paquetes: {e}")
            return False
    
    return True

def test_mysql_direct():
    """Probar conexión directa a MySQL"""
    print_step(2, "Probando conexión directa a MySQL")
    
    try:
        import pymysql
        
        connection = pymysql.connect(
            host=os.getenv('MYSQL_HOST', '100.111.108.116'),
            port=int(os.getenv('MYSQL_PORT', '3306')),
            user=os.getenv('MYSQL_USERNAME', 'ILSANMES'),
            password=os.getenv('MYSQL_PASSWORD', 'ISEMM2025'),
            database=os.getenv('MYSQL_DATABASE', 'isemm2025'),
            connect_timeout=10
        )
        
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        cursor.close()
        connection.close()
        
        if result:
            print("✅ Conexión directa a MySQL exitosa")
            print(f"📊 Host: {os.getenv('MYSQL_HOST')}")
            print(f"🗄️ Base de datos: {os.getenv('MYSQL_DATABASE')}")
            return True
        else:
            print("❌ Conexión directa falló")
            return False
    
    except Exception as e:
        print(f"❌ Error en conexión directa: {e}")
        return False

def start_proxy_server():
    """Iniciar el servidor proxy en segundo plano"""
    print_step(3, "Iniciando servidor proxy MySQL")
    
    try:
        # Verificar si ya está corriendo
        try:
            response = requests.get('http://localhost:5001/health', timeout=5)
            if response.status_code == 200:
                print("✅ Servidor proxy ya está corriendo")
                return True
        except:
            pass
        
        # Iniciar servidor
        print("🚀 Iniciando servidor proxy...")
        
        # Ejecutar en segundo plano
        if os.name == 'nt':  # Windows
            subprocess.Popen([
                sys.executable, 'mysql_proxy_server.py'
            ], creationflags=subprocess.CREATE_NEW_CONSOLE)
        else:  # Linux/Mac
            subprocess.Popen([
                sys.executable, 'mysql_proxy_server.py'
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Esperar a que inicie
        print("⏳ Esperando que el servidor inicie...")
        for i in range(10):
            time.sleep(2)
            try:
                response = requests.get('http://localhost:5001/health', timeout=5)
                if response.status_code == 200:
                    print("✅ Servidor proxy iniciado exitosamente")
                    return True
            except:
                print(f"⏳ Intento {i+1}/10...")
        
        print("❌ No se pudo iniciar el servidor proxy")
        return False
    
    except Exception as e:
        print(f"❌ Error iniciando servidor proxy: {e}")
        return False

def test_proxy_connection():
    """Probar conexión a través del proxy"""
    print_step(4, "Probando conexión HTTP al proxy")
    
    try:
        # Verificar salud del proxy
        response = requests.get('http://localhost:5001/health', timeout=10)
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ Proxy saludable: {health_data.get('status')}")
            print(f"📊 MySQL: {health_data.get('mysql')}")
        else:
            print(f"❌ Proxy no saludable: {response.status_code}")
            return False
        
        # Probar consulta
        api_key = os.getenv('PROXY_API_KEY', 'ISEMM_PROXY_2024_SUPER_SECRETO')
        
        query_data = {
            'query': 'SELECT 1 as test',
            'fetch': 'one',
            'api_key': api_key
        }
        
        response = requests.post(
            'http://localhost:5001/execute',
            json=query_data,
            headers={'X-API-Key': api_key},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success') and result.get('result', {}).get('test') == 1:
                print("✅ Consulta de prueba exitosa")
                return True
            else:
                print(f"❌ Error en consulta: {result}")
                return False
        else:
            print(f"❌ Error HTTP: {response.status_code} - {response.text}")
            return False
    
    except Exception as e:
        print(f"❌ Error probando proxy: {e}")
        return False

def test_hybrid_config():
    """Probar configuración híbrida"""
    print_step(5, "Probando configuración híbrida")
    
    try:
        # Importar y probar config híbrida
        sys.path.append(os.path.join(os.getcwd(), 'app'))
        from config_mysql_hybrid import test_connection, get_connection_info
        
        info = get_connection_info()
        print(f"📊 Modo detectado: {info['mode']}")
        print(f"🔗 Conexión directa: {info['direct_available']}")
        print(f"🌐 Conexión HTTP: {info['http_available']}")
        
        if test_connection():
            print("✅ Configuración híbrida funcionando")
            return True
        else:
            print("❌ Error en configuración híbrida")
            return False
    
    except Exception as e:
        print(f"❌ Error probando configuración híbrida: {e}")
        return False

def generate_hosting_config():
    """Generar configuración para el hosting"""
    print_step(6, "Generando configuración para hosting")
    
    # Obtener IP pública o dominio
    try:
        response = requests.get('https://api.ipify.org', timeout=10)
        public_ip = response.text.strip()
        print(f"📡 IP pública detectada: {public_ip}")
    except:
        public_ip = "TU_IP_PUBLICA"
        print("⚠️ No se pudo detectar IP pública")
    
    hosting_env = f"""
# Configuración para HOSTING (copiar a tu servidor)
# ================================================

# Base de datos MySQL (a través de proxy HTTP)
DB_TYPE=mysql
USE_HTTP_PROXY=true

# URL del proxy MySQL (cambiar por tu dominio/IP)
MYSQL_PROXY_URL=http://{public_ip}:5001

# Clave API (debe coincidir con el servidor proxy)
PROXY_API_KEY=ISEMM_PROXY_2024_SUPER_SECRETO

# Configuración Flask
SECRET_KEY=tu_clave_secreta_super_segura_cambiar_en_produccion_2024
FLASK_ENV=production
FLASK_DEBUG=False

# Configuración de seguridad
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax

# Configuración de aplicación
APP_NAME=ISEMM_MES
"""
    
    with open('hosting_config.env', 'w', encoding='utf-8') as f:
        f.write(hosting_env)
    
    print("✅ Archivo 'hosting_config.env' generado")
    print("📋 Instrucciones para el hosting:")
    print("   1. Copia el contenido de 'hosting_config.env' a tu archivo .env en el hosting")
    print(f"   2. Asegúrate de que el puerto 5001 esté abierto en tu firewall")
    print(f"   3. Cambia la URL del proxy si usas un dominio en lugar de IP")
    print("   4. Instala las dependencias en el hosting: flask, flask-cors, requests, python-dotenv")

def show_final_instructions():
    """Mostrar instrucciones finales"""
    print_header("CONFIGURACIÓN COMPLETADA")
    
    print("🎉 ¡Configuración del proxy MySQL completada exitosamente!")
    
    print("\n📋 RESUMEN:")
    print("✅ Dependencias instaladas")
    print("✅ Conexión directa a MySQL verificada")
    print("✅ Servidor proxy iniciado")
    print("✅ Conexión HTTP al proxy verificada")
    print("✅ Configuración híbrida funcionando")
    print("✅ Configuración para hosting generada")
    
    print("\n🚀 PRÓXIMOS PASOS:")
    print("\n1. PARA USO LOCAL:")
    print("   - Tu aplicación ya puede usar la configuración híbrida")
    print("   - Se conectará directamente a MySQL cuando esté disponible")
    
    print("\n2. PARA HOSTING:")
    print("   - Copia el archivo 'hosting_config.env' a tu servidor")
    print("   - Renómbralo a '.env' en el hosting")
    print("   - Asegúrate de que el puerto 5001 esté abierto")
    print("   - Instala las dependencias necesarias")
    
    print("\n3. SEGURIDAD:")
    print("   - Cambia PROXY_API_KEY por una clave más segura")
    print("   - Configura ALLOWED_HOSTS para restringir acceso")
    print("   - Considera usar HTTPS en producción")
    
    print("\n🔧 COMANDOS ÚTILES:")
    print("   - Iniciar proxy: python mysql_proxy_server.py")
    print("   - Probar conexión: python app/config_mysql_hybrid.py")
    print("   - Ver logs del proxy: tail -f mysql_proxy.log")
    
    print("\n📞 SOPORTE:")
    print("   - Si hay problemas, revisa los logs")
    print("   - Verifica que Tailscale esté activo")
    print("   - Confirma que MySQL esté corriendo")

def main():
    """Función principal"""
    print_header("CONFIGURACIÓN DE MYSQL PROXY HTTP")
    print("Este script configurará la conexión entre tu hosting y MySQL local")
    print("usando Tailscale como túnel de red.")
    
    # Verificar dependencias
    if not check_dependencies():
        print("❌ Error en dependencias. Abortando.")
        return False
    
    # Probar MySQL directo
    if not test_mysql_direct():
        print("❌ No se puede conectar a MySQL. Verifica Tailscale y MySQL.")
        return False
    
    # Iniciar proxy
    if not start_proxy_server():
        print("❌ No se pudo iniciar el servidor proxy.")
        return False
    
    # Probar proxy
    if not test_proxy_connection():
        print("❌ El proxy no funciona correctamente.")
        return False
    
    # Probar configuración híbrida
    if not test_hybrid_config():
        print("❌ Error en configuración híbrida.")
        return False
    
    # Generar configuración para hosting
    generate_hosting_config()
    
    # Mostrar instrucciones finales
    show_final_instructions()
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n🎉 ¡Configuración completada exitosamente!")
        else:
            print("\n❌ Configuración falló. Revisa los errores arriba.")
    except KeyboardInterrupt:
        print("\n⚠️ Configuración cancelada por el usuario.")
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")