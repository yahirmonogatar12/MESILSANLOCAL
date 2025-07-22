import sqlite3

conn = sqlite3.connect('app/database/ISEMM_MES.db')
cursor = conn.cursor()

# Obtener ID del permiso info_control_bom
cursor.execute('SELECT id FROM permisos_botones WHERE pagina = "informacion_basica" AND boton = "info_control_bom"')
permiso_id = cursor.fetchone()[0]
print(f'ID del permiso info_control_bom: {permiso_id}')

# Obtener rol del usuario test_user
cursor.execute('SELECT rol_id FROM usuario_roles ur JOIN usuarios_sistema u ON ur.usuario_id = u.id WHERE u.username = "test_user"')
rol_id = cursor.fetchone()[0]
print(f'Rol ID del test_user: {rol_id}')

# Asignar permiso
cursor.execute('INSERT OR IGNORE INTO rol_permisos_botones (rol_id, permiso_boton_id) VALUES (?, ?)', (rol_id, permiso_id))
conn.commit()
print(f'Permiso info_control_bom asignado al test_user')

# Verificar que se asignó
cursor.execute("""
SELECT pb.pagina, pb.seccion, pb.boton 
FROM rol_permisos_botones rpb 
JOIN permisos_botones pb ON rpb.permiso_boton_id = pb.id 
WHERE rpb.rol_id = ? AND pb.pagina = 'informacion_basica'
""", (rol_id,))

permisos_info = cursor.fetchall()
print(f'Permisos de informacion_basica para test_user: {len(permisos_info)}')
for p in permisos_info:
    print(f'  {p[0]} -> {p[1]} -> {p[2]}')

conn.close()
