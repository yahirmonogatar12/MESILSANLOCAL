import sys
sys.path.append(".")
from app.db_mysql import execute_query
import pymysql

print("=== COMPARACIÓN EXECUTE_QUERY VS PYMYSQL DIRECTO ===")

# Datos de prueba
codigo = "COMPARACION123,202508130007"
especificacion_completa = "PRUEBA DIRECTA PYMYSQL VS EXECUTE_QUERY COMPLETA"

print(f"Especificación a insertar: \"{especificacion_completa}\"")
print()

# MÉTODO 1: Usando execute_query (el que falla)
print("1. USANDO execute_query:")
query1 = """
INSERT INTO control_material_salida (
    codigo_material_recibido, numero_parte, numero_lote, modelo, depto_salida,
    proceso_salida, cantidad_salida, fecha_salida, fecha_registro, especificacion_material
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""

from datetime import datetime
fecha_registro = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

params1 = (codigo, "COMPARACION123", "", "", "", "SMD", 1, None, fecha_registro, especificacion_completa)

result1 = execute_query(query1, params1)
print(f"Resultado inserción: {result1}")

# Verificar qué se guardó
verify_query1 = "SELECT especificacion_material FROM control_material_salida WHERE codigo_material_recibido = %s ORDER BY fecha_registro DESC LIMIT 1"
result_verify1 = execute_query(verify_query1, (codigo,), fetch="one")
if result_verify1:
    guardado1 = result_verify1["especificacion_material"]
    print(f"Especificación guardada: \"{guardado1}\"")
    print(f"Match: {especificacion_completa == guardado1}")
else:
    print("No se encontró registro")

print()

# MÉTODO 2: Usando PyMySQL directo
print("2. USANDO PyMySQL DIRECTO:")
try:
    from app.config_mysql import get_mysql_connection
    connection = get_mysql_connection()
    cursor = connection.cursor()
    
    codigo2 = "COMPARACION456,202508130008"
    query2 = """
    INSERT INTO control_material_salida (
        codigo_material_recibido, numero_parte, numero_lote, modelo, depto_salida,
        proceso_salida, cantidad_salida, fecha_salida, fecha_registro, especificacion_material
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    params2 = (codigo2, "COMPARACION456", "", "", "", "SMD", 1, None, fecha_registro, especificacion_completa)
    
    cursor.execute(query2, params2)
    connection.commit()
    print(f"Filas afectadas: {cursor.rowcount}")
    
    # Verificar qué se guardó
    cursor.execute("SELECT especificacion_material FROM control_material_salida WHERE codigo_material_recibido = %s ORDER BY fecha_registro DESC LIMIT 1", (codigo2,))
    result2 = cursor.fetchone()
    if result2:
        guardado2 = result2[0]  # PyMySQL directo retorna tuplas
        print(f"Especificación guardada: \"{guardado2}\"")
        print(f"Match: {especificacion_completa == guardado2}")
    else:
        print("No se encontró registro")
        
    cursor.close()
    connection.close()
    
except Exception as e:
    print(f"Error con PyMySQL directo: {e}")

