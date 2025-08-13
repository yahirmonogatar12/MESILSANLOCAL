import sys
sys.path.append(".")
from app.config_mysql import convert_sqlite_to_mysql

# Probar qué hace convert_sqlite_to_mysql con la query INSERT
query = """
            INSERT INTO control_material_salida (
                codigo_material_recibido, numero_parte, numero_lote, modelo, depto_salida,
                proceso_salida, cantidad_salida, fecha_salida, fecha_registro, especificacion_material
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

print("Query original:")
print(repr(query))
print()

mysql_query = convert_sqlite_to_mysql(query)
print("Query después de convert_sqlite_to_mysql:")
print(repr(mysql_query))
print()

print("Son iguales?", query == mysql_query)
