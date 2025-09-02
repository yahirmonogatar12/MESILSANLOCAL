#!/usr/bin/env python3
"""
Script simple para verificar la tabla historial_cambio_material_smt
"""

import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db_mysql import get_connection

def verificar_tabla():
    """Verifica la existencia de la tabla y sus datos"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        print("🔍 Verificando tabla historial_cambio_material_smt...")
        
        # Verificar si la tabla existe
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_schema = DATABASE() 
            AND table_name = 'historial_cambio_material_smt'
        """)
        
        table_exists = cursor.fetchone()[0]
        print(f"📋 Tabla existe: {'✅ Sí' if table_exists > 0 else '❌ No'}")
        
        if table_exists > 0:
            # Mostrar estructura de la tabla
            cursor.execute("DESCRIBE historial_cambio_material_smt")
            columns = cursor.fetchall()
            print("\n📊 Estructura de la tabla:")
            for col in columns:
                print(f"  - {col[0]} ({col[1]})")
            
            # Contar registros
            cursor.execute("SELECT COUNT(*) FROM historial_cambio_material_smt")
            count = cursor.fetchone()[0]
            print(f"\n📈 Total de registros: {count}")
            
            # Mostrar algunos registros de ejemplo
            if count > 0:
                cursor.execute("SELECT * FROM historial_cambio_material_smt LIMIT 3")
                registros = cursor.fetchall()
                print("\n📋 Primeros 3 registros:")
                for i, registro in enumerate(registros, 1):
                    print(f"  {i}. {registro}")
            else:
                print("⚠️  No hay datos disponibles")
                
                # Sugerencia para insertar datos de prueba
                print("\n💡 Insertar datos de prueba:")
                print("   INSERT INTO historial_cambio_material_smt")
                print("   (equipment, slot_no, regist_date, warehousing, regist_quantity, current_quantity)")
                print("   VALUES")
                print("   ('SMT-LINE-01', 'SLOT-001', NOW(), 'WAREHOUSE-A', 100, 95),")
                print("   ('SMT-LINE-02', 'SLOT-002', NOW(), 'WAREHOUSE-B', 200, 180);")
        else:
            print("\n❌ La tabla no existe. Necesita ser creada.")
            print("💡 Crear la tabla con:")
            print("""
CREATE TABLE historial_cambio_material_smt (
    id INT AUTO_INCREMENT PRIMARY KEY,
    equipment VARCHAR(100) NOT NULL,
    slot_no VARCHAR(50) NOT NULL,
    regist_date DATETIME NOT NULL,
    warehousing VARCHAR(100),
    regist_quantity INT DEFAULT 0,
    current_quantity INT DEFAULT 0,
    part_name VARCHAR(200),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_equipment (equipment),
    INDEX idx_slot_no (slot_no),
    INDEX idx_regist_date (regist_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return table_exists > 0

if __name__ == "__main__":
    verificar_tabla()
