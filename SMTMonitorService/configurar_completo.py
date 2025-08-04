#!/usr/bin/env python3
"""
Script para crear la tabla smt_data y actualizar credenciales
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

def crear_tabla_smt_data():
    """Crear la tabla smt_data con la estructura correcta"""
    print("CREANDO TABLA SMT_DATA")
    print("=" * 50)
    
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()
        
        print("✅ Conectado a la base de datos")
        
        # SQL para crear la tabla
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS smt_data (
            id INT AUTO_INCREMENT PRIMARY KEY,
            serial_number VARCHAR(100),
            part_number VARCHAR(100),
            work_order VARCHAR(100),
            feeder_slots TEXT,
            components_data TEXT,
            pcb_thickness VARCHAR(50),
            test_result VARCHAR(50),
            test_time VARCHAR(50),
            cycle_time VARCHAR(50),
            operator VARCHAR(100),
            station VARCHAR(100),
            barcode VARCHAR(200),
            feeder_base VARCHAR(200),
            additional_info TEXT,
            linea VARCHAR(10),
            maquina VARCHAR(20),
            timestamp DATETIME,
            source_file VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_timestamp (timestamp),
            INDEX idx_linea_maquina (linea, maquina),
            INDEX idx_barcode (barcode),
            INDEX idx_source_file (source_file)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        
        print("🔧 Creando tabla smt_data...")
        cursor.execute(create_table_sql)
        print("✅ Tabla smt_data creada exitosamente")
        
        # Verificar que la tabla se creó correctamente
        cursor.execute("DESCRIBE smt_data")
        columnas = cursor.fetchall()
        
        print(f"\n📋 ESTRUCTURA DE LA TABLA (Total columnas: {len(columnas)}):")
        for i, col in enumerate(columnas, 1):
            print(f"   {i:2d}. {col[0]:20} - {col[1]}")
        
        # Insertar un registro de prueba
        print(f"\n🧪 Insertando registro de prueba...")
        test_sql = """
        INSERT INTO smt_data (
            serial_number, part_number, work_order, feeder_slots, components_data,
            pcb_thickness, test_result, test_time, cycle_time, operator,
            station, barcode, feeder_base, additional_info, linea, maquina,
            timestamp, source_file
        ) VALUES (
            'TEST001', 'PART001', 'WO001', 'SLOT1,SLOT2', 'COMP1,COMP2',
            '1.6mm', 'PASS', '10:30:45', '120s', 'OPERATOR1',
            'STATION1', 'BC123456', 'BASE001', 'Test data', 'L1', 'L1 m1',
            NOW(), 'test_setup.csv'
        )
        """
        
        cursor.execute(test_sql)
        connection.commit()
        
        # Verificar el registro
        cursor.execute("SELECT COUNT(*) FROM smt_data")
        count = cursor.fetchone()[0]
        print(f"✅ Registro de prueba insertado. Total registros: {count}")
        
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
    patron = r"DB_CONFIG\s*=\s*\{[^}]*\}"
    
    if re.search(patron, contenido_original):
        contenido_nuevo = re.sub(patron, nueva_config_str, contenido_original)
        
        with open(archivo_path, 'w', encoding='utf-8') as f:
            f.write(contenido_nuevo)
        
        print(f"✅ Archivo actualizado: {os.path.basename(archivo_path)}")
        return True
    else:
        print(f"⚠️  No se encontró DB_CONFIG en: {os.path.basename(archivo_path)}")
        return False

def actualizar_todos_los_archivos():
    """Actualizar todos los archivos con las credenciales correctas"""
    print(f"\nACTUALIZANDO ARCHIVOS CON CREDENCIALES CORRECTAS")
    print("=" * 60)
    
    archivos_para_actualizar = [
        'smt_monitor_service.py',
        'verificar_datos.py', 
        'monitor_tiempo_real.py'
    ]
    
    directorio_actual = os.path.dirname(__file__)
    archivos_actualizados = 0
    
    for nombre_archivo in archivos_para_actualizar:
        archivo_path = os.path.join(directorio_actual, nombre_archivo)
        if actualizar_archivo(archivo_path, DB_CONFIG):
            archivos_actualizados += 1
    
    # También actualizar el archivo del servicio instalado
    posibles_rutas_servicio = [
        r'C:\SMTMonitorService\smt_monitor_service.py',
        r'C:\SMTMonitor\smt_monitor_service.py'
    ]
    
    for ruta_servicio in posibles_rutas_servicio:
        if os.path.exists(ruta_servicio):
            print(f"\n🔧 Actualizando servicio instalado: {ruta_servicio}")
            if actualizar_archivo(ruta_servicio, DB_CONFIG):
                archivos_actualizados += 1
    
    return archivos_actualizados

def probar_conexion_final():
    """Probar la conexión final y mostrar datos"""
    print(f"\nPROBANDO CONEXIÓN FINAL")
    print("=" * 40)
    
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()
        
        print("✅ Conexión exitosa")
        
        # Contar registros
        cursor.execute("SELECT COUNT(*) FROM smt_data")
        count = cursor.fetchone()[0]
        print(f"📊 Registros en smt_data: {count}")
        
        # Mostrar último registro
        cursor.execute("""
            SELECT timestamp, source_file, linea, maquina, barcode
            FROM smt_data 
            ORDER BY timestamp DESC 
            LIMIT 1
        """)
        ultimo = cursor.fetchone()
        
        if ultimo:
            print(f"📋 Último registro:")
            print(f"   Fecha: {ultimo[0]}")
            print(f"   Archivo: {ultimo[1]}")
            print(f"   Línea/Máquina: {ultimo[2]}/{ultimo[3]}")
            print(f"   Barcode: {ultimo[4]}")
        
        return True
        
    except Error as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()

def main():
    print("CONFIGURADOR COMPLETO SMT - BASE DE DATOS")
    print("=" * 60)
    
    print("CREDENCIALES CONFIGURADAS:")
    print(f"Host: {DB_CONFIG['host']}:{DB_CONFIG['port']}")
    print(f"Usuario: {DB_CONFIG['user']}")
    print(f"Base de datos: {DB_CONFIG['database']}")
    
    # Paso 1: Crear tabla
    if not crear_tabla_smt_data():
        print("❌ No se pudo crear la tabla. Abortando.")
        return
    
    # Paso 2: Actualizar archivos
    archivos_actualizados = actualizar_todos_los_archivos()
    
    # Paso 3: Probar conexión final
    if probar_conexion_final():
        print(f"\n" + "=" * 60)
        print("🎉 CONFIGURACIÓN COMPLETADA EXITOSAMENTE")
        print("=" * 60)
        print(f"✅ Tabla smt_data creada")
        print(f"✅ {archivos_actualizados} archivos actualizados")
        print(f"✅ Conexión verificada")
        
        print("\nPASOS SIGUIENTES:")
        print("1. Reiniciar el servicio:")
        print("   sc stop SMTMonitorService")
        print("   sc start SMTMonitorService")
        print("\n2. Verificar datos:")
        print("   python verificar_datos.py")
        print("\n3. Monitorear en tiempo real:")
        print("   python monitor_tiempo_real.py")
        
    else:
        print("❌ Hubo problemas en la configuración final")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error en script: {e}")
    
    input("\nPresiona Enter para continuar...")
