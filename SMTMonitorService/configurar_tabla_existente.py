#!/usr/bin/env python3
"""
Script para configurar con la tabla existente: historial_cambio_material_smt
"""

import mysql.connector
from mysql.connector import Error
import os
import re

# CREDENCIALES CORRECTAS
DB_CONFIG = {
    'host': 'up-de-fra1-mysql-1.db.run-on-seenode.com',
    'port': 11550,
    'user': 'db_rrpq0erbdujn',
    'password': '5fUNbSRcPP3LN9K2I33Pr0ge',
    'database': 'db_rrpq0erbdujn'
}

def verificar_tabla_existente():
    """Verificar la tabla historial_cambio_material_smt"""
    print("VERIFICANDO TABLA EXISTENTE")
    print("=" * 50)
    
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()
        
        print("✅ Conectado a la base de datos")
        
        # Verificar que existe la tabla
        cursor.execute("SHOW TABLES LIKE 'historial_cambio_material_smt'")
        tabla_existe = cursor.fetchone()
        
        if tabla_existe:
            print("✅ Tabla 'historial_cambio_material_smt' encontrada")
            
            # Mostrar estructura
            cursor.execute("DESCRIBE historial_cambio_material_smt")
            columnas = cursor.fetchall()
            
            print(f"\n📋 ESTRUCTURA ACTUAL DE LA TABLA ({len(columnas)} columnas):")
            for i, col in enumerate(columnas, 1):
                print(f"   {i:2d}. {col[0]:25} - {col[1]}")
            
            # Contar registros
            cursor.execute("SELECT COUNT(*) FROM historial_cambio_material_smt")
            count = cursor.fetchone()[0]
            print(f"\n📊 Registros actuales: {count}")
            
            # Mostrar últimos 3 registros si existen
            if count > 0:
                cursor.execute("""
                    SELECT * FROM historial_cambio_material_smt 
                    ORDER BY id DESC 
                    LIMIT 3
                """)
                registros = cursor.fetchall()
                
                print(f"\n📋 ÚLTIMOS 3 REGISTROS:")
                for i, reg in enumerate(registros, 1):
                    print(f"   {i}. ID: {reg[0]} - {reg[1] if len(reg) > 1 else 'N/A'}")
            
            return True
        else:
            print("❌ Tabla 'historial_cambio_material_smt' NO encontrada")
            
            # Mostrar todas las tablas disponibles
            cursor.execute("SHOW TABLES")
            tablas = cursor.fetchall()
            print(f"\nTablas disponibles en la base de datos:")
            for tabla in tablas:
                print(f"   - {tabla[0]}")
            
            return False
        
    except Error as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()

def actualizar_archivo_con_tabla_correcta(archivo_path, config_nueva, nombre_tabla):
    """Actualizar archivo con la configuración y nombre de tabla correctos"""
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
    
    # Nueva configuración
    nueva_config_str = f"""DB_CONFIG = {{
    'host': '{config_nueva['host']}',
    'port': {config_nueva['port']},
    'user': '{config_nueva['user']}',
    'password': '{config_nueva['password']}',
    'database': '{config_nueva['database']}'
}}"""
    
    # Actualizar contenido
    contenido_nuevo = contenido_original
    
    # 1. Actualizar DB_CONFIG
    patron_config = r"DB_CONFIG\s*=\s*\{[^}]*\}"
    if re.search(patron_config, contenido_nuevo):
        contenido_nuevo = re.sub(patron_config, nueva_config_str, contenido_nuevo)
        print(f"   ✅ DB_CONFIG actualizado")
    
    # 2. Cambiar referencias de 'smt_data' a 'historial_cambio_material_smt'
    if 'smt_data' in contenido_nuevo:
        contenido_nuevo = contenido_nuevo.replace('smt_data', nombre_tabla)
        print(f"   ✅ Referencias de tabla actualizadas: smt_data → {nombre_tabla}")
    
    # 3. Escribir archivo actualizado
    with open(archivo_path, 'w', encoding='utf-8') as f:
        f.write(contenido_nuevo)
    
    print(f"✅ Archivo actualizado: {os.path.basename(archivo_path)}")
    return True

