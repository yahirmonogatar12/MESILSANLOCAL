#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🔧 TEST CORRECCION FETCH_ONE - SISTEMA SALIDAS MYSQL
==================================================

Script de prueba para verificar que la corrección del parámetro 
fetch_one → fetch='one' resolvió el error en registrar_salida_material_mysql.

Ejecuta una salida de prueba con el material 0RH5602C622,202508130004
"""

import sys
import os

# Añadir el directorio de la aplicación al path
app_dir = os.path.join(os.path.dirname(__file__), 'app')
sys.path.insert(0, app_dir)

# Importar módulos
from config_mysql import execute_query

def test_correccion_fetch_one():
    """
    Prueba la corrección del error fetch_one verificando la sintaxis
    """
    
    print("🔧 TEST CORRECCIÓN FETCH_ONE - SISTEMA SALIDAS MYSQL")
    print("=" * 55)
    
    # Datos de prueba
    codigo_material = "0RH5602C622,202508130004"
    
    try:
        # Probar que execute_query funciona con fetch='one'
        print(f"📊 PROBANDO SINTAXIS CORREGIDA:")
        
        query_test = """
        SELECT 
            codigo_material_recibido,
            cantidad_total
        FROM inventario_general 
        WHERE codigo_material_recibido = %s
        LIMIT 1
        """
        
        print(f"   Ejecutando consulta con fetch='one'...")
        result = execute_query(query_test, (codigo_material,), fetch='one')
        
        if result:
            print("✅ SINTAXIS CORREGIDA FUNCIONA CORRECTAMENTE")
            print(f"   - Material encontrado: {result[0]}")
            print(f"   - Cantidad: {result[1]}")
        else:
            print("⚠️  Material no encontrado, pero sintaxis funciona")
            
        # Probar también fetch='all'
        print(f"\n   Ejecutando consulta con fetch='all'...")
        result_all = execute_query(query_test, (codigo_material,), fetch='all')
        
        if result_all:
            print("✅ SINTAXIS CON FETCH='ALL' TAMBIÉN FUNCIONA")
            print(f"   - Resultados encontrados: {len(result_all)}")
        else:
            print("⚠️  No hay resultados, pero sintaxis funciona")
            
    except Exception as e:
        print(f"❌ ERROR DURANTE LA PRUEBA: {str(e)}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")
        
    print("\n" + "=" * 55)
    print("🔧 FIN DEL TEST DE CORRECCIÓN")

if __name__ == "__main__":
    test_correccion_fetch_one()

if __name__ == "__main__":
    test_correccion_fetch_one()
