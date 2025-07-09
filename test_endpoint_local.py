import sqlite3
import json

def simular_endpoint_consulta():
    """Simula exactamente lo que hace el endpoint /consultar_control_almacen"""
    try:
        # Conectar igual que el endpoint
        conn = sqlite3.connect('app/database/ISEMM_MES.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Query exacta del endpoint
        query = '''
            SELECT * FROM control_material_almacen 
            WHERE 1=1
        '''
        params = []
        query += ' ORDER BY fecha_registro DESC'
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # Procesar igual que el endpoint
        registros = []
        for row in rows:
            registros.append({
                'id': row['id'],
                'forma_material': row['forma_material'],
                'cliente': row['cliente'],
                'codigo_material_original': row['codigo_material_original'],
                'codigo_material': row['codigo_material'],
                'material_importacion_local': row['material_importacion_local'],
                'fecha_recibo': row['fecha_recibo'],
                'fecha_fabricacion': row['fecha_fabricacion'],
                'cantidad_actual': row['cantidad_actual'],
                'numero_lote_material': row['numero_lote_material'],
                'codigo_material_recibido': row['codigo_material_recibido'],
                'numero_parte': row['numero_parte'],
                'cantidad_estandarizada': row['cantidad_estandarizada'],
                'codigo_material_final': row['codigo_material_final'],
                'propiedad_material': row['propiedad_material'],
                'especificacion': row['especificacion'],
                'material_importacion_local_final': row['material_importacion_local_final'],
                'estado_desecho': row['estado_desecho'],
                'ubicacion_salida': row['ubicacion_salida'],
                'fecha_registro': row['fecha_registro']
            })
        
        conn.close()
        
        # Mostrar resultado como JSON igual que Flask
        print("=== SIMULACION DEL ENDPOINT ===")
        print(f"Registros encontrados: {len(registros)}")
        print(f"JSON que devolvería el endpoint:")
        
        # Generar el JSON exacto que enviaría Flask
        json_response = json.dumps(registros, default=str)
        print(json_response)
        
        print(f"\n=== ANALISIS PARA EL FRONTEND ===")
        if registros:
            print("Array.isArray(data):", isinstance(registros, list))
            print("data.length:", len(registros))
            print("\nPrimer registro para la tabla:")
            
            # Campos exactos que usa cargarDatosEnTabla
            primer_registro = registros[0]
            campos_tabla = [
                'codigo_material_recibido',
                'codigo_material_final', 
                'numero_parte',
                'numero_lote_material',
                'propiedad_material',
                'cantidad_actual',
                'cantidad_estandarizada',
                'ubicacion_salida',
                'fecha_recibo',
                'especificacion',
                'material_importacion_local',
                'estado_desecho'
            ]
            
            for campo in campos_tabla:
                valor = primer_registro.get(campo, '')
                print(f"  {campo}: '{valor}'")
                
        return registros
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return []

if __name__ == "__main__":
    simular_endpoint_consulta()
