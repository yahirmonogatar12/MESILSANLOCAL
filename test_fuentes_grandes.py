#!/usr/bin/env python3
"""
Test para etiqueta con fuentes MÁS GRANDES
Solucionando el problema de texto muy pequeño
"""

import json
import requests
from datetime import datetime

def generar_zpl_fuentes_grandes():
    """
    Genera comando ZPL con fuentes MÁS GRANDES para mejor legibilidad
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
    
    # Comando ZPL con FUENTES MÁS GRANDES
    comando_zpl = f"""^XA
^XFR:si.ZPL^FS
^PW264^LL112
^FO5,5^BQN,2,4^FDQA,{texto_qr}^FS
^FO70,5^ADN,12,8^FD{codigo[:9]}^FS
^FO70,22^ADN,10,6^FD{fecha[:8]}^FS
^FO70,38^ADN,8,5^FDILSAN^FS
^FO5,55^ADN,6,4^FDL:{lote[:6]}^FS
^FO5,70^ADN,6,4^FDP:{parte[:6]}^FS
^FO5,85^ADN,6,4^FDQ:{cantidad[:4]}^FS
^FO130,55^ADN,6,4^FD{propiedad[:5]}^FS
^FO130,70^ADN,6,4^FDOK^FS
^FO130,85^ADN,6,4^FD{datetime.now().strftime('%H:%M')}^FS
^PQ1,0,1
^XZ"""
    
    return comando_zpl, texto_qr, datos_qr_compactos

def mostrar_cambios_fuentes():
    """
    Muestra los cambios en los tamaños de fuente
    """
    print("\n" + "🔤 CAMBIOS EN TAMAÑOS DE FUENTE")
    print("="*40)
    print()
    print("❌ ANTES (muy pequeño):")
    print("   • Código: ADN,7,4")
    print("   • Fecha: ADN,5,3") 
    print("   • Empresa: ADN,4,2")
    print("   • Detalles: ADN,3,2")
    print("   • QR: BQN,2,3")
    print()
    print("✅ AHORA (más grande y legible):")
    print("   • Código: ADN,12,8 (MUCHO MÁS GRANDE)")
    print("   • Fecha: ADN,10,6 (MÁS GRANDE)")
    print("   • Empresa: ADN,8,5 (GRANDE)")
    print("   • Detalles: ADN,6,4 (LEGIBLE)")
    print("   • QR: BQN,2,4 (MÁS GRANDE)")
    print()
    print("📊 Incremento de tamaño:")
    print("   • Código: +71% más grande")
    print("   • Fecha: +100% más grande")
    print("   • Empresa: +100% más grande")
    print("   • Detalles: +100% más grande")
    print("   • QR: +33% más grande")
    print()

def mostrar_layout_fuentes_grandes():
    """
    Muestra el layout con fuentes más grandes
    """
    print("\n" + "📐 LAYOUT CON FUENTES MÁS GRANDES")
    print("="*40)
    print()
    print("┌──────────────────────────────────┐")
    print("│ ██ 0RH5602C6                     │")  # QR + Código (ADN,12,8 - MUY GRANDE)
    print("│ ██ 16/07/25                      │")  # QR + Fecha (ADN,10,6 - GRANDE)
    print("│ ██ ILSAN                         │")  # QR + Empresa (ADN,8,5 - GRANDE)
    print("│ QR L:L20250         RESIS        │")  # QR + Lote + Material (ADN,6,4 - LEGIBLE)
    print("│    P:P12345         OK           │")  # QR + Parte + Estado (ADN,6,4 - LEGIBLE)
    print("│    Q:100            16:15        │")  # QR + Cantidad + Hora (ADN,6,4 - LEGIBLE)
    print("└──────────────────────────────────┘")
    print()
    print("🎯 Características del nuevo layout:")
    print("   • Código MUCHO más visible (ADN,12,8)")
    print("   • Fecha grande y clara (ADN,10,6)")
    print("   • Todos los detalles legibles (ADN,6,4)")
    print("   • QR más grande para mejor escaneo")
    print("   • Posiciones ajustadas para el nuevo tamaño")
    print()

def mostrar_posiciones_ajustadas():
    """
    Muestra cómo se ajustaron las posiciones para las fuentes más grandes
    """
    print("\n" + "📐 POSICIONES AJUSTADAS PARA FUENTES GRANDES")
    print("="*50)
    print()
    print("🔧 Ajustes realizados:")
    print("   • QR: ^FO5,5 (sin cambio)")
    print("   • Código: ^FO70,5 (movido a la derecha)")
    print("   • Fecha: ^FO70,22 (espaciado vertical aumentado)")
    print("   • Empresa: ^FO70,38 (espaciado vertical aumentado)")
    print("   • Detalles izq: ^FO5,55/70/85 (espaciado aumentado)")
    print("   • Detalles der: ^FO130,55/70/85 (sin cambio)")
    print()
    print("📏 Espaciado vertical:")
    print("   • Entre código y fecha: 17 dots (era 12)")
    print("   • Entre fecha y empresa: 16 dots (era 12)")
    print("   • Entre filas de detalles: 15 dots (era 10)")
    print()
    print("💡 Esto asegura que el texto no se superponga")
    print("   y sea completamente legible en la etiqueta.")

def probar_impresion_fuentes_grandes():
    """
    Prueba la impresión con fuentes más grandes
    """
    comando_zpl, texto_qr, datos = generar_zpl_fuentes_grandes()
    
    print("\n" + "🖨️ PROBANDO CON FUENTES MÁS GRANDES:")
    print("="*40)
    
    try:
        url = "http://localhost:5002/print"
        payload = {
            "zpl": comando_zpl,
            "codigo": datos["c"],
            "source": "Test_Fuentes_Grandes_Legibles"
        }
        
        print(f"📡 Enviando a: {url}")
        print(f"📦 Código: {datos['c']}")
        print(f"📱 QR longitud: {len(texto_qr)} caracteres")
        print(f"📏 ZPL longitud: {len(comando_zpl)} caracteres")
        
        response = requests.post(url, json=payload, timeout=5)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ ¡Impresión exitosa con fuentes MÁS GRANDES!")
            print(f"📄 Respuesta: {result}")
            print("🎉 ¡Ahora el texto debería verse MUCHO más grande!")
            
        else:
            print(f"⚠️ Error HTTP {response.status_code}: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Servicio de impresión no disponible")
        print("💡 Para probar: ejecute start_print_service.bat")
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    """
    Función principal del test con fuentes más grandes
    """
    print("🔤 TEST ETIQUETA - FUENTES MÁS GRANDES Y LEGIBLES")
    print("="*60)
    
    # Generar ZPL con fuentes más grandes
    comando_zpl, texto_qr, datos = generar_zpl_fuentes_grandes()
    
    # Mostrar cambios en fuentes
    mostrar_cambios_fuentes()
    
    # Mostrar layout
    mostrar_layout_fuentes_grandes()
    
    # Mostrar posiciones ajustadas
    mostrar_posiciones_ajustadas()
    
    # Mostrar comando ZPL generado
    print("\n" + "📝 COMANDO ZPL CON FUENTES MÁS GRANDES:")
    print("="*40)
    print(comando_zpl)
    print(f"\n📏 Longitud del comando: {len(comando_zpl)} caracteres")
    print(f"📱 Longitud del QR: {len(texto_qr)} caracteres")
    
    # Mostrar datos del QR
    print("\n" + "📱 CONTENIDO DEL QR:")
    print("="*40)
    print(f"Texto: {texto_qr}")
    
    # Probar impresión
    probar_impresion_fuentes_grandes()
    
    print("\n" + "✅ TEST COMPLETADO CON FUENTES GRANDES")
    print("💡 La etiqueta ahora tiene:")
    print("   • Código MUCHO más grande (ADN,12,8)")
    print("   • Fecha más visible (ADN,10,6)")
    print("   • Empresa legible (ADN,8,5)")
    print("   • Detalles claros (ADN,6,4)")
    print("   • QR más grande para mejor escaneo")
    print("   • Posiciones ajustadas sin superposición")
    print("\n🎯 ¡El texto ya NO debería verse pequeño!")

if __name__ == "__main__":
    main()
