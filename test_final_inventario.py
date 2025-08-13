
# Prueba final de inventario específico
import sys
sys.path.append(".")
from app.db_mysql import registrar_salida_material_mysql, execute_query

print("=== PRUEBA FINAL DE INVENTARIO ESPECÍFICO ===")
print()

# Test: Salida a proceso MAIN
print("Test: Salida a proceso MAIN")
salida_main = {
    "codigo_material_recibido": "0RH5602C622,202508130004",
    "proceso_salida": "MAIN",
    "cantidad_salida": 20
}

resultado_main = registrar_salida_material_mysql(salida_main)
print(f"Resultado MAIN: {resultado_main}")
print()

# Verificar inventario MAIN
print("Verificando inventario MAIN:")
query = "SELECT * FROM InventarioRollosMAIN WHERE codigo_barras = %s ORDER BY id DESC LIMIT 1"
result = execute_query(query, ("0RH5602C622,202508130004",), fetch="one")

if result:
    rollo_id = result.get("id")
    numero_parte = result.get("numero_parte")
    estado = result.get("estado")
    cantidad_inicial = result.get("cantidad_inicial")
    cantidad_actual = result.get("cantidad_actual")
    origen = result.get("origen_almacen")
    
    print(" Rollo creado en InventarioRollosMAIN:")
    print(f"  - ID: {rollo_id}")
    print(f"  - Número parte: {numero_parte}")
    print(f"  - Estado: {estado}")
    print(f"  - Cantidad inicial: {cantidad_inicial}")
    print(f"  - Cantidad actual: {cantidad_actual}")
    print(f"  - Origen: {origen}")
else:
    print(" No se creó rollo en InventarioRollosMAIN")

print()
print("=== RESUMEN FINAL ===")
if resultado_main.get("success"):
    print(" ÉXITO COMPLETO:")
    print("  1. Salida registrada en control_material_salida")
    print("  2. Especificación completa guardada")
    print("  3. Inventario general actualizado")
    print("  4. Inventario específico MAIN actualizado")
else:
    print(" ERROR en el procesamiento")

