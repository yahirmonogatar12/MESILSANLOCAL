from app.config_mysql import execute_query

# Verificar columnas de la tabla embarques
result = execute_query('DESCRIBE embarques', fetch='all')

print("Columnas de embarques:")
if result:
    for col in result:
        print(f"- {col['Field']} ({col['Type']})")
else:
    print("No se pudieron obtener las columnas")
