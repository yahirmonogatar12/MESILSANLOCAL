#!/usr/bin/env python3
"""
Script de prueba para el endpoint de actualización de control de almacén
"""

import requests
import json

# URL del servidor
BASE_URL = "http://localhost:5000"

def test_actualizar_control_almacen():
    """Probar el endpoint de actualización"""
    
    # Datos de prueba (usando los mismos datos que enviaste)
    test_data = {
        "id": "17",
        "cantidad_actual": "200",
        "cantidad_estandarizada": "4000",
        "cliente": "",
        "codigo_material": "",
        "codigo_material_final": "EBC63016106",
        "codigo_material_original": "",
        "codigo_material_recibido": "EBC63016106,202509030001",
        "especificacion": "0.2F 2W (SMD 6432)",
        "estado_desecho": "",
        "fecha_fabricacion": "",
        "fecha_recibo": "",
        "forma_material": "OriginCode",
        "material_importacion_local": "Local",
        "material_importacion_local_final": "",
        "numero_lote_material": "",
        "numero_parte": "",
        "propiedad_material": "",
        "ubicacion_salida": ""
    }
    
    print("🔧 Probando endpoint de actualización...")
    print(f"📤 Datos a enviar: {json.dumps(test_data, indent=2)}")
    
    try:
        # Realizar la petición POST
        response = requests.post(
            f"{BASE_URL}/actualizar_control_almacen",
            json=test_data,
            headers={
                'Content-Type': 'application/json'
            },
            timeout=10
        )
        
        print(f"📡 Status Code: {response.status_code}")
        print(f"📋 Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Respuesta exitosa: {json.dumps(result, indent=2)}")
        else:
            print(f"❌ Error HTTP {response.status_code}")
            print(f"💬 Contenido: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error de conexión: {e}")
    except json.JSONDecodeError as e:
        print(f"❌ Error al decodificar JSON: {e}")
        print(f"💬 Respuesta raw: {response.text}")

if __name__ == "__main__":
    test_actualizar_control_almacen()
