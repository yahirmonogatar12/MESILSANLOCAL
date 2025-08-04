#!/usr/bin/env python3
"""
Script para buscar y mostrar el log del servicio SMT Monitor
"""

import os
import glob

def buscar_logs():
    """Buscar archivos de log del servicio SMT"""
    
    # Posibles ubicaciones del log
    posibles_rutas = [
        r'C:\SMTMonitor\smt_monitor_service.log',
        r'C:\SMTMonitorService\smt_monitor_service.log',
        r'c:\Users\yahir\OneDrive\Escritorio\ISEMM_MES\SMTMonitorService\smt_monitor_service.log',
        # Buscar en el directorio actual
        os.path.join(os.path.dirname(__file__), 'smt_monitor_service.log')
    ]
    
    logs_encontrados = []
    
    print("BUSCANDO ARCHIVOS DE LOG DEL SERVICIO SMT...")
    print("=" * 60)
    
    # Verificar rutas específicas
    for ruta in posibles_rutas:
        if os.path.exists(ruta):
            size = os.path.getsize(ruta)
            modified = os.path.getmtime(ruta)
            logs_encontrados.append((ruta, size, modified))
            print(f"✅ ENCONTRADO: {ruta}")
            print(f"   Tamaño: {size} bytes")
            print(f"   Modificado: {os.path.ctime(modified)}")
            print()
    
    # Buscar globalmente archivos que contengan "smt_monitor" y terminen en .log
    print("Buscando archivos de log globalmente...")
    patrones = [
        r'C:\**\smt_monitor*.log',
        r'C:\Users\**\smt_monitor*.log'
    ]
    
    for patron in patrones:
        try:
            archivos = glob.glob(patron, recursive=True)
            for archivo in archivos:
                if archivo not in [log[0] for log in logs_encontrados]:
                    if os.path.exists(archivo):
                        size = os.path.getsize(archivo)
                        modified = os.path.getmtime(archivo)
                        logs_encontrados.append((archivo, size, modified))
                        print(f"✅ ENCONTRADO (búsqueda global): {archivo}")
                        print(f"   Tamaño: {size} bytes")
                        print(f"   Modificado: {os.path.ctime(modified)}")
                        print()
        except Exception as e:
            print(f"Error buscando patrón {patron}: {e}")
    
    return logs_encontrados

def mostrar_ultimas_lineas(archivo_log, num_lineas=50):
    """Mostrar las últimas N líneas del archivo de log"""
    try:
        print(f"\n=== ÚLTIMAS {num_lineas} LÍNEAS DE: {archivo_log} ===")
        print("=" * 80)
        
        with open(archivo_log, 'r', encoding='utf-8') as f:
            lineas = f.readlines()
        
        # Tomar las últimas N líneas
        ultimas_lineas = lineas[-num_lineas:]
        
        for i, linea in enumerate(ultimas_lineas, 1):
            print(f"{i:3d}: {linea.rstrip()}")
        
        print("=" * 80)
        print(f"Total de líneas en el archivo: {len(lineas)}")
        print(f"Mostrando últimas {len(ultimas_lineas)} líneas")
        
    except Exception as e:
        print(f"❌ Error leyendo archivo {archivo_log}: {e}")

def main():
    print("BUSCADOR DE LOGS DEL SERVICIO SMT MONITOR")
    print("=" * 60)
    
    logs = buscar_logs()
    
    if not logs:
        print("❌ NO SE ENCONTRARON ARCHIVOS DE LOG")
        print()
        print("POSIBLES CAUSAS:")
        print("1. El servicio no se ha ejecutado aún")
        print("2. El servicio no tiene permisos para escribir logs")
        print("3. El archivo está en una ubicación diferente")
        print()
        print("PARA DIAGNOSTICAR:")
        print("1. Verifica si el servicio está ejecutándose:")
        print("   sc query SMTMonitorService")
        print("2. Ejecuta el servicio en modo consola:")
        print("   python smt_monitor_service.py")
        print("3. Revisa los logs del sistema Windows:")
        print("   eventvwr.msc")
        return
    
    print(f"\n✅ SE ENCONTRARON {len(logs)} ARCHIVO(S) DE LOG")
    print()
    
    # Mostrar el log más reciente
    log_mas_reciente = max(logs, key=lambda x: x[2])
    archivo_reciente = log_mas_reciente[0]
    
    print(f"📁 Archivo más reciente: {archivo_reciente}")
    mostrar_ultimas_lineas(archivo_reciente, 50)
    
    # Si hay múltiples logs, preguntar si mostrar otros
    if len(logs) > 1:
        print(f"\nSe encontraron {len(logs)} archivos de log en total:")
        for i, (archivo, size, modified) in enumerate(logs, 1):
            print(f"{i}. {archivo} ({size} bytes, {os.path.ctime(modified)})")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error en script: {e}")
    
    input("\nPresiona Enter para continuar...")
