
import sys
sys.path.append(".")
from app.config_mysql import get_mysql_connection

# Conectar y buscar tablas relacionadas con inventario específico
try:
    conn = get_mysql_connection()
    cursor = conn.cursor()
    
    # Buscar todas las tablas que contengan smd, imd, main o rollos
    cursor.execute("SHOW TABLES")
    all_tables = cursor.fetchall()
    
    print("=== TODAS LAS TABLAS EN LA BASE DE DATOS ===")
    inventario_tables = []
    
    for table in all_tables:
        table_name = table[0].lower()
        print(f"- {table[0]}")
        
        # Buscar tablas relacionadas con inventario específico
        if any(keyword in table_name for keyword in ["smd", "imd", "main", "rollo", "inventario"]):
            inventario_tables.append(table[0])
    
    print(f"\\n=== TABLAS RELACIONADAS CON INVENTARIO ESPECÍFICO ===")
    for table in inventario_tables:
        print(f"- {table}")
        
        # Describir estructura de cada tabla
        try:
            cursor.execute(f"DESCRIBE {table}")
            columns = cursor.fetchall()
            print(f"  Columnas: {[col[0] for col in columns]}")
        except Exception as e:
            print(f"  Error describiendo tabla: {e}")
        print()
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")

