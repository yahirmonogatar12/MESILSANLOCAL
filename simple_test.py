import sqlite3
import json

# Conectar directamente a la base de datos
conn = sqlite3.connect('app/database/ISEMM_MES.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Usar la misma query que el endpoint
query = 'SELECT * FROM control_material_almacen WHERE 1=1 ORDER BY fecha_registro DESC'
cursor.execute(query)
rows = cursor.fetchall()

registros = []
for row in rows:
    registros.append({
        'id': row['id'],
        'codigo_material_recibido': row['codigo_material_recibido'],
        'codigo_material_final': row['codigo_material_final'],
        'numero_parte': row['numero_parte'],
        'numero_lote_material': row['numero_lote_material'],
        'propiedad_material': row['propiedad_material'],
        'cantidad_actual': row['cantidad_actual'],
        'cantidad_estandarizada': row['cantidad_estandarizada'],
        'ubicacion_salida': row['ubicacion_salida'],
        'fecha_recibo': row['fecha_recibo'],
        'especificacion': row['especificacion'],
        'material_importacion_local': row['material_importacion_local'],
        'estado_desecho': row['estado_desecho']
    })

print('Registros encontrados:', len(registros))
if registros:
    print('Primer registro para tabla:')
    reg = registros[0]
    print('  codigo_material_recibido:', repr(reg['codigo_material_recibido']))
    print('  codigo_material_final:', repr(reg['codigo_material_final']))
    print('  numero_parte:', repr(reg['numero_parte']))
    print('  numero_lote_material:', repr(reg['numero_lote_material']))
    print('  propiedad_material:', repr(reg['propiedad_material']))
    print('  cantidad_actual:', repr(reg['cantidad_actual']))
    print('  ubicacion_salida:', repr(reg['ubicacion_salida']))
    print('  fecha_recibo:', repr(reg['fecha_recibo']))

conn.close()
print('Test completado')
