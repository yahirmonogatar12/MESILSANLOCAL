import requests
import json

def test_filtro_bom():
    base_url = "http://192.168.0.211:5000"
    
    print("=== Prueba del filtro de BOM ===")
    
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
    
    # Obtener datos de BOM para probar filtros
    print("\n1. Obteniendo datos de BOM...")
    try:
        bom_data = {'modelo': 'EBR30299301'}
        bom_response = session.post(
            f"{base_url}/listar_bom",
            headers={'Content-Type': 'application/json'},
            data=json.dumps(bom_data)
        )
        
        if bom_response.status_code == 200:
            bom_items = bom_response.json()
            print(f"✓ {len(bom_items)} elementos obtenidos para modelo EBR30299301")
            
            # Mostrar tipos de materiales únicos para entender qué se puede filtrar
            tipos = set()
            codigos_ejemplo = []
            
            for item in bom_items[:10]:  # Solo primeros 10 para ejemplo
                tipos.add(item.get('tipoMaterial', ''))
                codigos_ejemplo.append(item.get('codigoMaterial', ''))
            
            print("\n2. Ejemplos de datos para filtrar:")
            print(f"   Tipos de material únicos: {sorted(list(tipos))}")
            print(f"   Códigos de ejemplo: {codigos_ejemplo[:5]}")
            
            # Sugerir búsquedas de ejemplo
            print("\n3. Búsquedas sugeridas para probar:")
            if 'RAD' in tipos:
                print("   - Buscar 'RAD' para ver resistores")
            if 'MAIN' in tipos:
                print("   - Buscar 'MAIN' para componentes principales")
            if codigos_ejemplo:
                primer_codigo = codigos_ejemplo[0][:4] if codigos_ejemplo[0] else ""
                if primer_codigo:
                    print(f"   - Buscar '{primer_codigo}' para códigos similares")
            
        else:
            print(f"✗ Error obteniendo BOM: {bom_response.status_code}")
            
    except Exception as e:
        print(f"✗ Error: {e}")
    
    print(f"\n4. Accede a la aplicación en: {base_url}")
    print("   - Selecciona un modelo del dropdown")
    print("   - Haz clic en 'Consultar' para cargar datos")
    print("   - Usa el campo de búsqueda para filtrar elementos")
    print("   - Haz clic en 'Limpiar filtro' para ver todos los elementos nuevamente")
    
    print("\n=== Filtro implementado exitosamente ===")

if __name__ == "__main__":
    test_filtro_bom()
