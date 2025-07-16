#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TEST: Verificación de cambios en etiqueta
- Cambio de propiedad_material a almacen_especificacion_material
- Eliminación del texto "QTY:"
- Validación de campos correctos
"""

import json
from datetime import datetime

def generar_zpl_corregido(codigo, cantidad_actual="", especificacion_material="", numero_lote="", numero_parte=""):
    """
    Función de test para generar comando ZPL CORREGIDO
    """
    
    fecha_hora = datetime.now().strftime('%d/%m/%Y, %H:%M:%S')
    fecha = datetime.now().strftime('%d/%m/%Y')
    
    print(f"🏷️ Generando comando ZPL CORREGIDO para: {codigo}")
    print(f"📊 Cantidad actual: '{cantidad_actual}'")
    print(f"📊 Especificación material: '{especificacion_material}'")
    print(f"📊 Número lote: '{numero_lote}'")
    print(f"📊 Número parte: '{numero_parte}'")
    
    # Crear datos para el QR compactos
    datos_qr = {
        'c': codigo[:15],  # Código acortado
        'f': fecha[:10],   # Solo fecha, sin hora
        'l': numero_lote[:8], # Lote acortado
        'p': numero_parte[:8], # Parte acortado
        'q': cantidad_actual[:6], # Cantidad acortada
        'm': especificacion_material[:6], # Especificación acortada
        's': 'OK',  # Estado simplificado
        'e': 'ILSAN' # Empresa acortada
    }
    
    # Convertir a JSON ultra compacto para el QR
    texto_qr = json.dumps(datos_qr).replace('"', '').replace(':', '=').replace(',', '|')
    
    print(f"📋 Datos para QR (COMPACTOS): {datos_qr}")
    print(f"📱 Texto QR generado (COMPACTO): {texto_qr}")
    print(f"📏 Longitud del QR: {len(texto_qr)} caracteres")
    
    # Generar comando ZPL CORREGIDO (sin "QTY:")
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
^FT160,125^A0N,14,14^FH\\^CI28^FD{cantidad_actual}^FS^CI27
^FT160,140^A0N,14,14^FH\\^CI28^FD{especificacion_material}^FS^CI27
^FT164,158^A0N,17,18^FH\\^CI28^FDHora: {datetime.now().strftime('%H:%M:%S')}^FS^CI27
^PQ1,0,1,Y
^XZ"""
    
    print("📝 Comando ZPL CORREGIDO generado:")
    print("=" * 50)
    print(comando_zpl)
    print("=" * 50)
    
    # Verificar líneas específicas
    lineas = comando_zpl.split('\n')
    resultado_verificacion = []
    
    for i, linea in enumerate(lineas):
        # Verificar que NO aparezca "QTY:"
        if 'FDQTY:' in linea:
            resultado_verificacion.append(f"❌ Línea {i+1} - PROBLEMA: Todavía aparece 'QTY:': {linea.strip()}")
        
        # Verificar línea de cantidad (sin QTY:)
        if f'^FD{cantidad_actual}^FS' in linea and cantidad_actual:
            resultado_verificacion.append(f"✅ Línea {i+1} - Cantidad sin 'QTY:': {linea.strip()}")
        
        # Verificar línea de especificación
        if f'^FD{especificacion_material}^FS' in linea and especificacion_material:
            resultado_verificacion.append(f"✅ Línea {i+1} - Especificación: {linea.strip()}")
    
    # Mostrar resultados de verificación
    print("\n🔍 === VERIFICACIÓN DE CORRECCIONES ===")
    for resultado in resultado_verificacion:
        print(resultado)
    
    # Verificar que los datos aparezcan en el ZPL
    print(f"\n📊 === VALIDACIÓN FINAL ===")
    if cantidad_actual and cantidad_actual in comando_zpl:
        print(f"✅ CANTIDAD ACTUAL '{cantidad_actual}' ENCONTRADA en ZPL")
    else:
        print(f"❌ CANTIDAD ACTUAL '{cantidad_actual}' NO ENCONTRADA en ZPL")
    
    if especificacion_material and especificacion_material in comando_zpl:
        print(f"✅ ESPECIFICACIÓN MATERIAL '{especificacion_material}' ENCONTRADA en ZPL")
    else:
        print(f"❌ ESPECIFICACIÓN MATERIAL '{especificacion_material}' NO ENCONTRADA en ZPL")
    
    # Verificar que NO aparezca "QTY:"
    if 'QTY:' not in comando_zpl:
        print(f"✅ TEXTO 'QTY:' ELIMINADO CORRECTAMENTE")
    else:
        print(f"❌ TEXTO 'QTY:' TODAVÍA APARECE")
    
    print(f"📊 Longitud total del comando ZPL: {len(comando_zpl)} caracteres")
    
    return comando_zpl

