import requests
import json

# Datos de prueba
data = {
    "id": "17",
    "cantidad_actual": "200",
    "cantidad_estandarizada": "4000",
    "forma_material": "OriginCode"
}

print("Probando endpoint...")
try:
    response = requests.post(
        "http://localhost:5000/actualizar_control_almacen",
        json=data,
        headers={'Content-Type': 'application/json'},
        timeout=5
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
