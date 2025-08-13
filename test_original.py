import sys
sys.path.append(".")
from app.db_mysql import registrar_salida_material_mysql

print("=== PRUEBA CON EL MATERIAL ORIGINAL ===")

# Agregar stock al material original para poder hacer la prueba
from app.db_mysql import execute_query

# Actualizar cantidad del material original
update_query = "UPDATE control_material_almacen SET cantidad_actual = 1000 WHERE codigo_material_recibido = %s"
execute_query(update_query, ("0RH5602C622,202508130004",))
print(" Stock agregado al material original")

# Ahora hacer la prueba de salida
salida_data = {
    "codigo_material_recibido": "0RH5602C622,202508130004",
    "numero_lote": "",
    "modelo": "",
    "depto_salida": "",
    "proceso_salida": "AUTO",
    "cantidad_salida": 5,
    "fecha_salida": ""
}

print(f"\\nDatos de entrada: {salida_data}")
print()

resultado = registrar_salida_material_mysql(salida_data)
print(f"Resultado: {resultado}")
print()

# Verificar qué se guardó
verify_query = """
SELECT especificacion_material 
FROM control_material_salida 
WHERE codigo_material_recibido = %s
ORDER BY fecha_registro DESC 
LIMIT 1
"""

verify_result = execute_query(verify_query, (salida_data["codigo_material_recibido"],), fetch="one")
if verify_result:
    actual_spec = verify_result["especificacion_material"]
    print(f" Especificación guardada: \"{actual_spec}\"")
    
    if "56KJ 1/10W SMD" in actual_spec:
        print(" PERFECTO! El material original ahora funciona correctamente")
        print(" Especificación completa transferida de entrada a salida")
    else:
        print(f" Problema: se esperaba especificación completa")
else:
    print(" No se encontró el registro")
