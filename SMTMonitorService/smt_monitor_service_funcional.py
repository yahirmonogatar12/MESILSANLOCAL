#!/usr/bin/env python3
"""
Servicio de Windows para monitoreo de archivos CSV SMT
Basado en smt_monitor_local.py que funciona correctamente
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
import glob
import mysql.connector
import csv
from datetime import datetime

# Configuración del servicio
SERVICE_NAME = "SMTMonitorService"
SERVICE_DISPLAY_NAME = "SMT CSV Monitor Service"
SERVICE_DESCRIPTION = "Monitorea carpetas CSV para sistema SMT y actualiza base de datos automáticamente"

# Configuración global
LOG_FILE = os.path.join(os.path.dirname(__file__), 'smt_monitor_service.log')
BASE_PATH = r'C:\LOT CHECK  ALL'  # NOTA: DOS ESPACIOS entre CHECK y ALL

# Configuración de base de datos (CREDENCIALES CORRECTAS)
DB_CONFIG = {
    'host': 'up-de-fra1-mysql-1.db.run-on-seenode.com',
    'port': 11550,
    'user': 'db_rrpq0erbdujn',
    'password': '5fUNbSRcPP3LN9K2I33Pr0ge',
    'database': 'db_rrpq0erbdujn',
    'charset': 'utf8mb4',
    'autocommit': True
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
    """Monitor de archivos CSV para sistema SMT (basado en versión funcional)"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.running = False
        
        # Configuración de carpetas a monitorear (RUTA CORREGIDA)
        self.base_path = BASE_PATH
        self.folders_to_monitor = []
        
        # Configurar todas las subcarpetas por línea
        lines_config = {
            "1line": ["L1 m1", "L1 m2", "L1 m3"],
            "2line": ["L2 m1", "L2 m2", "L2 m3"], 
            "3line": ["L3 m1", "L3 m2", "L3 m3"],
            "4line": ["L4 m1", "L4 m2", "L4 m3"]
        }
        
        # Crear la lista completa de carpetas a monitorear
        for line, mounters in lines_config.items():
            for mounter in mounters:
                folder_path = os.path.join(self.base_path, line, mounter)
                self.folders_to_monitor.append(folder_path)
        
        self.logger.info(f"Monitor configurado para BASE_PATH: {self.base_path}")
        self.logger.info(f"Carpetas a monitorear: {len(self.folders_to_monitor)}")
        for folder in self.folders_to_monitor:
            self.logger.info(f"  - {folder}")
            
        # Verificar/crear tablas
        self.setup_database()
    
    def setup_database(self):
        """Verificar/crear tablas necesarias (copiado de versión funcional)"""
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor()
            
            # Crear tabla principal si no existe (estructura exacta de la versión funcional)
            create_table_query = """
            CREATE TABLE IF NOT EXISTS historial_cambio_material_smt (
                id INT AUTO_INCREMENT PRIMARY KEY,
                scan_date DATE,
                scan_time TIME,
                slot_no VARCHAR(50),
                result VARCHAR(50),
                previous_barcode VARCHAR(100),
                product_date VARCHAR(50),
                part_name VARCHAR(100),
                quantity VARCHAR(50),
                seq VARCHAR(50),
                vendor VARCHAR(100),
                lotno VARCHAR(100),
                barcode VARCHAR(100),
                feeder_base VARCHAR(100),
                extra_column VARCHAR(100),
                archivo_origen VARCHAR(255),
                fecha_procesado TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_scan_date (scan_date),
                INDEX idx_barcode (barcode),
                INDEX idx_feeder_base (feeder_base)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
            
            cursor.execute(create_table_query)
            
            # Crear tabla de control de archivos
            create_control_query = """
            CREATE TABLE IF NOT EXISTS archivos_procesados_smt (
                id INT AUTO_INCREMENT PRIMARY KEY,
                archivo VARCHAR(255) UNIQUE,
                ruta_completa VARCHAR(500),
                fecha_procesado TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                registros_procesados INT DEFAULT 0
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
            
            cursor.execute(create_control_query)
            conn.commit()
            
            self.logger.info("✅ Tablas de base de datos verificadas/creadas exitosamente")
            
        except mysql.connector.Error as err:
            self.logger.error(f"❌ Error configurando base de datos: {err}")
            raise
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    def conectar_bd(self):
        """Crear conexión a la base de datos"""
        try:
            return mysql.connector.connect(**DB_CONFIG)
        except mysql.connector.Error as err:
            self.logger.error(f"Error conectando a la base de datos: {err}")
            return None
    
    def parse_csv_row(self, row):
        """Parse de fila CSV con mapeo corregido (14 columnas) - copiado de versión funcional"""
        if len(row) < 14:
            return None
            
        try:
            return {
                'scan_date': row[0] if row[0] else None,
                'scan_time': row[1] if row[1] else None,
                'slot_no': row[2] if row[2] else None,
                'result': row[3] if row[3] else None,
                'previous_barcode': row[4] if row[4] else None,
                'product_date': row[5] if row[5] else None,
                'part_name': row[6] if row[6] else None,
                'quantity': row[7] if row[7] else None,
                'seq': row[8] if row[8] else None,        # Columna 8
                'vendor': row[9] if row[9] else None,    # Columna 9
                'lotno': row[10] if row[10] else None,   # Columna 10
                'barcode': row[11] if row[11] else None, # Columna 11
                'feeder_base': row[12] if row[12] else None, # Columna 12
                'extra_column': row[13] if len(row) > 13 else None
            }
        except Exception as e:
            self.logger.error(f"Error parseando fila: {e}")
            return None
    
    def archivo_ya_procesado(self, archivo_nombre, cursor):
        """Verificar si un archivo ya fue procesado"""
        cursor.execute(
            "SELECT registros_procesados FROM archivos_procesados_smt WHERE archivo = %s",
            (archivo_nombre,)
        )
        resultado = cursor.fetchone()
        return resultado[0] if resultado else 0
    
    def marcar_archivo_procesado(self, archivo_nombre, ruta_completa, registros_procesados, cursor):
        """Marcar archivo como procesado"""
        cursor.execute("""
            INSERT INTO archivos_procesados_smt (archivo, ruta_completa, registros_procesados)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE
            fecha_procesado = CURRENT_TIMESTAMP,
            registros_procesados = %s
        """, (archivo_nombre, ruta_completa, registros_procesados, registros_procesados))
    
    def process_csv_file(self, filepath):
        """Procesar un archivo CSV específico (copiado de versión funcional)"""
        archivo_nombre = os.path.basename(filepath)
        
        try:
            conn = self.conectar_bd()
            if not conn:
                return False
                
            cursor = conn.cursor()
            
            # Verificar si ya fue procesado
            registros_existentes = self.archivo_ya_procesado(archivo_nombre, cursor)
            
            with open(filepath, 'r', encoding='utf-8') as file:
                csv_reader = csv.reader(file)
                registros_procesados = 0
                
                for row_num, row in enumerate(csv_reader, 1):
                    if row_num <= registros_existentes:
                        continue  # Saltar registros ya procesados
                        
                    parsed_data = self.parse_csv_row(row)
                    if not parsed_data:
                        continue
                        
                    # Insertar en base de datos (TABLA CORRECTA)
                    insert_query = """
                        INSERT INTO historial_cambio_material_smt 
                        (scan_date, scan_time, slot_no, result, previous_barcode, 
                         product_date, part_name, quantity, seq, vendor, lotno, 
                         barcode, feeder_base, extra_column, archivo_origen)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    
                    values = (
                        parsed_data['scan_date'],
                        parsed_data['scan_time'],
                        parsed_data['slot_no'],
                        parsed_data['result'],
                        parsed_data['previous_barcode'],
                        parsed_data['product_date'],
                        parsed_data['part_name'],
                        parsed_data['quantity'],
                        parsed_data['seq'],
                        parsed_data['vendor'],
                        parsed_data['lotno'],
                        parsed_data['barcode'],
                        parsed_data['feeder_base'],
                        parsed_data['extra_column'],
                        archivo_nombre
                    )
                    
                    cursor.execute(insert_query, values)
                    registros_procesados += 1
                    
                # Marcar archivo como procesado
                total_registros = registros_existentes + registros_procesados
                self.marcar_archivo_procesado(archivo_nombre, filepath, total_registros, cursor)
                
                conn.commit()
                
                if registros_procesados > 0:
                    self.logger.info(f"✅ Archivo procesado exitosamente: {archivo_nombre} ({registros_procesados} registros)")
                else:
                    self.logger.debug(f"Archivo {archivo_nombre} ya procesado anteriormente ({total_registros} registros)")
                    
                return True
                
        except Exception as e:
            self.logger.error(f"❌ Error procesando archivo {filepath}: {e}")
            return False
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    def scan_folders(self):
        """Escanear todas las carpetas en busca de archivos CSV"""
        archivos_encontrados = []
        
        for folder in self.folders_to_monitor:
            if os.path.exists(folder):
                csv_files = glob.glob(os.path.join(folder, "*.csv"))
                archivos_encontrados.extend(csv_files)
            else:
                self.logger.warning(f"Carpeta no encontrada: {folder}")
                
        return sorted(archivos_encontrados)
    
    def monitor_folders(self):
        """Función principal de monitoreo"""
        self.logger.info("🚀 Iniciando monitoreo de carpetas...")
        
        # Verificar carpetas al inicio
        if not any(os.path.exists(folder) for folder in self.folders_to_monitor):
            self.logger.error("❌ No se pueden monitorear carpetas: ninguna carpeta existe")
            return
        
        self.running = True
        self.logger.info("✅ Monitor iniciado correctamente")
        
        # Procesar archivos existentes
        self.logger.info("Procesando archivos existentes...")
        archivos = self.scan_folders()
        
        for archivo in archivos:
            if not self.running:
                break
            self.process_csv_file(archivo)
        
        # Monitoreo continuo
        self.logger.info("Iniciando monitoreo continuo...")
        while self.running:
            try:
                archivos = self.scan_folders()
                for archivo in archivos:
                    if not self.running:
                        break
                    self.process_csv_file(archivo)
                    
                time.sleep(30)  # Verificar cada 30 segundos
                
            except Exception as e:
                self.logger.error(f"❌ Error en ciclo de monitoreo: {e}")
                time.sleep(60)  # Esperar más tiempo si hay error
        
        self.logger.info("🛑 Monitoreo detenido")
    
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
        self.running = False


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
