#!/usr/bin/env python3
"""
Monitor en tiempo real de procesamiento de datos SMT
"""

import mysql.connector
from mysql.connector import Error
import time
import os
from datetime import datetime

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

def obtener_conteo_actual():
    """Obtener conteo actual de registros"""
    connection = conectar_db()
    if not connection:
        return None
    
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM smt_data")
        count = cursor.fetchone()[0]
        return count
    except:
        return None
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

def obtener_ultimo_registro():
    """Obtener información del último registro"""
    connection = conectar_db()
    if not connection:
        return None
    
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT timestamp, source_file, linea, maquina, barcode
            FROM smt_data 
            ORDER BY timestamp DESC 
            LIMIT 1
        """)
        result = cursor.fetchone()
        return result
    except:
        return None
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

def verificar_servicio():
    """Verificar estado del servicio"""
    try:
        result = os.system("sc query SMTMonitorService > nul 2>&1")
        return result == 0
    except:
        return False

def monitor_tiempo_real():
    """Monitorear en tiempo real"""
    print("MONITOR EN TIEMPO REAL - SMT DATA PROCESSING")
    print("=" * 60)
    print("Presiona Ctrl+C para detener")
    print("=" * 60)
    
    conteo_anterior = obtener_conteo_actual()
    ultimo_registro_anterior = obtener_ultimo_registro()
    
    if conteo_anterior is None:
        print("❌ No se puede conectar a la base de datos")
        return
    
    print(f"📊 Conteo inicial: {conteo_anterior} registros")
    if ultimo_registro_anterior:
        print(f"📋 Último registro: {ultimo_registro_anterior[0]} - {ultimo_registro_anterior[1]}")
    
    print("\nMonitoreando cambios cada 10 segundos...")
    print("Formato: [HORA] - Nuevos registros: X - Total: Y")
    print("-" * 60)
    
    try:
        while True:
            time.sleep(10)  # Esperar 10 segundos
            
            # Verificar estado del servicio
            servicio_activo = verificar_servicio()
            
            # Obtener conteo actual
            conteo_actual = obtener_conteo_actual()
            ultimo_registro_actual = obtener_ultimo_registro()
            
            if conteo_actual is None:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Error conectando a DB")
                continue
            
            # Calcular diferencia
            nuevos = conteo_actual - conteo_anterior
            
            # Status del servicio
            status_servicio = "🟢" if servicio_activo else "🔴"
            
            if nuevos > 0:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] {status_servicio} ✅ Nuevos: {nuevos} - Total: {conteo_actual}")
                
                # Mostrar info del nuevo registro
                if ultimo_registro_actual and ultimo_registro_actual != ultimo_registro_anterior:
                    print(f"                     📄 Último: {ultimo_registro_actual[1]} ({ultimo_registro_actual[2]}/{ultimo_registro_actual[3]})")
                
                ultimo_registro_anterior = ultimo_registro_actual
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] {status_servicio} ⏳ Sin cambios - Total: {conteo_actual}")
            
            conteo_anterior = conteo_actual
            
    except KeyboardInterrupt:
        print("\n\n🛑 Monitoreo detenido por usuario")
        print("=" * 60)
        
        # Mostrar estadísticas finales
        conteo_final = obtener_conteo_actual()
        if conteo_final:
            print(f"📊 Registros finales: {conteo_final}")

def main():
    print("MONITOR DE PROCESAMIENTO EN TIEMPO REAL")
    print("=" * 60)
    
    # Verificación inicial
    print("🔍 Verificando conexión inicial...")
    connection = conectar_db()
    if not connection:
        print("❌ No se puede conectar a la base de datos")
        print("Verifica la configuración de red y credenciales")
        return
    
    connection.close()
    print("✅ Conexión a DB establecida")
    
    # Verificar servicio
    if verificar_servicio():
        print("✅ Servicio SMTMonitorService está activo")
    else:
        print("⚠️  Servicio SMTMonitorService no está activo")
        print("   Ejecuta: sc start SMTMonitorService")
    
    print()
    
    # Iniciar monitoreo
    monitor_tiempo_real()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error en script: {e}")
    
    input("\nPresiona Enter para continuar...")
