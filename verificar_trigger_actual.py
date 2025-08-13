import sys
sys.path.append(".")
from app.db_mysql import execute_query

# Verificar el trigger actual
query = "SHOW TRIGGERS LIKE \"control_material_salida\""

resultados = execute_query(query, fetch="all")
print("=== TRIGGERS ACTUALES EN control_material_salida ===")

for row in resultados:
    trigger_name = row.get("Trigger", "")
    event = row.get("Event", "")
    timing = row.get("Timing", "")
    statement = row.get("Statement", "")
    
    if "especificacion" in trigger_name.lower():
        print(f"Trigger: {trigger_name}")
        print(f"Evento: {timing} {event}")
        print(f"Statement: {statement}")
        print("---")
