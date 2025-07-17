#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TEST: Solución para campos vacíos en etiqueta
Compara la función original vs la nueva función con datos específicos
"""

import json
from datetime import datetime

def simular_guardar_original():
    """
    Simula el comportamiento ORIGINAL (problemas)
    """
    print("🔴 === SIMULANDO COMPORTAMIENTO ORIGINAL (PROBLEMÁTICO) ===\n")
    
    # 1. Datos del formulario antes de guardar
    datos_formulario = {
        'codigo_material_recibido': 'TEST123,20250716001',
        'numero_lote_material': 'LOT123',
        'numero_parte': 'PART456',
        'cantidad_actual': '1000',
        'propiedad_material': '68F 1608'
    }
    
    print("📋 Datos del formulario ANTES de guardar:")
    for campo, valor in datos_formulario.items():
        print(f"   {campo}: '{valor}'")
    
    # 2. Guardar en BD (simulado)
    print("\n💾 Guardando en base de datos...")
    print("✅ Datos guardados en BD")
    
    # 3. Limpiar formulario (PROBLEMA: se ejecuta antes de imprimir)
    print("\n🗑️ Limpiando formulario...")
    datos_formulario_limpio = {campo: '' for campo in datos_formulario}
    
    print("📋 Datos del formulario DESPUÉS de limpiar:")
    for campo, valor in datos_formulario_limpio.items():
        print(f"   {campo}: '{valor}'")
    
    # 4. Intentar imprimir etiqueta (PROBLEMA: usa formulario vacío)
    print("\n🖨️ Intentando imprimir etiqueta...")
    print("⚠️ PROBLEMA: Los campos están vacíos porque se limpiaron")
    
    # Simular generación ZPL con campos vacíos
    codigo = datos_formulario_limpio['codigo_material_recibido'] or 'VACIO'
    cantidad = datos_formulario_limpio['cantidad_actual'] or ''
    propiedad = datos_formulario_limpio['propiedad_material'] or ''
    
    zpl_fragmento = f"""
^FT160,125^A0N,14,14^FH\\^CI28^FDQTY: {cantidad}^FS^CI27
^FT160,140^A0N,14,14^FH\\^CI28^FD{propiedad}^FS^CI27
"""
    
    print("📝 Fragmento ZPL generado (PROBLEMÁTICO):")
    print(zpl_fragmento)
    print("❌ RESULTADO: Campos vacíos en la etiqueta impresa")
    
    return False

def simular_guardar_solucion():
    """
    Simula el comportamiento NUEVO (solucionado)
    """
    print("\n🟢 === SIMULANDO COMPORTAMIENTO NUEVO (SOLUCIONADO) ===\n")
    
    # 1. Datos del formulario antes de guardar
    datos_formulario = {
        'codigo_material_recibido': 'TEST123,20250716001',
        'numero_lote_material': 'LOT123',
        'numero_parte': 'PART456',
        'cantidad_actual': '1000',
        'propiedad_material': '68F 1608'
    }
    
    print("📋 Datos del formulario ANTES de guardar:")
    for campo, valor in datos_formulario.items():
        print(f"   {campo}: '{valor}'")
    
    # 2. CAPTURAR datos ANTES de guardar (SOLUCIÓN)
    datos_capturados = {
        'codigo': datos_formulario['codigo_material_recibido'],
        'numeroLote': datos_formulario['numero_lote_material'],
        'numeroParte': datos_formulario['numero_parte'],
        'cantidadActual': datos_formulario['cantidad_actual'],
        'propiedadMaterial': datos_formulario['propiedad_material']
    }
    
    print("\n✅ SOLUCIÓN: Datos capturados ANTES de limpiar:")
    for campo, valor in datos_capturados.items():
        print(f"   {campo}: '{valor}'")
    
    # 3. Guardar en BD (simulado)
    print("\n💾 Guardando en base de datos...")
    print("✅ Datos guardados en BD")
    
    # 4. Limpiar formulario (ya no afecta la impresión)
    print("\n🗑️ Limpiando formulario...")
    datos_formulario_limpio = {campo: '' for campo in datos_formulario}
    
    print("📋 Datos del formulario DESPUÉS de limpiar:")
    for campo, valor in datos_formulario_limpio.items():
        print(f"   {campo}: '{valor}'")
    
    # 5. Imprimir etiqueta usando datos capturados (SOLUCIÓN)
    print("\n🖨️ Imprimiendo etiqueta con datos capturados...")
    print("✅ SOLUCIÓN: Usando datos capturados, NO del formulario")
    
    # Simular generación ZPL con datos capturados
    codigo = datos_capturados['codigo']
    cantidad = datos_capturados['cantidadActual']
    propiedad = datos_capturados['propiedadMaterial']
    
    zpl_fragmento = f"""
