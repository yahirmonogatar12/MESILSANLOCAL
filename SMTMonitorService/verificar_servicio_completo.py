#!/usr/bin/env python3
"""
Verificador completo del servicio SMT Monitor
"""

import os
import sys
import time
import mysql.connector
from datetime import datetime

def verificar_servicio():
    """Verificar estado del servicio"""
    print("🔍 VERIFICANDO SERVICIO SMT MONITOR")
    print("=" * 50)
    
    try:
        import subprocess
        result = subprocess.run(['sc', 'query', 'SMTMonitorService'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Servicio instalado")
            if "RUNNING" in result.stdout:
                print("✅ Servicio está ejecutándose")
            elif "STOPPED" in result.stdout:
                print("⚠️  Servicio detenido")
            else:
                print("❓ Estado del servicio desconocido")
            
            print("\nESTADO COMPLETO:")
            print(result.stdout)
        else:
            print("❌ Servicio no está instalado")
            
    except Exception as e:
        print(f"❌ Error verificando servicio: {e}")

def verificar_logs():
    """Verificar logs del servicio"""
    print("\n📋 VERIFICANDO LOGS")
    print("=" * 30)
    
    log_file = "smt_monitor_service.log"
    
    if os.path.exists(log_file):
        print(f"✅ Archivo de logs encontrado: {log_file}")
        
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            print(f"📊 Total de líneas en log: {len(lines)}")
            
            if len(lines) > 0:
                print("\n🔔 ÚLTIMAS 10 LÍNEAS:")
                print("-" * 50)
                for line in lines[-10:]:
                    print(f"  {line.strip()}")
        except Exception as e:
            print(f"❌ Error leyendo logs: {e}")
    else:
        print("❌ No se encontró archivo de logs")

def verificar_conexion_db():
    """Verificar conexión a la base de datos"""
    print("\n🔗 VERIFICANDO CONEXIÓN A BASE DE DATOS")
    print("=" * 45)
    
    db_config = {
        'host': 'up-de-fra1-mysql-1.db.run-on-seenode.com',
        'port': 11550,
        'user': 'db_rrpq0erbdujn',
        'password': '5fUNbSRcPP3LN9K2I33Pr0ge',
        'database': 'db_rrpq0erbdujn'
    }
    
    try:
        conn = mysql.connector.connect(**db_config)
        print("✅ Conexión a base de datos exitosa")
        
        cursor = conn.cursor()
        
        # Verificar tabla principal
        cursor.execute("SHOW TABLES LIKE 'historial_cambio_material_smt'")
        if cursor.fetchone():
            print("✅ Tabla principal existe")
            
            # Contar registros
            cursor.execute("SELECT COUNT(*) FROM historial_cambio_material_smt")
            total = cursor.fetchone()[0]
            print(f"📊 Total de registros: {total}")
            
            # Último registro
            cursor.execute("""
                SELECT fecha_procesado, archivo_origen 
                FROM historial_cambio_material_smt 
                ORDER BY fecha_procesado DESC 
                LIMIT 1
            """)
            ultimo = cursor.fetchone()
            if ultimo:
                print(f"📅 Último registro: {ultimo[0]} - {ultimo[1]}")
        else:
            print("❌ Tabla principal no existe")
        
        # Verificar tabla de control
        cursor.execute("SHOW TABLES LIKE 'archivos_procesados_smt'")
        if cursor.fetchone():
            print("✅ Tabla de control existe")
            
            cursor.execute("SELECT COUNT(*) FROM archivos_procesados_smt")
            total_archivos = cursor.fetchone()[0]
            print(f"📁 Archivos procesados: {total_archivos}")
        else:
            print("❌ Tabla de control no existe")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error conectando a base de datos: {e}")

def verificar_carpetas():
    """Verificar carpetas de monitoreo"""
    print("\n📁 VERIFICANDO CARPETAS DE MONITOREO")
    print("=" * 40)
    
    base_path = r"C:\LOT CHECK  ALL"
    
    if os.path.exists(base_path):
        print(f"✅ Carpeta base existe: {base_path}")
        
        try:
            subcarpetas = [d for d in os.listdir(base_path) 
                          if os.path.isdir(os.path.join(base_path, d))]
            
            print(f"📂 Subcarpetas encontradas: {len(subcarpetas)}")
            
            for carpeta in subcarpetas[:10]:  # Mostrar primeras 10
                ruta_completa = os.path.join(base_path, carpeta)
                try:
                    archivos_csv = [f for f in os.listdir(ruta_completa) 
                                   if f.lower().endswith('.csv')]
                    print(f"  📁 {carpeta}: {len(archivos_csv)} archivos CSV")
                except:
                    print(f"  📁 {carpeta}: No accesible")
            
            if len(subcarpetas) > 10:
                print(f"  ... y {len(subcarpetas) - 10} carpetas más")
                
        except Exception as e:
            print(f"❌ Error listando subcarpetas: {e}")
    else:
        print(f"❌ Carpeta base no existe: {base_path}")
        print("⚠️  Esto es normal si estás probando en otra PC")

def mostrar_comandos_utiles():
    """Mostrar comandos útiles"""
    print("\n🔧 COMANDOS ÚTILES")
    print("=" * 20)
    print("Gestión del servicio:")
    print("  sc start SMTMonitorService    - Iniciar servicio")
    print("  sc stop SMTMonitorService     - Detener servicio")
    print("  sc query SMTMonitorService    - Ver estado")
    print("  sc delete SMTMonitorService   - Desinstalar")
    print()
    print("Logs y monitoreo:")
    print("  type smt_monitor_service.log  - Ver logs")
    print("  python smt_monitor_service.py - Probar en consola")
    print()
    print("Base de datos:")
    print("  python verificar_tabla_existente.py - Verificar tabla")

def main():
    print("🚀 VERIFICADOR COMPLETO SMT MONITOR SERVICE")
    print("=" * 60)
    print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    verificar_servicio()
    verificar_logs()
    verificar_conexion_db()
    verificar_carpetas()
    mostrar_comandos_utiles()
    
    print("\n" + "=" * 60)
    print("✅ VERIFICACIÓN COMPLETA")
    print("=" * 60)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Error en verificación: {e}")
    
    input("\nPresiona Enter para continuar...")
