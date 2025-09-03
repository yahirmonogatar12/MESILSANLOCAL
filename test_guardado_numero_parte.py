#!/usr/bin/env python3
"""
Script para probar el guardado completo con el número de parte correcto
"""

from app.db import agregar_control_material_almacen
from app.config_mysql import execute_query
from datetime import datetime, timedelta

def test_guardado_con_numero_parte():
    """Probar el guardado completo del material con número de parte"""
    
    print("=== PRUEBA COMPLETA CON NÚMERO DE PARTE ===")
    
    # Usar datos que coincidan con la tabla materiales
    # Código de material que existe en la tabla
    codigo_material_existente = "1E1621020519206225110301102000008"
    numero_parte_esperado = "0CE106AH638"
    
    utc_now = datetime.utcnow()
    mexico_time = utc_now - timedelta(hours=6)
    fecha_hoy = mexico_time.strftime('%Y-%m-%d')
    
    print(f"\n1. DATOS DE PRUEBA:")
    print(f"   Código de material: {codigo_material_existente}")
    print(f"   Número de parte esperado: {numero_parte_esperado}")
    print(f"   Fecha: {fecha_hoy}")
    
    material_data = {
        "forma_material": "DIODO",
        "cliente": "ILSAN_ELECTRONICS", 
        "codigo_material_original": codigo_material_existente,
        "codigo_material": codigo_material_existente,
        "material_importacion_local": "LOCAL",
        "fecha_recibo": fecha_hoy,
        "fecha_fabricacion": fecha_hoy,
        "cantidad_actual": 100,
        "numero_lote_material": "LOTE_TEST_001",
        "codigo_material_recibido": "",  # Esto se debe generar automáticamente
        "numero_parte": numero_parte_esperado,
        "cantidad_estandarizada": 100,
        "codigo_material_final": codigo_material_existente,
        "propiedad_material": "IMD",
        "especificacion": "10uF 16V 20% RG,KMG",
        "material_importacion_local_final": "LOCAL",
        "estado_desecho": False,
        "ubicacion_salida": "ALMACEN_PRINCIPAL"
    }
    
    print(f"\n2. REGISTRANDO MATERIAL...")
    
    try:
        # Registrar el material
        resultado = agregar_control_material_almacen(material_data)
        
        if resultado:
            print(f"   ✅ Material registrado exitosamente")
            
            # Verificar cómo se guardó el código recibido
            result = execute_query("""
                SELECT codigo_material_recibido, numero_parte, codigo_material_original
                FROM control_material_almacen 
                WHERE codigo_material_original = %s
                ORDER BY id DESC LIMIT 1
            """, (codigo_material_existente,), fetch='one')
            
            if result:
                print(f"\n3. VERIFICACIÓN EN BASE DE DATOS:")
                print(f"   Código material original: {result['codigo_material_original']}")
                print(f"   Número de parte:          {result['numero_parte']}")
                print(f"   Código material recibido: {result['codigo_material_recibido']}")
                
                # Validar que el código recibido use el número de parte
                codigo_recibido = result['codigo_material_recibido']
                
                print(f"\n4. VALIDACIÓN:")
                if numero_parte_esperado in codigo_recibido:
                    print(f"   ✅ El código recibido contiene el número de parte: '{numero_parte_esperado}'")
                else:
                    print(f"   ❌ El código recibido NO contiene el número de parte esperado")
                    
                if codigo_material_existente not in codigo_recibido:
                    print(f"   ✅ El código recibido ya NO contiene el código de material largo")
                else:
                    print(f"   ❌ El código recibido aún contiene el código de material largo")
                    
                # Verificar el formato esperado: NUMERO_PARTE,YYYYMMDD0001
                fecha_formato = mexico_time.strftime('%Y%m%d')
                patron_esperado = f"{numero_parte_esperado},{fecha_formato}"
                
                if patron_esperado in codigo_recibido:
                    print(f"   ✅ El código tiene el formato correcto: '{patron_esperado}XXXX'")
                else:
                    print(f"   ❌ El código NO tiene el formato esperado: '{patron_esperado}XXXX'")
                    
            else:
                print(f"   ❌ No se encontró el registro en la base de datos")
                
        else:
            print(f"   ❌ Error al registrar el material")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    test_guardado_con_numero_parte()
