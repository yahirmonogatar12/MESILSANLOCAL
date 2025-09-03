import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db_mysql import get_connection

try:
    conn = get_connection()
    cursor = conn.cursor()
    
    # Ver estructura de la tabla
    cursor.execute("DESCRIBE control_material_almacen")
    columns = cursor.fetchall()
    
    print("=== ESTRUCTURA DE LA TABLA ===")
    for col in columns:
        field_name = col[0]
        field_type = col[1]
        null_allowed = col[2]
        key = col[3]
        default = col[4]
        extra = col[5]
        print(f"{field_name}: {field_type} (Null: {null_allowed}, Key: {key}, Default: {default}, Extra: {extra})")
        
    # Ver valores únicos en estado_desecho
    cursor.execute("SELECT DISTINCT estado_desecho FROM control_material_almacen LIMIT 10")
    valores = cursor.fetchall()
    
    print("\n=== VALORES ÚNICOS EN estado_desecho ===")
    for val in valores:
        print(f"Valor: {val[0]} (Tipo: {type(val[0])})")
        
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")
