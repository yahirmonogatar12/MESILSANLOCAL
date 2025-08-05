#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para recrear las tablas con charset correcto
"""

import mysql.connector
import sys

# Configuración MySQL
DB_CONFIG = {
    'host': 'up-de-fra1-mysql-1.db.run-on-seenode.com',
    'port': 11550,
    'user': 'db_rrpq0erbdujn',
    'password': '5fUNbSRcPP3LN9K2I33Pr0ge',
    'database': 'db_rrpq0erbdujn',
    'charset': 'utf8mb4'
}

def recreate_tables():
    """Recrear tablas con charset correcto"""
    try:
        print("🔧 Conectando a MySQL para recrear tablas...")
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Deshabilitar checks de foreign keys temporalmente
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        
        # Lista de tablas a recrear en orden
        tables_to_drop = ['bom', 'movimientos_inventario', 'inventario']
        
        print("\n🗑️ Eliminando tablas existentes...")
        for table in tables_to_drop:
            try:
                cursor.execute(f"DROP TABLE IF EXISTS {table}")
                print(f"✓ Tabla {table} eliminada")
            except Exception as e:
                print(f"⚠️ Error eliminando {table}: {e}")
        
        # Reactivar checks de foreign keys
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
        
        # Recrear tablas con charset correcto
        print("\n🔨 Recreando tablas con charset correcto...")
        
        # Tabla inventario
        cursor.execute('''
            CREATE TABLE inventario (
                id INT AUTO_INCREMENT PRIMARY KEY,
                numero_parte VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci UNIQUE NOT NULL,
                cantidad_actual INT DEFAULT 0,
                ultima_actualizacion DATETIME DEFAULT NOW(),
                FOREIGN KEY (numero_parte) REFERENCES materiales(numero_parte)
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        ''')
        print("✓ Tabla inventario recreada")
        
        # Tabla movimientos_inventario
        cursor.execute('''
            CREATE TABLE movimientos_inventario (
                id INT AUTO_INCREMENT PRIMARY KEY,
                numero_parte VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
                tipo_movimiento VARCHAR(50) NOT NULL,
                cantidad INT NOT NULL,
                comentarios TEXT,
                fecha_movimiento DATETIME DEFAULT NOW(),
                usuario VARCHAR(255),
                FOREIGN KEY (numero_parte) REFERENCES materiales(numero_parte)
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        ''')
        print("✓ Tabla movimientos_inventario recreada")
        
        # Tabla BOM
        cursor.execute('''
            CREATE TABLE bom (
                id INT AUTO_INCREMENT PRIMARY KEY,
                modelo VARCHAR(255) NOT NULL,
                numero_parte VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
                descripcion TEXT,
                cantidad INT DEFAULT 1,
                side VARCHAR(50),
                ubicacion VARCHAR(255),
                categoria VARCHAR(255),
                proveedor VARCHAR(255),
                fecha_registro DATETIME DEFAULT NOW(),
                UNIQUE KEY unique_bom (modelo, numero_parte, side),
                FOREIGN KEY (numero_parte) REFERENCES materiales(numero_parte)
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        ''')
        print("✓ Tabla bom recreada")
        
        # Verificar que las foreign keys se crearon correctamente
        print("\n🔍 Verificando foreign keys...")
        cursor.execute("""
            SELECT 
                CONSTRAINT_NAME, TABLE_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE 
            WHERE TABLE_SCHEMA = 'db_rrpq0erbdujn' 
            AND REFERENCED_TABLE_NAME IS NOT NULL
            AND TABLE_NAME IN ('inventario', 'movimientos_inventario', 'bom')
        """)
        
        constraints = cursor.fetchall()
        for constraint in constraints:
            print(f"✓ FK: {constraint[1]}.{constraint[2]} -> {constraint[3]}.{constraint[4]}")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("\n✅ Tablas recreadas exitosamente con charset compatible")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = recreate_tables()
    sys.exit(0 if success else 1)
