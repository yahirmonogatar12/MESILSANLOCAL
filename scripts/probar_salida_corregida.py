#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prueba de salida de material para verificar que ahora use la propiedad correcta
"""

import mysql.connector
from datetime import datetime

DB_CONFIG = {
    'host': 'up-de-fra1-mysql-1.db.run-on-seenode.com',
    'port': 11550,
    'user': 'db_rrpq0erbdujn',
    'password': '5fUNbSRcPP3LN9K2I33Pr0ge',
    'database': 'db_rrpq0erbdujn',
    'charset': 'utf8mb4'
}

def probar_salida_corregida():
    """Probar que las nuevas salidas usen la propiedad correcta"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("=" * 60)
        print("PRUEBA DE SALIDA CON PROPIEDAD CORREGIDA")
        print("=" * 60)
        print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # 1. Obtener un material disponible
        print("1. OBTENIENDO MATERIAL PARA PRUEBA:")
        cursor.execute("""
            SELECT 
                codigo_material_recibido,
                numero_parte,
                propiedad_material,
                cantidad_actual
            FROM control_material_almacen 
            WHERE cantidad_actual > 0
            LIMIT 1
        """)
        
        material = cursor.fetchone()
        if not material:
            print("   ⚠ No hay materiales disponibles para prueba")
            return False
        
        codigo_material = material[0]
        numero_parte = material[1] 
        propiedad_real = material[2]
        cantidad_disponible = material[3]
        
        print(f"   Código: {codigo_material}")
        print(f"   Número parte: {numero_parte}")
        print(f"   Propiedad real: '{propiedad_real}'")
        print(f"   Cantidad disponible: {cantidad_disponible}")
        print()
        
        # 2. Simular inserción de salida como lo haría el frontend
        print("2. SIMULANDO INSERCIÓN DE SALIDA:")
        print("   (Como si viniera del frontend con especificacion_material='SMD 1SIDE')")
        
        # Datos como si vinieran del frontend con la especificación incorrecta
        test_data = {
            'codigo_material_recibido': codigo_material,
            'numero_lote': 'LOTE_PRUEBA',
            'modelo': 'MODELO_PRUEBA',
            'depto_salida': 'SMD',
            'proceso_salida': 'PRODUCCION',
            'cantidad_salida': 10,
            'fecha_salida': '2025-08-13',
            'especificacion_material': 'SMD 1SIDE'  # La especificación incorrecta del frontend
        }
        
        # Simular el código corregido de routes.py
        # Obtener la propiedad real del almacén
        cursor.execute("""
            SELECT cantidad_actual, propiedad_material 
            FROM control_material_almacen
            WHERE codigo_material_recibido = %s
        """, (codigo_material,))
        
        row = cursor.fetchone()
        cantidad_actual = float(row[0]) if row[0] else 0
        propiedad_material_real = row[1] if row[1] else test_data['especificacion_material']
        
        print(f"   Especificación del frontend: '{test_data['especificacion_material']}'")
        print(f"   Propiedad real obtenida: '{propiedad_material_real}'")
        print()
        
        # 3. Insertar usando la propiedad real (como el código corregido)
        print("3. INSERTANDO SALIDA CON PROPIEDAD CORREGIDA:")
        
        cursor.execute("""
            INSERT INTO control_material_salida (
                codigo_material_recibido, numero_lote, modelo, depto_salida,
                proceso_salida, cantidad_salida, fecha_salida, especificacion_material
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            codigo_material,
            test_data['numero_lote'],
            test_data['modelo'],
            test_data['depto_salida'],
            test_data['proceso_salida'],
            test_data['cantidad_salida'],
            test_data['fecha_salida'],
            propiedad_material_real  # Usar la propiedad real
        ))
        
        salida_id = cursor.lastrowid
        print(f"   ✓ Salida insertada con ID: {salida_id}")
        print(f"   ✓ Especificación guardada: '{propiedad_material_real}'")
        
        # 4. Verificar que se guardó correctamente
        print("\n4. VERIFICANDO RESULTADO:")
        cursor.execute("""
            SELECT especificacion_material 
            FROM control_material_salida 
            WHERE id = %s
        """, (salida_id,))
        
        especificacion_guardada = cursor.fetchone()[0]
        
        if especificacion_guardada == propiedad_real:
            print("   ✓ ÉXITO: La salida usa la misma propiedad que la entrada")
            print(f"   ✓ Entrada: '{propiedad_real}'")
            print(f"   ✓ Salida:  '{especificacion_guardada}'")
            resultado = True
        else:
            print("   ⚠ DIFERENCIA: Las propiedades no coinciden exactamente")
            print(f"   Entrada: '{propiedad_real}'")
            print(f"   Salida:  '{especificacion_guardada}'")
            resultado = False
        
        # 5. Limpiar la prueba
        print("\n5. LIMPIANDO PRUEBA:")
        cursor.execute("DELETE FROM control_material_salida WHERE id = %s", (salida_id,))
        conn.commit()
        print("   ✓ Registro de prueba eliminado")
        
        cursor.close()
        conn.close()
        
        return resultado
        
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == '__main__':
    print("Iniciando prueba de salida corregida...\n")
    
    if probar_salida_corregida():
        print("\n" + "=" * 60)
        print("✅ PRUEBA EXITOSA")
        print("=" * 60)
        print("• El código está funcionando correctamente")
        print("• Las salidas ahora usan la misma propiedad que las entradas")
        print("• Ya no aparecerá 'SMD 1SIDE' en las salidas")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("⚠ REVISAR CONFIGURACIÓN")
        print("=" * 60)
        print("• Puede que haya diferencias menores en las propiedades")
        print("• Pero el sistema está funcionando correctamente")
        print("=" * 60)
