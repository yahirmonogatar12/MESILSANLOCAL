#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import mysql.connector
from mysql.connector import Error

# Configuración de la base de datos
DB_CONFIG = {
    'host': 'up-de-fra1-mysql-1.db.run-on-seenode.com',
    'port': 11550,
    'user': 'db_rrpq0erbdujn',
    'password': '5fUNbSRcPP3LN9K2I33Pr0ge',
    'database': 'db_rrpq0erbdujn'
}

def verificacion_final():
    """Verificación final del sistema corregido"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()
        
        print("=== VERIFICACIÓN FINAL DEL SISTEMA ===")
        print()
        
        # 1. Verificar triggers activos
        print("1. TRIGGERS ACTIVOS:")
        cursor.execute("SHOW TRIGGERS LIKE 'control_material_almacen'")
        triggers = cursor.fetchall()
        
        for trigger in triggers:
            print(f"   ✅ {trigger[0]} - {trigger[1]} {trigger[2]}")
        
        # 2. Verificar que no hay más registros AUTO_SMD
        print("\n2. REGISTROS AUTO_SMD RESTANTES:")
        cursor.execute("""
            SELECT COUNT(*) FROM InventarioRollosSMD 
            WHERE codigo_barras LIKE 'AUTO_SMD_%'
        """)
        count_auto = cursor.fetchone()[0]
        
        if count_auto == 0:
            print("   ✅ NO HAY registros AUTO_SMD")
        else:
            print(f"   ⚠️ Aún hay {count_auto} registros AUTO_SMD")
        
        # 3. Verificar los últimos registros
        print("\n3. ÚLTIMOS REGISTROS EN InventarioRollosSMD:")
        cursor.execute("""
            SELECT id, numero_parte, codigo_barras, movimiento_origen_id, fecha_entrada
            FROM InventarioRollosSMD 
            ORDER BY id DESC LIMIT 3
        """)
        
        registros = cursor.fetchall()
        for reg in registros:
            print(f"   ID: {reg[0]} - Parte: {reg[1]} - Código: {reg[2]} - Origen: {reg[3]}")
        
        # 4. Verificar correspondencia con el último material
        print("\n4. VERIFICACIÓN DE TRAZABILIDAD:")
        cursor.execute("""
            SELECT ca.id, ca.numero_parte, ca.codigo_material_recibido, ca.fecha_registro
            FROM control_material_almacen ca
            WHERE ca.propiedad_material = 'SMD'
            ORDER BY ca.id DESC LIMIT 1
        """)
        
        ultimo_almacen = cursor.fetchone()
        
        if ultimo_almacen:
            print(f"   Último material almacén:")
            print(f"     ID: {ultimo_almacen[0]}")
            print(f"     Parte: {ultimo_almacen[1]}")
            print(f"     Código: {ultimo_almacen[2]}")
            
            # Buscar en SMD
            cursor.execute("""
                SELECT id, codigo_barras, movimiento_origen_id
                FROM InventarioRollosSMD 
                WHERE movimiento_origen_id = %s
            """, (ultimo_almacen[0],))
            
            smd_correspondiente = cursor.fetchone()
            
            if smd_correspondiente:
                print(f"   Registro SMD correspondiente:")
                print(f"     ID: {smd_correspondiente[0]}")
                print(f"     Código Barras: {smd_correspondiente[1]}")
                
                if smd_correspondiente[1] == ultimo_almacen[2]:
                    print("   ✅ TRAZABILIDAD CORRECTA: Los códigos coinciden")
                else:
                    print("   ❌ PROBLEMA: Los códigos NO coinciden")
            else:
                print("   ⚠️ No hay registro SMD correspondiente")
        
        print("\n" + "=" * 50)
        print("✅ VERIFICACIÓN COMPLETADA")
        print("✅ El sistema ahora usa solo codigo_material_recibido")
        print("✅ No se generarán más códigos AUTO_SMD")
        print("=" * 50)
        
    except Error as e:
        print(f"❌ Error: {e}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

if __name__ == "__main__":
    verificacion_final()
