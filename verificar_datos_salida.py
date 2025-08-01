from app.db import get_db_connection
import traceback

print("Iniciando verificación de datos...")

try:
    print("Obteniendo conexión a la base de datos...")
    conn = get_db_connection()
    cursor = conn.cursor()
    print("Conexión establecida exitosamente")
    
    # Verificar cuántos registros hay en control_material_salida
    print("\nVerificando tabla control_material_salida...")
    cursor.execute('SELECT COUNT(*) FROM control_material_salida')
    result = cursor.fetchone()
    print(f'Resultado de la consulta: {result}, tipo: {type(result)}')
    
    if isinstance(result, dict):
        count_salida = list(result.values())[0] if result else 0
    else:
        count_salida = result[0] if result else 0
    print(f'Registros en control_material_salida: {count_salida}')
    
    # Verificar cuántos registros hay en control_material_almacen
    print("\nVerificando tabla control_material_almacen...")
    cursor.execute('SELECT COUNT(*) FROM control_material_almacen')
    result = cursor.fetchone()
    print(f'Resultado de la consulta: {result}, tipo: {type(result)}')
    
    if isinstance(result, dict):
        count_almacen = list(result.values())[0] if result else 0
    else:
        count_almacen = result[0] if result else 0
    print(f'Registros en control_material_almacen: {count_almacen}')
    
    # Verificar si hay tablas relacionadas
    print("\nListando todas las tablas...")
    cursor.execute('SHOW TABLES')
    tables = cursor.fetchall()
    print('Tablas disponibles:')
    for table in tables:
        if isinstance(table, dict):
            table_name = list(table.values())[0]
        else:
            table_name = table[0]
        print(f'  - {table_name}')
        
    # Ahora vamos a probar la consulta que está fallando
    print("\nProbando la consulta de historial de salidas...")
    query = '''
        SELECT 
            s.fecha_salida,
            s.proceso_salida,
            s.codigo_material_recibido,
            a.codigo_material,
            a.numero_parte,
            s.cantidad_salida as disp,
            0 as hist,
            a.codigo_material_original,
            s.numero_lote,
            s.modelo as maquina_linea,
            s.depto_salida as departamento,
            s.especificacion_material
        FROM control_material_salida s
        LEFT JOIN control_material_almacen a ON s.codigo_material_recibido = a.codigo_material_recibido
        WHERE 1=1
        ORDER BY s.fecha_salida DESC, s.fecha_registro DESC
        LIMIT 3
    '''
    cursor.execute(query)
    resultados = cursor.fetchall()
    print(f'Resultados obtenidos: {len(resultados)}')
    
    if resultados:
        print('Primer resultado:')
        print(resultados[0])
        print(f'Tipo del primer resultado: {type(resultados[0])}')
        
        # Convertir a lista de diccionarios como en la función original
        columnas = [desc[0] for desc in cursor.description]
        print(f'Columnas: {columnas}')
        
        datos = []
        for fila in resultados:
            if isinstance(fila, dict):
                registro = fila
            else:
                registro = dict(zip(columnas, fila))
            datos.append(registro)
        
        print(f'Datos procesados: {datos[0]}')
        
    print("\nVerificación completada exitosamente")
        
except Exception as e:
    print(f'Error durante la verificación: {e}')
    print(f'Tipo de error: {type(e).__name__}')
    traceback.print_exc()
finally:
    try:
        if 'conn' in locals() and conn:
            conn.close()
            print("Conexión cerrada")
    except:
        pass