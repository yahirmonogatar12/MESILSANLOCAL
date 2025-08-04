#!/usr/bin/env python3
"""
Script para verificar la tabla historial_cambio_material_smt
"""

import mysql.connector
from datetime import datetime
import os

# Configuración de la base de datos (correcta)
DB_CONFIG = {
    'host': 'up-de-fra1-mysql-1.db.run-on-seenode.com',
    'port': 11550,
    'user': 'db_rrpq0erbdujn',
    'password': '5fUNbSRcPP3LN9K2I33Pr0ge',
    'database': 'db_rrpq0erbdujn'
}

def conectar_db():
    """Conectar a la base de datos"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        print("✅ Conexión exitosa a la base de datos")
        return conn
    except Exception as e:
        print(f"❌ Error conectando: {e}")
        return None

def verificar_tabla():
    """Verificar estructura de la tabla"""
    conn = conectar_db()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Verificar que la tabla existe
        cursor.execute("SHOW TABLES LIKE 'historial_cambio_material_smt'")
        tabla_existe = cursor.fetchone()
        
        if not tabla_existe:
            print("❌ Tabla 'historial_cambio_material_smt' NO existe")
            return False
        
        print("✅ Tabla 'historial_cambio_material_smt' existe")
        
        # Obtener estructura de la tabla
        cursor.execute("DESCRIBE historial_cambio_material_smt")
        columnas = cursor.fetchall()
        
        print("\nESTRUCTURA DE LA TABLA:")
        print("-" * 50)
        for col in columnas:
            print(f"  {col[0]} - {col[1]}")
        
        # Contar registros
        cursor.execute("SELECT COUNT(*) FROM historial_cambio_material_smt")
        total = cursor.fetchone()[0]
        print(f"\n📊 Total de registros: {total}")
        
        # Mostrar últimos registros
        if total > 0:
            cursor.execute("""
                SELECT * FROM historial_cambio_material_smt 
                ORDER BY fecha_cambio DESC 
                LIMIT 5
            """)
            registros = cursor.fetchall()
            
            print("\nÚLTIMOS 5 REGISTROS:")
            print("-" * 100)
            for reg in registros:
                print(f"  {reg}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error verificando tabla: {e}")
        return False
    finally:
        if conn:
            conn.close()

def insertar_prueba():
    """Insertar un registro de prueba"""
    conn = conectar_db()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Datos de prueba
        datos_prueba = (
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),  # fecha_cambio
            'PRUEBA_SERVICIO',                              # tipo_movimiento
            'P12345',                                       # part_number
            'LOT001',                                       # lote
            '999',                                          # cantidad_original
            '1',                                            # cantidad_cambiada
            'Sistema de monitoreo',                         # usuario
            'Prueba de inserción',                          # comentarios
            'C:\\LOT CHECK  ALL\\PRUEBA',                  # ruta_archivo
            'test.csv',                                     # nombre_archivo
            '1',                                            # linea_archivo
            'ACTIVO',                                       # estatus
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),  # fecha_procesamiento
            'COMPLETED',                                    # estado_proceso
            'JSON_DATOS_PRUEBA'                            # datos_json
        )
        
        cursor.execute("""
            INSERT INTO historial_cambio_material_smt 
            (fecha_cambio, tipo_movimiento, part_number, lote, cantidad_original, 
             cantidad_cambiada, usuario, comentarios, ruta_archivo, nombre_archivo, 
             linea_archivo, estatus, fecha_procesamiento, estado_proceso, datos_json)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, datos_prueba)
        
        conn.commit()
        print("✅ Registro de prueba insertado correctamente")
        return True
        
    except Exception as e:
        print(f"❌ Error insertando prueba: {e}")
        return False
    finally:
        if conn:
            conn.close()

def main():
    print("VERIFICADOR DE TABLA FUNCIONAL")
    print("=" * 50)
    
    # Verificar estructura
    if verificar_tabla():
        print("\n" + "=" * 50)
        print("✅ TABLA VERIFICADA CORRECTAMENTE")
        
        # Preguntar si insertar prueba
        respuesta = input("\n¿Insertar registro de prueba? (s/n): ")
        if respuesta.lower() == 's':
            insertar_prueba()
    
    else:
        print("❌ Error verificando tabla")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}")
    
    input("\nPresiona Enter para continuar...")
