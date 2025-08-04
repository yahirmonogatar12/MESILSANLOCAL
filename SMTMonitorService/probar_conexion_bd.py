#!/usr/bin/env python3
"""
Script para probar la conexión a la base de datos remota
"""

import mysql.connector
from datetime import datetime

def probar_conexion():
    """Probar conexión a la base de datos remota"""
    
    print("=" * 60)
    print("PRUEBA DE CONEXIÓN A BASE DE DATOS REMOTA")
    print("=" * 60)
    
    # Configuración de la base de datos remota
    db_config = {
        'host': 'up-de-fra1-mysql-1.db.run-on-seenode.com',
        'port': 11550,
        'user': 'db_rrpq0erbdujn',
        'password': '5fUNbSRcPP3LN9K2I33Pr0ge',
        'database': 'db_rrpq0erbdujn',
        'charset': 'utf8mb4',
        'autocommit': True
    }
    
    print(f"Host: {db_config['host']}")
    print(f"Puerto: {db_config['port']}")
    print(f"Usuario: {db_config['user']}")
    print(f"Base de datos: {db_config['database']}")
    print(f"\nIntentando conectar...")
    
    try:
        # Intentar conexión
        connection = mysql.connector.connect(**db_config)
        print("✅ CONEXIÓN EXITOSA!")
        
        cursor = connection.cursor()
        
        # Verificar tablas
        print(f"\n📋 VERIFICANDO TABLAS:")
        
        # Verificar tabla principal
        cursor.execute("SHOW TABLES LIKE 'historial_cambio_material_smt'")
        tabla_principal = cursor.fetchone()
        
        if tabla_principal:
            print("✅ Tabla 'historial_cambio_material_smt' existe")
            
            # Contar registros
            cursor.execute("SELECT COUNT(*) FROM historial_cambio_material_smt")
            total_registros = cursor.fetchone()[0]
            print(f"   📊 Total de registros: {total_registros}")
            
        else:
            print("⚠️  Tabla 'historial_cambio_material_smt' NO existe")
            print("   Se creará automáticamente al ejecutar el monitor")
        
        # Verificar tabla de control
        cursor.execute("SHOW TABLES LIKE 'archivos_procesados_smt'")
        tabla_control = cursor.fetchone()
        
        if tabla_control:
            print("✅ Tabla 'archivos_procesados_smt' existe")
            
            # Contar archivos procesados
            cursor.execute("SELECT COUNT(*) FROM archivos_procesados_smt")
            total_archivos = cursor.fetchone()[0]
            print(f"   📁 Archivos procesados: {total_archivos}")
            
        else:
            print("⚠️  Tabla 'archivos_procesados_smt' NO existe")
            print("   Se creará automáticamente al ejecutar el monitor")
        
        # Mostrar información del servidor
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()[0]
        print(f"\n🔧 Versión MySQL: {version}")
        
        cursor.execute("SELECT DATABASE()")
        db_actual = cursor.fetchone()[0]
        print(f"📂 Base de datos actual: {db_actual}")
        
        cursor.execute("SELECT USER()")
        usuario_actual = cursor.fetchone()[0]
        print(f"👤 Usuario actual: {usuario_actual}")
        
        print(f"\n✅ PRUEBA DE CONEXIÓN COMPLETADA EXITOSAMENTE")
        print(f"   El servicio SMT puede conectarse correctamente a la BD remota")
        
    except mysql.connector.Error as err:
        print(f"❌ ERROR DE CONEXIÓN: {err}")
        print(f"\n🔧 POSIBLES SOLUCIONES:")
        print(f"   1. Verificar conexión a internet")
        print(f"   2. Comprobar que el host es accesible")
        print(f"   3. Verificar credenciales de base de datos")
        print(f"   4. Comprobar que el puerto 11550 esté abierto")
        
    except Exception as e:
        print(f"❌ ERROR INESPERADO: {e}")
        
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()

def probar_creacion_tablas():
    """Probar la creación de tablas si no existen"""
    
    print(f"\n" + "=" * 60)
    print("PRUEBA DE CREACIÓN DE TABLAS")
    print("=" * 60)
    
    db_config = {
        'host': 'up-de-fra1-mysql-1.db.run-on-seenode.com',
        'port': 11550,
        'user': 'db_rrpq0erbdujn',
        'password': '5fUNbSRcPP3LN9K2I33Pr0ge',
        'database': 'db_rrpq0erbdujn',
        'charset': 'utf8mb4',
        'autocommit': True
    }
    
    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()
        
        # Crear tabla principal si no existe
        print("🔨 Creando tabla 'historial_cambio_material_smt'...")
        create_table_query = """
        CREATE TABLE IF NOT EXISTS historial_cambio_material_smt (
            id INT AUTO_INCREMENT PRIMARY KEY,
            scan_date DATE,
            scan_time TIME,
            slot_no VARCHAR(50),
            result VARCHAR(50),
            previous_barcode VARCHAR(100),
            product_date VARCHAR(50),
            part_name VARCHAR(100),
            quantity VARCHAR(50),
            seq VARCHAR(50),
            vendor VARCHAR(100),
            lotno VARCHAR(100),
            barcode VARCHAR(100),
            feeder_base VARCHAR(100),
            extra_column VARCHAR(100),
            archivo_origen VARCHAR(255),
            fecha_procesado TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_scan_date (scan_date),
            INDEX idx_barcode (barcode),
            INDEX idx_feeder_base (feeder_base)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        
        cursor.execute(create_table_query)
        print("✅ Tabla principal creada/verificada")
        
        # Crear tabla de control si no existe
        print("🔨 Creando tabla 'archivos_procesados_smt'...")
        create_control_query = """
        CREATE TABLE IF NOT EXISTS archivos_procesados_smt (
            id INT AUTO_INCREMENT PRIMARY KEY,
            archivo VARCHAR(255) UNIQUE,
            ruta_completa VARCHAR(500),
            fecha_procesado TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            registros_procesados INT DEFAULT 0
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        
        cursor.execute(create_control_query)
        print("✅ Tabla de control creada/verificada")
        
        print(f"\n✅ TABLAS PREPARADAS CORRECTAMENTE")
        print(f"   El servicio SMT está listo para procesar archivos CSV")
        
    except mysql.connector.Error as err:
        print(f"❌ ERROR CREANDO TABLAS: {err}")
        
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

if __name__ == "__main__":
    probar_conexion()
    probar_creacion_tablas()
    
    print(f"\n" + "=" * 60)
    print("RESUMEN:")
    print("- Si la conexión fue exitosa, el servicio funcionará correctamente")
    print("- Las tablas se crean automáticamente al instalar el servicio")
    print("- El monitor procesará archivos CSV en la base de datos remota")
    print("=" * 60)
