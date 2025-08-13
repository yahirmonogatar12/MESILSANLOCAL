#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🔍 DEBUG ESPECIFICACIÓN - FUNCIÓN SALIDAS
========================================

Debug específico para entender por qué la especificación
se está guardando como 'SMD' en lugar de '56KJ 1/10W SMD'
"""

import sys
import os

# Añadir el directorio de la aplicación al path
app_dir = os.path.join(os.path.dirname(__file__), 'app')
sys.path.insert(0, app_dir)

from config_mysql import execute_query

def debug_especificacion():
    """
    Debug paso a paso de la obtención de especificación
    """
    
    print("🔍 DEBUG ESPECIFICACIÓN - FUNCIÓN SALIDAS")
    print("=" * 50)
    
    codigo_material = "0RH5602C622,202508130004"
    
    # PASO 1: Verificar que la especificación esté en control_material_almacen
    print(f"📋 PASO 1: Verificar especificación en control_material_almacen")
    
    query_especificacion = """
        SELECT especificacion, propiedad_material
        FROM control_material_almacen 
        WHERE codigo_material_recibido = %s
        ORDER BY id DESC LIMIT 1
    """
    
    result_spec = execute_query(query_especificacion, (codigo_material,), fetch='one')
    
    print(f"   Query ejecutada:")
    print(f"   {query_especificacion.strip()}")
    print(f"   Parámetros: {(codigo_material,)}")
    print(f"   Resultado tipo: {type(result_spec)}")
    print(f"   Resultado: {result_spec}")
    
    if result_spec:
        especificacion_original = result_spec.get('especificacion', '')
        propiedad_material = result_spec.get('propiedad_material', '')
        
        print(f"   ✅ Material encontrado:")
        print(f"      - especificacion_original: '{especificacion_original}'")
        print(f"      - propiedad_material: '{propiedad_material}'")
        
        # PASO 2: Simular lo que hace la función
        print(f"\n🎯 PASO 2: Simular lógica de la función registrar_salida_material_mysql")
        
        # Proceso de determinación (como en la función original)
        proceso_salida = 'PRODUCCION'  # Default
        
        if propiedad_material:
            if propiedad_material.upper() == 'SMD':
                proceso_salida = 'SMD'
            elif propiedad_material.upper() == 'IMD':
                proceso_salida = 'IMD'
            elif propiedad_material.upper() in ['MAIN', 'THROUGH_HOLE']:
                proceso_salida = 'MAIN'
                
        print(f"   proceso_salida determinado: '{proceso_salida}'")
        
        # PASO 3: Verificar qué se estaría insertando
        print(f"\n💾 PASO 3: Datos que se insertarían en control_material_salida")
        
        # Simular los datos que se pasarían al INSERT
        data_simulado = {
            'codigo_material_recibido': codigo_material,
            'cantidad_salida': 1000.0,
            'especificacion_material': ''  # Como viene del frontend
        }
        
        # Lógica de la función original
        especificacion_final = especificacion_original or data_simulado.get('especificacion_material', '')
        
        print(f"   - especificacion_original: '{especificacion_original}'")
        print(f"   - data.get('especificacion_material'): '{data_simulado.get('especificacion_material', '')}'")
        print(f"   - especificacion_final (OR logic): '{especificacion_final}'")
        
        # PASO 4: Verificar qué especificación tienen las salidas actuales
        print(f"\n🗃️  PASO 4: Verificar salidas existentes en BD")
        
        query_salidas = """
            SELECT id, especificacion_material, proceso_salida, fecha_registro
            FROM control_material_salida 
            WHERE codigo_material_recibido = %s 
            ORDER BY id DESC LIMIT 3
        """
        
        salidas_existentes = execute_query(query_salidas, (codigo_material,), fetch='all')
        
        if salidas_existentes:
            print(f"   Salidas encontradas: {len(salidas_existentes)}")
            for i, salida in enumerate(salidas_existentes, 1):
                print(f"      {i}. ID: {salida['id']}, Espec: '{salida['especificacion_material']}', Proceso: '{salida['proceso_salida']}'")
        else:
            print(f"   No hay salidas registradas para este material")
            
    else:
        print(f"   ❌ Material no encontrado en control_material_almacen")
        
    print("\n" + "=" * 50)
    print("🔍 FIN DEL DEBUG")

if __name__ == "__main__":
    debug_especificacion()
