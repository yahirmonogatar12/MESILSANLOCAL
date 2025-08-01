#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de prueba final para conexión Tailscale
Prueba la conexión a SQL Server usando la IP de Tailscale
"""

import pyodbc
import socket

def test_network_connectivity():
    """Probar conectividad de red"""
    print("🔍 Probando conectividad de red a Tailscale...")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        result = sock.connect_ex(('100.111.108.116', 1433))
        sock.close()
        
        if result == 0:
            print("✅ Conectividad de red OK: 100.111.108.116:1433")
            return True
        else:
            print("❌ No se puede conectar a 100.111.108.116:1433")
            return False
    except Exception as e:
        print(f"❌ Error de conectividad: {e}")
        return False

def test_tailscale_connection_with_password(password):
    """Probar conexión con contraseña específica"""
    print(f"\n🔍 Probando conexión SQL Server con contraseña...")
    
    conn_string = (
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=100.111.108.116,1433;"
        "DATABASE=ISEMM_MES_SQLSERVER;"
        "UID=sa;"
        f"PWD={password};"
        "Encrypt=yes;"
        "TrustServerCertificate=yes;"
        "Connection Timeout=30;"
    )
    
    try:
        print(f"📝 Intentando conexión con usuario 'sa'...")
        conn = pyodbc.connect(conn_string)
        
        # Probar consulta simple
        cursor = conn.cursor()
        cursor.execute("SELECT @@VERSION as version, DB_NAME() as database_name")
        result = cursor.fetchone()
        
        print(f"✅ Conexión exitosa a SQL Server")
        print(f"📊 Versión: {result.version[:80]}...")
        print(f"🗄️  Base de datos: {result.database_name}")
        
        # Probar tablas
        cursor.execute("""
            SELECT COUNT(*) as table_count
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_TYPE = 'BASE TABLE'
        """)
        
        table_count = cursor.fetchone().table_count
        print(f"📋 Tablas encontradas: {table_count}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error de conexión SQL: {e}")
        return False

def test_without_password():
    """Probar conexión sin contraseña (usuario sa sin password)"""
    print(f"\n🔍 Probando conexión sin contraseña...")
    
    conn_string = (
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=100.111.108.116,1433;"
        "DATABASE=ISEMM_MES_SQLSERVER;"
        "UID=sa;"
        "PWD=;"
        "Encrypt=yes;"
        "TrustServerCertificate=yes;"
        "Connection Timeout=30;"
    )
    
    try:
        conn = pyodbc.connect(conn_string)
        cursor = conn.cursor()
        cursor.execute("SELECT @@VERSION")
        result = cursor.fetchone()
        print(f"✅ Conexión exitosa sin contraseña: {result[0][:50]}...")
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Error sin contraseña: {str(e)[:100]}...")
        return False

def main():
    """Función principal"""
    print("🚀 ISEMM MES - Prueba Final de Conexión Tailscale")
    print("=" * 60)
    print("📍 IP Tailscale: 100.111.108.116")
    print("🔌 Puerto: 1433")
    print("🗄️  Base de datos: ISEMM_MES_SQLSERVER")
    print("👤 Usuario: sa")
    
    # Probar conectividad de red
    if not test_network_connectivity():
        print("\n💡 Sugerencias para conectividad:")
        print("   - Verifica que Tailscale esté conectado: tailscale status")
        print("   - Confirma que el servidor remoto esté encendido")
        print("   - Revisa que el puerto 1433 esté abierto en el firewall")
        return False
    
    # Probar sin contraseña primero
    if test_without_password():
        print("\n🎉 ¡Conexión exitosa sin contraseña!")
        print("✅ Puedes usar la configuración actual")
        print("\n📝 Para usar con la aplicación:")
        print("   1. Edita .env.tailscale y deja SQL_SERVER_PASSWORD vacío")
        print("   2. Ejecuta: cp .env.tailscale .env")
        print("   3. Ejecuta: python run.py")
        return True
    
    # Si falla sin contraseña, pedir contraseña
    print("\n🔐 La conexión sin contraseña falló.")
    print("Necesitas configurar una contraseña para el usuario 'sa'.")
    
    # Probar con contraseñas comunes
    common_passwords = [
        "",  # Sin contraseña
        "sa",  # Contraseña igual al usuario
        "admin",  # Contraseña común
        "password",  # Contraseña común
        "123456",  # Contraseña común
    ]
    
    print("\n🔍 Probando contraseñas comunes...")
    for pwd in common_passwords:
        if test_tailscale_connection_with_password(pwd):
            print(f"\n🎉 ¡Conexión exitosa con contraseña: '{pwd}'!")
            print("\n📝 Para usar con la aplicación:")
            print(f"   1. Edita .env.tailscale: SQL_SERVER_PASSWORD={pwd}")
            print("   2. Ejecuta: cp .env.tailscale .env")
            print("   3. Ejecuta: python run.py")
            return True
    
    # Si ninguna funciona, mostrar instrucciones
    print("\n❌ No se pudo conectar con contraseñas comunes.")
    print("\n📋 Necesitas configurar SQL Server:")
    print("\n1️⃣ Abrir SQL Server Management Studio")
    print("2️⃣ Conectarte al servidor local")
    print("3️⃣ Security → Logins → sa → Properties")
    print("4️⃣ Establecer una contraseña segura")
    print("5️⃣ Status → Login: Enabled")
    print("6️⃣ Server Properties → Security → Mixed Mode")
    print("7️⃣ Reiniciar SQL Server")
    print("\n📖 Consulta el archivo CONFIGURAR_PASSWORD_TAILSCALE.md para instrucciones detalladas")
    
    return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 ¡Configuración lista para Tailscale!")
    else:
        print("\n⚠️  Configuración adicional requerida")
    
    input("\nPresiona Enter para continuar...")