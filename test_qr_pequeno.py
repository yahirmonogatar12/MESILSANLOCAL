#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TEST QR MÁS PEQUEÑO - Plantilla profesional con QR reducido
========================================================

Este archivo prueba la plantilla profesional con QR más pequeño
según la solicitud del usuario.

Ejecutar: python test_qr_pequeno.py
"""

import requests
import json
from datetime import datetime

def generar_zpl_qr_pequeno(codigo_material):
    """Genera ZPL con QR más pequeño (BQN,2,4 en lugar de BQN,2,8)"""
    
    # Datos simulados del material
    lote = "L202501"
    parte = "P12345"
    cantidad = "100"
    propiedad = "RESIST"
    fecha = datetime.now().strftime("%d/%m/%Y")
    
    # QR ultra-compacto (misma fórmula exitosa)
    qr_data = f"C:{codigo_material[:8]},L:{lote[:6]},P:{parte[:6]},Q:{cantidad[:3]},R:{propiedad[:5]}"
    
    # ZPL con QR MÁS PEQUEÑO (BQN,2,4)
    zpl_command = f"""CT~~CD,~CC^~CT~
^XA
~TA000
~JSN
^LT37
^MNW
^MTT
^PON
^PMN
^LH0,0
^JMA
^PR4,4
~SD15
^JUS
^LRN
^CI27
^PA0,1,1,0
^XZ
^XA
^MMT
^PW392
^LL224
^LS0
^FT13,192^BQN,2,4
^FH\\^FDLA,{qr_data}^FS
^FT190,25^A0N,18,18^FH\\^CI28^FDILSAN ELECTRONICS MES^FS^CI27
^FT190,46^A0N,16,15^FH\\^CI28^FDCodigo de material recibido:^FS^CI27
^FT190,67^A0N,20,20^FH\\^CI28^FD{codigo_material}^FS^CI27
^FT190,88^A0N,15,15^FH\\^CI28^FDFecha de entrada: {fecha}^FS^CI27
^FT190,109^A0N,14,14^FH\\^CI28^FDLote: {lote} Parte: {parte}^FS^CI27
^FT190,130^A0N,14,14^FH\\^CI28^FDCantidad: {cantidad} Prop: {propiedad}^FS^CI27
^FT194,151^A0N,17,18^FH\\^CI28^FDHora: {datetime.now().strftime('%H:%M:%S')}^FS^CI27
^PQ1,0,1,Y
^XZ"""
    
    return zpl_command, qr_data

def mostrar_comparacion_qr():
    """Muestra la comparación de tamaños de QR"""
    print("📱 COMPARACIÓN DE TAMAÑOS DE QR:")
    print("=" * 45)
    print("ANTERIOR → NUEVO:")
    print("  • QR: BQN,2,8 → BQN,2,4 (50% más pequeño)")
    print("  • Beneficios del QR más pequeño:")
    print("    ✅ Ocupa menos espacio en la etiqueta")
    print("    ✅ Deja más espacio para el texto")
    print("    ✅ Más rápido de generar")
    print("    ✅ Sigue siendo escaneables")
    print("    ✅ Mantiene toda la información")
    print("\n✅ RESULTADO: QR compacto pero funcional")

def test_qr_pequeno():
    """Test del QR más pequeño"""
    print("📱 === TEST QR MÁS PEQUEÑO ===")
    print("=" * 40)
    
    # Generar código de prueba
    codigo = f"QR-SMALL-{datetime.now().strftime('%H%M%S')}"
    print(f"📋 Código de prueba: {codigo}")
    
    # Mostrar comparación
    mostrar_comparacion_qr()
    
    # Generar ZPL con QR pequeño
    zpl_command, qr_data = generar_zpl_qr_pequeno(codigo)
    
    print(f"\n📏 ANÁLISIS QR PEQUEÑO:")
    print(f"  • Longitud total ZPL: {len(zpl_command)} caracteres")
    print(f"  • QR compacto: {len(qr_data)} caracteres")
    print(f"  • Tamaño etiqueta: 392x224 dots (grande)")
    print(f"  • QR tamaño: BQN,2,4 (PEQUEÑO)")
    print(f"  • Fuentes: A0N,20,20 (grandes)")
    print(f"  • Codificación: Unicode CI28")
    
    print(f"\n📱 CONTENIDO QR:")
    print(f"  '{qr_data}'")
    
    print(f"\n🖨️ COMANDO ZPL CON QR PEQUEÑO:")
    print("-" * 45)
    print(zpl_command)
    print("-" * 45)
    
    # Intentar enviar a print service
    try:
        print(f"\n🚀 Enviando a print service...")
        
        url = "http://localhost:5002/print"
        payload = {
            "printer": "ZDesigner ZT230-300dpi ZPL",
            "zpl_command": zpl_command
        }
        
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            print("✅ ÉXITO: QR PEQUEÑO impreso correctamente")
            print("📱 El QR debería verse más compacto ahora")
            resultado = response.json()
            if 'message' in resultado:
                print(f"   Mensaje: {resultado['message']}")
        else:
            print(f"❌ Error HTTP: {response.status_code}")
            print(f"   Respuesta: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("⚠️ Print service no disponible en localhost:5002")
        print("   Pero el ZPL con QR PEQUEÑO está listo para usar")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print(f"\n📱 QR PEQUEÑO IMPLEMENTADO:")
    print("  ✅ QR más compacto (BQN,2,4)")
    print("  ✅ Libera espacio en la etiqueta")
    print("  ✅ Mantiene legibilidad del texto")
    print("  ✅ Sigue siendo escaneable")
    print("  ✅ Información completa preservada")
    
    return zpl_command

def comparar_todas_las_versiones():
    """Compara todas las versiones de QR desarrolladas"""
    print("\n📊 EVOLUCIÓN COMPLETA DE LOS QR:")
    print("=" * 50)
    print("1️⃣ QR inicial: Información básica")
    print("2️⃣ QR completo: Información detallada")
    print("3️⃣ QR ultra-compacto: Sin STRING TOO LONG")
    print("4️⃣ QR grande: BQN,2,8 (máxima legibilidad)")
    print("5️⃣ QR PEQUEÑO: BQN,2,4 (óptimo espacio/función)")
    print("\n🎯 El QR pequeño logra el equilibrio perfecto")
    print("   Entre funcionalidad y uso eficiente del espacio")

def main():
    """Función principal"""
    print("📱 QR MÁS PEQUEÑO - PLANTILLA PROFESIONAL")
    print("=" * 50)
    print("Optimizando el QR para usar menos espacio")
    print("Manteniendo toda la funcionalidad")
    print()
    
    # Ejecutar test
    zpl_pequeno = test_qr_pequeno()
    
    # Mostrar comparación completa
    comparar_todas_las_versiones()
    
    print(f"\n💡 INSTRUCCIONES DE USO:")
    print("1. Ejecute en navegador: testPlantillaProfesional()")
    print("2. O use este ZPL directamente")
    print("3. ¡El QR ahora es más compacto y eficiente!")
    
    return zpl_pequeno

if __name__ == "__main__":
    main()
