import sqlite3

conn = sqlite3.connect('app/database/ISEMM_MES.db')
cursor = conn.cursor()

cursor.execute('SELECT pagina, seccion, boton FROM permisos_botones WHERE pagina LIKE "%INFORMACION%" ORDER BY seccion, boton')
permisos = cursor.fetchall()

print('Permisos disponibles para INFORMACION:')
for row in permisos:
    print(f'  {row[0]} -> {row[1]} -> {row[2]}')

print('\nTodas las páginas disponibles:')
cursor.execute('SELECT DISTINCT pagina FROM permisos_botones ORDER BY pagina')
paginas = cursor.fetchall()
for p in paginas:
    print(f'  {p[0]}')

conn.close()
