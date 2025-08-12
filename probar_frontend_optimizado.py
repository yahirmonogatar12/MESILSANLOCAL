#!/usr/bin/env python3
"""
Verificador del frontend optimizado con entradas y salidas
"""
import requests
import json

def probar_frontend_optimizado():
    """Probar la funcionalidad del frontend optimizado"""
    print("=== VERIFICACIÓN DEL FRONTEND OPTIMIZADO ===\n")
    
    try:
        # Hacer solicitud al endpoint optimizado
        url = "http://localhost:5000/api/inventario/consultar"
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            print(f" Endpoint responde correctamente")
            print(f"📊 Total de registros: {len(data)}")
            
            # Mostrar algunos ejemplos de datos
            print("\n=== EJEMPLOS DE DATOS OPTIMIZADOS ===")
            for i, item in enumerate(data[:3]):  # Primeros 3 registros
                numero_parte = item.get('numero_parte', 'N/A')
                total_entradas = item.get('total_entradas', 0)
                total_salidas = item.get('total_salidas', 0)
                cantidad_total = item.get('cantidad_total', 0)
                
                print(f"\n{i+1}. Número de Parte: {numero_parte}")
                print(f"   📈 Entradas: {total_entradas:,}")
                print(f"   📉 Salidas: {total_salidas:,}")
                print(f"   📦 Disponible: {cantidad_total:,}")
                
                # Determinar estado visual
                if cantidad_total > 0:
                    status = "🟢 DISPONIBLE"
                elif cantidad_total < 0:
                    status = "🔴 DÉFICIT"
                else:
                    status = "🟡 EQUILIBRIO"
                
                print(f"   Estado: {status}")
            
            # Verificar estructura esperada
            print("\n=== VERIFICACIÓN DE ESTRUCTURA ===")
            if data:
                sample = data[0]
                campos_esperados = ['numero_parte', 'total_entradas', 'total_salidas', 'cantidad_total']
                for campo in campos_esperados:
                    if campo in sample:
                        print(f" Campo '{campo}' presente")
                    else:
                        print(f"❌ Campo '{campo}' faltante")
            
        else:
            print(f"❌ Error en endpoint: {response.status_code}")
            print(f"Respuesta: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ No se puede conectar al servidor. ¿Está ejecutándose?")
        print("💡 Ejecuta: python run.py")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")

def generar_ejemplo_html():
    """Generar ejemplo de cómo se verá en el frontend"""
    print("\n=== EJEMPLO DE RENDERIZADO FRONTEND ===")
    print("""
    Así se verá en la interfaz:
    
    ┌─────────────────┬──────────────┬──────────────┐
    │ Número de Parte │ Código       │ Cantidad     │
    ├─────────────────┼──────────────┼──────────────┤
    │ 0RH5602C622     │ MAT-001      │ 📈 -15,000   │
    │                 │              │ +90,000      │
    │                 │              │ -105,000     │
    ├─────────────────┼──────────────┼──────────────┤
    │ 0CK102CK5DA     │ MAT-002      │  -8,000    │
    │                 │              │ +4,000       │
    │                 │              │ -12,000      │
    └─────────────────┴──────────────┴──────────────┘
    
    Colores:
    🟢 Verde: Inventario positivo (disponible)
    🔴 Rojo: Inventario negativo (déficit)  
    🟡 Amarillo: Inventario en cero (equilibrio)
    
    Tooltip al pasar el mouse:
    "Entradas: 90,000
     Salidas: 105,000
     Disponible: -15,000"
    """)

if __name__ == "__main__":
    probar_frontend_optimizado()
    generar_ejemplo_html()
