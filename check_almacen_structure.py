
import sys
sys.path.append(".")
from app.config_mysql import get_mysql_connection

# Verificar estructura de control_material_almacen
try:
    conn = get_mysql_connection()
    cursor = conn.cursor()
    
    cursor.execute("DESCRIBE control_material_almacen")
    columns = cursor.fetchall()
    
    print("=== ESTRUCTURA DE control_material_almacen ===")
    for col in columns:
        print(f"- {col[0]} ({col[1]})")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")

