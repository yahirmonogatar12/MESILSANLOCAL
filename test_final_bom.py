import requests

def test_bom_final():
    base_url = "http://192.168.0.211:5000"
    
    print("=== Test Final del Sistema BOM ===")
    
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
    
    # Test página de Control de BOM
    print("\n🌐 Probando página de Control de BOM...")
    try:
        bom_page_response = session.get(f"{base_url}/informacion_basica/control_de_bom")
        if bom_page_response.status_code == 200:
            html_content = bom_page_response.text
            print("✅ Página cargada exitosamente")
            
            # Verificar que los modelos estén en el HTML
            modelos_en_html = []
            if 'EBR30299301' in html_content:
                modelos_en_html.append('EBR30299301')
            if 'EBR30299302' in html_content:
                modelos_en_html.append('EBR30299302')
            if 'EBR30299361' in html_content:
                modelos_en_html.append('EBR30299361')
                
            if modelos_en_html:
                print(f"✅ Modelos encontrados en HTML: {modelos_en_html}")
            else:
                print("❌ No se encontraron modelos en el HTML")
                
        else:
            print(f"❌ Error cargando página: {bom_page_response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test endpoint de modelos
    print("\n🔍 Probando endpoint de modelos...")
    try:
        modelos_response = session.get(f"{base_url}/listar_modelos_bom")
        if modelos_response.status_code == 200:
            modelos = modelos_response.json()
            print(f"✅ Endpoint funcionando: {len(modelos)} modelos")
            
            # Buscar específicamente los modelos que necesitas
            modelos_encontrados = {}
            for modelo in modelos:
                if '9301' in modelo['modelo']:
                    modelos_encontrados['9301'] = modelo['modelo']
                elif '9302' in modelo['modelo']:
                    modelos_encontrados['9302'] = modelo['modelo']
                elif '9361' in modelo['modelo']:
                    modelos_encontrados['9361'] = modelo['modelo']
                    
            print("🎯 Modelos específicos encontrados:")
            for codigo, nombre_completo in modelos_encontrados.items():
                print(f"  ✅ {codigo}: {nombre_completo}")
                
        else:
            print(f"❌ Error en endpoint: {modelos_response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n🎉 Instrucciones para usar:")
    print(f"1. Ve a: {base_url}")
    print("2. Login: 1111 / 1111")
    print("3. Navega a Control de BOM")
    print("4. Ahora deberías ver los modelos (9301, 9302, 9361, etc.) en ambos dropdowns")
    print("5. Selecciona 'Todos los modelos' y haz clic en 'Consultar'")
    print("6. Usa el segundo dropdown para filtrar por modelo específico")

if __name__ == "__main__":
    test_bom_final()
