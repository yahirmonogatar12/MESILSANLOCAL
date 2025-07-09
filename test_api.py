#!/usr/bin/env python3
import requests
import json

def test_endpoint():
    """Test directo del endpoint sin autenticación"""
    try:
        # Test endpoint de consulta
        print("=== Probando endpoint /consultar_control_almacen ===")
        
        url = "http://localhost:5000/consultar_control_almacen"
        
        # Intentar hacer request
        response = requests.get(url, timeout=10)
        
        print(f"Status code: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        print(f"URL final: {response.url}")
        
        if response.status_code == 200:
            print("✅ Respuesta exitosa")
            try:
                data = response.json()
                print(f"Tipo de datos: {type(data)}")
                print(f"Es array: {isinstance(data, list)}")
                if isinstance(data, list):
                    print(f"Cantidad de registros: {len(data)}")
                    if data:
                        print("Primer registro:")
                        print(json.dumps(data[0], indent=2, default=str))
                else:
                    print("Datos recibidos:", data)
            except Exception as e:
                print(f"❌ Error al parsear JSON: {e}")
                print("Contenido de la respuesta:")
                print(response.text[:500] + "..." if len(response.text) > 500 else response.text)
        else:
            print(f"❌ Error HTTP {response.status_code}")
            print("Contenido de la respuesta:")
            print(response.text[:500] + "..." if len(response.text) > 500 else response.text)
            
    except requests.exceptions.ConnectionError:
        print("❌ No se pudo conectar al servidor. ¿Está Flask ejecutándose en puerto 5000?")
    except requests.exceptions.Timeout:
        print("❌ Timeout al conectar al servidor")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")

if __name__ == "__main__":
    test_endpoint()
