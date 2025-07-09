from app.db import get_db_connection

def test_codigos_material():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT codigo_material, numero_parte, especificacion_material 
        FROM materiales 
        WHERE codigo_material IS NOT NULL AND codigo_material != ''
        ORDER BY codigo_material ASC
        LIMIT 5
    ''')
    rows = cursor.fetchall()
    
    print(f'Total códigos encontrados: {len(rows)}')
    
    codigos = []
    for row in rows:
        codigo_data = {
            'codigo': row['codigo_material'],
            'nombre': row['numero_parte'] or '',
            'spec': row['especificacion_material'] or ''
        }
        codigos.append(codigo_data)
        print(f"  Codigo: {codigo_data['codigo']}, Nombre: {codigo_data['nombre']}, Spec: {codigo_data['spec']}")
    
    cursor.close()
    conn.close()
    return codigos

if __name__ == "__main__":
    test_codigos_material()
