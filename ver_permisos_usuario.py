import sqlite3

conn = sqlite3.connect('app/database/ISEMM_MES.db')
cursor = conn.cursor()

cursor.execute("""
SELECT pb.pagina, pb.seccion, pb.boton 
FROM rol_permisos_botones rpb 
JOIN permisos_botones pb ON rpb.permiso_boton_id = pb.id 
JOIN usuario_roles ur ON rpb.rol_id = ur.rol_id 
JOIN usuarios_sistema u ON ur.usuario_id = u.id 
WHERE u.username = 'test_user' 
ORDER BY pb.pagina, pb.seccion, pb.boton
""")

permisos = cursor.fetchall()
print(f'Permisos del test_user ({len(permisos)} total):')
for p in permisos:
    print(f'  {p[0]} -> {p[1]} -> {p[2]}')

conn.close()
