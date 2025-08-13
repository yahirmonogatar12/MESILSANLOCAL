import sys
sys.path.append(".")
from app.routes import app
import json

print("=== PRUEBA COMPLETA DEL FLUJO ===")

# Simular una petición POST como la haría el frontend
with app.test_client() as client:
    with app.app_context():
        # Datos exactos como los envía el frontend
        data = {
            "codigo_material_recibido": "0RH5602C622,202508130004",
            "cantidad_salida": 1,
            "proceso_salida": "AUTO"
        }
        
        response = client.post("/procesar_salida_material", 
                             data=json.dumps(data),
                             content_type="application/json")
        
        print(f"Response status: {response.status_code}")
        print(f"Response data: {response.get_json()}")
