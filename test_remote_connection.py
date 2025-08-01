#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de verificación de conexión remota a SQL Server
Este script ayuda a verificar que la configuración de acceso remoto funciona correctamente
"""

import pyodbc
import socket
import sys
import os
from datetime import datetime

def print_header():
    print("="*70)
    print("🔍 VERIFICACIÓN DE CONEXIÓN REMOTA - ISEMM MES")
    print("="*70)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

def test_port_connectivity(host, port):
    """Prueba si el puerto está abierto y accesible"""
    print(f"🔌 Probando conectividad al puerto {host}:{port}...")
    
    try:
        # Separar host y puerto si vienen juntos
        if ',' in host:
            host_part, port_part = host.split(',')
            port = int(port_part)
            host = host_part
        elif '\\' in host:
            # Para casos como localhost\SQLEXPRESS
            host = host.split('\\')[0]
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        result = sock.connect_ex((host, int(port)))
        sock.close()
        
        if result == 0:
            print(f"✅ Puerto {port} está abierto en {host}")
            return True
        else:
            print(f"❌ Puerto {port} está cerrado o no accesible en {host}")
            return False
            
    except Exception as e:
        print(f"❌ Error probando conectividad: {e}")
        return False

def test_sql_server_connection(config):
    """Prueba la conexión completa a SQL Server"""
    print(f"🗄️  Probando conexión a SQL Server...")
    
    try:
        # Construir cadena de conexión
        connection_string = f"""
        DRIVER={config['driver']};
        SERVER={config['server']};
        DATABASE={config['database']};
        UID={config['username']};
        PWD={config['password']};
        Trusted_Connection={config.get('trusted_connection', 'no')};
        Encrypt={config.get('encrypt', 'yes')};
        TrustServerCertificate={config.get('trust_server_certificate', 'yes')};
        """
        
        print(f"   Servidor: {config['server']}")
        print(f"   Base de datos: {config['database']}")
        print(f"   Usuario: {config['username']}")
        print(f"   Driver: {config['driver']}")
        
        # Intentar conexión
        conn = pyodbc.connect(connection_string, timeout=30)
        cursor = conn.cursor()
        
        # Probar consulta simple
        cursor.execute("SELECT @@VERSION as version, @@SERVERNAME as server_name, DB_NAME() as database_name")
        result = cursor.fetchone()
        
        print(f"✅ Conexión exitosa a SQL Server")
        print(f"   Versión: {result[0][:50]}...")
        print(f"   Servidor: {result[1]}")
        print(f"   Base de datos: {result[2]}")
        
        # Probar acceso a tablas principales
        tables_to_check = [
            'materiales',
            'control_material_almacen',
            'control_material_salida',
            'inventario_general',
            'bom'
        ]
        
        print(f"\n📊 Verificando tablas principales...")
        for table in tables_to_check:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"   ✅ {table}: {count} registros")
            except Exception as e:
                print(f"   ❌ {table}: Error - {e}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error de conexión a SQL Server: {e}")
        return False

def check_odbc_drivers():
    """Verifica los drivers ODBC disponibles"""
    print(f"🔧 Verificando drivers ODBC...")
    
    try:
        drivers = pyodbc.drivers()
        sql_drivers = [d for d in drivers if 'SQL Server' in d]
        
        if sql_drivers:
            print(f"✅ Drivers SQL Server encontrados:")
            for driver in sql_drivers:
                print(f"   - {driver}")
            return True
        else:
            print(f"❌ No se encontraron drivers SQL Server")
            print(f"   Instala: Microsoft ODBC Driver 17 for SQL Server")
            return False
            
    except Exception as e:
        print(f"❌ Error verificando drivers: {e}")
        return False

def load_config_from_file():
    """Carga configuración desde archivo"""
    try:
        # Intentar cargar desde config_sqlserver.py
        sys.path.append('app')
        import config_sqlserver
        
        config = config_sqlserver.SQL_SERVER_CONFIG.copy()
        print(f"✅ Configuración cargada desde app/config_sqlserver.py")
        return config
        
    except ImportError:
        print(f"⚠️  No se pudo cargar app/config_sqlserver.py")
        return None
    except Exception as e:
        print(f"❌ Error cargando configuración: {e}")
        return None

def get_manual_config():
    """Solicita configuración manual al usuario"""
    print(f"\n📝 Ingresa la configuración manualmente:")
    
    config = {
        'server': input("Servidor (ej: 192.168.1.100,1433): ").strip(),
        'database': input("Base de datos (ej: ISEMM_MES_SQLSERVER): ").strip() or 'ISEMM_MES_SQLSERVER',
        'username': input("Usuario (ej: isemm_app_user): ").strip() or 'isemm_app_user',
        'password': input("Contraseña: ").strip(),
        'driver': '{ODBC Driver 17 for SQL Server}',
        'trusted_connection': 'no',
        'encrypt': 'yes',
        'trust_server_certificate': 'yes'
    }
    
    return config

def print_connection_info(config):
    """Muestra información de conexión para compartir"""
    print(f"\n" + "="*70)
    print(f"📋 INFORMACIÓN DE CONEXIÓN PARA COMPARTIR:")
    print(f"="*70)
    print(f"Servidor: {config['server']}")
    print(f"Base de Datos: {config['database']}")
    print(f"Usuario: {config['username']}")
    print(f"Contraseña: {config['password']}")
    print(f"Driver: {config['driver']}")
    print(f"")
    print(f"Cadena de conexión completa:")
    print(f"DRIVER={config['driver']};")
    print(f"SERVER={config['server']};")
    print(f"DATABASE={config['database']};")
    print(f"UID={config['username']};")
    print(f"PWD={config['password']};")
    print(f"Trusted_Connection=no;")
    print(f"Encrypt=yes;")
    print(f"TrustServerCertificate=yes;")
    print(f"="*70)

def main():
    """Función principal"""
    print_header()
    
    # Verificar drivers ODBC
    if not check_odbc_drivers():
        print(f"\n❌ No se pueden realizar más pruebas sin drivers ODBC")
        return False
    
    print()
    
    # Cargar configuración
    config = load_config_from_file()
    
    if not config:
        print(f"\n⚠️  Configuración no encontrada. Ingresa manualmente:")
        config = get_manual_config()
    
    if not config or not config.get('server') or not config.get('password'):
        print(f"❌ Configuración incompleta")
        return False
    
    print(f"\n" + "-"*50)
    
    # Extraer host y puerto para prueba de conectividad
    server = config['server']
    host = server
    port = 1433
    
    if ',' in server:
        host, port = server.split(',')
        port = int(port)
    elif '\\' in server:
        host = server.split('\\')[0]
    
    # Probar conectividad de puerto
    port_ok = test_port_connectivity(host, port)
    
    print()
    
    # Probar conexión SQL Server
    sql_ok = test_sql_server_connection(config)
    
    print(f"\n" + "-"*50)
    
    # Resumen de resultados
    print(f"\n📊 RESUMEN DE PRUEBAS:")
    print(f"   Drivers ODBC: ✅")
    print(f"   Conectividad de puerto: {'✅' if port_ok else '❌'}")
    print(f"   Conexión SQL Server: {'✅' if sql_ok else '❌'}")
    
    if port_ok and sql_ok:
        print(f"\n🎉 ¡Conexión remota funcionando correctamente!")
        print_connection_info(config)
        return True
    else:
        print(f"\n❌ Hay problemas con la conexión remota")
        print(f"\n🔧 POSIBLES SOLUCIONES:")
        if not port_ok:
            print(f"   - Verificar que SQL Server esté ejecutándose")
            print(f"   - Verificar configuración de firewall")
            print(f"   - Verificar port forwarding en router")
            print(f"   - Verificar que TCP/IP esté habilitado en SQL Server")
        if not sql_ok:
            print(f"   - Verificar credenciales de usuario")
            print(f"   - Verificar que el usuario tenga permisos")
            print(f"   - Verificar que la base de datos exista")
            print(f"   - Verificar configuración de autenticación mixta")
        return False

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            sys.exit(1)
    except KeyboardInterrupt:
        print(f"\n\n⚠️  Prueba cancelada por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error durante la prueba: {e}")
        sys.exit(1)