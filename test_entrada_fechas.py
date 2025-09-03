#!/usr/bin/env python3
"""
Script para probar la corrección de fechas en control_material_almacen
"""

from app.db import agregar_control_material_almacen
from app.config_mysql import execute_query
from datetime import datetime, timedelta

def test_entrada_material():
    """Probar entrada de material con fechas corregidas"""
    
    print("=== PRUEBA DE ENTRADA DE MATERIAL CON FECHAS CORREGIDAS ===")
    
    # Simular datos como vienen del frontend (solo fecha, sin hora)
    utc_now = datetime.utcnow()
    mexico_time = utc_now - timedelta(hours=6)
    fecha_hoy = mexico_time.strftime('%Y-%m-%d')
    
    print(f"\n1. DATOS DE PRUEBA:")
    print(f"   Fecha actual México: {mexico_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Fecha desde frontend: {fecha_hoy} (sin hora)")
    
    material_data = {
        "forma_material": "DIODO",
        "cliente": "ILSAN_ELECTRONICS", 
        "codigo_material_original": "TEST_FECHA_001",
        "codigo_material": "TEST_FECHA_001",
        "material_importacion_local": "LOCAL",
        "fecha_recibo": fecha_hoy,  # Solo fecha como viene del frontend
        "fecha_fabricacion": fecha_hoy,  # Solo fecha como viene del frontend
        "cantidad_actual": 50,
        "numero_lote_material": "LOTE_FECHA_001",
        "codigo_material_recibido": f"TEST_FECHA_001,{mexico_time.strftime('%Y%m%d')}0001",
        "numero_parte": "TEST_FECHA_PART_001",
        "cantidad_estandarizada": 50,
        "codigo_material_final": "TEST_FECHA_001_FINAL",
        "propiedad_material": "Prueba corrección de fechas",
        "especificacion": "Material de prueba para validar que las fechas incluyan hora",
        "material_importacion_local_final": "LOCAL",
        "estado_desecho": False,
        "ubicacion_salida": "ALMACEN_PRINCIPAL"
    }
    
    print(f"\n2. REGISTRANDO MATERIAL...")
    print(f"   Código: {material_data['codigo_material_recibido']}")
    
    try:
        # Registrar el material
        resultado = agregar_control_material_almacen(material_data)
        
        if resultado:
            print(f"   ✅ Material registrado exitosamente")
            
            # Verificar cómo se guardó
            print(f"\n3. VERIFICANDO COMO SE GUARDÓ...")
            
            result = execute_query("""
                SELECT codigo_material_recibido,
                       DATE_FORMAT(fecha_recibo, '%%Y-%%m-%%d %%H:%%i:%%s') as fecha_recibo_formatted,
                       DATE_FORMAT(fecha_fabricacion, '%%Y-%%m-%%d %%H:%%i:%%s') as fecha_fabricacion_formatted,
                       DATE_FORMAT(fecha_registro, '%%Y-%%m-%%d %%H:%%i:%%s') as fecha_registro_formatted
                FROM control_material_almacen 
                WHERE codigo_material_recibido = %s
                ORDER BY id DESC LIMIT 1
            """, (material_data['codigo_material_recibido'],), fetch='one')
            
            if result:
                print(f"   📋 RESULTADO EN BASE DE DATOS:")
                print(f"      Fecha recibo:      {result['fecha_recibo_formatted']}")
                print(f"      Fecha fabricación: {result['fecha_fabricacion_formatted']}")
                print(f"      Fecha registro:    {result['fecha_registro_formatted']}")
                
                # Verificar que NO sea 00:00:00
                recibo_time = result['fecha_recibo_formatted'].split(' ')[1]
                fabricacion_time = result['fecha_fabricacion_formatted'].split(' ')[1]
                registro_time = result['fecha_registro_formatted'].split(' ')[1]
                
                print(f"\n4. VALIDACIÓN:")
                
                if recibo_time == "00:00:00":
                    print(f"   ❌ fecha_recibo aún muestra 00:00:00")
                else:
                    print(f"   ✅ fecha_recibo tiene hora: {recibo_time}")
                    
                if fabricacion_time == "00:00:00":
                    print(f"   ❌ fecha_fabricacion aún muestra 00:00:00")
                else:
                    print(f"   ✅ fecha_fabricacion tiene hora: {fabricacion_time}")
                    
                if registro_time == "00:00:00":
                    print(f"   ❌ fecha_registro muestra 00:00:00")
                else:
                    print(f"   ✅ fecha_registro tiene hora: {registro_time}")
                    
                # Comparar con hora actual de México
                hora_esperada = mexico_time.strftime('%H:%M')
                print(f"\n5. COMPARACIÓN CON HORA ACTUAL:")
                print(f"   Hora México actual: {hora_esperada}")
                print(f"   Hora en recibo:     {recibo_time[:5]}")
                print(f"   Hora en registro:   {registro_time[:5]}")
                
                # La diferencia debe ser mínima (pocos minutos)
                if abs(int(recibo_time[:2]) - int(hora_esperada[:2])) <= 1:
                    print(f"   ✅ Las horas coinciden con México")
                else:
                    print(f"   ⚠️ Diferencia significativa en horas")
                    
            else:
                print(f"   ❌ No se encontró el registro en la base de datos")
                
        else:
            print(f"   ❌ Error al registrar el material")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    test_entrada_material()
