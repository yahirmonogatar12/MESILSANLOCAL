#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para diagnosticar y solucionar problema de Foreign Key
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

def fix_foreign_key_issue():
    """Diagnosticar y solucionar problema de clave foránea"""
    try:
        print("🔍 Conectando a MySQL para diagnosticar problema de FK...")
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # 1. Verificar estructura de tabla materiales
        print("\n📋 Estructura de tabla 'materiales':")
        cursor.execute("DESCRIBE materiales")
        materiales_columns = cursor.fetchall()
        for col in materiales_columns:
            if col[0] == 'numero_parte':
                print(f"  - materiales.numero_parte: {col[1]} | {col[2]} | {col[3]} | {col[4]} | {col[5]}")
        
        # 2. Verificar si existe tabla inventario
        cursor.execute("SHOW TABLES LIKE 'inventario'")
        inventario_exists = cursor.fetchone()
        
        if inventario_exists:
            print("\n📋 Estructura de tabla 'inventario':")
            cursor.execute("DESCRIBE inventario")
            inventario_columns = cursor.fetchall()
            for col in inventario_columns:
                if col[0] == 'numero_parte':
                    print(f"  - inventario.numero_parte: {col[1]} | {col[2]} | {col[3]} | {col[4]} | {col[5]}")
        
        # 3. Obtener información detallada de charset y collation
        print("\n🔍 Información detallada de columnas:")
        cursor.execute("""
            SELECT 
                TABLE_NAME, COLUMN_NAME, DATA_TYPE, CHARACTER_SET_NAME, COLLATION_NAME, COLUMN_TYPE
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = 'db_rrpq0erbdujn' 
            AND COLUMN_NAME = 'numero_parte'
            AND TABLE_NAME IN ('materiales', 'inventario')
        """)
        
        columns_info = cursor.fetchall()
        for info in columns_info:
            print(f"  - {info[0]}.{info[1]}: {info[2]} | Charset: {info[3]} | Collation: {info[4]} | Type: {info[5]}")
        
        # 4. Verificar constrainst existentes
        print("\n🔍 Constraints existentes:")
        cursor.execute("""
            SELECT 
                CONSTRAINT_NAME, TABLE_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE 
            WHERE TABLE_SCHEMA = 'db_rrpq0erbdujn' 
            AND REFERENCED_TABLE_NAME IS NOT NULL
        """)
        
        constraints = cursor.fetchall()
        for constraint in constraints:
            print(f"  - {constraint[0]}: {constraint[1]}.{constraint[2]} -> {constraint[3]}.{constraint[4]}")
        
        # 5. Solución: Recrear tabla inventario con la estructura correcta
        print("\n🔧 Aplicando solución...")
        
        # Eliminar tabla inventario si existe (con constraints)
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        cursor.execute("DROP TABLE IF EXISTS inventario")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
        print("✓ Tabla inventario eliminada")
        
        # Obtener la definición exacta de numero_parte de materiales
        cursor.execute("SHOW CREATE TABLE materiales")
        create_materiales = cursor.fetchone()[1]
        print(f"📋 Definición de materiales: {create_materiales}")
        
        # Crear tabla inventario con la misma definición de columna
        create_inventario_query = """
            CREATE TABLE inventario (
                id INT AUTO_INCREMENT PRIMARY KEY,
                numero_parte VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci UNIQUE NOT NULL,
                cantidad_actual INT DEFAULT 0,
                ultima_actualizacion DATETIME DEFAULT NOW(),
                FOREIGN KEY (numero_parte) REFERENCES materiales(numero_parte)
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        """
        
        cursor.execute(create_inventario_query)
        print("✓ Tabla inventario recreada con estructura compatible")
        
        # Verificar que la FK se creó correctamente
        cursor.execute("""
            SELECT 
                CONSTRAINT_NAME, TABLE_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE 
            WHERE TABLE_SCHEMA = 'db_rrpq0erbdujn' 
            AND TABLE_NAME = 'inventario'
            AND REFERENCED_TABLE_NAME IS NOT NULL
        """)
        
        new_constraints = cursor.fetchall()
        for constraint in new_constraints:
            print(f"✓ FK creada: {constraint[0]}: {constraint[1]}.{constraint[2]} -> {constraint[3]}.{constraint[4]}")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("\n✅ Problema de Foreign Key solucionado exitosamente")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = fix_foreign_key_issue()
    sys.exit(0 if success else 1)
