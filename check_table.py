import sys
sys.path.append(".")
from app.db_mysql import execute_query

# Verificar la estructura de la tabla
query = "DESCRIBE control_material_salida"

resultados = execute_query(query, fetch="all")
print("=== ESTRUCTURA DE LA TABLA control_material_salida ===")

if resultados:
    for row in resultados:
        field = row["Field"]
        type_info = row["Type"]
        null_info = row["Null"]
        key_info = row["Key"]
        default_info = row["Default"]
        extra_info = row["Extra"]
        print(f"Campo: {field}")
        print(f"  Tipo: {type_info}")
        print(f"  Null: {null_info}")
        print(f"  Key: {key_info}")
        print(f"  Default: {default_info}")
        print(f"  Extra: {extra_info}")
        print()
else:
    print("No se pudo obtener la estructura")
