#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de prueba con credenciales específicas
Usuario: isemm_app_user
Contraseña: ISEMM2025
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

def test_specific_credentials():
    """Probar conexión con credenciales específicas"""
    print(f"\n🔍 Probando conexión con usuario 'isemm_app_user'...")
    
    conn_string = (
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=100.111.108.116,1433;"
        "DATABASE=ISEMM_MES_SQLSERVER;"
        "UID=isemm_app_user;"
        "PWD=ISEMM2025;"
        "Encrypt=yes;"
        "TrustServerCertificate=yes;"
        "Connection Timeout=30;"
    )
    
    try:
        print(f"📝 Usuario: isemm_app_user")
        print(f"🔐 Contraseña: ISEMM2025")
        print(f"🌐 Servidor: 100.111.108.116:1433")
        print(f"🗄️  Base de datos: ISEMM_MES_SQLSERVER")
        
        conn = pyodbc.connect(conn_string)
        
        # Probar consulta simple
        cursor = conn.cursor()
        cursor.execute("SELECT @@VERSION as version, DB_NAME() as database_name, USER_NAME() as login_user")
        result = cursor.fetchone()
        
        print(f"\n✅ ¡Conexión exitosa!")
        print(f"📊 Versión SQL Server: {result.version[:80]}...")
        print(f"🗄️  Base de datos actual: {result.database_name}")
        print(f"👤 Usuario conectado: {result.login_user}")
        
        # Probar permisos básicos
        try:
            cursor.execute("""
                SELECT COUNT(*) as table_count
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_TYPE = 'BASE TABLE'
            """)
            
            table_count = cursor.fetchone().table_count
            print(f"📋 Tablas accesibles: {table_count}")
            
            # Probar tablas específicas
            cursor.execute("""
                SELECT TABLE_NAME 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_TYPE = 'BASE TABLE' 
                AND TABLE_NAME IN ('materials', 'bom_data', 'usuarios')
                ORDER BY TABLE_NAME
            """)
            
            tables = cursor.fetchall()
            if tables:
                table_names = [t.TABLE_NAME for t in tables]
                print(f"🎯 Tablas principales encontradas: {', '.join(table_names)}")
            else:
                print("⚠️  No se encontraron las tablas principales (materials, bom_data, usuarios)")
                
        except Exception as perm_error:
            print(f"⚠️  Error verificando permisos: {perm_error}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        
        # Analizar el tipo de error
        error_str = str(e)
        if "Login failed" in error_str:
            print("\n💡 El error indica fallo de autenticación:")
            print("   - Verifica que el usuario 'isemm_app_user' exista en SQL Server")
            print("   - Confirma que la contraseña 'ISEMM2025' sea correcta")
            print("   - Revisa que el usuario tenga permisos en la base de datos")
        elif "server was not found" in error_str:
            print("\n💡 El servidor no se encuentra:")
            print("   - Verifica que Tailscale esté conectado")
            print("   - Confirma que la IP 100.111.108.116 sea correcta")
        elif "Cannot open database" in error_str:
            print("\n💡 Problema con la base de datos:")
            print("   - Verifica que la base de datos 'ISEMM_MES_SQLSERVER' exista")
            print("   - Confirma que el usuario tenga acceso a esta base de datos")
        
        return False

def main():
    """Función principal"""
    print("🚀 ISEMM MES - Prueba de Credenciales Específicas")
    print("=" * 55)
    print("👤 Usuario: isemm_app_user")
    print("🔐 Contraseña: ISEMM2025")
    print("🌐 Servidor Tailscale: 100.111.108.116:1433")
    print("🗄️  Base de datos: ISEMM_MES_SQLSERVER")
    
    # Probar conectividad de red
    if not test_network_connectivity():
        print("\n💡 Sugerencias para conectividad:")
        print("   - Ejecuta: tailscale status")
        print("   - Verifica que el servidor remoto esté encendido")
        print("   - Confirma que el puerto 1433 esté abierto")
        return False
    
    # Probar credenciales específicas
    if test_specific_credentials():
        print("\n🎉 ¡Conexión exitosa con credenciales específicas!")
        print("\n📝 Para usar con la aplicación:")
        print("   1. Las credenciales ya están configuradas en .env.tailscale")
        print("   2. Ejecuta: copy .env.tailscale .env")
        print("   3. Ejecuta: python run.py")
        print("   4. Accede desde cualquier dispositivo: http://100.111.108.116:5000")
        return True
    else:
        print("\n❌ Error con las credenciales específicas")
        print("\n📋 Pasos para configurar el usuario en SQL Server:")
        print("\n1️⃣ Conectarse a SQL Server Management Studio (local)")
        print("2️⃣ Ejecutar estos comandos SQL:")
        print("\n```sql")
        print("-- Crear el login")
        print("CREATE LOGIN isemm_app_user WITH PASSWORD = 'ISEMM2025';")
        print("")
        print("-- Usar la base de datos")
        print("USE ISEMM_MES_SQLSERVER;")
        print("")
        print("-- Crear el usuario")
        print("CREATE USER isemm_app_user FOR LOGIN isemm_app_user;")
        print("")
        print("-- Asignar permisos")
        print("ALTER ROLE db_datareader ADD MEMBER isemm_app_user;")
        print("ALTER ROLE db_datawriter ADD MEMBER isemm_app_user;")
        print("ALTER ROLE db_ddladmin ADD MEMBER isemm_app_user;")
        print("GRANT EXECUTE TO isemm_app_user;")
        print("```")
        print("\n3️⃣ Habilitar autenticación mixta:")
        print("   - Server Properties → Security → Mixed Mode")
        print("   - Reiniciar SQL Server")
        
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 ¡Todo configurado correctamente!")
    else:
        print("\n⚠️  Se requiere configuración adicional en SQL Server")
    
    input("\nPresiona Enter para continuar...")