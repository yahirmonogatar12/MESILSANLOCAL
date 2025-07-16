#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TEST: Verificar que los campos cantidad_actual y propiedad_material se muestran correctamente en la etiqueta
Verifica la generación del comando ZPL con datos reales
"""

import json
from datetime import datetime

def generar_comando_zpl_test(codigo, cantidad_actual="", propiedad_material="", numero_lote="", numero_parte=""):
    """
    Función de test para generar comando ZPL igual que JavaScript
    """
    
    fecha_hora = datetime.now().strftime('%d/%m/%Y, %H:%M:%S')
    fecha = datetime.now().strftime('%d/%m/%Y')
    
    print(f"🏷️ Generando comando ZPL para: {codigo}")
    print(f"📊 Cantidad actual: '{cantidad_actual}'")
    print(f"📊 Propiedad material: '{propiedad_material}'")
    print(f"📊 Número lote: '{numero_lote}'")
    print(f"📊 Número parte: '{numero_parte}'")
    
    # Crear datos para el QR compactos
    datos_qr = {
        'c': codigo[:15],  # Código acortado
        'f': fecha[:10],   # Solo fecha, sin hora
        'l': numero_lote[:8], # Lote acortado
        'p': numero_parte[:8], # Parte acortado
        'q': cantidad_actual[:6], # Cantidad acortada
        'm': propiedad_material[:6], # Material acortado
        's': 'OK',  # Estado simplificado
        'e': 'ILSAN' # Empresa acortada
    }
    
    # Convertir a JSON ultra compacto para el QR
    texto_qr = json.dumps(datos_qr).replace('"', '').replace(':', '=').replace(',', '|')
    
    print(f"📋 Datos para QR (COMPACTOS): {datos_qr}")
    print(f"📱 Texto QR generado (COMPACTO): {texto_qr}")
    print(f"📏 Longitud del QR: {len(texto_qr)} caracteres")
    
    # Generar comando ZPL (etiqueta profesional)
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
^FT160,62^A0N,16,16^FH\\^CI28^FD{codigo}^FS^CI27
^FT160,83^A0N,15,15^FH\\^CI28^FDFecha de entrada: {fecha}^FS^CI27
^FT160,104^A0N,14,14^FH\\^CI28^FD{numero_lote} {numero_parte}^FS^CI27
^FT160,125^A0N,14,14^FH\\^CI28^FDQTY: {cantidad_actual}^FS^CI27
^FT160,140^A0N,14,14^FH\\^CI28^FD{propiedad_material}^FS^CI27
^FT164,158^A0N,17,18^FH\\^CI28^FDHora: {datetime.now().strftime('%H:%M:%S')}^FS^CI27
^PQ1,0,1,Y
^XZ"""
    
    print("📝 Comando ZPL generado:")
    print("=" * 50)
    print(comando_zpl)
    print("=" * 50)
    
    # Verificar líneas específicas
    lineas = comando_zpl.split('\n')
    for i, linea in enumerate(lineas):
        if 'FDQTY:' in linea:
            print(f"✅ Línea {i+1} - QTY encontrada: {linea.strip()}")
        if '^FD' in linea and (cantidad_actual in linea or propiedad_material in linea):
            if 'QTY' not in linea and 'Fecha' not in linea and 'Codigo' not in linea and 'Hora' not in linea:
                print(f"✅ Línea {i+1} - Datos encontrados: {linea.strip()}")
    
    # Verificar que los datos aparezcan en el ZPL
    if cantidad_actual and cantidad_actual in comando_zpl:
        print(f"✅ CANTIDAD ACTUAL '{cantidad_actual}' ENCONTRADA en ZPL")
    else:
        print(f"❌ CANTIDAD ACTUAL '{cantidad_actual}' NO ENCONTRADA en ZPL")
    
    if propiedad_material and propiedad_material in comando_zpl:
        print(f"✅ PROPIEDAD MATERIAL '{propiedad_material}' ENCONTRADA en ZPL")
    else:
        print(f"❌ PROPIEDAD MATERIAL '{propiedad_material}' NO ENCONTRADA en ZPL")
    
    print(f"📊 Longitud total del comando ZPL: {len(comando_zpl)} caracteres")
    
    return comando_zpl

def test_casos_diferentes():
    """
    Probar diferentes casos de datos
    """
    print("🧪 === PROBANDO DIFERENTES CASOS ===\n")
    
    # Caso 1: Datos completos
    print("📋 CASO 1: Datos completos")
    generar_comando_zpl_test(
        codigo="TEST123,20250716001",
        cantidad_actual="1000",
        propiedad_material="68F 1608",
        numero_lote="LOT123",
        numero_parte="PART456"
    )
    print("\n" + "="*60 + "\n")
    
    # Caso 2: Datos vacíos (problema actual)
    print("📋 CASO 2: Datos vacíos (problema actual)")
    generar_comando_zpl_test(
        codigo="TEST123,20250716002",
        cantidad_actual="",
        propiedad_material="",
        numero_lote="",
        numero_parte=""
    )
    print("\n" + "="*60 + "\n")
    
    # Caso 3: Solo algunos datos
    print("📋 CASO 3: Solo algunos datos")
    generar_comando_zpl_test(
        codigo="TEST123,20250716003",
        cantidad_actual="500",
        propiedad_material="",
        numero_lote="",
        numero_parte=""
    )
    print("\n" + "="*60 + "\n")
    
    # Caso 4: Datos largos (prueba de truncamiento)
    print("📋 CASO 4: Datos largos")
    generar_comando_zpl_test(
        codigo="TEST123,20250716004",
        cantidad_actual="123456789",
        propiedad_material="ESPECIFICACION_MUY_LARGA_DE_MATERIAL",
        numero_lote="LOTE_LARGO",
        numero_parte="PARTE_LARGA"
    )

def main():
    """
    Función principal de test
    """
    print("🔍 === TEST DE VERIFICACIÓN DE CAMPOS EN ETIQUETA ===")
    print("📅 Fecha:", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print("🎯 Objetivo: Verificar que cantidad_actual y propiedad_material aparezcan en ZPL")
    print()
    
    test_casos_diferentes()
    
    print("\n🔧 === INSTRUCCIONES DE DEBUG ===")
    print("1. Si los campos aparecen en el ZPL pero no en la etiqueta impresa:")
    print("   -> El problema está en la impresora o en el envío del comando")
    print("2. Si los campos NO aparecen en el ZPL:")
    print("   -> El problema está en que los campos del formulario están vacíos")
    print("3. Para verificar en el navegador:")
    print("   -> Abrir consola del navegador (F12)")
    print("   -> Ejecutar: document.getElementById('cantidad_actual').value")
    print("   -> Ejecutar: document.getElementById('propiedad_material').value")
    print("4. Para probar la función JavaScript:")
    print("   -> Ejecutar: testGenerarZPL('TEST123,20250716005', 'material')")

if __name__ == "__main__":
    main()
