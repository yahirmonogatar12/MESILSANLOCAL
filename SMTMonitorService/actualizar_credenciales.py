#!/usr/bin/env python3
"""
Script para actualizar credenciales de base de datos en todos los archivos
"""

import os
import mysql.connector
from mysql.connector import Error

# CREDENCIALES CORRECTAS
DB_CONFIG_CORRECTO = {
    'host': 'up-de-fra1-mysql-1.db.run-on-seenode.com',
    'port': 11550,
    'user': 'db_rrpq0erbdujn',
    'password': '5fUNbSRcPP3LN9K2I33Pr0ge',
    'database': 'db_rrpq0erbdujn'
}

def probar_credenciales_correctas():
    """Probar las credenciales correctas"""
    print("PROBANDO CREDENCIALES CORRECTAS")
    print("=" * 50)
    
    print(f"Host: {DB_CONFIG_CORRECTO['host']}:{DB_CONFIG_CORRECTO['port']}")
    print(f"Usuario: {DB_CONFIG_CORRECTO['user']}")
    print(f"Base de datos: {DB_CONFIG_CORRECTO['database']}")
    
    try:
        connection = mysql.connector.connect(**DB_CONFIG_CORRECTO)
        cursor = connection.cursor()
        
        print("✅ CONEXIÓN EXITOSA!")
        
        # Verificar base de datos
        cursor.execute("SELECT DATABASE();")
        db_name = cursor.fetchone()
        print(f"✅ Conectado a base de datos: {db_name[0]}")
        
        # Verificar tabla smt_data
        cursor.execute("SHOW TABLES LIKE 'smt_data'")
        tabla_existe = cursor.fetchone()
        
        if tabla_existe:
            print("✅ Tabla 'smt_data' encontrada")
            
            # Contar registros
            cursor.execute("SELECT COUNT(*) FROM smt_data")
            count = cursor.fetchone()[0]
            print(f"📊 Registros actuales en tabla: {count}")
        else:
            print("⚠️  Tabla 'smt_data' NO encontrada - se creará automáticamente")
        
        return True
        
    except Error as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()

def actualizar_archivo(archivo_path, config_nueva):
    """Actualizar un archivo con la nueva configuración"""
    if not os.path.exists(archivo_path):
        print(f"⚠️  Archivo no encontrado: {archivo_path}")
        return False
    
    print(f"🔧 Actualizando: {os.path.basename(archivo_path)}")
    
    # Crear backup
    backup_path = archivo_path + ".backup"
    with open(archivo_path, 'r', encoding='utf-8') as f:
        contenido_original = f.read()
    
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(contenido_original)
    
    # Nueva configuración como string
    nueva_config_str = f"""DB_CONFIG = {{
    'host': '{config_nueva['host']}',
    'port': {config_nueva['port']},
    'user': '{config_nueva['user']}',
    'password': '{config_nueva['password']}',
    'database': '{config_nueva['database']}'
}}"""
    
    # Buscar y reemplazar la configuración antigua
    import re
    
    # Patrón para encontrar DB_CONFIG = { ... }
    patron = r"DB_CONFIG\s*=\s*\{[^}]*\}"
    
    if re.search(patron, contenido_original):
        contenido_nuevo = re.sub(patron, nueva_config_str, contenido_original)
        
        with open(archivo_path, 'w', encoding='utf-8') as f:
            f.write(contenido_nuevo)
        
        print(f"✅ Archivo actualizado: {os.path.basename(archivo_path)}")
        print(f"   Backup creado: {os.path.basename(backup_path)}")
        return True
    else:
        print(f"⚠️  No se encontró DB_CONFIG en: {os.path.basename(archivo_path)}")
        return False

def main():
    print("ACTUALIZADOR DE CREDENCIALES DE BASE DE DATOS")
    print("=" * 60)
    
    # Primero probar las credenciales
    if not probar_credenciales_correctas():
        print("❌ Las credenciales no funcionan. Revisa la configuración.")
        return
    
    print("\n" + "=" * 60)
    print("ACTUALIZANDO ARCHIVOS CON CREDENCIALES CORRECTAS")
    print("=" * 60)
    
    # Archivos a actualizar
    archivos_para_actualizar = [
        'smt_monitor_service.py',
        'verificar_datos.py', 
        'monitor_tiempo_real.py'
    ]
    
    # Buscar archivos en el directorio actual
    directorio_actual = os.path.dirname(__file__)
    
    archivos_actualizados = 0
    
    for nombre_archivo in archivos_para_actualizar:
        archivo_path = os.path.join(directorio_actual, nombre_archivo)
        if actualizar_archivo(archivo_path, DB_CONFIG_CORRECTO):
            archivos_actualizados += 1
    
    # También actualizar el archivo del servicio instalado si existe
    archivo_servicio_instalado = r'C:\SMTMonitorService\smt_monitor_service.py'
    if os.path.exists(archivo_servicio_instalado):
        print(f"\n🔧 Actualizando servicio instalado...")
        if actualizar_archivo(archivo_servicio_instalado, DB_CONFIG_CORRECTO):
            archivos_actualizados += 1
    
    archivo_servicio_instalado2 = r'C:\SMTMonitor\smt_monitor_service.py'
    if os.path.exists(archivo_servicio_instalado2):
        print(f"\n🔧 Actualizando servicio instalado (ruta 2)...")
        if actualizar_archivo(archivo_servicio_instalado2, DB_CONFIG_CORRECTO):
            archivos_actualizados += 1
    
    print(f"\n" + "=" * 60)
    print(f"✅ ACTUALIZACIÓN COMPLETADA")
    print(f"   Archivos actualizados: {archivos_actualizados}")
    print("=" * 60)
    
    print("\nNUEVA CONFIGURACIÓN APLICADA:")
    print(f"Host: {DB_CONFIG_CORRECTO['host']}:{DB_CONFIG_CORRECTO['port']}")
    print(f"Usuario: {DB_CONFIG_CORRECTO['user']}")
    print(f"Base de datos: {DB_CONFIG_CORRECTO['database']}")
    
    print("\nPASOS SIGUIENTES:")
    print("1. Reiniciar el servicio:")
    print("   sc stop SMTMonitorService")
    print("   sc start SMTMonitorService")
    print("\n2. Probar conexión:")
    print("   python verificar_datos.py")
    print("\n3. Monitorear en tiempo real:")
    print("   python monitor_tiempo_real.py")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error en script: {e}")
    
    input("\nPresiona Enter para continuar...")
