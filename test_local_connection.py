#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de prueba para verificar la conexión local a SQL Server
Este script prueba la conexión directamente sin Tailscale
"""

import os
import sys
import pyodbc
from dotenv import load_dotenv

def test_local_connection():
    """Probar conexión local a SQL Server"""
    print("🔍 Probando conexión local a SQL Server...")
    
    # Configuración local directa
    conn_string = (
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=localhost\\SQLEXPRESS;"
        "DATABASE=ISEMM_MES_SQLSERVER;"
        "Trusted_Connection=yes;"
        "Encrypt=yes;"
        "TrustServerCertificate=yes;"
    )
    
    try:
        print(f"📝 Cadena de conexión: {conn_string}")
        
        # Intentar conexión
        conn = pyodbc.connect(conn_string)
        
        # Probar consulta simple
        cursor = conn.cursor()
        cursor.execute("SELECT @@VERSION as version, DB_NAME() as database_name")
        result = cursor.fetchone()
        
        print(f"✅ Conexión local exitosa")
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
        print(f"❌ Error de conexión local: {e}")
        return False

def test_drivers():
    """Verificar drivers ODBC disponibles"""
    print("\n🔍 Verificando drivers ODBC...")
    drivers = [x for x in pyodbc.drivers() if 'SQL Server' in x]
    if drivers:
        print(f"✅ Drivers encontrados: {', '.join(drivers)}")
    else:
        print("❌ No se encontraron drivers de SQL Server")
    return len(drivers) > 0

def main():
    """Función principal"""
    print("🚀 ISEMM MES - Prueba de Conexión Local SQL Server")
    print("=" * 55)
    
    # Verificar drivers
    if not test_drivers():
        return False
    
    # Probar conexión local
    if test_local_connection():
        print("\n🎉 ¡Conexión local exitosa!")
        print("✅ El sistema puede conectarse a SQL Server localmente")
        print("\n💡 Para usar con Tailscale, necesitarás:")
        print("   1. Configurar SQL Server Authentication")
        print("   2. Crear un usuario específico con contraseña")
        print("   3. Habilitar conexiones remotas")
        return True
    else:
        print("\n❌ Error en la conexión local")
        print("💡 Verifica que:")
        print("   - SQL Server esté ejecutándose")
        print("   - La base de datos ISEMM_MES_SQLSERVER exista")
        print("   - Tu usuario tenga permisos")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)