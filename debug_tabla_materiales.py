#!/usr/bin/env python3
"""
Script para verificar la estructura de la tabla materiales
"""

from app.config_mysql import execute_query

def verificar_tabla_materiales():
    """Verificar la estructura y datos de la tabla materiales"""
    
    print("=== VERIFICACIÓN DE TABLA MATERIALES ===")
    
    try:
        # Verificar estructura de la tabla
        result = execute_query("DESCRIBE materiales", fetch='all')
        
        print(f"\n1. ESTRUCTURA DE LA TABLA:")
        for column in result:
            print(f"   {column['Field']}: {column['Type']} ({column['Key']})")
            
        # Verificar algunos registros
        result = execute_query("SELECT numero_parte, codigo_material FROM materiales LIMIT 10", fetch='all')
        
        print(f"\n2. ALGUNOS REGISTROS:")
        for row in result:
            print(f"   numero_parte: '{row['numero_parte']}' -> codigo_material: '{row['codigo_material']}'")
            
        # Buscar específicamente el código que estamos probando
        codigo_buscar = "1E162102051920622511030110200"
        result = execute_query(
            "SELECT numero_parte, codigo_material FROM materiales WHERE codigo_material = %s",
            (codigo_buscar,),
            fetch='one'
        )
        
        print(f"\n3. BÚSQUEDA ESPECÍFICA PARA '{codigo_buscar}':")
        if result:
            print(f"   ✅ Encontrado:")
            print(f"      numero_parte: '{result['numero_parte']}'")
            print(f"      codigo_material: '{result['codigo_material']}'")
        else:
            print(f"   ❌ No encontrado en la tabla")
            
        # Buscar códigos similares
        result = execute_query(
            "SELECT numero_parte, codigo_material FROM materiales WHERE codigo_material LIKE %s LIMIT 5",
            (f"{codigo_buscar[:10]}%",),
            fetch='all'
        )
        
        print(f"\n4. CÓDIGOS SIMILARES QUE EMPIECEN CON '{codigo_buscar[:10]}':")
        for row in result:
            print(f"   numero_parte: '{row['numero_parte']}' -> codigo_material: '{row['codigo_material']}'")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    verificar_tabla_materiales()