def crear_archivos_compatibles():
    """Crear versiones compatibles de los archivos de verificación"""
    print(f"\nCREANDO ARCHIVOS COMPATIBLES CON TABLA EXISTENTE")
    print("=" * 60)
    
    # Crear verificador compatible
    verificador_compatible = """#!/usr/bin/env python3
import mysql.connector
from mysql.connector import Error
from datetime import datetime

DB_CONFIG = {
    'host': 'up-de-fra1-mysql-1.db.run-on-seenode.com',
    'port': 11550,
    'user': 'db_rrpq0erbdujn',
    'password': '5fUNbSRcPP3LN9K2I33Pr0ge',
    'database': 'db_rrpq0erbdujn'
}

def verificar_datos():
    print("VERIFICANDO DATOS EN TABLA EXISTENTE")
    print("=" * 50)
    
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()
        
        # Total de registros
        cursor.execute("SELECT COUNT(*) FROM historial_cambio_material_smt")
        total = cursor.fetchone()[0]
        print(f"📊 Total de registros: {total}")
        
        # Registros de hoy
        cursor.execute('''
            SELECT COUNT(*) FROM historial_cambio_material_smt 
            WHERE DATE(timestamp) = CURDATE()
        ''')
        hoy = cursor.fetchone()[0]
        print(f"📅 Registros de hoy: {hoy}")
        
        # Últimos 5 registros
        print(f"\\n📋 ÚLTIMOS 5 REGISTROS:")
        cursor.execute('''
            SELECT * FROM historial_cambio_material_smt 
            ORDER BY timestamp DESC 
            LIMIT 5
        ''')
        registros = cursor.fetchall()
        
        for i, reg in enumerate(registros, 1):
            print(f"   {i}. ID: {reg[0]} - Timestamp: {reg[1] if len(reg) > 1 else 'N/A'}")
        
        return True
        
    except Error as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

if __name__ == "__main__":
    verificar_datos()
    input("Presiona Enter para continuar...")
"""
    
    with open('verificar_tabla_existente.py', 'w', encoding='utf-8') as f:
        f.write(verificador_compatible)
    
    print("✅ Creado: verificar_tabla_existente.py")

def main():
    print("CONFIGURADOR PARA TABLA EXISTENTE")
    print("=" * 60)
    
    print("CREDENCIALES:")
    print(f"Host: {DB_CONFIG['host']}:{DB_CONFIG['port']}")
    print(f"Usuario: {DB_CONFIG['user']}")
    print(f"Base de datos: {DB_CONFIG['database']}")
    print(f"Tabla objetivo: historial_cambio_material_smt")
    
    # Verificar tabla existente
    if not verificar_tabla_existente():
        print("❌ No se puede continuar sin la tabla correcta")
        return
    
    # Crear archivos compatibles
    crear_archivos_compatibles()
    
    # Actualizar archivos existentes
    print(f"\nACTUALIZANDO ARCHIVOS EXISTENTES")
    print("=" * 40)
    
    archivos_para_actualizar = [
        'verificar_datos.py', 
        'monitor_tiempo_real.py'
    ]
    
    directorio_actual = os.path.dirname(__file__)
    archivos_actualizados = 0
    
    for nombre_archivo in archivos_para_actualizar:
        archivo_path = os.path.join(directorio_actual, nombre_archivo)
        if actualizar_archivo_con_tabla_correcta(archivo_path, DB_CONFIG, 'historial_cambio_material_smt'):
            archivos_actualizados += 1
    
    print(f"\n" + "=" * 60)
    print("✅ CONFIGURACIÓN COMPLETADA")
    print("=" * 60)
    print(f"✅ Tabla 'historial_cambio_material_smt' verificada")
    print(f"✅ {archivos_actualizados} archivos actualizados")
    print(f"✅ Archivo compatible creado: verificar_tabla_existente.py")
    
    print("\nPROXIMOS PASOS:")
    print("1. Probar conexión con tabla existente:")
    print("   python verificar_tabla_existente.py")
    print("\n2. Actualizar el servicio para usar la tabla correcta")
    print("   Necesitas modificar smt_monitor_service.py manualmente")
    print("   Cambiar todas las referencias de 'smt_data' a 'historial_cambio_material_smt'")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error en script: {e}")
    
    input("\nPresiona Enter para continuar...")
