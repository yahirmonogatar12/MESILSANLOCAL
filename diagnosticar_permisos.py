import sqlite3

conn = sqlite3.connect('app/database/ISEMM_MES.db')
cursor = conn.cursor()

print("=== DIAGNÓSTICO DEL PROBLEMA ===")

# 1. Verificar todos los roles
print("1. ROLES DISPONIBLES:")
cursor.execute('SELECT id, nombre, descripcion FROM roles ORDER BY nivel DESC')
roles = cursor.fetchall()
for r in roles:
    print(f"   ID:{r[0]} - {r[1]} ({r[2]})")

# 2. Verificar usuarios supervisor/almacén
print("\n2. USUARIOS CON ROLES DE SUPERVISOR/ALMACÉN:")
cursor.execute('''
SELECT u.username, r.nombre as rol, u.activo 
FROM usuarios_sistema u 
JOIN usuario_roles ur ON u.id = ur.usuario_id 
JOIN roles r ON ur.rol_id = r.id 
WHERE r.nombre LIKE '%supervisor%' OR r.nombre LIKE '%almacen%'
''')
usuarios = cursor.fetchall()
for u in usuarios:
    estado = "ACTIVO" if u[2] else "INACTIVO"
    print(f"   {u[0]} - {u[1]} ({estado})")

# 3. Verificar tipos de permisos que existen
print("\n3. TIPOS DE PERMISOS EN LA BASE DE DATOS:")
cursor.execute('SELECT DISTINCT pagina FROM permisos_botones ORDER BY pagina')
paginas = cursor.fetchall()
for p in paginas:
    cursor.execute('SELECT COUNT(*) FROM permisos_botones WHERE pagina = ?', (p[0],))
    count = cursor.fetchone()[0]
    print(f"   {p[0]}: {count} permisos")

# 4. Identificar permisos específicos para dropdowns
print("\n4. PERMISOS DE INFORMACIÓN BÁSICA (DROPDOWNS):")
cursor.execute('SELECT pagina, seccion, boton FROM permisos_botones WHERE pagina = "informacion_basica" ORDER BY seccion, boton')
permisos_info = cursor.fetchall()
for p in permisos_info:
    print(f"   {p[0]} -> {p[1]} -> {p[2]}")

print("\n5. PERMISOS DE LISTAS (POSIBLES DROPDOWNS):")
cursor.execute('SELECT pagina, seccion, boton FROM permisos_botones WHERE pagina LIKE "LISTA_%" ORDER BY pagina, seccion, boton')
permisos_listas = cursor.fetchall()
for p in permisos_listas[:10]:  # Solo primeros 10
    print(f"   {p[0]} -> {p[1]} -> {p[2]}")
if len(permisos_listas) > 10:
    print(f"   ... y {len(permisos_listas) - 10} más")

conn.close()
