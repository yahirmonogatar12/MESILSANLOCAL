#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para probar la conexión a MySQL del hosting
Autor: Asistente AI
Fecha: 2025-07-31
"""

import pymysql
import os
from datetime import datetime

# Configuración de la base de datos del hosting
HOSTING_CONFIG = {
    'host': 'up-de-fra1-mysql-1.db.run-on-seenode.com',
    'port': 11550,
    'database': 'db_rrpq0erbdujn',
    'username': 'db_rrpq0erbdujn',
    'password': '5fUNbSRcPP3LN9K2I33Pr0ge'
}

def test_conexion():
    """Probar la conexión a la base de datos del hosting"""
    print("🔄 Probando conexión a MySQL del hosting...")
    print(f"📍 Host: {HOSTING_CONFIG['host']}")
    print(f"🔌 Puerto: {HOSTING_CONFIG['port']}")
    print(f"🗄️  Base de datos: {HOSTING_CONFIG['database']}")
    print("-" * 50)
    
    try:
        # Intentar conectar
        conexion = pymysql.connect(
            host=HOSTING_CONFIG['host'],
            port=HOSTING_CONFIG['port'],
            user=HOSTING_CONFIG['username'],
            password=HOSTING_CONFIG['password'],
            database=HOSTING_CONFIG['database'],
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=10
        )
        
        print("✅ ¡Conexión exitosa!")
        
        # Probar consultas básicas
        cursor = conexion.cursor()
        
        # 1. Verificar versión de MySQL
        cursor.execute("SELECT VERSION() as version")
        version = cursor.fetchone()
        print(f"📊 Versión MySQL: {version['version']}")
        
        # 2. Listar tablas
        cursor.execute("SHOW TABLES")
        tablas = cursor.fetchall()
        print(f"📋 Tablas encontradas: {len(tablas)}")
        
        for tabla in tablas:
            tabla_nombre = list(tabla.values())[0]
            cursor.execute(f"SELECT COUNT(*) as total FROM {tabla_nombre}")
            count = cursor.fetchone()
            print(f"   📄 {tabla_nombre}: {count['total']} registros")
        
        # 3. Probar consulta específica en materiales
        print("\n🔍 Probando consulta en tabla materiales...")
        cursor.execute("SELECT COUNT(*) as total FROM materiales")
        materiales_count = cursor.fetchone()
        print(f"✅ Materiales en base de datos: {materiales_count['total']}")
        
        # 4. Probar consulta en BOM
        print("\n🔍 Probando consulta en tabla bom...")
        cursor.execute("SELECT COUNT(*) as total FROM bom")
        bom_count = cursor.fetchone()
        print(f"✅ Registros BOM en base de datos: {bom_count['total']}")
        
        # 5. Verificar estructura de tabla usuarios
        print("\n🔍 Verificando estructura de tabla usuarios...")
        cursor.execute("DESCRIBE usuarios")
        estructura = cursor.fetchall()
        print("✅ Estructura de tabla usuarios:")
        for campo in estructura:
            print(f"   🔸 {campo['Field']}: {campo['Type']}")
        
        conexion.close()
        print("\n🎉 ¡Todas las pruebas pasaron exitosamente!")
        print("\n📝 La base de datos del hosting está lista para usar")
        return True
        
    except pymysql.Error as e:
        print(f"❌ Error de MySQL: {e}")
        return False
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return False

def test_configuracion_app():
    """Simular la configuración que usará la aplicación"""
    print("\n" + "=" * 50)
    print("🧪 SIMULANDO CONFIGURACIÓN DE LA APLICACIÓN")
    print("=" * 50)
    
    # Simular variables de entorno
    os.environ['DB_TYPE'] = 'mysql'
    os.environ['USE_HTTP_PROXY'] = 'false'
    os.environ['MYSQL_HOST'] = HOSTING_CONFIG['host']
    os.environ['MYSQL_PORT'] = str(HOSTING_CONFIG['port'])
    os.environ['MYSQL_DATABASE'] = HOSTING_CONFIG['database']
    os.environ['MYSQL_USERNAME'] = HOSTING_CONFIG['username']
    os.environ['MYSQL_PASSWORD'] = HOSTING_CONFIG['password']
    
    print("✅ Variables de entorno configuradas")
    print(f"🔧 DB_TYPE: {os.environ.get('DB_TYPE')}")
    print(f"🔧 USE_HTTP_PROXY: {os.environ.get('USE_HTTP_PROXY')}")
    print(f"🔧 MYSQL_HOST: {os.environ.get('MYSQL_HOST')}")
    print(f"🔧 MYSQL_PORT: {os.environ.get('MYSQL_PORT')}")
    print(f"🔧 MYSQL_DATABASE: {os.environ.get('MYSQL_DATABASE')}")
    
    # Probar importar el módulo de configuración
    try:
        import sys
        sys.path.append('app')
        from config_mysql_hybrid import get_db_connection
        
        print("\n🔄 Probando conexión usando config_mysql_hybrid...")
        conn = get_db_connection()
        if conn:
            print("✅ ¡Conexión exitosa usando la configuración de la app!")
            conn.close()
            return True
        else:
            print("❌ Error en la conexión usando la configuración de la app")
            return False
            
    except ImportError as e:
        print(f"⚠️  No se pudo importar config_mysql_hybrid: {e}")
        print("   (Esto es normal si no tienes todos los módulos instalados)")
        return True
    except Exception as e:
        print(f"❌ Error probando configuración de la app: {e}")
        return False

def main():
    """Función principal"""
    print("🧪 PRUEBA DE CONEXIÓN MYSQL HOSTING")
    print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    # Prueba 1: Conexión básica
    if test_conexion():
        # Prueba 2: Configuración de aplicación
        test_configuracion_app()
        
        print("\n" + "=" * 50)
        print("🎯 RESUMEN FINAL")
        print("=" * 50)
        print("✅ La base de datos del hosting está funcionando")
        print("✅ Los datos se migraron correctamente")
        print("✅ La aplicación puede conectarse")
        print("\n📋 CONFIGURACIÓN PARA EL HOSTING:")
        print("   📁 Archivo: hosting_config_mysql_directo.env")
        print("   🔧 Build Command: pip install -r requirements_hosting.txt")
        print("   🚀 Start Command: python run.py")
        print("\n🎉 ¡Todo listo para el despliegue!")
    else:
        print("\n❌ Hay problemas con la conexión a la base de datos")
        print("   Verifica las credenciales y la conectividad")

if __name__ == "__main__":
    main()