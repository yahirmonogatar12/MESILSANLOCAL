#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TEST ETIQUETA FINAL OPTIMIZADA - Basada en imagen real
===================================================

Este archivo prueba la versión FINAL optimizada de la etiqueta,
con mejoras basadas en la imagen real proporcionada por el usuario.

Ejecutar: python test_etiqueta_final_optimizada.py
"""

import requests
import json
from datetime import datetime

def generar_zpl_final_optimizado(codigo_material):
    """Genera ZPL con la versión FINAL optimizada"""
    
    # Datos simulados del material
    lote = "L202501"
    parte = "P12345"
    cantidad = "100"
    propiedad = "RESIST"
    empresa = "ILSAN"
    fecha = datetime.now().strftime("%d/%m")
    
    # QR ultra-compacto (misma fórmula exitosa)
    qr_data = f"C:{codigo_material[:8]},L:{lote[:6]},P:{parte[:6]},Q:{cantidad[:3]},R:{propiedad[:5]}"
    
    # ZPL FINAL OPTIMIZADO - Basado en la imagen real
    zpl_command = f"""^XA
^XFR:si.ZPL^FS
^PW264^LL112
^FO5,5^BQN,2,4^FDQA,{qr_data}^FS
^FO65,5^ADN,14,10^FD{codigo_material[:12]}^FS
^FO65,25^ADN,12,8^FD{fecha}^FS
^FO65,45^ADN,10,6^FD{empresa}^FS
^FO5,65^ADN,8,5^FDL:{lote[:7]}^FS
^FO5,80^ADN,8,5^FDP:{parte[:7]}^FS
^FO5,95^ADN,8,5^FDQ:{cantidad[:5]}^FS
^FO140,65^ADN,8,5^FD{propiedad[:6]}^FS
^FO140,80^ADN,8,5^FDOK^FS
^FO140,95^ADN,8,5^FD{datetime.now().strftime('%H:%M')}^FS
^PQ1,0,1
^XZ"""
    
    return zpl_command, qr_data

def mostrar_mejoras_aplicadas():
    """Muestra las mejoras aplicadas basadas en la imagen real"""
    print("🏆 MEJORAS APLICADAS BASADAS EN LA IMAGEN REAL:")
    print("=" * 55)
    print("VERSIÓN ANTERIOR → VERSIÓN FINAL OPTIMIZADA:")
    print("  • Código: ADN,12,8 → ADN,14,10 (+25% más grande)")
    print("  • Fecha:  ADN,10,6 → ADN,12,8 (+33% más grande)")
    print("  • Empresa: ADN,8,5 → ADN,10,6 (+25% más grande)")
    print("  • Detalles: ADN,6,4 → ADN,8,5 (+33% más grande)")
    print("  • Posición código: X=70 → X=65 (mejor espacio)")
    print("  • QR: Mantenido BQN,2,4 (perfecto)")
    print("\n✅ RESULTADO: Texto AÚN MÁS GRANDE y mejor distribuido")

def test_etiqueta_final_optimizada():
    """Test de la etiqueta final optimizada"""
    print("🎯 === TEST ETIQUETA FINAL OPTIMIZADA ===")
    print("=" * 50)
    
    # Generar código de prueba
    codigo = f"FINAL-OPT-{datetime.now().strftime('%H%M%S')}"
    print(f"📋 Código de prueba: {codigo}")
    
    # Mostrar mejoras
    mostrar_mejoras_aplicadas()
    
    # Generar ZPL optimizado
    zpl_command, qr_data = generar_zpl_final_optimizado(codigo)
    
    print(f"\n📏 ANÁLISIS ZPL FINAL OPTIMIZADO:")
    print(f"  • Longitud total: {len(zpl_command)} caracteres")
    print(f"  • QR compacto: {len(qr_data)} caracteres")
    print(f"  • Fuentes: MÁS GRANDES que versión anterior")
    print(f"  • Layout: Optimizado basado en imagen real")
    
    print(f"\n📱 CONTENIDO QR:")
    print(f"  '{qr_data}'")
    
    print(f"\n🖨️ COMANDO ZPL FINAL OPTIMIZADO:")
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
            print("✅ ÉXITO: Etiqueta FINAL OPTIMIZADA enviada")
            print("🏆 Esta versión debería verse AÚN MEJOR que la anterior")
            resultado = response.json()
            if 'message' in resultado:
                print(f"   Mensaje: {resultado['message']}")
        else:
            print(f"❌ Error HTTP: {response.status_code}")
            print(f"   Respuesta: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("⚠️ Print service no disponible en localhost:5002")
        print("   Pero el ZPL FINAL OPTIMIZADO está listo para usar")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print(f"\n🎊 VERSIÓN FINAL OPTIMIZADA LISTA:")
    print("  ✅ Fuentes AÚN MÁS GRANDES")
    print("  ✅ Mejor distribución del espacio")
    print("  ✅ Basado en imagen real del usuario")
    print("  ✅ Mantiene QR compacto funcional")
    print("  ✅ Todos los comandos específicos incluidos")
    
    return zpl_command

def main():
    """Función principal"""
    print("🏆 VERSIÓN FINAL OPTIMIZADA DE LA ETIQUETA")
    print("=" * 50)
    print("Basada en la imagen real proporcionada por el usuario")
    print("Con fuentes AÚN MÁS GRANDES y mejor distribución")
    print()
    
    # Ejecutar test
    zpl_final = test_etiqueta_final_optimizada()
    
    print(f"\n💡 INSTRUCCIONES DE USO:")
    print("1. Ejecute en navegador: testEtiquetaFinalOptimizada()")
    print("2. O use este ZPL directamente")
    print("3. ¡El texto debería verse PERFECTO ahora!")
    
    return zpl_final

if __name__ == "__main__":
    main()
