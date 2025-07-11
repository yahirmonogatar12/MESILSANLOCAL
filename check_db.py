import sqlite3

# Conectar a la base de datos
conn = sqlite3.connect('app/database/ISEMM_MES.db')
cursor = conn.cursor()

# Obtener lista de tablas
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print("Tablas encontradas:")
for table in tables:
    print(f"- {table[0]}")

print("\n" + "="*50)

# Ver estructura de la tabla control_material_almacen
print("\nEstructura de control_material_almacen:")
cursor.execute("PRAGMA table_info(control_material_almacen)")
columns = cursor.fetchall()
for col in columns:
    print(f"- {col[1]} ({col[2]})")

print("\n" + "="*50)

# Ver algunos datos de ejemplo
print("\nPrimeros 3 registros de control_material_almacen:")
cursor.execute("SELECT * FROM control_material_almacen LIMIT 3")
rows = cursor.fetchall()
for row in rows:
    print(row)

# Buscar el código de ejemplo que mencionaste
print("\n" + "="*50)
print("\nBuscando código de ejemplo '0RH5602C622/202507100001':")
cursor.execute("SELECT * FROM control_material_almacen WHERE codigo_material_recibido LIKE '%0RH5602C622/202507100001%'")
resultado = cursor.fetchall()
if resultado:
    for row in resultado:
        print(row)
else:
    print("No encontrado, buscando patrones similares...")
    cursor.execute("SELECT codigo_material_recibido FROM control_material_almacen WHERE codigo_material_recibido IS NOT NULL AND codigo_material_recibido != ''")
    codigos = cursor.fetchall()
    print("Códigos existentes:")
    for codigo in codigos[:10]:  # Solo los primeros 10
        print(f"- {codigo[0]}")

conn.close()
