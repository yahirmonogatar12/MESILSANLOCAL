#!/usr/bin/env python3
"""
Diagnóstico específico para servicios de Windows
Simula el entorno del servicio para detectar problemas de acceso
"""

import os
import sys
import getpass
import subprocess
import glob
from datetime import datetime

def log_info(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")
    
def diagnostico_contexto():
    log_info("=== DIAGNÓSTICO DE CONTEXTO ===")
    log_info(f"Usuario actual: {getpass.getuser()}")
    log_info(f"Python ejecutable: {sys.executable}")
    log_info(f"Directorio actual: {os.getcwd()}")
    log_info(f"Variables PATH relevantes:")
    
    path_env = os.environ.get('PATH', '')
    for path_item in path_env.split(';')[:10]:  # Primeros 10
        if path_item.strip():
            log_info(f"  - {path_item}")
    
    log_info("")

def verificar_permisos_directos():
    log_info("=== VERIFICACIÓN DIRECTA DE PERMISOS ===")
    
    rutas_test = [
        r"C:",
        r"C:\LOT CHECK  ALL",
        r"C:\LOT CHECK  ALL\1line",
        r"C:\LOT CHECK  ALL\1line\L1 m1"
    ]
    
    for ruta in rutas_test:
        log_info(f"Probando: {ruta}")
        
        # Verificar existencia
        existe = os.path.exists(ruta)
        log_info(f"  - Existe: {existe}")
        
        if existe:
            # Verificar permisos de lectura
            try:
                es_dir = os.path.isdir(ruta)
                log_info(f"  - Es directorio: {es_dir}")
                
                if es_dir:
                    contenido = os.listdir(ruta)
                    log_info(f"  - Elementos en directorio: {len(contenido)}")
                    for item in contenido[:5]:  # Primeros 5
                        log_info(f"    * {item}")
                        
            except PermissionError as e:
                log_info(f"  - ERROR DE PERMISOS: {e}")
            except Exception as e:
                log_info(f"  - ERROR: {e}")
        
        log_info("")

def simular_monitoreo_servicio():
    log_info("=== SIMULACIÓN DE MONITOREO COMO SERVICIO ===")
    
    base_path = r"C:\LOT CHECK  ALL"
    
    # Configurar carpetas exactamente como el servicio
    lines_config = {
        "1line": ["L1 m1", "L1 m2", "L1 m3"],
        "2line": ["L2 m1", "L2 m2", "L2 m3"], 
        "3line": ["L3 m1", "L3 m2", "L3 m3"],
        "4line": ["L4 m1", "L4 m2", "L4 m3"]
    }
    
    folders_to_monitor = []
    for line, mounters in lines_config.items():
        for mounter in mounters:
            folder_path = os.path.join(base_path, line, mounter)
            folders_to_monitor.append(folder_path)
    
    log_info(f"Base path configurado: {base_path}")
    log_info(f"Total carpetas a monitorear: {len(folders_to_monitor)}")
    log_info("")
    
    carpetas_encontradas = 0
    total_archivos = 0
    
    for i, folder in enumerate(folders_to_monitor, 1):
        log_info(f"{i:2}. Verificando: {folder}")
        
        if os.path.exists(folder):
            carpetas_encontradas += 1
            try:
                csv_files = glob.glob(os.path.join(folder, "*.csv"))
                archivos_count = len(csv_files)
                total_archivos += archivos_count
                log_info(f"    ✓ ENCONTRADA - {archivos_count} archivos CSV")
                
                # Intentar leer un archivo
                if csv_files:
                    test_file = csv_files[0]
                    try:
                        with open(test_file, 'r', encoding='utf-8') as f:
                            primera_linea = f.readline().strip()
                            log_info(f"    ✓ Archivo legible: {os.path.basename(test_file)}")
                            log_info(f"    ✓ Primera línea: {primera_linea[:50]}...")
                    except Exception as e:
                        log_info(f"    ✗ Error leyendo archivo: {e}")
                        
            except Exception as e:
                log_info(f"    ✗ Error accediendo carpeta: {e}")
        else:
            log_info(f"    ✗ NO ENCONTRADA")
    
    log_info("")
    log_info(f"RESUMEN: {carpetas_encontradas}/{len(folders_to_monitor)} carpetas encontradas")
    log_info(f"Total archivos CSV: {total_archivos}")
    
    return carpetas_encontradas == len(folders_to_monitor)

def verificar_servicio_actual():
    log_info("=== VERIFICACIÓN DEL SERVICIO ACTUAL ===")
    
    try:
        # Verificar si el servicio existe
        result = subprocess.run(
            ['sc', 'query', 'SMTMonitorService'], 
            capture_output=True, text=True, shell=True
        )
        
        if result.returncode == 0:
            log_info("✓ Servicio SMTMonitorService encontrado")
            log_info("Estado del servicio:")
            for line in result.stdout.split('\n'):
                if line.strip():
                    log_info(f"  {line.strip()}")
        else:
            log_info("✗ Servicio SMTMonitorService no encontrado")
            
    except Exception as e:
        log_info(f"Error verificando servicio: {e}")
    
    log_info("")

def main():
    log_info("DIAGNÓSTICO COMPLETO DE SERVICIO SMT")
    log_info("=" * 60)
    log_info("")
    
    diagnostico_contexto()
    verificar_permisos_directos()
    verificar_servicio_actual()
    resultado = simular_monitoreo_servicio()
    
    log_info("")
    log_info("=== RECOMENDACIONES ===")
    
    if resultado:
        log_info("✓ Todas las carpetas son accesibles desde este contexto")
        log_info("El problema puede ser:")
        log_info("1. El servicio se ejecuta como usuario SYSTEM")
        log_info("2. Diferencias en variables de entorno")
        log_info("3. Permisos específicos del servicio")
        log_info("")
        log_info("SOLUCIONES:")
        log_info("- Ejecutar el servicio como usuario actual")
        log_info("- Dar permisos explícitos a SYSTEM para la carpeta")
        log_info("- Usar rutas UNC si es una unidad de red")
    else:
        log_info("✗ Hay problemas de acceso a las carpetas")
        log_info("Verifica permisos y rutas antes de instalar el servicio")

if __name__ == "__main__":
    main()
    input("\nPresiona Enter para continuar...")
