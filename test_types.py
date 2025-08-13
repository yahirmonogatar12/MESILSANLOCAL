import sys
sys.path.append(".")
from app.db_mysql import registrar_salida_material_mysql

# Simular datos como los envía el frontend (sin especificacion_material)
salida_data = {
    "codigo_material_recibido": "0RH5602C622,202508130004",
    "numero_lote": "",
    "modelo": "",
    "depto_salida": "",
    "proceso_salida": "AUTO",
    "cantidad_salida": 1,
    "fecha_salida": ""
}

print("=== ANÁLISIS DETALLADO DE TIPOS ===")

resultado = registrar_salida_material_mysql(salida_data)
