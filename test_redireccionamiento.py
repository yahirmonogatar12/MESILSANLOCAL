
# Script para probar el problema de redireccionamiento
import sys
sys.path.append(".")

# Simulemos diferentes escenarios de proceso_salida

test_cases = [
    {
        "nombre": "AUTO - debería usar determinación automática",
        "data": {
            "codigo_material_recibido": "0RH5602C622,202508130004",
            "proceso_salida": "AUTO",
            "cantidad_salida": 1
        }
    },
    {
        "nombre": "PRODUCCION - debería ir a PRODUCCION", 
        "data": {
            "codigo_material_recibido": "0RH5602C622,202508130004",
            "proceso_salida": "PRODUCCION",
            "cantidad_salida": 1
        }
    },
    {
        "nombre": "SMT 1st SIDE - debería convertirse a SMD",
        "data": {
            "codigo_material_recibido": "0RH5602C622,202508130004", 
            "proceso_salida": "SMT 1st SIDE",
            "cantidad_salida": 1
        }
    },
    {
        "nombre": "Vacío - debería usar determinación automática",
        "data": {
            "codigo_material_recibido": "0RH5602C622,202508130004",
            "proceso_salida": "",
            "cantidad_salida": 1
        }
    }
]

print("=== ANÁLISIS DE REDIRECCIONAMIENTO DE PROCESO ===")
print()

for test in test_cases:
    nombre = test["nombre"]
    print(f"Prueba: {nombre}")
    data = test["data"]
    
    # Simular la lógica de la función
    proceso_salida = "PRODUCCION"  # Default
    
    # Simular obtención de propiedad (sabemos que es SMD)
    propiedad_material = "SMD"
    especificacion_original = "56KJ 1/10W SMD"
    
    # Lógica automática 
    if propiedad_material:
        if propiedad_material.upper() == "SMD":
            proceso_salida = "SMD"
    
    print(f"  - Proceso determinado automáticamente: {proceso_salida}")
    
    # Override manual
    proceso_input = data.get("proceso_salida", "")
    if proceso_input and proceso_input not in ["AUTO", ""]:
        proceso_salida_manual = proceso_input
        if proceso_salida_manual == "SMT 1st SIDE":
            proceso_salida = "SMD"
        else:
            proceso_salida = proceso_salida_manual
        print(f"  - Proceso después de override: {proceso_salida}")
    else:
        print(f"  - Sin override manual (valor: {proceso_input})")
    
    print(f"  - RESULTADO FINAL: {proceso_salida}")
    print()

print()
print("El problema es que cuando el usuario selecciona un proceso específico,")
print("pero el sistema siempre redirige a SMD porque encuentra esa palabra en la especificación?")

