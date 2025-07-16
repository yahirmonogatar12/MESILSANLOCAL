import sys
import os

# Añadir el directorio de la aplicación al path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from db import obtener_modelos_bom, listar_bom_por_modelo

def test_bom_functions():
    print("=== Prueba de funciones BOM ===")
    
    # Probar obtener modelos
    print("\n1. Obteniendo modelos BOM...")
    try:
        modelos = obtener_modelos_bom()
        print(f"Modelos encontrados: {len(modelos)}")
        for i, modelo in enumerate(modelos[:5]):  # Solo primeros 5
            print(f"  {i+1}. {modelo['modelo']}")
        if len(modelos) > 5:
            print(f"  ... y {len(modelos)-5} más")
    except Exception as e:
        print(f"Error: {e}")
    
    # Probar listar BOM
    print("\n2. Obteniendo datos de BOM...")
    try:
        if modelos:
            primer_modelo = modelos[0]['modelo']
            print(f"Consultando BOM para modelo: {primer_modelo}")
            bom_data = listar_bom_por_modelo(primer_modelo)
            print(f"Registros encontrados: {len(bom_data)}")
            
            if bom_data:
                print("Primer registro:")
                primer_registro = bom_data[0]
                print(f"  - Código: {primer_registro.get('codigoMaterial', 'N/A')}")
                print(f"  - Número de parte: {primer_registro.get('numeroParte', 'N/A')}")
                print(f"  - Tipo: {primer_registro.get('tipoMaterial', 'N/A')}")
                print(f"  - Cantidad total: {primer_registro.get('cantidadTotal', 'N/A')}")
        else:
            print("No hay modelos para consultar")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n=== Fin de la prueba ===")

if __name__ == "__main__":
    test_bom_functions()
