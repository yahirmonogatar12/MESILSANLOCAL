import sys
sys.path.append(".")
from app.db_mysql import execute_query

# Verificar si hay triggers en la tabla
query = "SHOW TRIGGERS LIKE \"control_material_salida\""

resultados = execute_query(query, fetch="all")
print("=== TRIGGERS EN control_material_salida ===")

if resultados:
    for row in resultados:
        print(f"Trigger: {row}")
        print()
else:
    print("No hay triggers en la tabla")
    
# También verificar SHOW CREATE TABLE para cualquier detalle extra
query2 = "SHOW CREATE TABLE control_material_salida"
resultado2 = execute_query(query2, fetch="one")
if resultado2:
    print("=== DEFINICIÓN COMPLETA DE LA TABLA ===")
    table_def = resultado2["Create Table"]
    print(table_def)
