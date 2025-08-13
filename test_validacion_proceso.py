
# Probar la nueva validación de proceso de salida
import sys
sys.path.append(".")
from app.db_mysql import registrar_salida_material_mysql

print("=== PRUEBA DE VALIDACIÓN DE PROCESO DE SALIDA ===")
print()

# Test 1: proceso_salida vacío (debería fallar)
print("Test 1: proceso_salida vacío")
salida_vacia = {
    "codigo_material_recibido": "0RH5602C622,202508130004",
    "proceso_salida": "",
    "cantidad_salida": 1
}
resultado1 = registrar_salida_material_mysql(salida_vacia)
print(f"Resultado: {resultado1}")
print()

# Test 2: proceso_salida AUTO (debería fallar)
print("Test 2: proceso_salida AUTO")
salida_auto = {
    "codigo_material_recibido": "0RH5602C622,202508130004", 
    "proceso_salida": "AUTO",
    "cantidad_salida": 1
}
resultado2 = registrar_salida_material_mysql(salida_auto)
print(f"Resultado: {resultado2}")
print()

# Test 3: proceso_salida específico (debería funcionar)
print("Test 3: proceso_salida PRODUCCION")
salida_produccion = {
    "codigo_material_recibido": "0RH5602C622,202508130004",
    "proceso_salida": "PRODUCCION", 
    "cantidad_salida": 1
}
resultado3 = registrar_salida_material_mysql(salida_produccion)
print(f"Resultado: {resultado3}")
print()

print("=== RESUMEN ===")
if not resultado1.get("success"):
    print("- Proceso vacío: BLOQUEADO correctamente")
else:
    print("- Proceso vacío: ERROR - se permitió")

if not resultado2.get("success"):
    print("- Proceso AUTO: BLOQUEADO correctamente")
else:
    print("- Proceso AUTO: ERROR - se permitió")
    
if resultado3.get("success"):
    print("- Proceso específico: PERMITIDO correctamente")
else:
    print("- Proceso específico: ERROR - se bloqueó")

