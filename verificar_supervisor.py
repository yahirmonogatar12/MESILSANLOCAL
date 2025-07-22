import sqlite3

conn = sqlite3.connect('app/database/ISEMM_MES.db')
cursor = conn.cursor()

print("=== PERMISOS DEL SUPERVISOR DE ALMACÉN ===")

# Verificar permisos asignados al supervisor_almacen
cursor.execute('''
SELECT pb.pagina, pb.seccion, pb.boton 
FROM rol_permisos_botones rpb
JOIN permisos_botones pb ON rpb.permiso_boton_id = pb.id
JOIN roles r ON rpb.rol_id = r.id
WHERE r.nombre = 'supervisor_almacen'
ORDER BY pb.pagina, pb.seccion, pb.boton
''')

permisos = cursor.fetchall()
print(f"Total permisos para supervisor_almacen: {len(permisos)}")

# Agrupar por página
permisos_por_pagina = {}
for p in permisos:
    pagina = p[0]
    if pagina not in permisos_por_pagina:
        permisos_por_pagina[pagina] = []
    permisos_por_pagina[pagina].append(f"{p[1]} -> {p[2]}")

for pagina, lista_permisos in permisos_por_pagina.items():
    print(f"\n{pagina} ({len(lista_permisos)} permisos):")
    for permiso in lista_permisos:
        print(f"   {permiso}")

# Verificar específicamente permisos de informacion_basica
print(f"\n=== PERMISOS DE informacion_basica PARA supervisor_almacen ===")
cursor.execute('''
SELECT pb.seccion, pb.boton 
FROM rol_permisos_botones rpb
JOIN permisos_botones pb ON rpb.permiso_boton_id = pb.id
JOIN roles r ON rpb.rol_id = r.id
WHERE r.nombre = 'supervisor_almacen' AND pb.pagina = 'informacion_basica'
ORDER BY pb.seccion, pb.boton
''')

permisos_info = cursor.fetchall()
print(f"Permisos de información básica: {len(permisos_info)}")
for p in permisos_info:
    print(f"   {p[0]} -> {p[1]}")

conn.close()
