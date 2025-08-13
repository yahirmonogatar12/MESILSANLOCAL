
# Probar actualización de inventario específico corregida
import sys
sys.path.append(".")
from app.db_mysql import registrar_salida_material_mysql, execute_query

print("=== PRUEBA DE INVENTARIO ESPECÍFICO CORREGIDA ===")
print()

# Test: Salida a proceso IMD (para probar funcionalidad completa)
print("Test: Salida a proceso IMD")
salida_imd = {
    "codigo_material_recibido": "0RH5602C622,202508130004",
    "proceso_salida": "IMD",
    "cantidad_salida": 15
}

resultado_imd = registrar_salida_material_mysql(salida_imd)
print(f"Resultado IMD: {resultado_imd}")
print()

# Verificar que se creó entrada en InventarioRollosIMD
print("Verificando inventario IMD:")
query = "SELECT * FROM InventarioRollosIMD WHERE codigo_barras = %s"
result = execute_query(query, ("0RH5602C622,202508130004",), fetch="all")

if result:
    for rollo in result:
        rollo_id = rollo.get("id")
        numero_parte = rollo.get("numero_parte")
        codigo_barras = rollo.get("codigo_barras")
        estado = rollo.get("estado")
        cantidad_inicial = rollo.get("cantidad_inicial")
        cantidad_actual = rollo.get("cantidad_actual")
        fecha_entrada = rollo.get("fecha_entrada")
        
        print(f"- ID: {rollo_id}")
        print(f"  Número parte: {numero_parte}")
        print(f"  Código barras: {codigo_barras}")
        print(f"  Estado: {estado}")
        print(f"  Cantidad inicial: {cantidad_inicial}")
        print(f"  Cantidad actual: {cantidad_actual}")
        print(f"  Fecha entrada: {fecha_entrada}")
        print()
else:
    print("- No se encontraron rollos en InventarioRollosIMD")

print("=== RESUMEN ===")
if resultado_imd.get("success"):
    print("ÉXITO: Salida procesada y inventario específico actualizado")
else:
    print("ERROR: Falló el procesamiento")

