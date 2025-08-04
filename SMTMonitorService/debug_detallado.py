#!/usr/bin/env python3
"""
Versión de debug del SMT Monitor con logging detallado
"""

import os
import sys
import time
import logging
import getpass
from datetime import datetime

# Configurar logging muy detallado
def setup_detailed_logging():
    log_file = r"C:\SMTMonitor\debug_monitor.log"
    
    # Crear directorio si no existe
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger = logging.getLogger(__name__)
    return logger

def debug_environment(logger):
    """Debug del entorno de ejecución"""
    logger.info("=== DEBUG DE ENTORNO ===")
    logger.info(f"Usuario: {getpass.getuser()}")
    logger.info(f"Directorio actual: {os.getcwd()}")
    logger.info(f"Python executable: {sys.executable}")
    logger.info(f"PID del proceso: {os.getpid()}")
    
    # Variables de entorno relevantes
    env_vars = ['PATH', 'USERPROFILE', 'COMPUTERNAME', 'USERNAME']
    for var in env_vars:
        value = os.environ.get(var, 'NO DEFINIDA')
        logger.info(f"Variable {var}: {value[:100]}...")

def debug_folder_access(logger):
    """Debug detallado de acceso a carpetas"""
    base_path = r"C:\LOT CHECK  ALL"
    
    logger.info("=== DEBUG DE ACCESO A CARPETAS ===")
    logger.info(f"Ruta base configurada: {base_path}")
    
    # Verificar ruta base
    logger.info(f"Existe ruta base: {os.path.exists(base_path)}")
    
    if os.path.exists(base_path):
        logger.info("✓ Ruta base accesible")
        try:
            contenido_base = os.listdir(base_path)
            logger.info(f"Contenido ruta base ({len(contenido_base)} items): {contenido_base}")
        except Exception as e:
            logger.error(f"Error listando ruta base: {e}")
    else:
        logger.error("✗ Ruta base NO accesible")
        
        # Intentar alternativas
        alternativas = [
            r"C:\LOT CHECK ALL",  # Un espacio
            r"C:\LOTCHECK ALL",   # Sin espacio
            r"C:\LOT_CHECK_ALL",  # Con guiones bajos
        ]
        
        for alt in alternativas:
            logger.info(f"Probando alternativa: {alt}")
            if os.path.exists(alt):
                logger.info(f"✓ Alternativa encontrada: {alt}")
                break
    
    # Configurar carpetas como en el servicio
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
    
    logger.info(f"Total carpetas configuradas: {len(folders_to_monitor)}")
    
    # Verificar cada carpeta detalladamente
    for i, folder in enumerate(folders_to_monitor, 1):
        logger.info(f"--- Carpeta {i}: {folder} ---")
        
        # Verificar cada parte del path
        parts = folder.split('\\')
        current_path = ""
        
        for j, part in enumerate(parts):
            if j == 0:
                current_path = part + "\\"
            else:
                current_path = os.path.join(current_path, part)
            
            exists = os.path.exists(current_path)
            logger.info(f"  Parte {j+1} '{part}': {current_path} -> Existe: {exists}")
            
            if not exists:
                logger.error(f"  ✗ Ruta cortada en: {current_path}")
                break
        
        # Verificar carpeta final
        if os.path.exists(folder):
            logger.info(f"  ✓ Carpeta final accesible")
            try:
                import glob
                csv_files = glob.glob(os.path.join(folder, "*.csv"))
                logger.info(f"  ✓ Archivos CSV encontrados: {len(csv_files)}")
                if csv_files:
                    logger.info(f"  ✓ Primer archivo: {csv_files[0]}")
            except Exception as e:
                logger.error(f"  ✗ Error buscando CSVs: {e}")
        else:
            logger.error(f"  ✗ Carpeta final NO accesible")

def main():
    logger = setup_detailed_logging()
    
    logger.info("INICIANDO DEBUG DETALLADO SMT MONITOR")
    logger.info("=" * 50)
    
    debug_environment(logger)
    debug_folder_access(logger)
    
    logger.info("=" * 50)
    logger.info("DEBUG COMPLETADO - Revisa el log para detalles completos")
    
    print("\nDebug completado. Revisa el archivo C:\\SMTMonitor\\debug_monitor.log")

if __name__ == "__main__":
    main()
    input("Presiona Enter para continuar...")
