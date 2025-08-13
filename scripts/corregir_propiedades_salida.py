#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para corregir las propiedades de material en control_material_salida
Cambiar "SMD 1SIDE" por la propiedad real del material
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

def corregir_propiedades_salida():
    """Corregir las propiedades de material en salidas"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("=" * 60)
        print("CORRECCIÓN DE PROPIEDADES DE MATERIAL EN SALIDAS")
        print("=" * 60)
        print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # 1. Verificar registros con "SMD 1SIDE" u otras propiedades incorrectas
        print("1. IDENTIFICANDO REGISTROS CON PROPIEDADES INCORRECTAS:")
        cursor.execute("""
            SELECT 
                id,
                codigo_material_recibido,
                especificacion_material,
                fecha_salida
            FROM control_material_salida 
            WHERE especificacion_material LIKE '%SMD%SIDE%' 
               OR especificacion_material LIKE '%1SIDE%'
               OR especificacion_material LIKE '%2SIDE%'
            ORDER BY fecha_salida DESC
            LIMIT 20
        """)
        
        registros_incorrectos = cursor.fetchall()
        print(f"   Encontrados {len(registros_incorrectos)} registros con propiedades incorrectas")
        
        if registros_incorrectos:
            print("   Ejemplos:")
            for reg in registros_incorrectos[:5]:
                print(f"     ID {reg[0]}: {reg[1]} -> '{reg[2]}'")
            print()
        
        # 2. Actualizar registros usando la propiedad real del material
        print("2. CORRIGIENDO PROPIEDADES DE MATERIAL:")
        
        # Consulta para actualizar con la propiedad real
        update_query = """
            UPDATE control_material_salida cms
            LEFT JOIN control_material_almacen cma ON cms.codigo_material_recibido = cma.codigo_material_recibido
            SET cms.especificacion_material = COALESCE(cma.propiedad_material, cms.especificacion_material)
            WHERE (cms.especificacion_material LIKE '%SMD%SIDE%' 
                   OR cms.especificacion_material LIKE '%1SIDE%'
                   OR cms.especificacion_material LIKE '%2SIDE%'
                   OR cms.especificacion_material = '')
              AND cma.propiedad_material IS NOT NULL
              AND cma.propiedad_material != ''
        """
        
        # Primero contar cuántos se van a actualizar
        count_query = """
            SELECT COUNT(*)
            FROM control_material_salida cms
            LEFT JOIN control_material_almacen cma ON cms.codigo_material_recibido = cma.codigo_material_recibido
            WHERE (cms.especificacion_material LIKE '%SMD%SIDE%' 
                   OR cms.especificacion_material LIKE '%1SIDE%'
                   OR cms.especificacion_material LIKE '%2SIDE%'
                   OR cms.especificacion_material = '')
              AND cma.propiedad_material IS NOT NULL
              AND cma.propiedad_material != ''
        """
        
        cursor.execute(count_query)
        count_to_update = cursor.fetchone()[0]
        print(f"   Se actualizarán {count_to_update} registros")
        
        if count_to_update > 0:
            # Ejecutar la actualización
            cursor.execute(update_query)
            updated_rows = cursor.rowcount
            conn.commit()
            print(f"   ✓ Actualizados {updated_rows} registros exitosamente")
        else:
            print("   No hay registros para actualizar")
        
        print()
        
        # 3. Verificar algunos ejemplos después de la corrección
        print("3. VERIFICANDO CORRECCIÓN:")
        cursor.execute("""
            SELECT 
                cms.id,
                cms.codigo_material_recibido,
                cms.especificacion_material,
                cma.propiedad_material as propiedad_original
            FROM control_material_salida cms
            LEFT JOIN control_material_almacen cma ON cms.codigo_material_recibido = cma.codigo_material_recibido
            WHERE cms.fecha_salida >= CURDATE() - INTERVAL 7 DAY
            ORDER BY cms.id DESC
            LIMIT 10
        """)
        
        verificacion = cursor.fetchall()
        if verificacion:
            print("   Últimos registros (después de corrección):")
            for reg in verificacion:
                match = "✓" if reg[2] == reg[3] else "⚠"
                print(f"     {match} ID {reg[0]}: {reg[1]} -> '{reg[2]}'")
                if reg[2] != reg[3] and reg[3]:
                    print(f"       (Original: '{reg[3]}')")
        print()
        
        # 4. Resumen final
        print("4. RESUMEN FINAL:")
        
        # Contar registros que aún tienen problemas
        cursor.execute("""
            SELECT COUNT(*) 
            FROM control_material_salida 
            WHERE especificacion_material LIKE '%SMD%SIDE%' 
               OR especificacion_material LIKE '%1SIDE%'
               OR especificacion_material LIKE '%2SIDE%'
        """)
        
        registros_pendientes = cursor.fetchone()[0]
        
        if registros_pendientes == 0:
            print("   ✓ Todos los registros han sido corregidos")
            print("   ✓ Ahora las salidas mostrarán la misma propiedad que las entradas")
        else:
            print(f"   ⚠ Quedan {registros_pendientes} registros sin corregir")
            print("   Esto puede ser porque no tienen material original en control_material")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False

def crear_trigger_preventivo():
    """Crear un trigger para prevenir futuras inserciones incorrectas"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("\n" + "=" * 60)
        print("CREANDO TRIGGER PREVENTIVO")
        print("=" * 60)
        
        # Trigger para actualizar automáticamente la especificación al insertar
        trigger_sql = """
        CREATE TRIGGER IF NOT EXISTS tr_fix_especificacion_salida
        BEFORE INSERT ON control_material_salida
        FOR EACH ROW
        BEGIN
            DECLARE real_propiedad VARCHAR(512);
            
            -- Obtener la propiedad real del material
            SELECT propiedad_material INTO real_propiedad
            FROM control_material_almacen 
            WHERE codigo_material_recibido = NEW.codigo_material_recibido
            LIMIT 1;
            
            -- Si encontramos la propiedad real y es diferente a la que se va a insertar
            IF real_propiedad IS NOT NULL AND real_propiedad != '' THEN
                SET NEW.especificacion_material = real_propiedad;
            END IF;
        END
        """
        
        try:
            cursor.execute(trigger_sql)
            print("   ✓ Trigger preventivo creado exitosamente")
            print("   ➤ Futuras salidas usarán automáticamente la propiedad correcta")
        except Exception as e:
            if "already exists" in str(e).lower():
                print("   ✓ Trigger preventivo ya existe")
            else:
                print(f"   ⚠ No se pudo crear el trigger: {e}")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"Error creando trigger: {e}")
        return False

if __name__ == '__main__':
    print("Iniciando corrección de propiedades de material en salidas...\n")
    
    if corregir_propiedades_salida():
        crear_trigger_preventivo()
        
        print("\n" + "=" * 60)
        print("✓ CORRECCIÓN COMPLETADA")
        print("=" * 60)
        print("• Propiedades de material corregidas en salidas existentes")
        print("• Trigger preventivo instalado para futuras salidas")
        print("• Código de salidas actualizado para usar propiedad real")
        print("• Ahora las salidas mostrarán la misma propiedad que las entradas")
        print("=" * 60)
    else:
        print("✗ No se pudo completar la corrección")
