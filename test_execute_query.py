import sys
sys.path.append(".")
from app.config_mysql import execute_query
from datetime import datetime

query = """
INSERT INTO control_material_salida (
    codigo_material_recibido, numero_parte, numero_lote, modelo, depto_salida,
    proceso_salida, cantidad_salida, fecha_salida, fecha_registro, especificacion_material
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""

fecha_registro = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

params = (
    "TEST_EXECUTE_QUERY,202508130007",
    "TEST_EXECUTE_QUERY", 
    "",
    "",
    "",
    "SMD",
    1,
    None,
    fecha_registro,
    "56KJ 1/10W SMD - VIA EXECUTE_QUERY"
)

print("=== PRUEBA CON EXECUTE_QUERY ===")
print(f"Parámetros: {params}")
print(f"Especificación que envío: \"{params[9]}\"")

result = execute_query(query, params)
print(f"Resultado execute_query: {result}")

# Verificar inmediatamente qué se guardó
verify_query = """
SELECT especificacion_material 
FROM control_material_salida 
WHERE codigo_material_recibido = %s
ORDER BY fecha_registro DESC 
LIMIT 1
"""

resultado = execute_query(verify_query, ("TEST_EXECUTE_QUERY,202508130007",), fetch="one")
if resultado:
    espec_guardada = resultado["especificacion_material"]
    print(f"Especificación guardada en BD: \"{espec_guardada}\"")
    
    if espec_guardada != params[9]:
        print(f" PROBLEMA: Se envió \"{params[9]}\" pero se guardó \"{espec_guardada}\"")
    else:
        print(" OK: La especificación se guardó correctamente")
else:
    print("No se encontró el registro")
