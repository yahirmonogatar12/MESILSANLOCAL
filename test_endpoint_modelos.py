import requests
import json

def test_endpoint_modelos():
    base_url = "http://192.168.0.211:5000"
    
    print("=== Test del endpoint de modelos ===")
    
    # Login
    session = requests.Session()
    login_data = {'username': '1111', 'password': '1111'}
    
    try:
        print("🔑 Realizando login...")
        login_response = session.post(f"{base_url}/login", data=login_data)
        if login_response.status_code != 200:
            print(f"❌ Error en login: {login_response.status_code}")
            return
        print("✅ Login exitoso")
    except Exception as e:
        print(f"❌ Error conectando: {e}")
        return
    
    # Test del endpoint
    print("\n🌐 Probando endpoint /listar_modelos_bom...")
    try:
        response = session.get(f"{base_url}/listar_modelos_bom")
        print(f"📡 Status Code: {response.status_code}")
        print(f"📡 Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            modelos = response.json()
            print(f"✅ Respuesta exitosa: {len(modelos)} modelos")
            
            print("\n📋 Primeros 10 modelos:")
            for i, modelo in enumerate(modelos[:10]):
                print(f"  {i+1}. {modelo}")
                
            # Buscar específicamente los modelos 9301, 9302, 9361
            modelos_buscados = ['9301', '9302', '9361']
            print(f"\n🔍 Buscando modelos que contengan: {modelos_buscados}")
            
            for buscar in modelos_buscados:
                encontrados = [m['modelo'] for m in modelos if buscar in m['modelo']]
                if encontrados:
                    print(f"  ✅ Modelos con '{buscar}': {encontrados}")
                else:
                    print(f"  ❌ No se encontraron modelos con '{buscar}'")
                    
        else:
            print(f"❌ Error en respuesta: {response.status_code}")
            print(f"📄 Contenido: {response.text[:200]}...")
            
    except Exception as e:
        print(f"❌ Error en request: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n🌍 Puedes probar manualmente en: {base_url}/listar_modelos_bom")
    print("(Después de hacer login)")

if __name__ == "__main__":
    test_endpoint_modelos()
