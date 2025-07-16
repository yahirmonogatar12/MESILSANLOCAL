import requests
import json

def test_bom_endpoints():
    base_url = "http://192.168.0.211:5000"
    
    print("=== Prueba de endpoints BOM ===")
    
    # Test de login (necesario para las rutas protegidas)
    print("\n1. Realizando login...")
    login_data = {
        'username': '1111',
        'password': '1111'
    }
    
    session = requests.Session()
    
    try:
        login_response = session.post(f"{base_url}/login", data=login_data)
        if login_response.status_code == 200:
            print("✓ Login exitoso")
        else:
            print(f"✗ Error en login: {login_response.status_code}")
            return
    except Exception as e:
        print(f"✗ Error conectando al servidor: {e}")
        return
    
    # Test de listar modelos BOM
    print("\n2. Probando /listar_modelos_bom...")
    try:
        modelos_response = session.get(f"{base_url}/listar_modelos_bom")
        if modelos_response.status_code == 200:
            modelos = modelos_response.json()
            print(f"✓ Modelos obtenidos: {len(modelos)}")
            if modelos:
                print(f"  Primer modelo: {modelos[0]['modelo']}")
        else:
            print(f"✗ Error al obtener modelos: {modelos_response.status_code}")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # Test de listar BOM
    print("\n3. Probando /listar_bom...")
    try:
        bom_data = {
            'modelo': 'EBR30299301'
        }
        bom_response = session.post(
            f"{base_url}/listar_bom", 
            headers={'Content-Type': 'application/json'},
            data=json.dumps(bom_data)
        )
        if bom_response.status_code == 200:
            bom_items = bom_response.json()
            print(f"✓ Items BOM obtenidos: {len(bom_items)}")
            if bom_items:
                print(f"  Primer item: {bom_items[0]['numeroParte']}")
        else:
            print(f"✗ Error al obtener BOM: {bom_response.status_code}")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    print("\n=== Fin de pruebas ===")

if __name__ == "__main__":
    test_bom_endpoints()
