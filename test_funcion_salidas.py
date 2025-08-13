#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🔧 TEST FUNCIÓN REGISTRAR_SALIDA_MATERIAL_MYSQL
============================================

Test específico para probar la función registrar_salida_material_mysql
después de corregir el error fetch_one → fetch='one'
"""

import sys
import os

# Añadir el directorio de la aplicación al path
app_dir = os.path.join(os.path.dirname(__file__), 'app')
sys.path.insert(0, app_dir)

def test_registrar_salida_material():
    """
    Prueba la función registrar_salida_material_mysql directamente
    """
    
    print("🔧 TEST FUNCIÓN REGISTRAR_SALIDA_MATERIAL_MYSQL")
    print("=" * 55)
    
    # Importar aquí para evitar problemas de importación relativa
    try:
        from db_mysql import registrar_salida_material_mysql
        print("✅ Función importada correctamente")
    except Exception as e:
        print(f"❌ Error importando función: {e}")
        return
    
    # Datos de prueba para el material que sabemos que existe
    data = {
        'codigo_material_recibido': '0RH5602C622,202508130004',
        'cantidad_salida': 1000.0,  # Cantidad de prueba
        'numero_lote': 'LOTE_TEST_001',
        'modelo': 'MODELO_TEST',
        'depto_salida': 'PRUEBAS',
        'proceso_salida': 'AUTO',  # Usar AUTO para activar lógica automática
        'fecha_salida': '2025-08-13',
        'especificacion_material': ''  # Dejar vacío para que use la original
    }
    
    print(f"📊 DATOS DE PRUEBA:")
    print(f"   - Material: {data['codigo_material_recibido']}")
    print(f"   - Cantidad: {data['cantidad_salida']}")
    print(f"   - Proceso: {data['proceso_salida']} (AUTO)")
    
    try:
        print(f"\n🧪 EJECUTANDO FUNCIÓN:")
        resultado = registrar_salida_material_mysql(data, usuario="YAHIR_TEST")
        
        if resultado:
            if resultado.get('success'):
                print("✅ FUNCIÓN EJECUTADA EXITOSAMENTE")
                print(f"   - Proceso destino: {resultado.get('proceso_destino', 'N/A')}")
                print(f"   - Especificación usada: {resultado.get('especificacion_usada', 'N/A')}")
                print(f"   - Mensaje: {resultado.get('message', 'Salida registrada')}")
                
                # Verificar que el proceso sea SMD (según la propiedad del material)
                if resultado.get('proceso_destino') == 'SMD':
                    print("🎯 CORRECTO: Material SMD enviado a proceso SMD")
                else:
                    print(f"⚠️  INESPERADO: Material SMD enviado a {resultado.get('proceso_destino')}")
                    
            else:
                print("❌ FUNCIÓN FALLÓ")
                print(f"   - Error: {resultado.get('error', 'Error desconocido')}")
        else:
            print("❌ FUNCIÓN DEVOLVIÓ None")
            
    except Exception as e:
        print(f"❌ ERROR DURANTE LA EJECUCIÓN: {str(e)}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")
        
    print("\n" + "=" * 55)
    print("🔧 FIN DEL TEST")

if __name__ == "__main__":
    test_registrar_salida_material()
