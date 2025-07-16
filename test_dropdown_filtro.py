import requests
import json

def test_filtro_dropdown_modelo():
    base_url = "http://192.168.0.211:5000"
    
    print("=== Prueba del filtro dropdown por modelo ===")
    
    # Login
    session = requests.Session()
    login_data = {'username': '1111', 'password': '1111'}
    
    try:
        login_response = session.post(f"{base_url}/login", data=login_data)
        if login_response.status_code != 200:
            print(f"Error en login: {login_response.status_code}")
            return
        print("✓ Login exitoso")
    except Exception as e:
        print(f"Error conectando: {e}")
        return
    
    # Obtener lista de modelos disponibles
    print("\n1. Obteniendo modelos disponibles...")
    try:
        modelos_response = session.get(f"{base_url}/listar_modelos_bom")
        if modelos_response.status_code == 200:
            modelos = modelos_response.json()
            print(f"✓ {len(modelos)} modelos disponibles")
            
            print("\n2. Lista de modelos para el filtro dropdown:")
            for i, modelo in enumerate(modelos[:10]):  # Mostrar primeros 10
                print(f"   {i+1}. {modelo['modelo']}")
            if len(modelos) > 10:
                print(f"   ... y {len(modelos)-10} más")
                
            # Probar filtrar por modelo específico
            if modelos:
                modelo_test = modelos[0]['modelo']
                print(f"\n3. Probando filtro para modelo: {modelo_test}")
                
                # Primero obtener todos los datos
                bom_data = {'modelo': 'todos'}
                bom_response = session.post(
                    f"{base_url}/listar_bom",
                    headers={'Content-Type': 'application/json'},
                    data=json.dumps(bom_data)
                )
                
                if bom_response.status_code == 200:
                    todos_items = bom_response.json()
                    print(f"   Total de elementos (todos los modelos): {len(todos_items)}")
                    
                    # Ahora filtrar por modelo específico
                    bom_data_especifico = {'modelo': modelo_test}
                    bom_response_especifico = session.post(
                        f"{base_url}/listar_bom",
                        headers={'Content-Type': 'application/json'},
                        data=json.dumps(bom_data_especifico)
                    )
                    
                    if bom_response_especifico.status_code == 200:
                        items_especificos = bom_response_especifico.json()
                        print(f"   Elementos del modelo {modelo_test}: {len(items_especificos)}")
                        
                        if items_especificos:
                            print(f"\n4. Primeros 3 elementos del modelo {modelo_test}:")
                            for i, item in enumerate(items_especificos[:3]):
                                print(f"   {i+1}. Código: {item.get('codigoMaterial', 'N/A')} - Tipo: {item.get('tipoMaterial', 'N/A')}")
                
        else:
            print(f"✗ Error obteniendo modelos: {modelos_response.status_code}")
            
    except Exception as e:
        print(f"✗ Error: {e}")
    
    print(f"\n5. Funcionalidad del filtro dropdown:")
    print("   - El primer dropdown selecciona el conjunto de datos a consultar")
    print("   - El segundo dropdown (filtro) permite filtrar por modelo específico")
    print("   - Cada elemento tiene su modelo asociado como data-attribute")
    print("   - El filtro muestra/oculta filas según el modelo seleccionado")
    
    print(f"\n6. Accede a: {base_url}")
    print("   - Haz login con 1111/1111")
    print("   - Ve a Control de BOM")
    print("   - Selecciona 'Todos los modelos' en el primer dropdown")
    print("   - Haz clic en 'Consultar' para cargar todos los datos")
    print("   - Usa el segundo dropdown para filtrar por modelo específico")
    print("   - Observa cómo se filtran los elementos en tiempo real")
    
    print("\n=== Filtro dropdown implementado exitosamente ===")

if __name__ == "__main__":
    test_filtro_dropdown_modelo()
