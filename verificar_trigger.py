import sys
sys.path.append(".")
from app.db_mysql import execute_query

# Verificar si existe el trigger problemático
query = "SHOW TRIGGERS WHERE `Table` = \"control_material_salida\""

resultados = execute_query(query, fetch="all")
print("=== TRIGGERS EN control_material_salida ===")

if resultados:
    for row in resultados:
        trigger_name = row.get("Trigger", "")
        event = row.get("Event", "")
        timing = row.get("Timing", "")
        statement = row.get("Statement", "")
        print(f"Trigger: {trigger_name}")
        print(f"Evento: {timing} {event}")
        print(f"Statement: {statement}")
        print("---")
else:
    print("No hay triggers en la tabla")
