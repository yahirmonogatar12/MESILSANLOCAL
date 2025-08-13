import sys
sys.path.append(".")
from app.db_mysql import registrar_salida_material_mysql

print("=== PRUEBA FINAL SIN TRIGGER PROBLEMÁTICO ===")

# Datos de prueba
salida_data = {
    "codigo_material_recibido": "TEST789,202508130006",
    "numero_lote": "",
    "modelo": "",
    "depto_salida": "",
    "proceso_salida": "AUTO",
    "cantidad_salida": 2,
    "fecha_salida": ""
}

print(f"Datos de entrada: {salida_data}")
print()

resultado = registrar_salida_material_mysql(salida_data)
print(f"Resultado: {resultado}")
print()

# Verificar qué se guardó en la base de datos
from app.db_mysql import execute_query
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
    print(f" Especificación guardada en BD: \"{actual_spec}\"")
    
    # Comparar con la original
    if "100UF 16V SMD CAPACITOR CERAMIC" in actual_spec:
        print(" ÉXITO TOTAL! Se guardó la especificación completa")
        print(" El problema estaba en el trigger tr_fix_especificacion_salida")
        print(" Ahora las especificaciones se transfieren correctamente de entrada a salida")
    else:
        print(f" Aún hay problemas. Se esperaba especificación completa")
        print(f"   Se obtuvo: \"{actual_spec}\"")
else:
    print(" No se encontró el registro")
