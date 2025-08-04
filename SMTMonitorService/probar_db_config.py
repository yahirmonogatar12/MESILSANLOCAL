#!/usr/bin/env python3
"""
Script para probar y configurar credenciales de base de datos
"""

import mysql.connector
from mysql.connector import Error

def probar_conexion(config, nombre_config):
    """Probar una configuración de base de datos"""
    print(f"\n🔍 Probando configuración: {nombre_config}")
    print(f"   Host: {config['host']}:{config['port']}")
    print(f"   Usuario: {config['user']}")
    print(f"   Base de datos: {config['database']}")
    
    try:
        connection = mysql.connector.connect(**config)
        if connection.is_connected():
            cursor = connection.cursor()
            cursor.execute("SELECT DATABASE();")
            db_name = cursor.fetchone()
            print(f"✅ CONEXIÓN EXITOSA a: {db_name[0]}")
            
            # Verificar si existe la tabla smt_data
            cursor.execute("SHOW TABLES LIKE 'smt_data'")
            tabla_existe = cursor.fetchone()
            
            if tabla_existe:
                print(f"✅ Tabla 'smt_data' encontrada")
                
                # Contar registros
                cursor.execute("SELECT COUNT(*) FROM smt_data")
                count = cursor.fetchone()[0]
                print(f"📊 Registros en tabla: {count}")
                
                return config
            else:
                print(f"⚠️  Tabla 'smt_data' NO encontrada")
                print("   Se necesita crear la tabla")
                return config
            
    except Error as e:
        print(f"❌ Error: {e}")
        return None
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()

def main():
    print("PROBADOR DE CONFIGURACIONES DE BASE DE DATOS")
    print("=" * 60)
    
    # Configuraciones a probar
    configuraciones = [
        {
            'nombre': 'Configuración Original',
            'config': {
                'host': 'up-de-fra1-mysql-1.db.run-on-seenode.com',
                'port': 11550,
                'user': 'db_rrpq0erbdujn_user',
                'password': 'RkQqhq98VCxD24J7',
                'database': 'db_rrpq0erbdujn'
            }
        },
        {
            'nombre': 'Configuración con usuario root',
            'config': {
                'host': 'up-de-fra1-mysql-1.db.run-on-seenode.com',
                'port': 11550,
                'user': 'root',
                'password': 'RkQqhq98VCxD24J7',
                'database': 'db_rrpq0erbdujn'
            }
        },
        {
            'nombre': 'Configuración sin especificar database',
            'config': {
                'host': 'up-de-fra1-mysql-1.db.run-on-seenode.com',
                'port': 11550,
                'user': 'db_rrpq0erbdujn_user',
                'password': 'RkQqhq98VCxD24J7'
            }
        }
    ]
    
    config_exitosa = None
    
    for config_test in configuraciones:
        resultado = probar_conexion(config_test['config'], config_test['nombre'])
        if resultado:
            config_exitosa = resultado
            config_nombre = config_test['nombre']
            break
    
    if config_exitosa:
        print(f"\n🎉 CONFIGURACIÓN EXITOSA ENCONTRADA: {config_nombre}")
        print("=" * 60)
        print("Configuración a usar:")
        print(f"Host: {config_exitosa['host']}")
        print(f"Puerto: {config_exitosa['port']}")
        print(f"Usuario: {config_exitosa['user']}")
        print(f"Base de datos: {config_exitosa.get('database', 'No especificada')}")
        
        # Mostrar código para actualizar
        print(f"\n📝 CÓDIGO PARA ACTUALIZAR EN LOS ARCHIVOS:")
        print("DB_CONFIG = {")
        print(f"    'host': '{config_exitosa['host']}',")
        print(f"    'port': {config_exitosa['port']},")
        print(f"    'user': '{config_exitosa['user']}',")
        print(f"    'password': '{config_exitosa['password']}',")
        if 'database' in config_exitosa:
            print(f"    'database': '{config_exitosa['database']}'")
        print("}")
        
        # Preguntar si crear script de actualización
        print(f"\n¿Quieres que actualice automáticamente todos los archivos? (s/n): ", end="")
        respuesta = input().lower().strip()
        
        if respuesta in ['s', 'si', 'sí', 'y', 'yes']:
            actualizar_archivos(config_exitosa)
        
    else:
        print(f"\n❌ NINGUNA CONFIGURACIÓN FUNCIONÓ")
        print("=" * 60)
        print("Posibles problemas:")
        print("1. Las credenciales han cambiado")
        print("2. El servidor está inaccesible")
        print("3. Tu IP está bloqueada")
        print("4. El puerto está cerrado")
        print("\nContacta al administrador de la base de datos")

def actualizar_archivos(config):
    """Actualizar archivos con la nueva configuración"""
    print(f"\n🔧 ACTUALIZANDO ARCHIVOS...")
    
    archivos_a_actualizar = [
        'smt_monitor_service.py',
        'verificar_datos.py',
        'monitor_tiempo_real.py'
    ]
    
    config_texto = f"""DB_CONFIG = {{
    'host': '{config['host']}',
    'port': {config['port']},
    'user': '{config['user']}',
    'password': '{config['password']}',"""
    
    if 'database' in config:
        config_texto += f"\n    'database': '{config['database']}'"
    
    config_texto += "\n}"
    
    print(f"Nueva configuración:")
    print(config_texto)
    print(f"\nArchivos que necesitan actualización:")
    for archivo in archivos_a_actualizar:
        print(f"  - {archivo}")
    
    print(f"\n⚠️  IMPORTANTE: Debes actualizar manualmente estos archivos")
    print("Reemplaza la sección DB_CONFIG = { ... } con la configuración de arriba")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error en script: {e}")
    
    input("\nPresiona Enter para continuar...")
