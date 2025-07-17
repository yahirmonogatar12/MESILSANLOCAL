import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from db import obtener_modelos_bom

def verificar_modelos():
    print("=== Verificando modelos en la base de datos ===")
    
    try:
        modelos = obtener_modelos_bom()
        print(f"Total de modelos encontrados: {len(modelos)}")
        
        print("\nPrimeros 15 modelos:")
        for i, modelo in enumerate(modelos[:15]):
            print(f"  {i+1}. {modelo['modelo']}")
            
        if len(modelos) > 15:
            print(f"  ... y {len(modelos)-15} más")
            
        # Buscar específicamente los modelos que mencionas
        modelos_buscados = ['9301', '9302', '9361']
        print(f"\nBuscando modelos que contengan: {modelos_buscados}")
        
        for buscar in modelos_buscados:
            encontrados = [m['modelo'] for m in modelos if buscar in m['modelo']]
            print(f"  Modelos con '{buscar}': {encontrados}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verificar_modelos()
