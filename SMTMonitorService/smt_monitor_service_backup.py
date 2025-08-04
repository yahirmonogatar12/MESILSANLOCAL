#!/usr/bin/env python3
"""
Servicio de Windows para monitoreo de archivos CSV SMT
Versión corregida con configuración definitiva
"""

import win32service
import win32serviceutil
import win32event
import servicemanager
import socket
import time
import logging
import os
import sys
import threading
from datetime import datetime
import mysql.connector
from mysql.connector import Error

# Configuración del servicio
SERVICE_NAME = "SMTMonitorService"
SERVICE_DISPLAY_NAME = "SMT CSV Monitor Service"
SERVICE_DESCRIPTION = "Monitorea carpetas CSV para sistema SMT y actualiza base de datos automáticamente"

# Configuración global
LOG_FILE = os.path.join(os.path.dirname(__file__), 'smt_monitor_service.log')
BASE_PATH = r'C:\LOT CHECK  ALL'  # NOTA: DOS ESPACIOS entre CHECK y ALL

# Configuración de base de datos remota
DB_CONFIG = {
    'host': 'up-de-fra1-mysql-1.db.run-on-seenode.com',
    'port': 11550,
    'user': 'db_rrpq0erbdujn_user',
    'password': 'RkQqhq98VCxD24J7',
    'database': 'db_rrpq0erbdujn'
}

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class SMTCSVMonitor:
    """Monitor de archivos CSV para sistema SMT"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.connection = None
        self.cursor = None
        self.is_running = False
        self.processed_files = set()
        
        # Configuración de carpetas a monitorear (RUTA CORREGIDA)
        self.monitor_folders = [
            os.path.join(BASE_PATH, '1line', 'L1 m1'),
            os.path.join(BASE_PATH, '1line', 'L1 m2'),
            os.path.join(BASE_PATH, '1line', 'L1 m3'),
            os.path.join(BASE_PATH, '2line', 'L2 m1'),
            os.path.join(BASE_PATH, '2line', 'L2 m2'),
            os.path.join(BASE_PATH, '2line', 'L2 m3'),
            os.path.join(BASE_PATH, '3line', 'L3 m1'),
            os.path.join(BASE_PATH, '3line', 'L3 m2'),
            os.path.join(BASE_PATH, '3line', 'L3 m3'),
            os.path.join(BASE_PATH, '4line', 'L4 m1'),
            os.path.join(BASE_PATH, '4line', 'L4 m2'),
            os.path.join(BASE_PATH, '4line', 'L4 m3'),
        ]
        
        self.logger.info(f"Monitor configurado para BASE_PATH: {BASE_PATH}")
        self.logger.info(f"Carpetas a monitorear: {len(self.monitor_folders)}")
        for folder in self.monitor_folders:
            self.logger.info(f"  - {folder}")
    
    def connect_database(self):
        """Conectar a la base de datos MySQL remota"""
        try:
            if self.connection and self.connection.is_connected():
                return True
                
            self.logger.info("Conectando a base de datos remota...")
            self.logger.info(f"Host: {DB_CONFIG['host']}:{DB_CONFIG['port']}")
            self.logger.info(f"Database: {DB_CONFIG['database']}")
            
            self.connection = mysql.connector.connect(**DB_CONFIG)
            self.cursor = self.connection.cursor()
            
            self.logger.info("✅ Conexión a base de datos establecida")
            return True
            
        except Error as e:
            self.logger.error(f"❌ Error conectando a base de datos: {e}")
            return False
    
    def disconnect_database(self):
        """Desconectar de la base de datos"""
        try:
            if self.cursor:
                self.cursor.close()
            if self.connection and self.connection.is_connected():
                self.connection.close()
            self.logger.info("Base de datos desconectada")
        except Exception as e:
            self.logger.error(f"Error desconectando base de datos: {e}")
    
    def verify_folders(self):
        """Verificar que las carpetas de monitoreo existen"""
        missing_folders = []
        existing_folders = []
        
        self.logger.info(f"Verificando carpetas en: {BASE_PATH}")
        
        # Verificar carpeta base
        if not os.path.exists(BASE_PATH):
            self.logger.error(f"❌ Carpeta base no encontrada: {BASE_PATH}")
            return False
        
        self.logger.info(f"✅ Carpeta base encontrada: {BASE_PATH}")
        
        # Verificar subcarpetas
        for folder in self.monitor_folders:
            if os.path.exists(folder):
                existing_folders.append(folder)
                self.logger.info(f"✅ Carpeta encontrada: {folder}")
            else:
                missing_folders.append(folder)
                self.logger.warning(f"⚠️  Carpeta no encontrada: {folder}")
        
        if missing_folders:
            self.logger.warning(f"Carpetas faltantes: {len(missing_folders)}")
            for folder in missing_folders:
                self.logger.warning(f"  - {folder}")
        
        self.logger.info(f"Carpetas disponibles para monitoreo: {len(existing_folders)}")
        
        # Retornar True si al menos una carpeta existe
        return len(existing_folders) > 0
    
    def get_csv_files(self, folder):
        """Obtener archivos CSV de una carpeta"""
        try:
            if not os.path.exists(folder):
                return []
            
            csv_files = []
            for file in os.listdir(folder):
                if file.lower().endswith('.csv'):
                    file_path = os.path.join(folder, file)
                    if file_path not in self.processed_files:
                        csv_files.append(file_path)
            
            return csv_files
        except Exception as e:
            self.logger.error(f"Error leyendo carpeta {folder}: {e}")
            return []
    
    def extract_info_from_path(self, file_path):
        """Extraer información de línea y máquina desde la ruta del archivo"""
        try:
            # Normalizar ruta
            normalized_path = os.path.normpath(file_path)
            parts = normalized_path.split(os.sep)
            
            linea = None
            maquina = None
            
            # Buscar información en los componentes de la ruta
            for part in parts:
                if 'line' in part.lower():
                    if '1line' in part:
                        linea = 'L1'
                    elif '2line' in part:
                        linea = 'L2'
                    elif '3line' in part:
                        linea = 'L3'
                    elif '4line' in part:
                        linea = 'L4'
                
                if 'L1 m' in part or 'L2 m' in part or 'L3 m' in part or 'L4 m' in part:
                    maquina = part
            
            self.logger.debug(f"Extraído de {file_path}: línea={linea}, máquina={maquina}")
            return linea, maquina
            
        except Exception as e:
            self.logger.error(f"Error extrayendo info de ruta {file_path}: {e}")
            return None, None
    
    def process_csv_file(self, file_path):
        """Procesar un archivo CSV individual"""
        try:
            self.logger.info(f"📄 Procesando archivo: {file_path}")
            
            # Extraer información de la ruta
            linea, maquina = self.extract_info_from_path(file_path)
            
            processed_count = 0
            
            with open(file_path, 'r', encoding='utf-8') as file:
                lines = file.readlines()
                
                for line_num, line in enumerate(lines, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Dividir por comas
                    columns = [col.strip().strip('"') for col in line.split(',')]
                    
                    # Verificar que tengamos al menos 14 columnas
                    if len(columns) < 14:
                        self.logger.warning(f"Línea {line_num} tiene solo {len(columns)} columnas, se esperaban 14")
                        continue
                    
                    # Mapeo corregido para 14 columnas
                    try:
                        data = {
                            'serial_number': columns[0] if len(columns) > 0 else '',
                            'part_number': columns[1] if len(columns) > 1 else '',
                            'work_order': columns[2] if len(columns) > 2 else '',
                            'feeder_slots': columns[3] if len(columns) > 3 else '',
                            'components_data': columns[4] if len(columns) > 4 else '',
                            'pcb_thickness': columns[5] if len(columns) > 5 else '',
                            'test_result': columns[6] if len(columns) > 6 else '',
                            'test_time': columns[7] if len(columns) > 7 else '',
                            'cycle_time': columns[8] if len(columns) > 8 else '',
                            'operator': columns[9] if len(columns) > 9 else '',
                            'station': columns[10] if len(columns) > 10 else '',
                            'barcode': columns[11] if len(columns) > 11 else '',  # Columna 12 (índice 11)
                            'feeder_base': columns[12] if len(columns) > 12 else '',  # Columna 13 (índice 12)
                            'additional_info': columns[13] if len(columns) > 13 else '',  # Columna 14 (índice 13)
                            'linea': linea,
                            'maquina': maquina,
                            'timestamp': datetime.now(),
                            'source_file': os.path.basename(file_path)
                        }
                        
                        # Insertar en base de datos
                        self.insert_data(data)
                        processed_count += 1
                        
                    except Exception as e:
                        self.logger.error(f"Error procesando línea {line_num}: {e}")
                        continue
            
            # Marcar archivo como procesado
            self.processed_files.add(file_path)
            self.logger.info(f"✅ Archivo procesado: {processed_count} registros insertados desde {os.path.basename(file_path)}")
            
            # Mover archivo a carpeta de procesados (opcional)
            try:
                processed_dir = os.path.join(os.path.dirname(file_path), 'procesados')
                if not os.path.exists(processed_dir):
                    os.makedirs(processed_dir)
                
                dest_path = os.path.join(processed_dir, os.path.basename(file_path))
                os.rename(file_path, dest_path)
                self.logger.info(f"📁 Archivo movido a: {dest_path}")
                
            except Exception as e:
                self.logger.warning(f"No se pudo mover archivo procesado: {e}")
                
        except Exception as e:
            self.logger.error(f"❌ Error procesando archivo {file_path}: {e}")
    
    def insert_data(self, data):
        """Insertar datos en la base de datos"""
        try:
            if not self.connection or not self.connection.is_connected():
                if not self.connect_database():
                    return False
            
            query = """
            INSERT INTO smt_data (
                serial_number, part_number, work_order, feeder_slots, components_data,
                pcb_thickness, test_result, test_time, cycle_time, operator,
                station, barcode, feeder_base, additional_info, linea, maquina,
                timestamp, source_file
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            """
            
            values = (
                data['serial_number'], data['part_number'], data['work_order'],
                data['feeder_slots'], data['components_data'], data['pcb_thickness'],
                data['test_result'], data['test_time'], data['cycle_time'],
                data['operator'], data['station'], data['barcode'], data['feeder_base'],
                data['additional_info'], data['linea'], data['maquina'],
                data['timestamp'], data['source_file']
            )
            
            self.cursor.execute(query, values)
            self.connection.commit()
            
            return True
            
        except Error as e:
            self.logger.error(f"❌ Error insertando datos: {e}")
            # Intentar reconectar
            self.connect_database()
            return False
    
    def monitor_folders(self):
        """Función principal de monitoreo"""
        self.logger.info("🚀 Iniciando monitoreo de carpetas...")
        
        # Verificar carpetas al inicio
        if not self.verify_folders():
            self.logger.error("❌ No se pueden monitorear carpetas: verificación falló")
            return
        
        # Conectar a base de datos
        if not self.connect_database():
            self.logger.error("❌ No se puede conectar a base de datos")
            return
        
        self.is_running = True
        self.logger.info("✅ Monitor iniciado correctamente")
        
        while self.is_running:
            try:
                total_files_found = 0
                
                for folder in self.monitor_folders:
                    if not self.is_running:
                        break
                    
                    if os.path.exists(folder):
                        csv_files = self.get_csv_files(folder)
                        total_files_found += len(csv_files)
                        
                        for csv_file in csv_files:
                            if not self.is_running:
                                break
                            self.process_csv_file(csv_file)
                
                if total_files_found == 0:
                    self.logger.debug("No se encontraron archivos CSV nuevos")
                
                # Esperar antes del siguiente ciclo
                time.sleep(30)  # Verificar cada 30 segundos
                
            except Exception as e:
                self.logger.error(f"❌ Error en ciclo de monitoreo: {e}")
                time.sleep(60)  # Esperar más tiempo si hay error
        
        self.logger.info("🛑 Monitoreo detenido")
        self.disconnect_database()
    
    def start(self):
        """Iniciar el monitor"""
        self.logger.info("Iniciando SMT CSV Monitor...")
        monitor_thread = threading.Thread(target=self.monitor_folders)
        monitor_thread.daemon = True
        monitor_thread.start()
        return monitor_thread
    
    def stop(self):
        """Detener el monitor"""
        self.logger.info("Deteniendo SMT CSV Monitor...")
        self.is_running = False
        self.disconnect_database()


class SMTMonitorService(win32serviceutil.ServiceFramework):
    """Clase del servicio de Windows"""
    
    _svc_name_ = SERVICE_NAME
    _svc_display_name_ = SERVICE_DISPLAY_NAME
    _svc_description_ = SERVICE_DESCRIPTION
    
    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.logger = logging.getLogger(__name__)
        self.monitor = None
        socket.setdefaulttimeout(60)
    
    def SvcStop(self):
        """Detener el servicio"""
        self.logger.info("🛑 Servicio SMT Monitor deteniéndose...")
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        
        if self.monitor:
            self.monitor.stop()
        
        win32event.SetEvent(self.hWaitStop)
        self.logger.info("✅ Servicio SMT Monitor detenido")
    
    def SvcDoRun(self):
        """Ejecutar el servicio"""
        try:
            self.logger.info("🚀 Servicio SMT Monitor iniciando...")
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_, '')
            )
            
            # Crear y iniciar monitor
            self.monitor = SMTCSVMonitor()
            monitor_thread = self.monitor.start()
            
            self.logger.info("✅ Servicio SMT Monitor iniciado correctamente")
            
            # Esperar hasta que se detenga el servicio
            win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)
            
        except Exception as e:
            self.logger.error(f"❌ Error en servicio: {e}")
            servicemanager.LogErrorMsg(f"Error en servicio SMT Monitor: {e}")


def main():
    """Función principal"""
    if len(sys.argv) == 1:
        # Ejecutar como aplicación de consola para testing
        print("Modo de prueba - Ejecutando como aplicación de consola")
        print("Para instalar como servicio, usa: python smt_monitor_service.py install")
        print("-" * 60)
        
        monitor = SMTCSVMonitor()
        monitor.monitor_folders()
    else:
        # Ejecutar como servicio de Windows
        win32serviceutil.HandleCommandLine(SMTMonitorService)


if __name__ == '__main__':
    main()