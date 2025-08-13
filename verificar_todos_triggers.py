import sys
sys.path.append(".")
from app.db_mysql import execute_query

# Verificar todos los triggers
query = "SHOW TRIGGERS"

resultados = execute_query(query, fetch="all")
print("=== TODOS LOS TRIGGERS ===")

if resultados:
    for row in resultados:
        trigger_name = row.get("Trigger", "")
        table_name = row.get("Table", "")
        event = row.get("Event", "")
        timing = row.get("Timing", "")
        print(f"Trigger: {trigger_name}")
        print(f"Tabla: {table_name}")
        print(f"Evento: {timing} {event}")
        if "salida" in table_name.lower() or "especificacion" in trigger_name.lower():
            statement = row.get("Statement", "")
            print(f"Statement: {statement}")
        print("---")
else:
    print("No hay triggers en la base de datos")
