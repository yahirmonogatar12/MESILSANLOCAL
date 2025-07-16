#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test para verificar los nuevos cambios en el layout:
- Eliminado "Prop:" 
- Agregada línea "QTY:" con cantidad actual
- Especificación del material en línea separada
"""

import json
import requests
from datetime import datetime

def test_especificacion_material():
    print('📋 === TEST ESPECIFICACIÓN DE MATERIAL ===')
    
    # Código de prueba
    codigo = f'TEST-SPEC-MAT-{datetime.now().strftime("%Y%m%d%H%M%S")}'
    print(f'📋 Código de prueba: {codigo}')
    
    # Datos simulados del formulario
    datos_simulados = {
        'codigo': codigo,
        'fecha': datetime.now().strftime('%d/%m/%Y'),
        'numeroLote': 'L2025001',
        'numeroParte': 'P12345', 
        'cantidadActual': '100',
        'propiedad': 'RESISTOR SMD 1K OHM 0603'  # Especificación más detallada
    }
    
    # Crear datos para el QR con información COMPACTA
    datos_qr = {
        'c': datos_simulados['codigo'][:15],  # Código acortado
        'f': datos_simulados['fecha'][:10],   # Solo fecha
        'l': datos_simulados['numeroLote'][:8], # Lote acortado
        'p': datos_simulados['numeroParte'][:8], # Parte acortado
        'q': datos_simulados['cantidadActual'][:6], # Cantidad acortada
        'm': datos_simulados['propiedad'][:12], # Especificación acortada
        's': 'OK',  # Estado simplificado
        'e': 'ILSAN' # Empresa acortada
    }
    
    # Convertir a JSON ultra compacto para el QR
    texto_qr = json.dumps(datos_qr).replace('"', '').replace(':', '=').replace(',', '|')
    
    print(f'📱 Texto QR compacto: {texto_qr}')
    print(f'📏 Longitud QR: {len(texto_qr)} caracteres')
    
    # Generar comando ZPL con especificación de material
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
^FT160,20^A0N,18,18^FH\\^CI28^FDILSAN ELECTRONICS MES^FS^CI27
^FT160,41^A0N,16,15^FH\\^CI28^FDCodigo de material recibido:^FS^CI27
^FT160,62^A0N,16,16^FH\\^CI28^FD{datos_simulados['codigo']}^FS^CI27
^FT160,83^A0N,15,15^FH\\^CI28^FDFecha de entrada: {datos_simulados['fecha']}^FS^CI27
^FT160,104^A0N,14,14^FH\\^CI28^FD{datos_simulados['numeroLote']} {datos_simulados['numeroParte']}^FS^CI27
^FT160,125^A0N,14,14^FH\\^CI28^FDQTY: {datos_simulados['cantidadActual']}^FS^CI27
^FT160,140^A0N,14,14^FH\\^CI28^FD{datos_simulados['propiedad']}^FS^CI27
^FT164,158^A0N,17,18^FH\\^CI28^FDHora: {datetime.now().strftime('%H:%M:%S')}^FS^CI27
^PQ1,0,1,Y
^XZ"""

    print('\n📐 === ANÁLISIS DE LOS NUEVOS CAMBIOS ===')
    print('✅ CAMBIOS REALIZADOS:')
    print('   • Eliminado "Prop:" de la especificación')
    print('   • Agregada línea "QTY:" con cantidad actual (Y=125)')
    print('   • Especificación de material en línea independiente (Y=140)')
    print('   • Hora ajustada a Y=158 para dar espacio')
    print('   • Información más clara y organizada')
    
    print('\n📊 NUEVO LAYOUT MEJORADO:')
    print('   ┌─────────────────────────────────────────────────┐')
    print('   │ QR   ILSAN ELECTRONICS MES                      │')
    print('   │ ██   Codigo de material recibido:               │') 
    print('   │ ██   TEST-SPEC-MAT-20250716...                  │')
    print('   │ ██   Fecha de entrada: 16/07/2025               │')
    print('   │ ██   L2025001 P12345                            │')
    print('   │      QTY: 100                     ← NUEVO       │')
    print('   │      RESISTOR SMD 1K OHM 0603     ← MEJORADO    │')
    print('   │      Hora: 14:30:25                             │')
    print('   └─────────────────────────────────────────────────┘')
    
    print('\n📏 VENTAJAS DEL NUEVO DISEÑO:')
    print('   ✅ Cantidad claramente etiquetada como "QTY:"')
    print('   ✅ Especificación completa del material visible')
    print('   ✅ Información técnica más detallada')
    print('   ✅ Layout más profesional e informativo')
    print('   ✅ Separación clara entre cantidad y especificación')
    print('   ✅ Más espacio para descripciones técnicas')
    
    print('\n🔄 COMPARACIÓN ANTES/DESPUÉS:')
    print('   ANTES: "100 Prop: RESISTOR"')
    print('   DESPUÉS: "QTY: 100"')
    print('           "RESISTOR SMD 1K OHM 0603"')
    print('   ')
    print('   VENTAJA: Especificación técnica completa visible')
    
    print('\n📋 ESTRUCTURA FINAL:')
    print('   1. Título empresa (Y=20)')
    print('   2. Etiqueta código (Y=41)')
    print('   3. Código material (Y=62)')
    print('   4. Fecha entrada (Y=83)')
    print('   5. Lote y Parte (Y=104)')
    print('   6. QTY: Cantidad (Y=125) ← NUEVO')
    print('   7. Especificación (Y=140) ← MEJORADO')
    print('   8. Hora (Y=158)')
    
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
                    'source': 'test_especificacion_material'
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
    print('✅ Eliminado "Prop:" para texto más limpio')
    print('✅ Agregada línea "QTY:" con cantidad destacada') 
    print('✅ Especificación del material en línea independiente')
    print('✅ Layout más profesional y técnicamente informativo')
    print('✅ Comando ZPL listo para impresión')
    
    return comando_zpl

if __name__ == '__main__':
    test_especificacion_material()
