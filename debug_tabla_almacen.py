#!/usr/bin/env python3
"""
Script para verificar la estructura de la tabla control_material_almacen
"""

from app.config_mysql import execute_query

def verificar_estructura_tabla():
    """Verificar estructura de control_material_almacen"""
    
    print("=== ESTRUCTURA DE TABLA control_material_almacen ===")
    
    try:
        result = execute_query('DESCRIBE control_material_almacen', fetch='all')
        
        if result:
            print("\nColumnas encontradas:")
            for row in result:
                field = row.get('Field', 'N/A')
                type_info = row.get('Type', 'N/A')
                null_info = row.get('Null', 'N/A')
                key_info = row.get('Key', 'N/A')
                default_info = row.get('Default', '')
                extra_info = row.get('Extra', '')
                
                # Convertir None a string vacío
                default_info = str(default_info) if default_info is not None else ''
                extra_info = str(extra_info) if extra_info is not None else ''
                
                print(f"  {field:25} | {type_info:20} | {null_info:5} | {default_info:15} | {extra_info}")
        else:
            print("No se pudo obtener la estructura de la tabla")
            
        # Verificar registros recientes
        print("\n=== REGISTROS RECIENTES ===")
        recent = execute_query("""
            SELECT id, codigo_material_recibido, fecha_recibo, fecha_fabricacion,
                   DATE_FORMAT(fecha_registro, '%Y-%m-%d %H:%i:%s') as fecha_registro_formatted
            FROM control_material_almacen 
            ORDER BY id DESC 
            LIMIT 5
        """, fetch='all')
        
        if recent:
            for row in recent:
                print(f"ID: {row.get('id')}")
                print(f"  Código: {row.get('codigo_material_recibido')}")
                print(f"  Fecha recibo: {row.get('fecha_recibo')}")
                print(f"  Fecha fabricación: {row.get('fecha_fabricacion')}")
                print(f"  Fecha registro: {row.get('fecha_registro_formatted')}")
                print("---")
        else:
            print("No hay registros recientes")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    verificar_estructura_tabla()
