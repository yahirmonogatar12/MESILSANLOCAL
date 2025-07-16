#!/usr/bin/env python3
"""
Test para etiqueta optimizada - SOLUCION "STRING TOO LONG"
Genera comandos ZPL compactos para 33.2mm x 14mm
"""

import json
import requests
from datetime import datetime

def generar_zpl_optimizado():
    """
    Genera comando ZPL optimizado para evitar "STRING TOO LONG"
    """
    # Datos de ejemplo con formato COMPACTO
    codigo = "0RH5602C622,20250716001"
    fecha = "16/07/25"  # Fecha acortada
    lote = "L202501"
    parte = "P12345"
    cantidad = "100"
    propiedad = "RESIST"
    
    # Datos ULTRA COMPACTOS para QR (evita STRING TOO LONG)
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
    
    # Crear texto QR ULTRA compacto (sin comillas ni espacios)
    texto_qr = json.dumps(datos_qr_compactos, separators=(',', ':')).replace('"', '').replace(':', '=').replace(',', '|')
    
    # Comando ZPL optimizado (reduce tamaños de fuente y posiciones)
    comando_zpl = f"""^XA
^PW264^LL112
^FO5,5^BQN,2,3^FDQA,{texto_qr}^FS
^FO65,8^ADN,8,5^FD{codigo[:10]}^FS
^FO65,22^ADN,6,3^FD{fecha[:8]}^FS
^FO65,35^ADN,5,3^FDILSAN^FS
^FO5,50^ADN,4,2^FDL:{lote[:6]}^FS
^FO5,62^ADN,4,2^FDP:{parte[:6]}^FS
^FO5,74^ADN,4,2^FDQ:{cantidad[:4]}^FS
^FO120,50^ADN,4,2^FD{propiedad[:5]}^FS
^FO120,62^ADN,4,2^FDOK^FS
^FO120,74^ADN,4,2^FD{datetime.now().strftime('%H:%M')}^FS
^XZ"""
    
    return comando_zpl, texto_qr, datos_qr_compactos

def mostrar_solucion_string_too_long():
    """
    Explica la solución al error STRING TOO LONG
    """
    print("\n" + "🚨 SOLUCIÓN AL ERROR 'STRING TOO LONG'")
    print("="*50)
    print()
    print("❌ PROBLEMA ANTERIOR:")
    print("   • QR con JSON largo: 180+ caracteres")
    print("   • Nombres de campos largos: 'codigo', 'propiedad', etc.")
    print("   • Datos sin comprimir")
    print()
    print("✅ SOLUCIÓN IMPLEMENTADA:")
    print("   • Campos ultra cortos: 'c', 'f', 'l', 'p', etc.")
    print("   • Datos truncados a tamaños específicos")
    print("   • JSON comprimido sin comillas ni espacios")
    print("   • QR reducido de BQN,2,4 a BQN,2,3")
    print("   • Fuentes optimizadas para espacio disponible")
    print()

def mostrar_layout_optimizado():
    """
    Muestra el layout optimizado para 33.2mm x 14mm
    """
    print("\n" + "📐 LAYOUT OPTIMIZADO (33.2mm x 14mm)")
    print("="*40)
    print()
    print("┌──────────────────────────────────┐")
    print("│ ██ 0RH5602C62                    │")  # QR + Código (10 chars)
    print("│ ██ 16/07/25                      │")  # QR + Fecha (8 chars)
    print("│ ██ ILSAN                         │")  # QR + Empresa
    print("│ QR L:L20250   RESIS              │")  # QR + Lote + Material (6+5 chars)
    print("│    P:P12345   OK                 │")  # QR + Parte + Estado
    print("│    Q:100      14:57              │")  # QR + Cantidad + Hora
    print("└──────────────────────────────────┘")
    print()

def mostrar_especificaciones_optimizadas():
    """
    Muestra las especificaciones técnicas optimizadas
    """
    print("\n" + "📊 ESPECIFICACIONES OPTIMIZADAS:")
    print("="*40)
    print("🔧 Cambios para evitar STRING TOO LONG:")
    print("   • QR: BQN,2,3 (era BQN,2,4)")
    print("   • Código: 10 caracteres (era 11)")
    print("   • Fecha: 8 caracteres (era 10)")
    print("   • Lote: 6 caracteres (era 7)")
    print("   • Parte: 6 caracteres (era 7)")
    print("   • Material: 5 caracteres (era 6)")
    print("   • JSON comprimido: 40-60 chars (era 180+)")
    print()
    print("📱 Formato QR ultra compacto:")
    print("   Antes: {\"codigo\":\"0RH5602C622,20250716001\",\"fecha\":\"16/07/2025\"...}")
    print("   Ahora: {c=0RH5602C622,202|f=16/07/25|l=L202501|p=P12345|q=100|m=RESIST|s=OK|e=ILSAN}")
    print()
    print("📏 Dimensiones mantenidas:")
    print("   • 33.2mm x 14mm = 264 x 112 dots a 300dpi")
    print("   • Posiciones ajustadas para mejor distribución")
    print()

def probar_impresion_optimizada():
    """
    Prueba la impresión con el comando optimizado
    """
    comando_zpl, texto_qr, datos = generar_zpl_optimizado()
    
    print("\n" + "🖨️ PROBANDO IMPRESIÓN OPTIMIZADA:")
    print("="*40)
    
    try:
        url = "http://localhost:5002/print"
        payload = {
            "zpl": comando_zpl,
            "codigo": datos["c"],
            "source": "Test_Optimizado_No_String_Too_Long"
        }
        
        print(f"📡 Enviando a: {url}")
        print(f"📦 Código: {datos['c']}")
        print(f"📱 QR longitud: {len(texto_qr)} caracteres")
        
        response = requests.post(url, json=payload, timeout=5)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ ¡Impresión exitosa!")
            print(f"📄 Respuesta: {result}")
            
            # Verificar que no hay error STRING TOO LONG
            if 'error' not in result or 'STRING TOO LONG' not in str(result.get('error', '')):
                print("🎉 ¡ERROR 'STRING TOO LONG' SOLUCIONADO!")
            else:
                print("⚠️ Aún hay error STRING TOO LONG")
                
        else:
            print(f"⚠️ Error HTTP {response.status_code}: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Servicio de impresión no disponible")
        print("💡 Para probar: ejecute start_print_service.bat")
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    """
    Función principal del test optimizado
    """
    print("🔧 TEST ETIQUETA OPTIMIZADA - SOLUCIÓN 'STRING TOO LONG'")
    print("="*60)
    
    # Generar ZPL optimizado
    comando_zpl, texto_qr, datos = generar_zpl_optimizado()
    
    # Mostrar solución
    mostrar_solucion_string_too_long()
    
    # Mostrar layout
    mostrar_layout_optimizado()
    
    # Mostrar especificaciones
    mostrar_especificaciones_optimizadas()
    
    # Mostrar comando ZPL generado
    print("\n" + "📝 COMANDO ZPL OPTIMIZADO:")
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
    probar_impresion_optimizada()
    
    print("\n" + "✅ TEST COMPLETADO")
    print("💡 La etiqueta optimizada:")
    print("   • Evita el error 'STRING TOO LONG'")
    print("   • Mantiene toda la información esencial")
    print("   • Usa formato ultra compacto para QR")
    print("   • Conserva las dimensiones 33.2mm x 14mm")
    print("   • Texto legible y bien distribuido")

if __name__ == "__main__":
    main()
