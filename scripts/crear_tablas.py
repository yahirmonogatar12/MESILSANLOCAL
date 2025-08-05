#!/usr/bin/env python3
"""
Script para crear las tablas necesarias en la base de datos remota
"""

import mysql.connector
from mysql.connector import Error

# Configuración de base de datos
DB_CONFIG = {
    'host': 'up-de-fra1-mysql-1.db.run-on-seenode.com',
    'port': 11550,
    'user': 'db_rrpq0erbdujn',
    'password': '5fUNbSRcPP3LN9K2I33Pr0ge',
    'database': 'db_rrpq0erbdujn',
    'charset': 'utf8mb4'
}

def create_tables():
    """Crea las tablas necesarias para SMT Monitor"""
    connection = None
    cursor = None
    
    try:
        print("Conectando a la base de datos...")
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()
        
        print("Creando tabla principal...")
        # Tabla principal de datos SMT
        create_main_table = """
        CREATE TABLE IF NOT EXISTS historial_cambio_material_smt (
            id INT AUTO_INCREMENT PRIMARY KEY,
            scan_date DATE NOT NULL,
            scan_time TIME NOT NULL,
            slot_no VARCHAR(50),
            result VARCHAR(10),
            part_name VARCHAR(100),
            quantity INT,
            vendor VARCHAR(100),
            lot_no VARCHAR(100),
            barcode VARCHAR(200),
            feeder_base VARCHAR(100),
            previous_barcode VARCHAR(200),
            source_file VARCHAR(255),
            line_number INT NOT NULL,
            mounter_number INT NOT NULL,
            file_hash VARCHAR(64),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            INDEX idx_scan_date (scan_date),
            INDEX idx_part_name (part_name),
            INDEX idx_result (result),
            INDEX idx_line_mounter (line_number, mounter_number),
            INDEX idx_barcode (barcode),
            INDEX idx_file_hash (file_hash),
            INDEX idx_created_at (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """
        
        cursor.execute(create_main_table)
        print("✓ Tabla historial_cambio_material_smt creada")
        
        print("Creando tabla de control...")
        # Tabla de control de archivos procesados
        create_control_table = """
        CREATE TABLE IF NOT EXISTS smt_files_processed (
            id INT AUTO_INCREMENT PRIMARY KEY,
            filename VARCHAR(255) UNIQUE NOT NULL,
            filepath VARCHAR(500),
            line_number INT NOT NULL,
            mounter_number INT NOT NULL,
            file_hash VARCHAR(64),
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            records_count INT DEFAULT 0,
            file_size BIGINT,
            
            INDEX idx_filename (filename),
            INDEX idx_file_hash (file_hash),
            INDEX idx_processed_at (processed_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """
        
        cursor.execute(create_control_table)
        print("✓ Tabla smt_files_processed creada")
        
        connection.commit()
        print("\n🎉 ¡Tablas creadas exitosamente!")
        
        # Verificar tablas
        cursor.execute("SHOW TABLES LIKE '%smt%'")
        tables = cursor.fetchall()
        print(f"\nTablas SMT encontradas: {len(tables)}")
        for table in tables:
            print(f"  - {table[0]}")
            
    except Error as e:
        print(f"❌ Error: {e}")
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
        print("\nConexión cerrada.")

if __name__ == "__main__":
    create_tables()
