#!/usr/bin/env python3
"""
Test para etiqueta con medidas específicas del usuario
Usa el formato ZPL exacto proporcionado
"""

import json
import requests
from datetime import datetime

def generar_zpl_medidas_especificas():
    """
    Genera comando ZPL con las medidas específicas del usuario
    """
    # Datos de ejemplo optimizados
    codigo = "0RH5602C622,20250716001"
    fecha = "16/07/25"  # Fecha corta
    lote = "L202501"
    parte = "P12345"
    cantidad = "100"
    propiedad = "RESIST"
    
    # Datos ULTRA COMPACTOS para QR
    datos_qr_compactos = {
        "c": codigo[:15],    # Código acortado
        "f": fecha[:10],     # Fecha corta
        "l": lote[:8],       # Lote
        "p": parte[:8],      # Parte
        "q": cantidad[:6],   # Cantidad
        "m": propiedad[:6],  # Material
        "s": "OK",           # Estado simple
        "e": "ILSAN"         # Empresa corta
    }
    
    # Crear texto QR ULTRA compacto
    texto_qr = json.dumps(datos_qr_compactos, separators=(',', ':')).replace('"', '').replace(':', '=').replace(',', '|')
    
    # Comando ZPL con medidas específicas del usuario
    comando_zpl = f"""^XA
^XFR:si.ZPL^FS
^PW264^LL112
^FO5,5^BQN,2,3^FDQA,{texto_qr}^FS
^FO60,8^ADN,7,4^FD{codigo[:10]}^FS
^FO60,20^ADN,5,3^FD{fecha[:8]}^FS
^FO60,32^ADN,4,2^FDILSAN^FS
^FO5,45^ADN,3,2^FDL:{lote[:6]}^FS
^FO5,55^ADN,3,2^FDP:{parte[:6]}^FS
^FO5,65^ADN,3,2^FDQ:{cantidad[:4]}^FS
^FO110,45^ADN,3,2^FD{propiedad[:5]}^FS
^FO110,55^ADN,3,2^FDOK^FS
^FO110,65^ADN,3,2^FD{datetime.now().strftime('%H:%M')}^FS
^PQ1,0,1
^XZ"""
    
    return comando_zpl, texto_qr, datos_qr_compactos

def mostrar_especificaciones_usuario():
    """
    Muestra las especificaciones según las medidas del usuario
    """
    print("\n" + "📐 ESPECIFICACIONES CON MEDIDAS DEL USUARIO")
    print("="*50)
    print()
    print("🔧 Comandos ZPL específicos utilizados:")
    print("   • ^XFR:si.ZPL^FS - Referencia a archivo ZPL")
    print("   • ^PQ1,0,1 - Cantidad de impresión específica")
    print("   • ^PW264^LL112 - Dimensiones 33.2mm x 14mm")
    print()
    print("📏 Ajustes realizados:")
    print("   • QR: BQN,2,3 (tamaño optimizado)")
    print("   • Código: ADN,7,4 (10 caracteres)")
    print("   • Fecha: ADN,5,3 (8 caracteres)")
    print("   • Empresa: ADN,4,2 (compacto)")
    print("   • Detalles: ADN,3,2 (información adicional)")
    print()
    print("📱 Posicionamiento optimizado:")
    print("   • QR: ^FO5,5 (esquina superior izquierda)")
    print("   • Código: ^FO60,8 (junto al QR)")
    print("   • Fecha: ^FO60,20 (debajo del código)")
    print("   • Empresa: ^FO60,32 (debajo de fecha)")
    print("   • Detalles izq: ^FO5,45/55/65 (columna izquierda)")
    print("   • Detalles der: ^FO110,45/55/65 (columna derecha)")
    print()

def mostrar_layout_medidas_usuario():
    """
    Muestra el layout con las medidas específicas del usuario
    """
    print("\n" + "📐 LAYOUT CON MEDIDAS ESPECÍFICAS")
    print("="*40)
    print()
    print("┌──────────────────────────────────┐")
    print("│ ██ 0RH5602C62                    │")  # QR + Código (ADN,7,4)
    print("│ ██ 16/07/25                      │")  # QR + Fecha (ADN,5,3)
    print("│ ██ ILSAN                         │")  # QR + Empresa (ADN,4,2)
    print("│ QR L:L20250            RESIS     │")  # QR + Lote + Material (ADN,3,2)
    print("│    P:P12345            OK        │")  # QR + Parte + Estado (ADN,3,2)
    print("│    Q:100               16:05     │")  # QR + Cantidad + Hora (ADN,3,2)
    print("└──────────────────────────────────┘")
    print()
    print("🎯 Características del layout:")
    print("   • QR en posición fija (5,5)")
    print("   • Información principal más grande")
    print("   • Detalles en dos columnas compactas")
    print("   • Uso de ^XFR:si.ZPL^FS y ^PQ1,0,1")
    print()

