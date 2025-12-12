"""
Script de prueba para las APIs v2 refactorizadas.
Ejecutar con el servidor corriendo en otra terminal.
"""
import requests
import json

BASE_URL = "http://localhost:5000"

def test_endpoint(name, method, url, data=None, headers=None):
    """Prueba un endpoint y muestra el resultado."""
    print(f"\n{'='*60}")
    print(f"🧪 TEST: {name}")
    print(f"   {method} {url}")
    print('='*60)
    
    try:
        if method == 'GET':
            response = requests.get(url, headers=headers, timeout=10)
        elif method == 'POST':
            response = requests.post(url, json=data, headers=headers, timeout=10)
        elif method == 'PUT':
            response = requests.put(url, json=data, headers=headers, timeout=10)
        elif method == 'DELETE':
            response = requests.delete(url, headers=headers, timeout=10)
        
        print(f"   Status: {response.status_code}")
        
        try:
            json_response = response.json()
            print(f"   Response:")
            print(json.dumps(json_response, indent=4, ensure_ascii=False)[:2000])
            if len(json.dumps(json_response)) > 2000:
                print("   ... (truncado)")
            return response.status_code, json_response
        except:
            print(f"   Response (text): {response.text[:500]}")
            return response.status_code, response.text
            
    except requests.exceptions.ConnectionError:
        print("   ❌ ERROR: No se puede conectar. ¿El servidor está corriendo?")
        return None, None
    except Exception as e:
        print(f"   ❌ ERROR: {type(e).__name__}: {e}")
        return None, None

def main():
    print("\n" + "="*60)
    print("🚀 PRUEBAS DE APIs v2 REFACTORIZADAS")
    print("="*60)
    
    # Verificar conexión básica
    print("\n📡 Verificando conexión al servidor...")
    try:
        r = requests.get(f"{BASE_URL}/", timeout=5)
        print(f"   ✅ Servidor respondiendo (status: {r.status_code})")
    except requests.exceptions.ConnectionError:
        print("   ❌ El servidor no está corriendo.")
        print("   Ejecuta 'python run.py' en otra terminal primero.")
        return
    
    # =======================
    # PRUEBAS API v2 PLAN
    # =======================
    print("\n\n📋 PRUEBAS DE API v2 PLAN (/api/v2/plan)")
    print("="*60)
    
    test_endpoint(
        "Listar todos los planes",
        "GET", 
        f"{BASE_URL}/api/v2/plan"
    )
    
    test_endpoint(
        "Obtener plan por ID (id=1)",
        "GET", 
        f"{BASE_URL}/api/v2/plan/1"
    )
    
    test_endpoint(
        "Buscar planes por fecha",
        "GET", 
        f"{BASE_URL}/api/v2/plan?fecha=2024-01-15"
    )
    
    # =======================
    # PRUEBAS API v2 BOM
    # =======================
    print("\n\n📦 PRUEBAS DE API v2 BOM (/api/v2/bom)")
    print("="*60)
    
    test_endpoint(
        "Listar todos los modelos",
        "GET", 
        f"{BASE_URL}/api/v2/bom/models"
    )
    
    test_endpoint(
        "Obtener BOM de un modelo",
        "GET", 
        f"{BASE_URL}/api/v2/bom/model/TESTMODEL"
    )
    
    # =======================
    # PRUEBAS API v2 MATERIALS
    # =======================
    print("\n\n🔧 PRUEBAS DE API v2 MATERIALS (/api/v2/materials)")
    print("="*60)
    
    test_endpoint(
        "Listar todos los materiales",
        "GET", 
        f"{BASE_URL}/api/v2/materials"
    )
    
    test_endpoint(
        "Buscar material por número de parte",
        "GET", 
        f"{BASE_URL}/api/v2/materials/TEST123"
    )
    
    # =======================
    # PRUEBAS APIs v1 EXISTENTES (para comparación)
    # =======================
    print("\n\n📌 PRUEBAS DE APIs v1 EXISTENTES (comparación)")
    print("="*60)
    
    test_endpoint(
        "API v1: Listar planes",
        "GET", 
        f"{BASE_URL}/api/obtener_plan_v2"
    )
    
    test_endpoint(
        "API v1: Listar materiales",
        "GET", 
        f"{BASE_URL}/api/materiales"
    )
    
    # =======================
    # RESUMEN
    # =======================
    print("\n\n" + "="*60)
    print("📊 RESUMEN DE PRUEBAS")
    print("="*60)
    print("""
Las APIs v2 refactorizadas proporcionan:
✅ Respuestas JSON estandarizadas con estructura:
   {
     "success": true/false,
     "data": {...},
     "message": "...",
     "timestamp": "...",
     "count": n
   }

✅ Separación de lógica de negocio en servicios
✅ Código más limpio y mantenible
✅ Manejo de errores consistente
✅ Validación de datos centralizada

Endpoints disponibles:
- /api/v2/plan          -> GET (listar), POST (crear)
- /api/v2/plan/<id>     -> GET, PUT, DELETE
- /api/v2/bom/models    -> GET (listar modelos)
- /api/v2/bom/model/<m> -> GET, POST (BOM por modelo)
- /api/v2/materials     -> GET (listar), POST (crear)
- /api/v2/materials/<p> -> GET, PUT, DELETE (por part number)
    """)

if __name__ == "__main__":
    main()