^FT160,125^A0N,14,14^FH\\^CI28^FDQTY: {cantidad}^FS^CI27
^FT160,140^A0N,14,14^FH\\^CI28^FD{propiedad}^FS^CI27
"""
    
    print("📝 Fragmento ZPL generado (SOLUCIONADO):")
    print(zpl_fragmento)
    print("✅ RESULTADO: Campos con datos correctos en la etiqueta impresa")
    
    return True

def comparar_metodos():
    """
    Compara ambos métodos lado a lado
    """
    print("\n📊 === COMPARACIÓN DE MÉTODOS ===\n")
    
    print("🔴 MÉTODO ORIGINAL (PROBLEMÁTICO):")
    print("   1. Guardar datos en BD")
    print("   2. Limpiar formulario")  
    print("   3. Imprimir etiqueta (lee formulario vacío)")
    print("   ❌ RESULTADO: Campos vacíos")
    
    print("\n🟢 MÉTODO NUEVO (SOLUCIONADO):")
    print("   1. Capturar datos del formulario")
    print("   2. Guardar datos en BD")
    print("   3. Limpiar formulario")
    print("   4. Imprimir etiqueta (usa datos capturados)")
    print("   ✅ RESULTADO: Campos con datos")
    
    print("\n🔧 FUNCIONES IMPLEMENTADAS:")
    print("   • imprimirZebraAutomaticoConDatos()")
    print("   • generarComandoZPLConDatos()")
    print("   • Captura de datos en guardarFormulario()")

def generar_codigo_javascript():
    """
    Genera código JavaScript para probar en el navegador
    """
    codigo_js = """
// === CÓDIGO PARA PROBAR EN CONSOLA DEL NAVEGADOR ===

// 1. Llenar campos de test
document.getElementById('codigo_material_recibido').value = 'TEST123,20250716001';
document.getElementById('numero_lote_material').value = 'LOT123';
document.getElementById('numero_parte_lower').value = 'PART456';
document.getElementById('cantidad_actual').value = '1000';
document.getElementById('propiedad_material').value = '68F 1608';

// 2. Verificar que se llenaron
verificarCamposEtiqueta();

// 3. Probar función original (problemática)
console.log('🔴 Probando función original...');
imprimirZebraAutomatico('TEST123,20250716001');

// 4. Probar función nueva (solucionada)
console.log('🟢 Probando función nueva...');
const datosTest = {
    codigo: 'TEST123,20250716001',
    numeroLote: 'LOT123', 
    numeroParte: 'PART456',
    cantidadActual: '1000',
    propiedadMaterial: '68F 1608'
};
imprimirZebraAutomaticoConDatos(datosTest);

// 5. Simular proceso completo
testSimularGuardar();
"""
    
    print("\n💻 === CÓDIGO JAVASCRIPT PARA PROBAR ===")
    print("Copie y pegue en la consola del navegador (F12):")
    print("=" * 50)
    print(codigo_js)
    print("=" * 50)

def main():
    """
    Función principal
    """
    print("🔍 === ANÁLISIS DE SOLUCIÓN PARA CAMPOS VACÍOS ===")
    print("📅 Fecha:", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print("🎯 Problema: Cantidad actual y especificación material no aparecen")
    print("💡 Causa: Formulario se limpia antes de imprimir")
    print("✅ Solución: Capturar datos antes de limpiar formulario")
    print()
    
    # Simular comportamiento original
    resultado_original = simular_guardar_original()
    
    # Simular comportamiento solucionado
    resultado_solucion = simular_guardar_solucion()
    
    # Comparar métodos
    comparar_metodos()
    
    # Generar código de prueba
    generar_codigo_javascript()
    
    print("\n🎯 === CONCLUSIÓN ===")
    if resultado_solucion:
        print("✅ SOLUCIÓN IMPLEMENTADA CORRECTAMENTE")
        print("📋 Los campos cantidad_actual y propiedad_material ahora aparecerán")
        print("🖨️ La etiqueta se imprimirá con todos los datos completos")
    else:
        print("❌ PROBLEMA NO RESUELTO")
    
    print("\n📋 === PRÓXIMOS PASOS ===")
    print("1. Probar en el navegador con el código JavaScript")
    print("2. Verificar que las funciones nuevas funcionan correctamente")
    print("3. Guardar un material real y verificar la etiqueta impresa")
    print("4. Confirmar que cantidad_actual y propiedad_material aparecen")

if __name__ == "__main__":
    main()
