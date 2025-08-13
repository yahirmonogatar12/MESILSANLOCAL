
# CÓDIGO CORREGIDO PARA routes.py
# Reemplazar el INSERT de control_material_salida existente con este:

# Primero obtener el numero_parte desde control_material_almacen
cursor.execute('''
    SELECT numero_parte, especificacion 
    FROM control_material_almacen 
    WHERE codigo_material_recibido = %s
    LIMIT 1
''', (codigo_material_recibido,))

resultado_almacen = cursor.fetchone()
numero_parte_real = resultado_almacen[0] if resultado_almacen else codigo_material_recibido
especificacion_real = resultado_almacen[1] if resultado_almacen else data.get('especificacion_material', '')

# Registrar la salida en control_material_salida CON numero_parte
cursor.execute('''
    INSERT INTO control_material_salida (
        codigo_material_recibido, numero_parte, numero_lote, modelo, depto_salida, 
        proceso_salida, cantidad_salida, fecha_salida, especificacion_material
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
''', (
    codigo_material_recibido,
    numero_parte_real,  # ← NUEVO: numero_parte desde almacen
    data.get('numero_lote', ''),
    data.get('modelo', ''),
    data.get('depto_salida', ''),
    data.get('proceso_salida', ''),
    cantidad_salida,
    fecha_salida,
    especificacion_real  # ← MEJORADO: especificacion desde almacen
))