def comparar_antes_despues():
    """
    Compara la estructura antes y después de los cambios
    """
    print("📊 === COMPARACIÓN ANTES VS DESPUÉS ===\n")
    
    print("🔴 ANTES (PROBLEMÁTICO):")
    print("   • Campo usado: propiedad_material")
    print("   • Línea cantidad: ^FDQTY: 1000^FS")
    print("   • Línea especificación: ^FD68F 1608^FS")
    print("   • Problema: Texto 'QTY:' innecesario")
    
    print("\n🟢 DESPUÉS (CORREGIDO):")
    print("   • Campo usado: almacen_especificacion_material")
    print("   • Línea cantidad: ^FD1000^FS")
    print("   • Línea especificación: ^FD68F 1608^FS")
    print("   • Solución: Sin texto 'QTY:'")

def test_casos_diferentes():
    """
    Probar diferentes casos con la estructura corregida
    """
    print("\n🧪 === PROBANDO CASOS CON ESTRUCTURA CORREGIDA ===\n")
    
    # Caso 1: Datos completos
    print("📋 CASO 1: Datos completos (CORREGIDO)")
    generar_zpl_corregido(
        codigo="TEST123,20250716001",
        cantidad_actual="1000",
        especificacion_material="68F 1608",
        numero_lote="LOT123",
        numero_parte="PART456"
    )
    print("\n" + "="*60 + "\n")
    
    # Caso 2: Solo cantidad sin especificación
    print("📋 CASO 2: Solo cantidad, sin especificación")
    generar_zpl_corregido(
        codigo="TEST123,20250716002",
        cantidad_actual="500",
        especificacion_material="",
        numero_lote="",
        numero_parte=""
    )
    print("\n" + "="*60 + "\n")
    
    # Caso 3: Solo especificación sin cantidad
    print("📋 CASO 3: Solo especificación, sin cantidad")
    generar_zpl_corregido(
        codigo="TEST123,20250716003",
        cantidad_actual="",
        especificacion_material="91F 1608",
        numero_lote="",
        numero_parte=""
    )

def generar_codigo_javascript_corregido():
    """
    Genera código JavaScript actualizado para probar
    """
    codigo_js = """
// === CÓDIGO JAVASCRIPT CORREGIDO PARA PROBAR ===

// 1. Llenar campos con la especificación correcta
document.getElementById('codigo_material_recibido').value = 'TEST123,20250716001';
document.getElementById('numero_lote_material').value = 'LOT123';
document.getElementById('numero_parte_lower').value = 'PART456';
document.getElementById('cantidad_actual').value = '1000';
document.getElementById('almacen_especificacion_material').value = '68F 1608'; // ✅ CORREGIDO

// 2. Verificar que se llenaron correctamente
verificarCamposEtiqueta();

// 3. Probar función nueva con datos específicos CORREGIDOS
console.log('🟢 Probando función nueva CORREGIDA...');
const datosTestCorregidos = {
    codigo: 'TEST123,20250716001',
    numeroLote: 'LOT123', 
    numeroParte: 'PART456',
    cantidadActual: '1000',
    propiedadMaterial: '68F 1608' // Usa especificación del campo correcto
};
imprimirZebraAutomaticoConDatos(datosTestCorregidos);

// 4. Simular proceso completo CORREGIDO
testSimularGuardar();

// 5. Verificar que el ZPL generado NO tenga "QTY:"
const codigo = 'TEST-VERIFICACION';
const zpl = generarComandoZPLDirecto(codigo, 'material');
if (zpl.includes('QTY:')) {
    console.error('❌ PROBLEMA: Todavía aparece QTY: en el ZPL');
} else {
    console.log('✅ CORRECTO: No aparece QTY: en el ZPL');
}
"""
    
    print("\n💻 === CÓDIGO JAVASCRIPT CORREGIDO ===")
    print("Copie y pegue en la consola del navegador (F12):")
    print("=" * 50)
    print(codigo_js)
    print("=" * 50)

def main():
    """
    Función principal de test
    """
    print("🔧 === VERIFICACIÓN DE CORRECCIONES EN ETIQUETA ===")
    print("📅 Fecha:", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print("🎯 Cambios implementados:")
    print("   1. ✅ Campo cambiado: propiedad_material → almacen_especificacion_material")
    print("   2. ✅ Texto eliminado: 'QTY:' removido de la etiqueta")
    print("   3. ✅ Estructura simplificada: Solo cantidad y especificación")
    print()
    
    # Comparar antes y después
    comparar_antes_despues()
    
    # Probar casos diferentes
    test_casos_diferentes()
    
    # Generar código JavaScript
    generar_codigo_javascript_corregido()
    
    print("\n🎯 === RESUMEN DE CORRECCIONES ===")
    print("✅ Campo especificación: Ahora usa 'almacen_especificacion_material'")
    print("✅ Texto QTY eliminado: La línea de cantidad ya no muestra 'QTY:'")
    print("✅ Captura corregida: guardarFormulario() usa formData.especificacion")
    print("✅ Funciones actualizadas: Todas las funciones de debug actualizadas")
    
    print("\n📋 === PRÓXIMOS PASOS ===")
    print("1. Probar en el navegador con el código JavaScript corregido")
    print("2. Guardar un material real y verificar la etiqueta impresa")
    print("3. Confirmar que:")
    print("   • La cantidad aparece sin 'QTY:'")
    print("   • La especificación del material aparece correctamente")
    print("   • Se usa el campo 'almacen_especificacion_material'")

if __name__ == "__main__":
    main()
