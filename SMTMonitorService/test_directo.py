#!/usr/bin/env python3
"""
Test directo de logs del servicio en tiempo real
"""
import os
import time
import threading
import logging
from datetime import datetime

def setup_logging():
    """Configurar logging para debug"""
    log_file = r"C:\SMTMonitor\test_directo.log"
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def test_acceso_carpetas(logger):
    """Test directo de acceso a carpetas exactamente como el servicio"""
    logger.info("=== TEST DIRECTO DE ACCESO ===")
    
    # Usar la ruta exacta del servicio
    base_path = r"C:\LOT CHECK  ALL"
    
    logger.info(f"Probando ruta base: {base_path}")
    logger.info(f"Ruta base existe: {os.path.exists(base_path)}")
    
    if not os.path.exists(base_path):
        logger.error("FALLO CRÍTICO: Ruta base no existe")
        
        # Probar alternativas
        alternativas = [
            r"C:\LOT CHECK ALL",
            r"C:\LOTCHECK ALL",
            r"C:\LOT_CHECK_ALL"
        ]
        
        for alt in alternativas:
            logger.info(f"Probando alternativa: {alt}")
            if os.path.exists(alt):
                logger.info(f"ALTERNATIVA ENCONTRADA: {alt}")
                base_path = alt
                break
        else:
            logger.error("NO SE ENCONTRÓ NINGUNA ALTERNATIVA")
            return False
    
    # Test de carpetas exacto como el servicio
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
    
    logger.info(f"Carpetas configuradas: {len(folders_to_monitor)}")
    
    # Verificar cada carpeta
    carpetas_ok = 0
    for i, folder in enumerate(folders_to_monitor, 1):
        existe = os.path.exists(folder)
        logger.info(f"{i:2}. {folder} -> Existe: {existe}")
        
        if existe:
            carpetas_ok += 1
            try:
                import glob
                csv_files = glob.glob(os.path.join(folder, "*.csv"))
                logger.info(f"    CSV files: {len(csv_files)}")
            except Exception as e:
                logger.error(f"    Error buscando CSV: {e}")
        else:
            # Debug detallado del path que falla
            parts = folder.split('\\')
            current = ""
            for j, part in enumerate(parts):
                if j == 0:
                    current = part + "\\"
                else:
                    current = os.path.join(current, part)
                exists = os.path.exists(current)
                logger.debug(f"    Parte {j}: {current} -> {exists}")
                if not exists:
                    break
    
    logger.info(f"RESULTADO: {carpetas_ok}/{len(folders_to_monitor)} carpetas encontradas")
    return carpetas_ok == len(folders_to_monitor)

def verificar_servicio_logs():
    """Verificar logs existentes del servicio"""
    log_paths = [
        r"C:\SMTMonitor\smt_monitor_service.log",
        r"C:\SMTMonitor\smt_monitor_local.log",
        r"C:\SMTMonitorService\smt_monitor_service.log"
    ]
    
    print("\n=== LOGS DEL SERVICIO ===")
    for log_path in log_paths:
        if os.path.exists(log_path):
            print(f"✓ Log encontrado: {log_path}")
            try:
                with open(log_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    print(f"  Líneas en log: {len(lines)}")
                    # Mostrar últimas 5 líneas
                    print("  Últimas líneas:")
                    for line in lines[-5:]:
                        print(f"    {line.strip()}")
            except Exception as e:
                print(f"  Error leyendo log: {e}")
        else:
            print(f"✗ Log no encontrado: {log_path}")

def main():
    print("TEST DIRECTO DEL PROBLEMA SMT")
    print("=" * 50)
    
    logger = setup_logging()
    
    # Test básico de acceso
    resultado = test_acceso_carpetas(logger)
    
    # Verificar logs existentes
    verificar_servicio_logs()
    
    print("\n" + "=" * 50)
    if resultado:
        print("✓ Test OK - Las carpetas son accesibles desde este contexto")
        print("El problema está en el contexto del servicio específicamente")
    else:
        print("✗ Test FALLO - Hay problemas básicos de acceso")
    
    print(f"\nLog detallado guardado en: C:\\SMTMonitor\\test_directo.log")

if __name__ == "__main__":
    main()
    input("\nPresiona Enter para continuar...")
