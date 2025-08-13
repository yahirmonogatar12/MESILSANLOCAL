import sys
sys.path.append(".")
from app.db_mysql import execute_query

query = "DESCRIBE control_material_almacen"
resultados = execute_query(query, fetch="all")
print("=== ESTRUCTURA DE control_material_almacen ===")
for campo in resultados:
    print(f"Campo: {campo}")
