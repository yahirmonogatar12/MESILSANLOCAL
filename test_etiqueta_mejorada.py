#!/usr/bin/env python3
"""
Test para la etiqueta mejorada con mejor distribución y texto más grande
Optimizada para 33.2mm x 14mm
"""

import json
import requests
from datetime import datetime

def generar_zpl_mejorado():
    """
    Genera comando ZPL con la nueva distribución mejorada
    """
    # Datos de ejemplo
    datos_material = {
        "codigo": "0RH5602C622,20250716001",
        "fecha": "16/07/2025", 
        "lote": "L202501",
        "parte": "P12345",
        "cantidad": "100",
        "propiedad": "RESISTOR",
        "estado": "ACTIVO",
        "empresa": "ILSAN_ELECTRONICS"
    }
    
    # Generar JSON para QR
    texto_qr = json.dumps(datos_material)
    
    # Comando ZPL mejorado con mejor distribución
    comando_zpl = f"""^XA
^PW264^LL112
^FO5,5^BQN,2,4^FDQA,{texto_qr}^FS
^FO75,5^ADN,9,6^FD{datos_material['codigo'][:11]}^FS
^FO75,20^ADN,7,4^FD{datos_material['fecha']}^FS
^FO75,35^ADN,6,3^FDILSAN^FS
^FO5,55^ADN,5,3^FDL:{datos_material['lote'][:7]}^FS
^FO5,70^ADN,5,3^FDP:{datos_material['parte'][:7]}^FS
^FO5,85^ADN,5,3^FDQ:{datos_material['cantidad']}^FS
^FO130,55^ADN,5,3^FD{datos_material['propiedad'][:6]}^FS
^FO130,70^ADN,5,3^FDACTIVO^FS
^FO130,85^ADN,5,3^FDOK^FS
^XZ"""
    
    return comando_zpl, texto_qr, datos_material

def mostrar_layout_mejorado():
    """
    Muestra el layout visual de la etiqueta mejorada
    """
    print("\n" + "="*60)
    print("📐 LAYOUT ETIQUETA MEJORADA (33.2mm x 14mm)")
    print("="*60)
    print()
    print("┌──────────────────────────────────┐")
    print("│ ██ 0RH5602C622,20250716001       │")  # QR + Código principal (más grande)
    print("│ ██ 16/07/2025                    │")  # QR + Fecha (más grande)
    print("│ ██ ILSAN                         │")  # QR + Empresa (más grande)
    print("│ QR L:L202501    RESIST           │")  # QR + Lote + Propiedad
    print("│    P:P12345     ACTIVO           │")  # QR + Parte + Estado
    print("│    Q:100        OK               │")  # QR + Cantidad + Status
    print("└──────────────────────────────────┘")
    print()

def mostrar_mejoras():
    """
    Muestra las mejoras implementadas
    """
    print("\n" + "🔧 MEJORAS IMPLEMENTADAS:")
    print("="*40)
    print("✅ QR más grande: 2x4 (era 2x3)")
    print("✅ Fuentes más grandes: ADN,5,3 a ADN,9,6")
    print("✅ Mejor distribución en 3 columnas")
    print("✅ Código principal más legible (ADN,9,6)")
    print("✅ Fecha más visible (ADN,7,4)")
    print("✅ Separación optimizada entre elementos")
    print("✅ Aprovechamiento total del espacio 33.2mm x 14mm")
    print()

def mostrar_especificaciones_tecnicas():
    """
    Muestra las especificaciones técnicas de la etiqueta
    """
    print("\n" + "📊 ESPECIFICACIONES TÉCNICAS:")
    print("="*40)
    print("📏 Dimensiones físicas:")
    print("   • Ancho: 33.2mm = 264 dots a 300dpi")
    print("   • Alto: 14mm = 112 dots a 300dpi")
    print()
    print("📱 QR Code:")
    print("   • Tamaño: BQN,2,4 (más grande que antes)")
    print("   • Posición: ^FO5,5 (esquina superior izquierda)")
    print("   • Ocupa aprox: 60x60 dots")
    print()
    print("🔤 Fuentes mejoradas:")
    print("   • Código principal: ADN,9,6 (muy grande)")
    print("   • Fecha: ADN,7,4 (grande)")
    print("   • Empresa: ADN,6,3 (mediano)")
    print("   • Detalles: ADN,5,3 (legible)")
    print()
    print("📐 Distribución por zonas:")
    print("   • Zona 1 (0-70): QR + Info principal")
    print("   • Zona 2 (75-264): Código, fecha, empresa")
    print("   • Zona 3 (55-112): Detalles en 3 columnas")
    print()

def probar_impresion_local():
    """
    Intenta enviar la etiqueta al servicio de impresión local
    """
    comando_zpl, texto_qr, datos = generar_zpl_mejorado()
    
    print("\n" + "🖨️ PROBANDO IMPRESIÓN LOCAL:")
    print("="*40)
    
    try:
        # Probar el servicio en puerto 5002
        url = "http://localhost:5002/print"
        payload = {
            "zpl": comando_zpl,
            "codigo": datos["codigo"],
            "source": "Test_Etiqueta_Mejorada"
        }
        
        print(f"📡 Enviando a: {url}")
        print(f"📦 Datos: {payload['codigo']}")
        
        response = requests.post(url, json=payload, timeout=5)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ ¡Impresión exitosa!")
            print(f"📄 Respuesta: {result}")
        else:
            print(f"⚠️ Error HTTP {response.status_code}: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ No se puede conectar al servicio de impresión")
        print("💡 Para imprimir:")
        print("   1. Ejecute: start_print_service.bat")
        print("   2. Luego ejecute este script nuevamente")
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    """
    Función principal del test
    """
    print("🧪 TEST ETIQUETA MEJORADA - MEJOR DISTRIBUCIÓN")
    print("="*60)
    
    # Generar ZPL
    comando_zpl, texto_qr, datos = generar_zpl_mejorado()
    
    # Mostrar layout visual
    mostrar_layout_mejorado()
    
    # Mostrar mejoras
    mostrar_mejoras()
    
    # Mostrar especificaciones
    mostrar_especificaciones_tecnicas()
    
    # Mostrar comando ZPL generado
    print("\n" + "📝 COMANDO ZPL GENERADO:")
    print("="*40)
    print(comando_zpl)
    print(f"\n📏 Longitud del comando: {len(comando_zpl)} caracteres")
    print(f"📱 Longitud del QR JSON: {len(texto_qr)} caracteres")
    
    # Mostrar datos del QR
    print("\n" + "📱 CONTENIDO DEL QR:")
    print("="*40)
    print(texto_qr)
    
    # Probar impresión
    probar_impresion_local()
    
    print("\n" + "✅ TEST COMPLETADO")
    print("💡 La etiqueta ahora tiene:")
    print("   • Texto más grande y legible")
    print("   • QR más grande (2x4)")
    print("   • Mejor distribución del espacio")
    print("   • Tres columnas de información")
    print("   • Aprovechamiento total de 33.2mm x 14mm")

if __name__ == "__main__":
    main()
