#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para corregir la estructura de la tabla sesiones_activas en MySQL
"""

import pymysql
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def conectar_mysql():
    """Conectar a MySQL"""
    try:
        connection = pymysql.connect(
            host=os.getenv('MYSQL_HOST', '100.111.108.116'),
            port=int(os.getenv('MYSQL_PORT', 3306)),
            user=os.getenv('MYSQL_USERNAME', 'ILSANMES'),
            password=os.getenv('MYSQL_PASSWORD', 'ISEMM2025'),
            database=os.getenv('MYSQL_DATABASE', 'isemm2025'),
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        print(f"✅ Conectado a MySQL: {os.getenv('MYSQL_HOST')}")
        return connection
    except Exception as e:
        print(f"❌ Error conectando a MySQL: {e}")
        return None

def verificar_estructura_sesiones(connection):
    """Verificar estructura actual de sesiones_activas"""
    cursor = connection.cursor()
    
    try:
        # Verificar si la tabla existe
        cursor.execute("SHOW TABLES LIKE 'sesiones_activas'")
        if not cursor.fetchone():
            print("❌ Tabla sesiones_activas no existe")
            return False
        
        # Obtener estructura actual
        cursor.execute("DESCRIBE sesiones_activas")
        columnas = cursor.fetchall()
        
        print("\n📋 Estructura actual de sesiones_activas:")
        for col in columnas:
            print(f"  - {col['Field']}: {col['Type']} {col['Null']} {col['Key']} {col['Default']}")
        
        # Verificar si tiene usuario_id
        columnas_nombres = [col['Field'] for col in columnas]
        tiene_usuario_id = 'usuario_id' in columnas_nombres
        
        print(f"\n🔍 ¿Tiene columna usuario_id? {tiene_usuario_id}")
        return tiene_usuario_id
        
    except Exception as e:
        print(f"❌ Error verificando estructura: {e}")
        return False
    finally:
        cursor.close()

def corregir_tabla_sesiones(connection):
    """Corregir la tabla sesiones_activas para que tenga la estructura correcta"""
    cursor = connection.cursor()
    
    try:
        print("\n🔧 Corrigiendo tabla sesiones_activas...")
        
        # Eliminar tabla existente
        cursor.execute("DROP TABLE IF EXISTS sesiones_activas")
        print("  - Tabla anterior eliminada")
        
        # Crear tabla con estructura correcta
        create_sql = """
        CREATE TABLE sesiones_activas (
            id INT AUTO_INCREMENT PRIMARY KEY,
            usuario_id INT NOT NULL,
            token VARCHAR(255) UNIQUE NOT NULL,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fecha_expiracion TIMESTAMP NOT NULL,
            ip_address VARCHAR(45),
            user_agent TEXT,
            activa BOOLEAN DEFAULT TRUE,
            INDEX idx_token (token),
            INDEX idx_usuario (usuario_id),
            INDEX idx_expiracion (fecha_expiracion)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        
        cursor.execute(create_sql)
        connection.commit()
        print("  - Tabla recreada con estructura correcta")
        
        # Verificar nueva estructura
        cursor.execute("DESCRIBE sesiones_activas")
        columnas = cursor.fetchall()
        
        print("\n✅ Nueva estructura de sesiones_activas:")
        for col in columnas:
            print(f"  - {col['Field']}: {col['Type']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error corrigiendo tabla: {e}")
        return False
    finally:
        cursor.close()

def main():
    """Función principal"""
    print("🔧 CORRECCIÓN DE TABLA SESIONES_ACTIVAS")
    print("="*50)
    
    # Conectar a MySQL
    connection = conectar_mysql()
    if not connection:
        return
    
    try:
        # Verificar estructura actual
        tiene_usuario_id = verificar_estructura_sesiones(connection)
        
        if not tiene_usuario_id:
            print("\n⚠️ La tabla no tiene la estructura correcta")
            respuesta = input("¿Desea corregir la tabla? (s/n): ")
            
            if respuesta.lower() in ['s', 'si', 'y', 'yes']:
                if corregir_tabla_sesiones(connection):
                    print("\n🎉 Tabla corregida exitosamente")
                    print("\n📝 Próximos pasos:")
                    print("   1. Reiniciar la aplicación Flask")
                    print("   2. Intentar login nuevamente")
                else:
                    print("\n❌ Error corrigiendo la tabla")
            else:
                print("\n⏭️ Corrección cancelada")
        else:
            print("\n✅ La tabla ya tiene la estructura correcta")
    
    except Exception as e:
        print(f"❌ Error en el proceso: {e}")
    
    finally:
        connection.close()
        print("\n🔌 Conexión cerrada")

if __name__ == "__main__":
    main()