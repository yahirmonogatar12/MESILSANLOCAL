import sys
sys.path.append(".")
from app.db_mysql import execute_query

query = """
SELECT 
    codigo_material_recibido,
    especificacion_material,
    proceso_salida,
    cantidad_salida,
    fecha_registro
FROM control_material_salida 
WHERE codigo_material_recibido = %s
ORDER BY fecha_registro DESC 
LIMIT 5
"""

resultados = execute_query(query, ("0RH5602C622,202508130004",), fetch="all")
print("=== ULTIMAS SALIDAS REGISTRADAS ===")

if resultados:
    for i, row in enumerate(resultados, 1):
        codigo = row["codigo_material_recibido"]
        espec = row["especificacion_material"]
        proceso = row["proceso_salida"]
        cantidad = row["cantidad_salida"]
        fecha = row["fecha_registro"]
        print(f"{i}. Código: {codigo}")
        print(f"   Especificación: {espec}")
        print(f"   Proceso: {proceso}")
        print(f"   Cantidad: {cantidad}")
        print(f"   Fecha registro: {fecha}")
        print()
else:
    print("No se encontraron registros")
