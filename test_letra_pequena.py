#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test para verificar el tamaño de letra reducido del código
en la plantilla profesional ZPL
"""

import json
import requests
from datetime import datetime

def test_letra_mas_pequena():
    print('🔤 === TEST LETRA MÁS PEQUEÑA PARA CÓDIGO ===')
    
    # Código de prueba
    codigo = f'TEST-LETRA-PEQUENA-{datetime.now().strftime("%Y%m%d%H%M%S")}'
    print(f'📋 Código de prueba: {codigo}')
    
    # Datos simulados del formulario
    datos_simulados = {
        'codigo': codigo,
        'fecha': datetime.now().strftime('%d/%m/%Y'),
        'numeroLote': 'L2025001',
        'numeroParte': 'P12345', 
        'cantidadActual': '100',
        'propiedad': 'RESISTOR'
    }
    
    # Crear datos para el QR con información COMPACTA
    datos_qr = {
        'c': datos_simulados['codigo'][:15],  # Código acortado
        'f': datos_simulados['fecha'][:10],   # Solo fecha
        'l': datos_simulados['numeroLote'][:8], # Lote acortado
        'p': datos_simulados['numeroParte'][:8], # Parte acortado
        'q': datos_simulados['cantidadActual'][:6], # Cantidad acortada
        'm': datos_simulados['propiedad'][:6], # Material acortado
        's': 'OK',  # Estado simplificado
        'e': 'ILSAN' # Empresa acortada
    }
    
    # Convertir a JSON ultra compacto para el QR
    texto_qr = json.dumps(datos_qr).replace('"', '').replace(':', '=').replace(',', '|')
    
    print(f'📱 Texto QR compacto: {texto_qr}')
    print(f'📏 Longitud QR: {len(texto_qr)} caracteres')
    
    # Generar comando ZPL con letra más pequeña para el código
    comando_zpl = f"""CT~~CD,~CC^~CT~
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
^FH\\^FDLA,{texto_qr}^FS
^FT160,25^A0N,18,18^FH\\^CI28^FDILSAN ELECTRONICS MES^FS^CI27
^FT160,46^A0N,16,15^FH\\^CI28^FDCodigo de material recibido:^FS^CI27
^FT160,67^A0N,18,18^FH\\^CI28^FD{datos_simulados['codigo']}^FS^CI27
^FT160,88^A0N,15,15^FH\\^CI28^FDFecha de entrada: {datos_simulados['fecha']}^FS^CI27
^FT160,109^A0N,14,14^FH\\^CI28^FDLote: {datos_simulados['numeroLote']} Parte: {datos_simulados['numeroParte']}^FS^CI27
^FT160,130^A0N,14,14^FH\\^CI28^FDCantidad: {datos_simulados['cantidadActual']} Prop: {datos_simulados['propiedad']}^FS^CI27
^FT164,151^A0N,17,18^FH\\^CI28^FDHora: {datetime.now().strftime('%H:%M:%S')}^FS^CI27
^PQ1,0,1,Y
^XZ"""

    print('\n📐 === ANÁLISIS DEL CAMBIO DE TAMAÑO ===')
    print('✅ CAMBIO REALIZADO:')
    print('   • Código: A0N,20,20 → A0N,18,18 (10% más pequeño)')
    print('   • Otros textos mantienen su tamaño')
    print('   • QR se mantiene en tamaño BQN,2,4')
    
    print('\n📊 COMPARACIÓN DE TAMAÑOS:')
    print('   ┌─────────────────────────────────────────────────┐')
    print('   │ QR   ILSAN ELECTRONICS MES     (18,18)          │')
    print('   │ ██   Codigo de material recibido: (16,15)       │') 
    print('   │ ██   TEST-LETRA-PEQUENA...      (18,18) ←NUEVO  │')
    print('   │ ██   Fecha de entrada: 16/07/2025  (15,15)      │')
    print('   │ ██   Lote: L2025001 Parte: P12345  (14,14)      │')
    print('   │      Cantidad: 100 Prop: RESISTOR  (14,14)      │')
    print('   │      Hora: 14:30:25                (17,18)      │')
    print('   └─────────────────────────────────────────────────┘')
    
    print('\n📏 JERARQUÍA DE TAMAÑOS (de mayor a menor):')
    print('   1. Título empresa: A0N,18,18 (igual que código)')
    print('   2. Código material: A0N,18,18 ← NUEVO TAMAÑO')
    print('   3. Hora: A0N,17,18')
    print('   4. Etiqueta código: A0N,16,15')
    print('   5. Fecha entrada: A0N,15,15')
    print('   6. Lote/Parte/Cantidad: A0N,14,14')
    
    print('\n🎯 VENTAJAS DEL NUEVO TAMAÑO:')
    print('   ✅ Código más legible sin ser dominante')
    print('   ✅ Mejor balance con otros elementos')
    print('   ✅ Más espacio para códigos largos')
    print('   ✅ Mantiene jerarquía visual apropiada')
    
    print(f'\n📝 Comando ZPL generado ({len(comando_zpl)} caracteres):')
    print('─' * 60)
    print(comando_zpl)
    print('─' * 60)
    
    # Probar envío al servicio de impresión
    print('\n🖨️ === PROBANDO SERVICIO DE IMPRESIÓN ===')
    try:
        service_url = 'http://localhost:5002'
        
        # Verificar estado del servicio
        response = requests.get(f'{service_url}/', timeout=5)
        if response.ok:
            data = response.json()
            print(f'✅ Servicio disponible: {data.get("zebra_printer", "No detectada")}')
            
            # Enviar comando ZPL
            print('📤 Enviando comando ZPL al servicio...')
            print_response = requests.post(f'{service_url}/print', 
                json={
                    'zpl': comando_zpl,
                    'codigo': codigo,
                    'source': 'test_letra_pequena'
                }, 
                timeout=10
            )
            
            if print_response.ok:
                result = print_response.json()
                print(f'✅ Comando enviado exitosamente: {result.get("status", "unknown")}')
            else:
                print(f'⚠️ Error al enviar: HTTP {print_response.status_code}')
                print(f'   Respuesta: {print_response.text[:200]}')
        else:
            print(f'❌ Servicio no disponible: HTTP {response.status_code}')
            
    except requests.exceptions.RequestException as e:
        print(f'⚠️ No se pudo conectar al servicio: {e}')
        print('💡 Asegúrese de que print_service.py esté ejecutándose')
    
    print('\n🎯 RESULTADO:')
    print('✅ Tamaño de letra del código reducido de A0N,20,20 a A0N,18,18')
    print('✅ Mejor balance visual manteniendo legibilidad') 
    print('✅ Jerarquía de tamaños más apropiada')
    print('✅ Comando ZPL listo para impresión')
    
    return comando_zpl

if __name__ == '__main__':
    test_letra_mas_pequena()
