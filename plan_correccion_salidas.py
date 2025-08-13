#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import mysql.connector
from mysql.connector import Error

# Configuración de base de datos remota
DB_CONFIG = {
    'host': 'up-de-fra1-mysql-1.db.run-on-seenode.com',
    'port': 11550,
    'database': 'db_rrpq0erbdujn',
    'user': 'db_rrpq0erbdujn',
    'password': '5fUNbSRcPP3LN9K2I33Pr0ge',
    'charset': 'utf8mb4'
}

def conectar_db():
    """Conectar a la base de datos MySQL"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        print("✅ Conexión exitosa a la base de datos remota")
        return connection
    except Error as e:
        print(f"❌ Error conectando a MySQL: {e}")
        return None

def mejorar_funcion_salida():
    """Mejorar la función de salida para determinar automáticamente el proceso destino"""
    
    funcion_mejorada = '''
def registrar_salida_material_mysql(data):
    """
    Registrar salida de material - VERSIÓN MEJORADA
    Determina automáticamente el proceso destino basado en la especificación del material
    """
    import logging
    from datetime import datetime
    
    fecha_registro = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    try:
        # Extraer numero_parte del codigo_material_recibido (antes de la coma)
        codigo_material = data['codigo_material_recibido']
        numero_parte = codigo_material.split(',')[0] if ',' in codigo_material else codigo_material
        
        # PASO 1: Obtener especificación del material original desde control_material_almacen
        query_especificacion = """
            SELECT especificacion, propiedad_material
            FROM control_material_almacen 
            WHERE codigo_material_recibido = %s
            ORDER BY id DESC LIMIT 1
        """
        
        result_spec = execute_query(query_especificacion, (codigo_material,), fetch_one=True)
        
        especificacion_original = ""
        propiedad_material = ""
        
        if result_spec:
            especificacion_original = result_spec.get('especificacion', '')
            propiedad_material = result_spec.get('propiedad_material', '')
            print(f"📋 Material encontrado - Especificación: {especificacion_original}, Propiedad: {propiedad_material}")
        else:
            print(f"⚠️ No se encontró el material {codigo_material} en almacén")
        
        # PASO 2: Determinar proceso_salida automáticamente
        proceso_salida = 'PRODUCCION'  # Default
        
        # Lógica de determinación automática basada en especificación y propiedad
        if propiedad_material:
            if propiedad_material.upper() == 'SMD':
                proceso_salida = 'SMD'
            elif propiedad_material.upper() == 'IMD':
                proceso_salida = 'IMD'
            elif propiedad_material.upper() in ['MAIN', 'THROUGH_HOLE']:
                proceso_salida = 'MAIN'
            else:
                # Si no está claro por propiedad, usar especificación
                spec_upper = especificacion_original.upper()
                if any(keyword in spec_upper for keyword in ['SMD', 'SURFACE', 'CHIP']):
                    proceso_salida = 'SMD'
                elif any(keyword in spec_upper for keyword in ['IMD', 'IN-MOLD']):
                    proceso_salida = 'IMD'
                elif any(keyword in spec_upper for keyword in ['THROUGH', 'HOLE', 'DIP']):
                    proceso_salida = 'MAIN'
        
        # Override manual si se especifica en los datos
        if data.get('proceso_salida') and data.get('proceso_salida') != 'AUTO':
            proceso_salida_manual = data.get('proceso_salida', '')
            if proceso_salida_manual == 'SMT 1st SIDE':
                proceso_salida = 'SMD'
            else:
                proceso_salida = proceso_salida_manual
        
        print(f"🎯 Proceso destino determinado: {proceso_salida}")
        
        # PASO 3: Insertar en control_material_salida
        query = """
            INSERT INTO control_material_salida (
                codigo_material_recibido, numero_parte, numero_lote, modelo, depto_salida,
                proceso_salida, cantidad_salida, fecha_salida, fecha_registro, especificacion_material
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        params = (
            data['codigo_material_recibido'],
            numero_parte,
            data.get('numero_lote', ''),
            data.get('modelo', ''),
            data.get('depto_salida', ''),
            proceso_salida,  # Proceso determinado automáticamente
            data['cantidad_salida'],
            data.get('fecha_salida', ''),
            fecha_registro,
            especificacion_original or data.get('especificacion_material', '')  # Usar especificación original
        )
        
        result = execute_query(query, params)
        
        if result > 0:
            print(f"✅ Salida registrada exitosamente - Proceso: {proceso_salida}")
            
            # PASO 4: Actualizar inventario general
            actualizar_inventario_general_material(numero_parte)
            
            return True
        else:
            print(f"❌ Error al registrar salida")
            return False
            
    except Exception as e:
        print(f"❌ Error en registrar_salida_material_mysql: {e}")
        return False
'''
    
    print("📝 FUNCIÓN MEJORADA DE SALIDA:")
    print("=" * 50)
    print("✅ Determina automáticamente el proceso destino (SMD, IMD, MAIN)")
    print("✅ Obtiene especificación del material original")
    print("✅ Corrige proceso_salida basado en propiedad_material")
    print("✅ Usa especificación original, no del formulario")
    print("=" * 50)
    print()
    print(funcion_mejorada)
    
    return funcion_mejorada

def corregir_frontend_proceso():
    """Generar código JavaScript corregido para el frontend"""
    
    js_corregido = '''
// ===============================================
// CÓDIGO JAVASCRIPT CORREGIDO PARA EL FRONTEND
// ===============================================

async function procesarSalidaAutomatica(materialActual, cantidadSalida, modelo, numeroLote) {
    try {
        const codigo = materialActual.codigo_material_recibido || materialActual.codigo_barras;
        
        // NO hardcodear proceso_salida, dejar que el backend lo determine
        const salidaResponse = await fetch('/api/material/salida', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                codigo_material_recibido: codigo,
                cantidad_salida: cantidadSalida,
                modelo: modelo,
                numero_lote: numeroLote,
                fecha_salida: document.getElementById('salida_fecha_salida_form')?.value || '',
                // NO enviar especificacion_material - el backend la obtendrá del original
                proceso_salida: 'AUTO',  // Cambiar de 'SMD' a 'AUTO' para determinación automática
                codigo_verificacion: document.getElementById('salida_verificacion_codigo')?.value || ''
            })
        });

        const salidaData = await salidaResponse.json();

        if (salidaData.success) {
            const modeloTexto = modelo === 'SIN_MODELO' ? ' (sin modelo)' : ` (${modelo})`;
            const procesoDestino = salidaData.proceso_destino || 'PRODUCCION';
            
            mostrarMensajeSimple(
                `✅ Salida automática procesada: ${cantidadSalida}${modeloTexto} → ${procesoDestino}`, 
                'success'
            );
            
            setTimeout(() => {
                limpiarCamposMaterial();
            }, 1000);
        } else {
            mostrarMensajeSimple(`❌ Error: ${salidaData.message}`, 'error');
        }

    } catch (error) {
        console.error('Error en salida automática:', error);
        mostrarMensajeSimple('❌ Error procesando salida automática', 'error');
    }
}
'''
    
    print("📝 CÓDIGO JAVASCRIPT CORREGIDO:")
    print("=" * 50)
    print("✅ No hardcodea proceso_salida='SMD'")
    print("✅ Usa proceso_salida='AUTO' para determinación automática")
    print("✅ No envía especificacion_material (backend la obtiene)")
    print("✅ Muestra el proceso destino en el mensaje")
    print("=" * 50)
    print()
    print(js_corregido)
    
    return js_corregido

def main():
    print("🔧 CORRECCIÓN COMPLETA DEL SISTEMA DE SALIDAS")
    print("=" * 60)
    
    print("1. PROBLEMAS IDENTIFICADOS:")
    print("   ❌ Frontend hardcodea proceso_salida='SMD'")
    print("   ❌ No obtiene especificación del material original")
    print("   ❌ Campo cantidad_actual vs cantidad_total en inventario_general")
    print("   ❌ No determina automáticamente el destino (SMD/IMD/MAIN)")
    print()
    
    print("2. SOLUCIONES PROPUESTAS:")
    print()
    
    # Mostrar función mejorada
    mejorar_funcion_salida()
    print()
    
    # Mostrar JavaScript corregido
    corregir_frontend_proceso()
    print()
    
    print("3. PASOS PARA APLICAR:")
    print("   1️⃣ Reemplazar función registrar_salida_material_mysql en db_mysql.py")
    print("   2️⃣ Actualizar JavaScript en MaterialTemplate.html")
    print("   3️⃣ El campo cantidad_actual ya fue corregido anteriormente")
    print()
    
    print("✅ PLAN DE CORRECCIÓN COMPLETADO")

if __name__ == "__main__":
    main()
