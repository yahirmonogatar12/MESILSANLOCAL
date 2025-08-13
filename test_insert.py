import sys
sys.path.append(".")
from app.db_mysql import execute_query

# Ver qué se está enviando exactamente
print("=== PRUEBA DE INSERCIÓN DIRECTA ===")

query = """
INSERT INTO control_material_salida (
    codigo_material_recibido, numero_parte, numero_lote, modelo, depto_salida,
    proceso_salida, cantidad_salida, fecha_salida, fecha_registro, especificacion_material
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""

from datetime import datetime
fecha_registro = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

params = (
    "TEST123,202508130005",
    "TEST123", 
    "",
    "",
    "",
    "SMD",
    1,
    None,
    fecha_registro,
    "56KJ 1/10W SMD - PRUEBA DIRECTA"
)

print(f"Parámetros a insertar: {params}")
print(f"Especificación que envío: \"{params[9]}\"")

result = execute_query(query, params)
print(f"Resultado inserción: {result}")

# Verificar qué se guardó
query_select = """
SELECT especificacion_material 
FROM control_material_salida 
WHERE codigo_material_recibido = %s
ORDER BY fecha_registro DESC 
LIMIT 1
"""

resultado = execute_query(query_select, ("TEST123,202508130005",), fetch="one")
if resultado:
    espec_guardada = resultado["especificacion_material"]
    print(f"Especificación guardada en BD: \"{espec_guardada}\"")
else:
    print("No se encontró el registro")
