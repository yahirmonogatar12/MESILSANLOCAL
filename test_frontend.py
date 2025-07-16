import requests
import json
import webbrowser
import time

def test_bom_frontend():
    base_url = "http://192.168.0.211:5000"
    
    print("=== Prueba de funcionalidad completa BOM ===")
    
    # Test de login
    session = requests.Session()
    login_data = {
        'username': '1111',
        'password': '1111'
    }
    
    try:
        login_response = session.post(f"{base_url}/login", data=login_data)
        if login_response.status_code != 200:
            print(f"Error en login: {login_response.status_code}")
            return
        print("✓ Login exitoso")
    except Exception as e:
        print(f"Error conectando al servidor: {e}")
        return
    
    # Probar cargar template de BOM
    print("\n1. Cargando template de Control de BOM...")
    try:
        template_data = {
            'template_path': 'INFORMACION BASICA/CONTROL_DE_BOM.html'
        }
        template_response = session.post(
            f"{base_url}/cargar_template",
            headers={'Content-Type': 'application/json'},
            data=json.dumps(template_data)
        )
        if template_response.status_code == 200:
            print("✓ Template cargado exitosamente")
            # Guardar el HTML para inspección
            with open('bom_template_test.html', 'w', encoding='utf-8') as f:
                f.write(template_response.text)
            print("  HTML guardado en bom_template_test.html")
        else:
            print(f"✗ Error cargando template: {template_response.status_code}")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # Simular consulta de BOM
    print("\n2. Simulando consulta de BOM...")
    try:
        # Obtener modelos
        modelos_response = session.get(f"{base_url}/listar_modelos_bom")
        modelos = modelos_response.json()
        
        if modelos:
            modelo_test = modelos[0]['modelo']
            print(f"  Consultando modelo: {modelo_test}")
            
            # Obtener datos del BOM
            bom_data = {'modelo': modelo_test}
            bom_response = session.post(
                f"{base_url}/listar_bom",
                headers={'Content-Type': 'application/json'},
                data=json.dumps(bom_data)
            )
            
            if bom_response.status_code == 200:
                bom_items = bom_response.json()
                print(f"✓ Datos BOM obtenidos: {len(bom_items)} elementos")
                
                # Mostrar algunos datos de ejemplo
                if bom_items:
                    print("  Primeros 3 elementos:")
                    for i, item in enumerate(bom_items[:3]):
                        print(f"    {i+1}. {item.get('numeroParte', 'N/A')} - {item.get('tipoMaterial', 'N/A')}")
            else:
                print(f"✗ Error obteniendo BOM: {bom_response.status_code}")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # Test de exportación
    print("\n3. Probando exportación a Excel...")
    try:
        export_response = session.get(f"{base_url}/exportar_excel_bom")
        if export_response.status_code == 200:
            print("✓ Exportación exitosa")
            with open('bom_export_test.xlsx', 'wb') as f:
                f.write(export_response.content)
            print("  Archivo guardado como bom_export_test.xlsx")
        else:
            print(f"✗ Error en exportación: {export_response.status_code}")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    print("\n=== Todas las pruebas completadas ===")
    print(f"\nPuedes acceder a la aplicación en: {base_url}")
    print("Usuario: 1111, Contraseña: 1111")

if __name__ == "__main__":
    test_bom_frontend()
