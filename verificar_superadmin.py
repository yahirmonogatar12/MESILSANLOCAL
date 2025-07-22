import sqlite3

conn = sqlite3.connect('app/database/ISEMM_MES.db')
cursor = conn.cursor()

print("=== VERIFICACIÓN DE SUPERADMIN ===")

# Verificar usuarios superadmin
cursor.execute('''
SELECT u.username, r.nombre as rol, r.nivel
FROM usuarios_sistema u 
JOIN usuario_roles ur ON u.id = ur.usuario_id 
JOIN roles r ON ur.rol_id = r.id 
WHERE r.nombre = 'superadmin'
''')

usuarios_superadmin = cursor.fetchall()
print('Usuarios superadmin:')
for u in usuarios_superadmin:
    print(f'  {u[0]} - {u[1]} (nivel: {u[2]})')

if usuarios_superadmin:
    username = usuarios_superadmin[0][0]
    print(f"\n=== PERMISOS PARA {username} ===")
    
    # Simular la consulta del endpoint para superadmin
    cursor.execute('SELECT pagina, seccion, boton FROM permisos_botones WHERE activo = 1 ORDER BY pagina, seccion, boton')
    todos_permisos = cursor.fetchall()
    
    print(f"Total de permisos disponibles: {len(todos_permisos)}")
    print("Primeros 10 permisos:")
    for p in todos_permisos[:10]:
        print(f"  {p[0]} -> {p[1]} -> {p[2]}")
        
    # Verificar permisos específicos de informacion_basica
    permisos_info_basica = [p for p in todos_permisos if p[0] == 'informacion_basica']
    print(f"\nPermisos de informacion_basica: {len(permisos_info_basica)}")
    for p in permisos_info_basica:
        print(f"  {p[1]} -> {p[2]}")

conn.close()
