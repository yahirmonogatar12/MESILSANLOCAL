import sys
sys.path.append(".")
from app.db_mysql import registrar_salida_material_mysql, buscar_material_por_codigo_mysql, obtener_total_salidas_material

print("=== SIMULACIÓN EXACTA DEL CÓDIGO DE ROUTES.PY ===")

# Simular exactamente el mismo flujo que routes.py
data = {
    "codigo_material_recibido": "0RH5602C622,202508130004",
    "cantidad_salida": 1,
    "proceso_salida": "AUTO"
}

codigo_recibido = data["codigo_material_recibido"]
cantidad_salida = float(data["cantidad_salida"])

print(f"1. Datos recibidos: {data}")

# Buscar el material (como lo hace routes.py)
material = buscar_material_por_codigo_mysql(codigo_recibido)
if not material:
    print("Material no encontrado")
    exit()

espec_material = material.get("especificacion", "N/A")
print(f"2. Material encontrado: especificacion = {espec_material}")

# Verificar stock (como lo hace routes.py)
total_salidas = obtener_total_salidas_material(codigo_recibido)
cantidad_recibida = float(material.get("cantidad_recibida", 0))
stock_disponible = cantidad_recibida - total_salidas

print(f"3. Stock: recibida={cantidad_recibida}, salidas={total_salidas}, disponible={stock_disponible}")

if cantidad_salida > stock_disponible:
    print(f"Error: Cantidad insuficiente")
    exit()

# Preparar datos para la salida (EXACTAMENTE como routes.py después de la corrección)
salida_data = {
    "codigo_material_recibido": codigo_recibido,
    "numero_lote": data.get("numero_lote", ""),
    "modelo": data.get("modelo", ""),
    "depto_salida": data.get("depto_salida", ""),
    "proceso_salida": data.get("proceso_salida", ""),
    "cantidad_salida": cantidad_salida,
    "fecha_salida": data.get("fecha_salida", "")
}

# Solo incluir especificacion_material si se proporciona explícitamente
if "especificacion_material" in data and data["especificacion_material"]:
    salida_data["especificacion_material"] = data["especificacion_material"]

print(f"4. Datos para salida: {salida_data}")

incluida = "INCLUIDA" if "especificacion_material" in salida_data else "NO INCLUIDA"
print(f"5. Nota: especificacion_material {incluida}")

# Registrar la salida
resultado_salida = registrar_salida_material_mysql(salida_data)
print(f"6. Resultado: {resultado_salida}")
