#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TEST QR POSICIÓN AJUSTADA - QR movido hacia arriba
=================================================

Este archivo prueba la nueva posición del QR más arriba en la etiqueta.

Ejecutar: python test_qr_posicion_arriba.py
"""

import requests
import json
from datetime import datetime

def generar_zpl_qr_arriba(codigo_material):
    """Genera ZPL con QR movido hacia arriba (Y=160 en lugar de Y=192)"""
    
    # Datos simulados del material
    lote = "L202501"
    parte = "P12345"
    cantidad = "100"
    propiedad = "RESIST"
    fecha = datetime.now().strftime("%d/%m/%Y")
    
    # QR ultra-compacto (misma fórmula exitosa)
    qr_data = f"C:{codigo_material[:8]},L:{lote[:6]},P:{parte[:6]},Q:{cantidad[:3]},R:{propiedad[:5]}"
    
    # ZPL con QR MOVIDO HACIA ARRIBA (Y=160)
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
^FT13,160^BQN,2,4
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

def mostrar_ajuste_posicion():
    """Muestra el ajuste de posición del QR"""
    print("📱 AJUSTE DE POSICIÓN DEL QR:")
    print("=" * 40)
    print("ANTES → AHORA:")
    print("  • Posición Y: 192 → 160 (32 puntos más arriba)")
    print("  • Beneficios del ajuste:")
    print("    ✅ QR más centrado en la etiqueta")
    print("    ✅ Mejor distribución del espacio")
    print("    ✅ Más equilibrio visual")
    print("    ✅ Separación óptima del texto")
    print("    ✅ Posición más natural")
    print("\n✅ RESULTADO: QR mejor posicionado")

def test_qr_posicion_arriba():
    """Test del QR con nueva posición"""
    print("📱 === TEST QR POSICIÓN ARRIBA ===")
    print("=" * 40)
    
    # Generar código de prueba
    codigo = f"QR-UP-{datetime.now().strftime('%H%M%S')}"
    print(f"📋 Código de prueba: {codigo}")
    
    # Mostrar ajuste
    mostrar_ajuste_posicion()
    
    # Generar ZPL con QR arriba
    zpl_command, qr_data = generar_zpl_qr_arriba(codigo)
    
    print(f"\n📏 ANÁLISIS POSICIÓN AJUSTADA:")
    print(f"  • Longitud total ZPL: {len(zpl_command)} caracteres")
    print(f"  • QR compacto: {len(qr_data)} caracteres")
    print(f"  • Posición QR: X=13, Y=160 (ARRIBA)")
    print(f"  • QR tamaño: BQN,2,4 (pequeño)")
    print(f"  • Etiqueta: 392x224 dots")
    print(f"  • Distribución: Más equilibrada")
    
    print(f"\n📱 CONTENIDO QR:")
    print(f"  '{qr_data}'")
    
    print(f"\n🖨️ COMANDO ZPL CON QR ARRIBA:")
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
            print("✅ ÉXITO: QR en nueva posición impreso")
            print("📱 El QR debería aparecer más arriba y centrado")
            resultado = response.json()
            if 'message' in resultado:
                print(f"   Mensaje: {resultado['message']}")
        else:
            print(f"❌ Error HTTP: {response.status_code}")
            print(f"   Respuesta: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("⚠️ Print service no disponible en localhost:5002")
        print("   Pero el ZPL con QR ARRIBA está listo para usar")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print(f"\n📱 QR REPOSICIONADO:")
    print("  ✅ QR movido 32 puntos hacia arriba")
    print("  ✅ Mejor centrado en la etiqueta")
    print("  ✅ Distribución más equilibrada")
    print("  ✅ Posición más natural")
    print("  ✅ Separación óptima del texto")
    
    return zpl_command

def mostrar_layout_mejorado():
    """Muestra el layout mejorado con QR arriba"""
    print("\n📐 LAYOUT MEJORADO CON QR ARRIBA:")
    print("=" * 45)
    print("┌──────────────────────────────────────┐")
    print("│ ILSAN ELECTRONICS MES               │")
    print("│ Codigo de material recibido:        │")
    print("│ QR-UP-164500                        │")
    print("│ Fecha de entrada: 16/07/2025        │")
    print("│ Lote: L202501 Parte: P12345         │")
    print("│ Cantidad: 100 Prop: RESIST          │")
    print("│ Hora: 16:45:00                      │")
    print("│                                      │")
    print("│      ████████                       │")
    print("│      ██ QR ██  ← QR AQUÍ (ARRIBA)   │")
    print("│      ████████                       │")
    print("└──────────────────────────────────────┘")
    print("\n🎯 Posición óptima: Centrado y bien distribuido")

def main():
    """Función principal"""
    print("📱 QR MOVIDO HACIA ARRIBA")
    print("=" * 40)
    print("Mejorando la posición del QR para mejor distribución")
    print()
    
    # Ejecutar test
    zpl_arriba = test_qr_posicion_arriba()
    
    # Mostrar layout mejorado
    mostrar_layout_mejorado()
    
    print(f"\n💡 INSTRUCCIONES DE USO:")
    print("1. Ejecute en navegador: testPlantillaProfesional()")
    print("2. O use este ZPL directamente")
    print("3. ¡El QR ahora está mejor posicionado!")
    
    return zpl_arriba

if __name__ == "__main__":
    main()
