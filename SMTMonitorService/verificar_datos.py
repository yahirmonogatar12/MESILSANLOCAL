#!/usr/bin/env python3
"""
Script para verificar si los datos están llegando a la base de datos
"""

import mysql.connector
from mysql.connector import Error
from datetime import datetime, timedelta
import os

# Configuración de base de datos
DB_CONFIG = {
    'host': 'up-de-fra1-mysql-1.db.run-on-seenode.com',
    'port': 11550,
    'user': 'db_rrpq0erbdujn_user',
    'password': 'RkQqhq98VCxD24J7',
    'database': 'db_rrpq0erbdujn'
}

def conectar_db():
    """Conectar a la base de datos"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except Error as e:
        print(f"❌ Error conectando a DB: {e}")
        return None

def verificar_datos_recientes():
    """Verificar datos de las últimas horas"""
    print("VERIFICANDO DATOS EN BASE DE DATOS")
    print("=" * 50)
    
    connection = conectar_db()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor()
        
        # 1. Contar total de registros
        cursor.execute("SELECT COUNT(*) FROM smt_data")
        total = cursor.fetchone()[0]
        print(f"📊 Total de registros en DB: {total}")
        
        # 2. Registros de hoy
        cursor.execute("""
            SELECT COUNT(*) FROM smt_data 
            WHERE DATE(timestamp) = CURDATE()
        """)
        hoy = cursor.fetchone()[0]
        print(f"📅 Registros de hoy: {hoy}")
        
        # 3. Registros de la última hora
        cursor.execute("""
            SELECT COUNT(*) FROM smt_data 
            WHERE timestamp >= DATE_SUB(NOW(), INTERVAL 1 HOUR)
        """)
        ultima_hora = cursor.fetchone()[0]
        print(f"🕐 Registros última hora: {ultima_hora}")
        
        # 4. Registros de los últimos 10 minutos
        cursor.execute("""
            SELECT COUNT(*) FROM smt_data 
            WHERE timestamp >= DATE_SUB(NOW(), INTERVAL 10 MINUTE)
        """)
        ultimos_10min = cursor.fetchone()[0]
        print(f"⏰ Registros últimos 10 min: {ultimos_10min}")
        
        # 5. Último registro insertado
        cursor.execute("""
            SELECT timestamp, source_file, linea, maquina, barcode
            FROM smt_data 
            ORDER BY timestamp DESC 
            LIMIT 1
        """)
        ultimo = cursor.fetchone()
        
        if ultimo:
            print(f"\n📋 ÚLTIMO REGISTRO:")
            print(f"   Fecha: {ultimo[0]}")
            print(f"   Archivo: {ultimo[1]}")
            print(f"   Línea: {ultimo[2]}")
            print(f"   Máquina: {ultimo[3]}")
            print(f"   Barcode: {ultimo[4]}")
        else:
            print("\n❌ No hay registros en la base de datos")
        
        # 6. Últimos 10 registros por timestamp
        print(f"\n📋 ÚLTIMOS 10 REGISTROS:")
        cursor.execute("""
            SELECT timestamp, source_file, linea, maquina, barcode
            FROM smt_data 
            ORDER BY timestamp DESC 
            LIMIT 10
        """)
        
        registros = cursor.fetchall()
        if registros:
            for i, reg in enumerate(registros, 1):
                print(f"   {i}. {reg[0]} - {reg[1]} - {reg[2]}/{reg[3]} - {reg[4]}")
        else:
            print("   No hay registros")
        
        # 7. Estadísticas por línea/máquina
        print(f"\n📈 ESTADÍSTICAS POR LÍNEA/MÁQUINA:")
        cursor.execute("""
            SELECT linea, maquina, COUNT(*) as total
            FROM smt_data 
            GROUP BY linea, maquina
            ORDER BY linea, maquina
        """)
        
        stats = cursor.fetchall()
        if stats:
            for stat in stats:
                print(f"   {stat[0]}/{stat[1]}: {stat[2]} registros")
        else:
            print("   No hay datos por línea/máquina")
        
        return True
        
    except Error as e:
        print(f"❌ Error ejecutando consultas: {e}")
        return False
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

def verificar_archivos_procesados():
    """Verificar si hay archivos CSV que deberían procesarse"""
    print(f"\n🔍 VERIFICANDO ARCHIVOS CSV DISPONIBLES")
    print("=" * 50)
    
    base_path = r"C:\LOT CHECK  ALL"
    
    if not os.path.exists(base_path):
        print(f"❌ Carpeta base no existe: {base_path}")
        return
    
    lines_config = {
        "1line": ["L1 m1", "L1 m2", "L1 m3"],
        "2line": ["L2 m1", "L2 m2", "L2 m3"], 
        "3line": ["L3 m1", "L3 m2", "L3 m3"],
        "4line": ["L4 m1", "L4 m2", "L4 m3"]
    }
    
    total_csvs = 0
    total_carpetas = 0
    
    for line, mounters in lines_config.items():
        for mounter in mounters:
            folder_path = os.path.join(base_path, line, mounter)
            total_carpetas += 1
            
            if os.path.exists(folder_path):
                try:
                    archivos = [f for f in os.listdir(folder_path) if f.lower().endswith('.csv')]
                    if archivos:
                        total_csvs += len(archivos)
                        print(f"📁 {line}/{mounter}: {len(archivos)} archivos CSV")
                        for archivo in archivos[:3]:  # Mostrar solo los primeros 3
                            file_path = os.path.join(folder_path, archivo)
                            mod_time = os.path.getmtime(file_path)
                            mod_date = datetime.fromtimestamp(mod_time)
                            print(f"   - {archivo} (modificado: {mod_date})")
                        if len(archivos) > 3:
                            print(f"   ... y {len(archivos) - 3} más")
                    else:
                        print(f"📁 {line}/{mounter}: Sin archivos CSV")
                except Exception as e:
                    print(f"❌ Error en {line}/{mounter}: {e}")
            else:
                print(f"❌ {line}/{mounter}: Carpeta no existe")
    
    print(f"\n📊 RESUMEN:")
    print(f"   Total carpetas verificadas: {total_carpetas}")
    print(f"   Total archivos CSV encontrados: {total_csvs}")
    
    if total_csvs > 0:
        print(f"\n⚠️  HAY {total_csvs} ARCHIVOS CSV DISPONIBLES")
        print("   Si no se están procesando, puede ser porque:")
        print("   1. El servicio no tiene permisos")
        print("   2. Los archivos ya fueron procesados y movidos")
        print("   3. Hay un error en el procesamiento")
    else:
        print("\n✅ No hay archivos CSV pendientes de procesar")

def main():
    print("VERIFICADOR DE PROCESAMIENTO SMT")
    print("=" * 60)
    
    # Verificar datos en DB
    verificar_datos_recientes()
    
    # Verificar archivos disponibles
    verificar_archivos_procesados()
    
    print("\n" + "=" * 60)
    print("VERIFICACIÓN COMPLETADA")
    print("\nSi no hay datos recientes pero hay archivos CSV:")
    print("1. Verifica que el servicio esté ejecutándose: sc query SMTMonitorService")
    print("2. Revisa los logs del servicio")
    print("3. Ejecuta en modo consola para debug: python smt_monitor_service.py")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error en script: {e}")
    
    input("\nPresiona Enter para continuar...")
