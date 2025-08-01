#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para probar la conectividad directa MySQL vía Tailscale desde hosting
"""

import os
import sys
import socket
import subprocess
import time
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv('hosting_config_tailscale.env')

def test_network_connectivity():
    """Prueba la conectividad de red básica."""
    print("=" * 60)
    print("PRUEBA DE CONECTIVIDAD DE RED")
    print("=" * 60)
    
    # Verificar conectividad a internet
    try:
        response = subprocess.run(['ping', '-c', '1', '8.8.8.8'], 
                                capture_output=True, text=True, timeout=10)
        if response.returncode == 0:
            print("✓ Conectividad a Internet: OK")
        else:
            print("✗ Conectividad a Internet: FALLO")
            return False
    except Exception as e:
        print(f"✗ Error probando conectividad: {e}")
        return False
    
    return True

def test_tailscale_status():
    """Verifica el estado de Tailscale."""
    print("\n" + "=" * 60)
    print("ESTADO DE TAILSCALE")
    print("=" * 60)
    
    try:
        # Verificar si Tailscale está instalado
        result = subprocess.run(['tailscale', 'status'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✓ Tailscale está instalado y funcionando")
            print("Estado de Tailscale:")
            print(result.stdout)
            return True
        else:
            print("✗ Tailscale no está funcionando correctamente")
            print(f"Error: {result.stderr}")
            return False
            
    except FileNotFoundError:
        print("✗ Tailscale no está instalado")
        print("\nPara instalar Tailscale:")
        print("curl -fsSL https://tailscale.com/install.sh | sh")
        print("sudo tailscale up")
        return False
    except Exception as e:
        print(f"✗ Error verificando Tailscale: {e}")
        return False

def test_mysql_host_connectivity():
    """Prueba la conectividad al host MySQL vía Tailscale."""
    print("\n" + "=" * 60)
    print("CONECTIVIDAD AL HOST MYSQL")
    print("=" * 60)
    
    mysql_host = os.getenv('MYSQL_HOST', '100.111.108.116')
    mysql_port = int(os.getenv('MYSQL_PORT', '3306'))
    
    print(f"Probando conexión a {mysql_host}:{mysql_port}")
    
    # Ping al host
    try:
        response = subprocess.run(['ping', '-c', '3', mysql_host], 
                                capture_output=True, text=True, timeout=15)
        if response.returncode == 0:
            print(f"✓ Ping a {mysql_host}: OK")
        else:
            print(f"✗ Ping a {mysql_host}: FALLO")
            print(f"Error: {response.stderr}")
            return False
    except Exception as e:
        print(f"✗ Error en ping: {e}")
        return False
    
    # Probar conexión al puerto MySQL
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        result = sock.connect_ex((mysql_host, mysql_port))
        sock.close()
        
        if result == 0:
            print(f"✓ Puerto {mysql_port} en {mysql_host}: ABIERTO")
            return True
        else:
            print(f"✗ Puerto {mysql_port} en {mysql_host}: CERRADO")
            return False
            
    except Exception as e:
        print(f"✗ Error probando puerto: {e}")
        return False

def test_mysql_connection():
    """Prueba la conexión directa a MySQL."""
    print("\n" + "=" * 60)
    print("CONEXIÓN DIRECTA A MYSQL")
    print("=" * 60)
    
    try:
        import pymysql
        
        # Configuración de conexión
        config = {
            'host': os.getenv('MYSQL_HOST', '100.111.108.116'),
            'port': int(os.getenv('MYSQL_PORT', '3306')),
            'user': os.getenv('MYSQL_USERNAME', 'ILSANMES'),
            'password': os.getenv('MYSQL_PASSWORD', 'ISEMM2025'),
            'database': os.getenv('MYSQL_DATABASE', 'isemm2025'),
            'connect_timeout': 10,
            'read_timeout': 10,
            'write_timeout': 10
        }
        
        print(f"Conectando a MySQL en {config['host']}:{config['port']}")
        print(f"Base de datos: {config['database']}")
        print(f"Usuario: {config['user']}")
        
        # Intentar conexión
        connection = pymysql.connect(**config)
        
        # Probar una consulta simple
        with connection.cursor() as cursor:
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()
            print(f"✓ Conexión exitosa a MySQL")
            print(f"✓ Versión de MySQL: {version[0]}")
            
            # Probar consulta a una tabla del sistema
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            print(f"✓ Tablas encontradas: {len(tables)}")
            
        connection.close()
        return True
        
    except ImportError:
        print("✗ PyMySQL no está instalado")
        print("Instalar con: pip install pymysql")
        return False
    except Exception as e:
        print(f"✗ Error conectando a MySQL: {e}")
        return False

def show_hosting_instructions():
    """Muestra las instrucciones para configurar en el hosting."""
    print("\n" + "=" * 60)
    print("INSTRUCCIONES PARA EL HOSTING")
    print("=" * 60)
    
    print("\n1. INSTALAR TAILSCALE EN EL HOSTING:")
    print("   curl -fsSL https://tailscale.com/install.sh | sh")
    print("   sudo tailscale up")
    
    print("\n2. VERIFICAR CONECTIVIDAD:")
    print("   ping 100.111.108.116")
    print("   telnet 100.111.108.116 3306")
    
    print("\n3. VARIABLES DE ENTORNO PARA EL HOSTING:")
    variables = [
        ('DB_TYPE', 'mysql'),
        ('USE_HTTP_PROXY', 'false'),
        ('MYSQL_HOST', '100.111.108.116'),
        ('MYSQL_PORT', '3306'),
        ('MYSQL_DATABASE', 'isemm2025'),
        ('MYSQL_USERNAME', 'ILSANMES'),
        ('MYSQL_PASSWORD', 'ISEMM2025'),
        ('SECRET_KEY', 'tu_clave_secreta_super_segura_cambiar_en_produccion_2024'),
        ('FLASK_ENV', 'production'),
        ('FLASK_DEBUG', 'False')
    ]
    
    for key, value in variables:
        print(f"   {key}={value}")
    
    print("\n4. INSTALAR DEPENDENCIAS:")
    print("   pip install -r requirements_hosting.txt")
    
    print("\n5. EJECUTAR ESTE SCRIPT EN EL HOSTING:")
    print("   python test_tailscale_hosting.py")

def main():
    """Función principal."""
    print("PRUEBA DE CONECTIVIDAD MYSQL VÍA TAILSCALE")
    print("Configuración: hosting_config_tailscale.env")
    
    tests = [
        ("Conectividad de Red", test_network_connectivity),
        ("Estado de Tailscale", test_tailscale_status),
        ("Conectividad al Host MySQL", test_mysql_host_connectivity),
        ("Conexión Directa a MySQL", test_mysql_connection)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ Error en {test_name}: {e}")
            results.append((test_name, False))
    
    # Resumen de resultados
    print("\n" + "=" * 60)
    print("RESUMEN DE PRUEBAS")
    print("=" * 60)
    
    passed = 0
    for test_name, result in results:
        status = "✓ PASÓ" if result else "✗ FALLÓ"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nResultado: {passed}/{len(results)} pruebas pasaron")
    
    if passed == len(results):
        print("\n🎉 ¡Todas las pruebas pasaron! Tailscale está funcionando correctamente.")
        print("Puedes usar la configuración directa en tu hosting.")
    else:
        print("\n⚠️  Algunas pruebas fallaron. Revisa la configuración de Tailscale.")
        show_hosting_instructions()
    
    return passed == len(results)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)