
# Probar actualización de inventario específico
import sys
sys.path.append(".")
from app.db_mysql import registrar_salida_material_mysql, execute_query

print("=== PRUEBA DE INVENTARIO ESPECÍFICO ===")
print()

# Primero verificar estado inicial de inventarios específicos
print("Estado inicial de inventarios específicos:")

for tabla in ["InventarioRollosSMD", "InventarioRollosIMD", "InventarioRollosMAIN"]:
    query = f"SELECT COUNT(*) as total FROM {tabla}"
    result = execute_query(query, fetch="one")
    total = result.get("total") if result else 0
    print(f"- {tabla}: {total} rollos")

print()

# Test 1: Salida a proceso SMD
print("Test 1: Salida a proceso SMD")
salida_smd = {
    "codigo_material_recibido": "0RH5602C622,202508130004",
    "proceso_salida": "SMD",
    "cantidad_salida": 10
}

resultado_smd = registrar_salida_material_mysql(salida_smd)
print(f"Resultado SMD: {resultado_smd}")
print()

# Verificar estado final SMD
print("Estado final SMD:")
query = "SELECT COUNT(*) as total FROM InventarioRollosSMD WHERE codigo_barras LIKE %s"
result = execute_query(query, ("%0RH5602C622%",), fetch="one")
total_smd = result.get("total") if result else 0
print(f"- InventarioRollosSMD: {total_smd} rollos del material de prueba")

print()
print("=== RESUMEN ===")
if resultado_smd.get("success"):
    print("SMD: EXITOSO")
else:
    print("SMD: ERROR")

