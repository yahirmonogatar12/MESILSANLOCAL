#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TEST PLANTILLA PROFESIONAL ZPL - Versión del usuario
==================================================

Este archivo prueba la plantilla ZPL profesional proporcionada por el usuario.
La plantilla es más grande y profesional que las versiones anteriores.

Ejecutar: python test_plantilla_profesional.py
"""

import requests
import json
from datetime import datetime

def generar_zpl_plantilla_profesional(codigo_material):
    """Genera ZPL usando la plantilla profesional del usuario"""
    
    # Datos simulados del material
    lote = "L202501"
    parte = "P12345"
    cantidad = "100"
    propiedad = "RESIST"
    fecha = datetime.now().strftime("%d/%m/%Y")
    
    # QR ultra-compacto (misma fórmula exitosa)
    qr_data = f"C:{codigo_material[:8]},L:{lote[:6]},P:{parte[:6]},Q:{cantidad[:3]},R:{propiedad[:5]}"
    
    # ZPL usando PLANTILLA PROFESIONAL del usuario
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
^FT13,192^BQN,2,8
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

def mostrar_ventajas_plantilla_profesional():
    """Muestra las ventajas de la plantilla profesional"""
    print("🏆 VENTAJAS DE LA PLANTILLA PROFESIONAL:")
    print("=" * 55)
    print("PLANTILLA ANTERIOR vs PLANTILLA PROFESIONAL:")
    print("  • Tamaño: 264x112 → 392x224 (+85% más grande)")
    print("  • QR: BQN,2,4 → BQN,2,8 (+100% más grande)")
    print("  • Fuentes código: ADN,14,10 → A0N,20,20 (+43% más grande)")
    print("  • Configuración: Básica → Profesional avanzada")
    print("  • Codificación: Simple → Unicode CI28")
    print("  • Layout: Compacto → Descriptivo con etiquetas")
    print("  • Calidad: Estándar → Profesional")
    print("\n✅ RESULTADO: Etiqueta PROFESIONAL de alta calidad")

def test_plantilla_profesional():
    """Test de la plantilla profesional"""
    print("🎯 === TEST PLANTILLA PROFESIONAL ===")
    print("=" * 45)
    
    # Generar código de prueba
    codigo = f"PROF-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    print(f"📋 Código de prueba: {codigo}")
    
    # Mostrar ventajas
    mostrar_ventajas_plantilla_profesional()
    
    # Generar ZPL con plantilla profesional
    zpl_command, qr_data = generar_zpl_plantilla_profesional(codigo)
    
    print(f"\n📏 ANÁLISIS PLANTILLA PROFESIONAL:")
    print(f"  • Longitud total: {len(zpl_command)} caracteres")
    print(f"  • QR compacto: {len(qr_data)} caracteres")
    print(f"  • Tamaño etiqueta: 392x224 dots (GRANDE)")
    print(f"  • QR tamaño: BQN,2,8 (MUCHO MÁS GRANDE)")
    print(f"  • Fuentes: A0N,20,20 (PROFESIONALES)")
    print(f"  • Codificación: Unicode CI28")
    
    print(f"\n📱 CONTENIDO QR:")
    print(f"  '{qr_data}'")
    
    print(f"\n🖨️ COMANDO ZPL PLANTILLA PROFESIONAL:")
    print("-" * 50)
    print(zpl_command)
    print("-" * 50)
    
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
            print("✅ ÉXITO: Plantilla PROFESIONAL enviada")
            print("🏆 Esta debería ser la MEJOR calidad hasta ahora")
            resultado = response.json()
            if 'message' in resultado:
                print(f"   Mensaje: {resultado['message']}")
        else:
            print(f"❌ Error HTTP: {response.status_code}")
            print(f"   Respuesta: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("⚠️ Print service no disponible en localhost:5002")
        print("   Pero la PLANTILLA PROFESIONAL está lista para usar")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print(f"\n🎊 PLANTILLA PROFESIONAL IMPLEMENTADA:")
    print("  ✅ Etiqueta MÁS GRANDE (392x224)")
    print("  ✅ QR MUCHO MÁS GRANDE (BQN,2,8)")
    print("  ✅ Fuentes profesionales grandes")
    print("  ✅ Layout con etiquetas descriptivas")
    print("  ✅ Codificación Unicode")
    print("  ✅ Configuración avanzada de impresora")
    print("  ✅ Calidad profesional")
    
    return zpl_command

def comparar_versiones():
    """Compara todas las versiones desarrolladas"""
    print("\n📊 EVOLUCIÓN DE LAS ETIQUETAS:")
    print("=" * 45)
    print("1️⃣ Versión inicial: Texto muy pequeño")
    print("2️⃣ Fuentes grandes: Solucionó el problema")
    print("3️⃣ Medidas específicas: 33.2mm x 14mm")
    print("4️⃣ Sin STRING TOO LONG: QR optimizado")
    print("5️⃣ Comandos específicos: ^XFR:si.ZPL^FS")
    print("6️⃣ PLANTILLA PROFESIONAL: ¡CALIDAD MÁXIMA!")
    print("\n🏆 La plantilla profesional es la MEJOR versión")

def main():
    """Función principal"""
    print("🏆 PLANTILLA PROFESIONAL ZPL")
    print("=" * 40)
    print("Usando la plantilla profesional del usuario")
    print("Calidad profesional y tamaño grande")
    print()
    
    # Ejecutar test
    zpl_profesional = test_plantilla_profesional()
    
    # Mostrar comparación
    comparar_versiones()
    
    print(f"\n💡 INSTRUCCIONES DE USO:")
    print("1. Ejecute en navegador: testPlantillaProfesional()")
    print("2. O use este ZPL directamente")
    print("3. ¡La calidad profesional es incomparable!")
    
    return zpl_profesional

if __name__ == "__main__":
    main()
