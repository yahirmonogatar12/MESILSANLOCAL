#!/usr/bin/env python3
"""
Script para probar la corrección del código de material recibido
Ahora debe usar número de parte en lugar del código de material
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import agregar_control_material_almacen
from app.config_mysql import execute_query
from datetime import datetime, timedelta

def test_codigo_material_recibido():
    """Probar que el código recibido use número de parte"""
    
    print("=== PRUEBA DE CÓDIGO MATERIAL RECIBIDO CON NÚMERO DE PARTE ===")
    
    # Obtener información de un material existente
    print(f"\n1. CONSULTANDO MATERIAL EXISTENTE...")
    
    result = execute_query("""
        SELECT codigo_material, numero_parte, especificacion_material
        FROM materiales 
        WHERE numero_parte IS NOT NULL AND numero_parte != ''
        ORDER BY codigo_material DESC 
        LIMIT 1
    """, fetch='one')
    
    if not result:
        print("❌ No se encontró material con número de parte")
        return
    
    codigo_material = result['codigo_material']
    numero_parte = result['numero_parte']
    especificacion = result['especificacion_material'] or 'Test material'
    
    print(f"   Código de material: {codigo_material}")
    print(f"   Número de parte:    {numero_parte}")
    print(f"   Especificación:     {especificacion}")
    
    # Simular datos como vienen del frontend
    utc_now = datetime.utcnow()
    mexico_time = utc_now - timedelta(hours=6)
    fecha_hoy = mexico_time.strftime('%Y-%m-%d')
    
    print(f"\n2. DATOS DE PRUEBA:")
    print(f"   Fecha actual México: {mexico_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    material_data = {
        "forma_material": "DIODO",
        "cliente": "ILSAN_ELECTRONICS", 
        "codigo_material_original": codigo_material,  # Usar código real
        "codigo_material": codigo_material,           # Usar código real
        "material_importacion_local": "LOCAL",
        "fecha_recibo": fecha_hoy,
        "fecha_fabricacion": fecha_hoy,
        "cantidad_actual": 100,
        "numero_lote_material": "LOTE_CODIGO_TEST_001",
        "codigo_material_recibido": "",  # Dejar vacío para que se genere automáticamente
        "numero_parte": numero_parte,     # Debería usar este valor
        "cantidad_estandarizada": 100,
        "codigo_material_final": f"{codigo_material}_FINAL",
        "propiedad_material": "Prueba número de parte en código recibido",
        "especificacion": especificacion,
        "material_importacion_local_final": "LOCAL",
        "estado_desecho": False,
        "ubicacion_salida": "ALMACEN_PRINCIPAL"
    }
    
    print(f"\n3. REGISTRANDO MATERIAL...")
    print(f"   Esperamos que el código recibido contenga: '{numero_parte}' (no '{codigo_material}')")
    
    try:
        # Registrar el material
        resultado = agregar_control_material_almacen(material_data)
        
        if resultado:
            print(f"   ✅ Material registrado exitosamente")
            
            # Verificar cómo se guardó el código recibido
            print(f"\n4. VERIFICANDO CÓDIGO RECIBIDO GENERADO...")
            
            result = execute_query("""
                SELECT codigo_material_recibido, numero_parte, codigo_material_original
                FROM control_material_almacen 
                WHERE codigo_material_original = %s
                ORDER BY id DESC LIMIT 1
            """, (codigo_material,), fetch='one')
            
            if result:
                codigo_recibido = result['codigo_material_recibido']
                numero_parte_guardado = result['numero_parte']
                codigo_original = result['codigo_material_original']
                
                print(f"   📋 RESULTADO EN BASE DE DATOS:")
                print(f"      Código original:    {codigo_original}")
                print(f"      Número de parte:    {numero_parte_guardado}")
                print(f"      Código recibido:    {codigo_recibido}")
                
                # Verificar que el código recibido contenga el número de parte
                print(f"\n5. VALIDACIÓN:")
                
                if numero_parte in codigo_recibido:
                    print(f"   ✅ El código recibido contiene el número de parte: '{numero_parte}'")
                    
                    # Verificar que NO contenga el código de material
                    if codigo_material not in codigo_recibido:
                        print(f"   ✅ El código recibido NO contiene el código de material: '{codigo_material}'")
                        print(f"   🎉 CORRECCIÓN EXITOSA: Se usa número de parte en lugar de código de material")
                    else:
                        print(f"   ❌ El código recibido aún contiene el código de material: '{codigo_material}'")
                        
                else:
                    print(f"   ❌ El código recibido NO contiene el número de parte: '{numero_parte}'")
                    
                    if codigo_material in codigo_recibido:
                        print(f"   ❌ El código recibido aún usa el código de material: '{codigo_material}'")
                        print(f"   ⚠️ La corrección NO funcionó correctamente")
                        
            else:
                print(f"   ❌ No se encontró el registro recién guardado")
                
        else:
            print(f"   ❌ Error al registrar el material")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_codigo_material_recibido()