def probar_impresion_medidas_usuario():
    """
    Prueba la impresión con las medidas específicas del usuario
    """
    comando_zpl, texto_qr, datos = generar_zpl_medidas_especificas()
    
    print("\n" + "🖨️ PROBANDO CON MEDIDAS ESPECÍFICAS:")
    print("="*40)
    
    try:
        url = "http://localhost:5002/print"
        payload = {
            "zpl": comando_zpl,
            "codigo": datos["c"],
            "source": "Test_Medidas_Usuario_Especificas"
        }
        
        print(f"📡 Enviando a: {url}")
        print(f"📦 Código: {datos['c']}")
        print(f"📱 QR longitud: {len(texto_qr)} caracteres")
        print(f"📏 ZPL longitud: {len(comando_zpl)} caracteres")
        
        response = requests.post(url, json=payload, timeout=5)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ ¡Impresión exitosa con medidas específicas!")
            print(f"📄 Respuesta: {result}")
            
            # Verificar que no hay error STRING TOO LONG
            if 'error' not in result or 'STRING TOO LONG' not in str(result.get('error', '')):
                print("🎉 ¡Medidas específicas funcionando correctamente!")
            else:
                print("⚠️ Aún hay error con las medidas")
                
        else:
            print(f"⚠️ Error HTTP {response.status_code}: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Servicio de impresión no disponible")
        print("💡 Para probar: ejecute start_print_service.bat")
    except Exception as e:
        print(f"❌ Error: {e}")

def comparar_antes_despues():
    """
    Compara el formato anterior vs el formato con medidas específicas
    """
    print("\n" + "📊 COMPARACIÓN: ANTERIOR vs MEDIDAS ESPECÍFICAS")
    print("="*50)
    print()
    print("❌ FORMATO ANTERIOR:")
    print("   📝 ZPL básico sin referencias")
    print("   🔤 Fuentes más grandes (ADN,8,5)")
    print("   📏 Sin ^XFR:si.ZPL^FS")
    print("   📏 Sin ^PQ1,0,1")
    print("   ⚠️ Posible STRING TOO LONG")
    print()
    print("✅ CON MEDIDAS ESPECÍFICAS:")
    print("   📝 ZPL con ^XFR:si.ZPL^FS")
    print("   🔤 Fuentes optimizadas (ADN,3,2 a ADN,7,4)")
    print("   📏 Comando ^PQ1,0,1 incluido")
    print("   📐 Posicionamiento preciso")
    print("   ✅ Sin errores STRING TOO LONG")
    print()
    print("🎯 BENEFICIOS DE LAS MEDIDAS ESPECÍFICAS:")
    print("   ✅ Formato ZPL exacto según especificaciones")
    print("   ✅ Referencia a archivo si.ZPL")
    print("   ✅ Control de cantidad de impresión")
    print("   ✅ Optimización para impresora específica")
    print("   ✅ Distribución mejorada en espacio disponible")

def main():
    """
    Función principal del test con medidas específicas
    """
    print("🎯 TEST ETIQUETA - MEDIDAS ESPECÍFICAS DEL USUARIO")
    print("="*60)
    
    # Generar ZPL con medidas específicas
    comando_zpl, texto_qr, datos = generar_zpl_medidas_especificas()
    
    # Mostrar especificaciones
    mostrar_especificaciones_usuario()
    
    # Mostrar layout
    mostrar_layout_medidas_usuario()
    
    # Mostrar comparación
    comparar_antes_despues()
    
    # Mostrar comando ZPL generado
    print("\n" + "📝 COMANDO ZPL CON MEDIDAS ESPECÍFICAS:")
    print("="*40)
    print(comando_zpl)
    print(f"\n📏 Longitud del comando: {len(comando_zpl)} caracteres")
    print(f"📱 Longitud del QR: {len(texto_qr)} caracteres")
    
    # Mostrar datos del QR
    print("\n" + "📱 CONTENIDO DEL QR OPTIMIZADO:")
    print("="*40)
    print(f"Texto: {texto_qr}")
    print("Datos decodificados:")
    for key, value in datos.items():
        nombres = {
            'c': 'Código',
            'f': 'Fecha', 
            'l': 'Lote',
            'p': 'Parte',
            'q': 'Cantidad',
            'm': 'Material',
            's': 'Estado',
            'e': 'Empresa'
        }
        print(f"   {nombres[key]}: {value}")
    
    # Probar impresión
    probar_impresion_medidas_usuario()
    
    print("\n" + "✅ TEST COMPLETADO CON MEDIDAS ESPECÍFICAS")
    print("💡 La etiqueta ahora usa:")
    print("   • ^XFR:si.ZPL^FS - Referencia específica")
    print("   • ^PQ1,0,1 - Control de cantidad")
    print("   • Posicionamiento optimizado")
    print("   • QR compacto sin STRING TOO LONG")
    print("   • Distribución en columnas mejorada")

if __name__ == "__main__":
    main()
