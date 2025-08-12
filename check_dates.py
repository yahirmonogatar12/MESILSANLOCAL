import app.config_mysql as config

# Ver las últimas fechas
result = config.execute_query('SELECT fecha, tipo, nparte FROM movimientosimd_smd ORDER BY fecha DESC LIMIT 10', fetch='all')
print('Últimos movimientos:')
for row in result:
    print(f'{row["fecha"]} - {row["tipo"]} - {row["nparte"]}')

print()
# Ver fechas únicas 
result2 = config.execute_query('SELECT DISTINCT DATE(fecha) as fecha_solo FROM movimientosimd_smd ORDER BY fecha_solo DESC LIMIT 10', fetch='all')
print('Fechas disponibles:')
for row in result2:
    print(f'{row["fecha_solo"]}')
