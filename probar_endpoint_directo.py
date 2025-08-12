#!/usr/bin/env python3
"""
Probar endpoint de inventario directamente
"""
import requests
import json
import time

def probar_endpoint_directo():
    """Probar el endpoint optimizado directamente"""
    print("=== PROBANDO ENDPOINT INVENTARIO OPTIMIZADO ===\n")
    
    # Esperar un momento para que el servidor se estabilice
    print("⏱️ Esperando que el servidor se estabilice...")
    time.sleep(2)
    
    try:
        # URL del endpoint
        url = "http://localhost:5000/api/inventario/consultar"
        
        # Datos de prueba (filtros vacíos)
        data = {
            "numeroParte": "",
            "propiedad": "",
            "cantidadMinima": 0
        }
        
        headers = {
            'Content-Type': 'application/json'
        }
        
        print(f"🔗 Enviando POST a: {url}")
        print(f"📄 Datos: {json.dumps(data, indent=2)}")
        
        # Hacer la solicitud
        response = requests.post(url, json=data, headers=headers, timeout=10)
        
        print(f"\n📊 Código de respuesta: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get('success'):
                inventario = result.get('inventario', [])
                print(f" Respuesta exitosa")
                print(f"📦 Total registros: {len(inventario)}")
                
                if inventario:
                    print(f"🗄️ Modo: {result.get('modo', 'desconocido')}")
                    
                    print("\n=== DATOS DEL INVENTARIO ===")
                    for i, item in enumerate(inventario[:3], 1):  # Primeros 3
                        numero_parte = item.get('numero_parte', 'N/A')
                        entradas = float(item.get('total_entradas', 0))
                        salidas = float(item.get('total_salidas', 0))
                        cantidad = float(item.get('cantidad_total', 0))
                        
                        print(f"\n{i}. {numero_parte}")
                        print(f"   📈 Entradas: {entradas:,.0f}")
                        print(f"   📉 Salidas: {salidas:,.0f}")
                        print(f"   📦 Disponible: {cantidad:,.0f}")
                        
                        # Verificar cálculo
                        esperado = entradas - salidas
                        if abs(cantidad - esperado) < 0.01:
                            print(f"    Cálculo correcto: {entradas:,.0f} - {salidas:,.0f} = {cantidad:,.0f}")
                        else:
                            print(f"   ❌ Error en cálculo: esperado {esperado:,.0f}, obtenido {cantidad:,.0f}")
                else:
                    print(" No hay datos en el inventario")
                    
            else:
                print(f"❌ Error en respuesta: {result.get('error', 'Error desconocido')}")
                
        elif response.status_code == 500:
            print("❌ Error interno del servidor (500)")
            try:
                error_data = response.json()
                print(f"Error detallado: {error_data.get('error', 'Error no especificado')}")
            except:
                print(f"Error texto: {response.text[:200]}...")
        else:
            print(f"❌ Error HTTP {response.status_code}")
            print(f"Respuesta: {response.text[:200]}...")
            
    except requests.exceptions.ConnectionError:
        print("❌ No se puede conectar al servidor")
        print("💡 Asegúrate de que el servidor Flask esté ejecutándose en http://localhost:5000")
    except requests.exceptions.Timeout:
        print("❌ La solicitud tardó demasiado en responder")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")

def mostrar_estado_esperado():
    """Mostrar el estado esperado del sistema"""
    print("\n=== ESTADO ESPERADO DEL SISTEMA ===")
    print("""
    📊 DATOS VERIFICADOS EN MySQL:
    
    1. 0RH5602C622: 
       📈 Entradas: 90,000
       📉 Salidas: 105,000  
       📦 Disponible: -15,000
       
    2. 0CK102CK5DA:
       📈 Entradas: 4,000
       📉 Salidas: 12,000
       📦 Disponible: -8,000
       
    3. 0DR107009AA:
       📈 Entradas: 5,000
       📉 Salidas: 0
       📦 Disponible: 5,000
    
     Tabla: db_rrpq0erbdujn.inventario_consolidado
     Registros: 4 números de parte
     Conexión MySQL: Funcionando intermitentemente
    """)

if __name__ == "__main__":
    probar_endpoint_directo()
    mostrar_estado_esperado()
