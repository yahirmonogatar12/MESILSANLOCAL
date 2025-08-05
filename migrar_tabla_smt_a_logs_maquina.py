#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para migrar la tabla historial_cambio_material_smt al esquema logs_maquina
"""

import mysql.connector
import traceback
from datetime import datetime

def conectar_mysql():
    """Conectar a la base de datos MySQL"""
    config = {
        'host': 'up-de-fra1-mysql-1.db.run-on-seenode.com',
        'port': 11550,
        'user': 'db_rrpq0erbdujn',
        'password': '5fUNbSRcPP3LN9K2I33Pr0ge',
        'database': 'db_rrpq0erbdujn',
        'charset': 'utf8mb4'
    }
    
    try:
        conn = mysql.connector.connect(**config)
        print("✅ Conexión MySQL establecida")
        return conn
    except Exception as e:
        print(f"❌ Error conectando a MySQL: {e}")
        return None

def respaldar_tabla_existente(cursor):
    """Crear respaldo de la tabla actual"""
    try:
        print("\n📦 Creando respaldo de la tabla existente...")
        
        # Crear tabla de respaldo con timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        tabla_respaldo = f"historial_cambio_material_smt_backup_{timestamp}"
        
        cursor.execute(f"""
            CREATE TABLE {tabla_respaldo} AS 
            SELECT * FROM historial_cambio_material_smt
        """)
        
        # Verificar cuántos registros se respaldaron
        cursor.execute(f"SELECT COUNT(*) FROM {tabla_respaldo}")
        count = cursor.fetchone()[0]
        
        print(f"✅ Respaldo creado: {tabla_respaldo} ({count} registros)")
        return tabla_respaldo
        
    except Exception as e:
        print(f"❌ Error creando respaldo: {e}")
        return None

def crear_nueva_tabla_logs_maquina(cursor):
    """Crear la nueva tabla logs_maquina"""
    try:
        print("\n🔧 Creando nueva tabla logs_maquina...")
        
        # Primero eliminar la tabla si existe
        cursor.execute("DROP TABLE IF EXISTS logs_maquina")
        
        # Crear la nueva tabla con el esquema especificado
        cursor.execute("""
            CREATE TABLE logs_maquina (
                id INT AUTO_INCREMENT PRIMARY KEY,
                linea VARCHAR(50),
                maquina VARCHAR(50),
                archivo VARCHAR(100),
                ScanDate VARCHAR(20),
                ScanTime VARCHAR(20),
                SlotNo INT,
                Result VARCHAR(10),
                PreviousBarcode VARCHAR(50),
                Productdate VARCHAR(20),
                PartName VARCHAR(50),
                Quantity INT,
                SEQ VARCHAR(20),
                Vendor VARCHAR(50),
                LOTNO VARCHAR(50),
                Barcode VARCHAR(50),
                FeederBase VARCHAR(10),
                fecha_subida DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        print("✅ Tabla logs_maquina creada exitosamente")
        return True
        
    except Exception as e:
        print(f"❌ Error creando tabla logs_maquina: {e}")
        return False

def migrar_datos_existentes(cursor):
    """Migrar datos de historial_cambio_material_smt a logs_maquina"""
    try:
        print("\n📊 Migrando datos existentes...")
        
        # Verificar si hay datos para migrar
        cursor.execute("SELECT COUNT(*) FROM historial_cambio_material_smt")
        total_registros = cursor.fetchone()[0]
        
        if total_registros == 0:
            print("ℹ️ No hay datos para migrar")
            return True
        
        print(f"📋 Encontrados {total_registros} registros para migrar")
        
        # Migrar datos lote por lote
        batch_size = 1000
        offset = 0
        registros_migrados = 0
        
        while offset < total_registros:
            # Obtener lote de datos
            cursor.execute(f"""
                SELECT 
                    scan_date,
                    scan_time,
                    slot_no,
                    result,
                    previous_barcode,
                    product_date,
                    part_name,
                    quantity,
                    seq,
                    vendor,
                    lot_no,
                    barcode,
                    feeder_base,
                    source_file,
                    created_at
                FROM historial_cambio_material_smt
                ORDER BY id
                LIMIT {batch_size} OFFSET {offset}
            """)
            
            registros = cursor.fetchall()
            
            if not registros:
                break
            
            # Insertar en la nueva tabla
            for registro in registros:
                try:
                    # Extraer linea y maquina del source_file
                    source_file = registro[13] or ""
                    
                    # Intentar extraer linea y maquina del nombre del archivo
                    # Ejemplo: "20250724.csv" -> linea="SMT1", maquina="LINE1"
                    linea = "SMT1"  # Valor por defecto
                    maquina = "LINE1"  # Valor por defecto
                    
                    if "SMT1" in source_file.upper():
                        linea = "SMT1"
                    elif "SMT2" in source_file.upper():
                        linea = "SMT2"
                    
                    if "LINE1" in source_file.upper():
                        maquina = "LINE1"
                    elif "LINE2" in source_file.upper():
                        maquina = "LINE2"
                    
                    cursor.execute("""
                        INSERT INTO logs_maquina (
                            linea, maquina, archivo, ScanDate, ScanTime, SlotNo,
                            Result, PreviousBarcode, Productdate, PartName, Quantity,
                            SEQ, Vendor, LOTNO, Barcode, FeederBase, fecha_subida
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        linea,                    # linea
                        maquina,                  # maquina
                        source_file,              # archivo
                        registro[0],              # ScanDate
                        registro[1],              # ScanTime
                        registro[2],              # SlotNo
                        registro[3],              # Result
                        registro[4],              # PreviousBarcode
                        registro[5],              # Productdate
                        registro[6],              # PartName
                        registro[7],              # Quantity
                        registro[8],              # SEQ
                        registro[9],              # Vendor
                        registro[10],             # LOTNO
                        registro[11],             # Barcode
                        registro[12],             # FeederBase
                        registro[14] or datetime.now()  # fecha_subida
                    ))
                    
                    registros_migrados += 1
                    
                except Exception as e:
                    print(f"⚠️ Error migrando registro: {e}")
                    continue
            
            offset += batch_size
            print(f"📊 Migrados {registros_migrados}/{total_registros} registros...")
        
        print(f"✅ Migración completada: {registros_migrados} registros migrados")
        return True
        
    except Exception as e:
        print(f"❌ Error migrando datos: {e}")
        print(f"❌ Traceback: {traceback.format_exc()}")
        return False

def eliminar_tabla_antigua(cursor):
    """Eliminar la tabla antigua después de confirmar que todo está bien"""
    try:
        print("\n🗑️ Eliminando tabla antigua...")
        
        # Verificar que la nueva tabla tiene datos
        cursor.execute("SELECT COUNT(*) FROM logs_maquina")
        count_nueva = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM historial_cambio_material_smt")
        count_vieja = cursor.fetchone()[0]
        
        if count_nueva >= count_vieja:
            cursor.execute("DROP TABLE historial_cambio_material_smt")
            print("✅ Tabla antigua eliminada exitosamente")
            return True
        else:
            print(f"⚠️ No se eliminó la tabla antigua. Nueva: {count_nueva}, Vieja: {count_vieja}")
            return False
            
    except Exception as e:
        print(f"❌ Error eliminando tabla antigua: {e}")
        return False

def verificar_migracion(cursor):
    """Verificar que la migración fue exitosa"""
    try:
        print("\n🔍 Verificando migración...")
        
        # Verificar estructura de la nueva tabla
        cursor.execute("DESCRIBE logs_maquina")
        columns = cursor.fetchall()
        
        print("📋 Estructura de logs_maquina:")
        for col in columns:
            print(f"   - {col[0]}: {col[1]}")
        
        # Verificar datos migrados
        cursor.execute("SELECT COUNT(*) FROM logs_maquina")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT archivo) FROM logs_maquina")
        archivos = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT linea) FROM logs_maquina")
        lineas = cursor.fetchone()[0]
        
        print(f"\n📊 Datos migrados:")
        print(f"   - Total registros: {total}")
        print(f"   - Archivos únicos: {archivos}")
        print(f"   - Líneas únicas: {lineas}")
        
        # Mostrar algunos ejemplos
        cursor.execute("SELECT linea, maquina, archivo, ScanDate, Result FROM logs_maquina LIMIT 5")
        ejemplos = cursor.fetchall()
        
        print(f"\n🔍 Ejemplos de datos migrados:")
        for ejemplo in ejemplos:
            print(f"   - {ejemplo[0]} | {ejemplo[1]} | {ejemplo[2]} | {ejemplo[3]} | {ejemplo[4]}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error verificando migración: {e}")
        return False

def main():
    """Función principal de migración"""
    print("🚀 MIGRACIÓN DE TABLA SMT A LOGS_MAQUINA")
    print("=" * 60)
    
    # Conectar a MySQL
    conn = conectar_mysql()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Paso 1: Respaldar tabla existente
        tabla_respaldo = respaldar_tabla_existente(cursor)
        if not tabla_respaldo:
            print("❌ No se pudo crear respaldo, abortando migración")
            return False
        
        # Paso 2: Crear nueva tabla
        if not crear_nueva_tabla_logs_maquina(cursor):
            print("❌ No se pudo crear nueva tabla, abortando migración")
            return False
        
        # Paso 3: Migrar datos
        if not migrar_datos_existentes(cursor):
            print("❌ Error en migración de datos")
            return False
        
        # Paso 4: Verificar migración
        if not verificar_migracion(cursor):
            print("❌ Error en verificación")
            return False
        
        # Paso 5: Confirmar eliminación de tabla antigua
        print("\n❓ ¿Eliminar tabla antigua? (los datos están respaldados)")
        respuesta = input("Escriba 'SI' para confirmar: ").strip().upper()
        
        if respuesta == 'SI':
            eliminar_tabla_antigua(cursor)
        else:
            print("ℹ️ Tabla antigua conservada para seguridad")
        
        # Confirmar cambios
        conn.commit()
        
        print("\n🎉 ¡MIGRACIÓN COMPLETADA EXITOSAMENTE!")
        print(f"📦 Respaldo disponible en: {tabla_respaldo}")
        print("🔧 Nueva tabla: logs_maquina")
        
        return True
        
    except Exception as e:
        print(f"❌ Error general en migración: {e}")
        print(f"❌ Traceback: {traceback.format_exc()}")
        conn.rollback()
        return False
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    main()
