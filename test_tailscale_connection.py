#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de prueba para verificar la conexión a SQL Server usando Tailscale
Configuración basada en las variables de entorno del archivo .env
"""

import os
import sys
import socket
from dotenv import load_dotenv

# Agregar el directorio app al path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

try:
    from config_sqlserver import get_sqlserver_connection, get_sqlserver_connection_string, SQL_SERVER_CONFIG
except ImportError as e:
    print(f"❌ Error importando configuración: {e}")
    sys.exit(1)

def test_network_connectivity():
    """Probar conectividad de red al servidor SQL Server"""
    print("\n🔍 Probando conectividad de red...")
    
    host = SQL_SERVER_CONFIG['server']
    port = int(os.getenv('SQL_SERVER_PORT', 1433))
    
    try:
        # Crear socket y probar conexión
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            print(f"✅ Conectividad de red OK: {host}:{port}")
            return True
        else:
            print(f"❌ No se puede conectar a {host}:{port}")
            return False
    except Exception as e:
        print(f"❌ Error de conectividad: {e}")
        return False

def test_sql_connection():
    """Probar conexión completa a SQL Server"""
    print("\n🔍 Probando conexión a SQL Server...")
    
    try:
        # Mostrar cadena de conexión (sin password)
        conn_string = get_sqlserver_connection_string()
        safe_conn_string = conn_string.replace(f"PWD={SQL_SERVER_CONFIG['password']}", "PWD=***")
        print(f"📝 Cadena de conexión: {safe_conn_string}")
        
        # Intentar conexión
        conn = get_sqlserver_connection()
        
        # Probar consulta simple
        cursor = conn.cursor()
        cursor.execute("SELECT @@VERSION as version, DB_NAME() as database_name")
        result = cursor.fetchone()
        
        print(f"✅ Conexión exitosa a SQL Server")
        print(f"📊 Versión: {result.version[:100]}...")
        print(f"🗄️  Base de datos: {result.database_name}")
        
        # Probar tablas principales
        cursor.execute("""
            SELECT TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_TYPE = 'BASE TABLE' 
            AND TABLE_NAME IN ('materials', 'bom_data', 'usuarios')
            ORDER BY TABLE_NAME
        """)
        
        tables = cursor.fetchall()
        if tables:
            print(f"📋 Tablas encontradas: {', '.join([t.TABLE_NAME for t in tables])}")
        else:
            print("⚠️  No se encontraron las tablas principales")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error de conexión SQL: {e}")
        return False

def show_configuration():
    """Mostrar configuración actual"""
    print("\n📋 Configuración actual:")
    print(f"🖥️  Servidor: {SQL_SERVER_CONFIG['server']}")
    print(f"🗄️  Base de datos: {SQL_SERVER_CONFIG['database']}")
    print(f"👤 Usuario: {SQL_SERVER_CONFIG['username'] or 'Windows Authentication'}")
    print(f"🔒 Encriptación: {SQL_SERVER_CONFIG['encrypt']}")
    print(f"🛡️  Certificado confiable: {SQL_SERVER_CONFIG['trust_server_certificate']}")
    print(f"⏱️  Timeout: {SQL_SERVER_CONFIG['timeout']} segundos")

def main():
    """Función principal"""
    print("🚀 ISEMM MES - Prueba de Conexión SQL Server con Tailscale")
    print("=" * 60)
    
    # Cargar variables de entorno
    load_dotenv()
    
    # Verificar que las variables críticas estén configuradas
    required_vars = ['SQL_SERVER_HOST']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    # Verificar autenticación
    trusted_connection = os.getenv('TRUSTED_CONNECTION', 'no').lower()
    if trusted_connection != 'yes':
        # Si no es Windows Authentication, verificar que al menos el usuario esté configurado
        if not os.getenv('SQL_SERVER_USERNAME'):
            missing_vars.append('SQL_SERVER_USERNAME')
        # La contraseña puede estar vacía para algunos usuarios como 'sa'
    
    if missing_vars:
        print(f"❌ Variables de entorno faltantes: {', '.join(missing_vars)}")
        print("💡 Asegúrate de configurar el archivo .env correctamente")
        return False
    
    # Mostrar configuración
    show_configuration()
    
    # Ejecutar pruebas
    network_ok = test_network_connectivity()
    if not network_ok:
        print("\n💡 Sugerencias:")
        print("   - Verifica que Tailscale esté conectado")
        print("   - Confirma que la IP del servidor sea correcta")
        print("   - Revisa que el puerto 1433 esté abierto")
        return False
    
    sql_ok = test_sql_connection()
    if not sql_ok:
        print("\n💡 Sugerencias:")
        print("   - Verifica las credenciales de usuario y contraseña")
        print("   - Confirma que el usuario tenga permisos en la base de datos")
        print("   - Revisa que SQL Server esté configurado para autenticación mixta")
        return False
    
    print("\n🎉 ¡Todas las pruebas pasaron exitosamente!")
    print("✅ El sistema está listo para usar con Tailscale")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)