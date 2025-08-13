import sys
sys.path.append(".")
from app.db_mysql import execute_query

# Buscar materiales con stock disponible
query = """
SELECT 
    a.codigo_material_recibido,
    a.especificacion,
    a.cantidad_recibida,
    COALESCE(s.total_salidas, 0) as total_salidas,
    (a.cantidad_recibida - COALESCE(s.total_salidas, 0)) as stock_disponible
FROM control_material_almacen a
LEFT JOIN (
    SELECT codigo_material_recibido, SUM(cantidad_salida) as total_salidas
    FROM control_material_salida 
    GROUP BY codigo_material_recibido
) s ON a.codigo_material_recibido = s.codigo_material_recibido
WHERE (a.cantidad_recibida - COALESCE(s.total_salidas, 0)) > 0
ORDER BY stock_disponible DESC
LIMIT 5
"""

materiales = execute_query(query, fetch="all")
print("=== MATERIALES CON STOCK DISPONIBLE ===")
for material in materiales:
    codigo = material["codigo_material_recibido"]
    espec = material["especificacion"]
    stock = material["stock_disponible"]
    print(f"Código: {codigo}")
    print(f"Especificación: {espec}")
    print(f"Stock: {stock}")
    print()
