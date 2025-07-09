import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

# Simular el endpoint directamente
import sqlite3
from app.db import get_db_connection
import json

print("=== Prueba directa del endpoint ===")

def simular_consultar_control_almacen():
    """Simula el endpoint consultar_control_almacen"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Usar la misma query que el endpoint
        query = '''
            SELECT * FROM control_material_almacen 
            WHERE 1=1
        '''
        params = []
        
        query += ' ORDER BY fecha_registro DESC'
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
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
        
        print(f"Registros encontrados: {len(registros)}")
        
        if registros:
            print("\nPrimer registro completo:")
            for key, value in registros[0].items():
                print(f"  {key}: {value}")
            
            print(f"\nJSON output (primeros 3):")
            print(json.dumps(registros[:3], indent=2, default=str))
        
        return registros
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return []
        
    finally:
        try:
            if cursor:
                cursor.close()
        except:
            pass
        try:
            if conn:
                conn.close()
        except:
            pass

if __name__ == '__main__':
    registros = simular_consultar_control_almacen()
    
    # Simular cómo el frontend debería procesar esto
    print("\n=== Simulación del frontend ===")
    print(f"Array.isArray(registros): {isinstance(registros, list)}")
    print(f"registros.length: {len(registros)}")
    
    if registros:
        print("\nPrimeros campos para la tabla:")
        registro = registros[0]
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
            valor = registro.get(campo, '')
            print(f"  {campo}: '{valor}'")
