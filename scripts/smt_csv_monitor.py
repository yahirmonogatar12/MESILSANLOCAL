#!/usr/bin/env python3
"""
Script de monitoreo en tiempo real para archivos CSV de SMT
Detecta automáticamente nuevos archivos CSV y los sube a MySQL
"""

import os
import sys
import time
import logging
import threading
from pathlib import Path
from datetime import datetime
import mysql.connector
from mysql.connector import Error
import csv
import re
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import hashlib

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('smt_csv_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SMTDatabaseManager:
    """Maneja todas las operaciones de base de datos"""
    
    def __init__(self, db_config):
        self.db_config = db_config
        self.init_database()
    
    def get_connection(self):
        """Obtiene conexión a la base de datos"""
        try:
            return mysql.connector.connect(**self.db_config)
        except Error as e:
            logger.error(f"Error conectando a MySQL: {e}")
            raise
    
    def init_database(self):
        """Inicializa las tablas si no existen"""
        connection = None
        cursor = None
        try:
            connection = self.get_connection()
            cursor = connection.cursor()
            
            # Crear tabla principal
            create_table_query = """
            CREATE TABLE IF NOT EXISTS historial_cambio_material_smt (
                id INT AUTO_INCREMENT PRIMARY KEY,
                scan_date DATE NOT NULL,
                scan_time TIME NOT NULL,
                slot_no VARCHAR(50),
                result VARCHAR(10),
                part_name VARCHAR(100),
                quantity INT,
                vendor VARCHAR(100),
                lot_no VARCHAR(100),
                barcode VARCHAR(200),
                feeder_base VARCHAR(100),
                previous_barcode VARCHAR(200),
                source_file VARCHAR(255),
                line_number INT NOT NULL,
                mounter_number INT NOT NULL,
                file_hash VARCHAR(64),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_scan_date (scan_date),
                INDEX idx_part_name (part_name),
                INDEX idx_result (result),
                INDEX idx_line_mounter (line_number, mounter_number),
                INDEX idx_barcode (barcode),
                INDEX idx_file_hash (file_hash)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """
            
            cursor.execute(create_table_query)
            
            # Crear tabla de control de archivos
            create_control_table = """
            CREATE TABLE IF NOT EXISTS smt_files_processed (
                id INT AUTO_INCREMENT PRIMARY KEY,
                filename VARCHAR(255) UNIQUE NOT NULL,
                filepath VARCHAR(500),
                line_number INT NOT NULL,
                mounter_number INT NOT NULL,
                file_hash VARCHAR(64),
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                records_count INT DEFAULT 0,
                file_size BIGINT,
                INDEX idx_filename (filename),
                INDEX idx_file_hash (file_hash)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """
            
            cursor.execute(create_control_table)
            connection.commit()
            logger.info("Tablas de base de datos verificadas/creadas exitosamente")
            
        except Error as e:
            logger.error(f"Error inicializando base de datos: {e}")
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    def calculate_file_hash(self, filepath):
        """Calcula hash MD5 del archivo para detectar cambios"""
        hash_md5 = hashlib.md5()
        try:
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            logger.error(f"Error calculando hash de {filepath}: {e}")
            return None
    
    def is_file_processed(self, filepath):
        """Verifica si el archivo ya fue procesado"""
        connection = None
        cursor = None
        try:
            connection = self.get_connection()
            cursor = connection.cursor()
            
            filename = os.path.basename(filepath)
            file_hash = self.calculate_file_hash(filepath)
            
            if not file_hash:
                return False
            
            # Verificar por hash (más seguro que solo nombre)
            query = """
                SELECT id, records_count FROM smt_files_processed 
                WHERE filename = %s OR file_hash = %s
            """
            cursor.execute(query, (filename, file_hash))
            result = cursor.fetchone()
            
            if result:
                logger.info(f"Archivo {filename} ya procesado anteriormente ({result[1]} registros)")
                return True
            
            return False
            
        except Error as e:
            logger.error(f"Error verificando archivo procesado: {e}")
            return False
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    def mark_file_as_processed(self, filepath, line_number, mounter_number, records_count):
        """Marca archivo como procesado"""
        connection = None
        cursor = None
        try:
            connection = self.get_connection()
            cursor = connection.cursor()
            
            filename = os.path.basename(filepath)
            file_hash = self.calculate_file_hash(filepath)
            file_size = os.path.getsize(filepath)
            
            query = """
                INSERT INTO smt_files_processed 
                (filename, filepath, line_number, mounter_number, file_hash, records_count, file_size)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                records_count = VALUES(records_count),
                file_size = VALUES(file_size),
                processed_at = CURRENT_TIMESTAMP
            """
            
            cursor.execute(query, (filename, filepath, line_number, 
                                 mounter_number, file_hash, records_count, file_size))
            connection.commit()
            
            logger.info(f"Archivo {filename} marcado como procesado")
            
        except Error as e:
            logger.error(f"Error marcando archivo como procesado: {e}")
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    def process_csv_file(self, filepath, line_number, mounter_number):
        """Procesa archivo CSV y lo inserta en MySQL"""
        if self.is_file_processed(filepath):
            return True, 0
        
        connection = None
        cursor = None
        records_inserted = 0
        
        try:
            connection = self.get_connection()
            cursor = connection.cursor()
            
            filename = os.path.basename(filepath)
            logger.info(f"Procesando archivo: {filename}")
            
            insert_query = """
                INSERT INTO historial_cambio_material_smt
                (scan_date, scan_time, slot_no, result, part_name, quantity,
                 vendor, lot_no, l_position, m_position, seq, barcode, feeder_base, 
                 previous_barcode, source_file, line_number, mounter_number, file_hash)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            batch_data = []
            file_hash = self.calculate_file_hash(filepath)
            
            # Leer archivo CSV
            with open(filepath, 'r', encoding='utf-8-sig', errors='ignore') as file:
                # Detectar delimiter de forma más robusta
                sample = file.read(2048)
                file.seek(0)
                
                # Intentar detectar delimiter probando varios
                delimiter = ','
                possible_delimiters = [',', ';', '\t', '|', ' ']
                
                try:
                    sniffer = csv.Sniffer()
                    delimiter = sniffer.sniff(sample, delimiters=',;\t| ').delimiter
                except:
                    # Si falla la detección automática, probar manualmente
                    for test_delim in possible_delimiters:
                        if test_delim in sample:
                            # Contar cuántas veces aparece en la primera línea
                            first_line = sample.split('\n')[0]
                            if first_line.count(test_delim) > 0:
                                delimiter = test_delim
                                break
                
                logger.debug(f"Usando delimitador: '{delimiter}' para {filename}")
                csv_reader = csv.reader(file, delimiter=delimiter)
                
                # Saltar encabezados si existen
                first_row = next(csv_reader, None)
                if first_row and any(header.lower() in ['date', 'time', 'scan', 'result'] 
                                   for header in first_row):
                    pass  # Es encabezado, ya lo saltamos
                else:
                    # No es encabezado, procesarlo
                    file.seek(0)
                    csv_reader = csv.reader(file, delimiter=delimiter)
                
                for row_num, row in enumerate(csv_reader, 1):
                    if len(row) < 4:  # Filtrar filas vacías/incompletas
                        continue
                    
                    try:
                        parsed_data = self.parse_csv_row(row, filename, file_hash, 
                                                       line_number, mounter_number)
                        if parsed_data:
                            batch_data.append(parsed_data)
                            
                            # Insertar en lotes de 500
                            if len(batch_data) >= 500:
                                cursor.executemany(insert_query, batch_data)
                                records_inserted += len(batch_data)
                                batch_data = []
                                logger.info(f"Insertados {records_inserted} registros...")
                                
                    except Exception as e:
                        logger.warning(f"Error en fila {row_num}: {e}")
                        continue
                
                # Insertar registros restantes
                if batch_data:
                    cursor.executemany(insert_query, batch_data)
                    records_inserted += len(batch_data)
            
            connection.commit()
            
            # Marcar archivo como procesado
            self.mark_file_as_processed(filepath, line_number, mounter_number, records_inserted)
            
            logger.info(f"Archivo procesado exitosamente: {filename} ({records_inserted} registros)")
            return True, records_inserted
            
        except Exception as e:
            logger.error(f"Error procesando {filepath}: {e}")
            if connection:
                connection.rollback()
            return False, 0
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    def parse_csv_row(self, row, filename, file_hash, line_number, mounter_number):
        """Parsea una fila del CSV"""
        try:
            # Estructura CSV REAL de 14 columnas basada en archivo 20250804.csv:
            # 0=ScanDate, 1=ScanTime, 2=SlotNo, 3=Result, 4=PreviousBarcode, 5=ProductDate,
            # 6=PartName, 7=Quantity, 8=SEQ, 9=Vendor, 10=LOTNO, 11=Barcode, 12=FeederBase, 13=Extra
            scan_date = self.parse_date(row[0]) if len(row) > 0 else datetime.now().date()
            scan_time = self.parse_time(row[1]) if len(row) > 1 else datetime.now().time()
            slot_no = row[2] if len(row) > 2 else ''
            result = row[3] if len(row) > 3 else ''
            previous_barcode = row[4] if len(row) > 4 else ''
            # product_date = row[5] - no usado en esta tabla
            part_name = row[6] if len(row) > 6 else ''
            quantity = self.parse_int(row[7]) if len(row) > 7 else 0
            l_position = ''  # No disponible en estructura real
            m_position = ''  # No disponible en estructura real  
            seq = row[8] if len(row) > 8 else ''  # CORREGIDO: de columna 10 a 8
            vendor = row[9] if len(row) > 9 else ''  # CORREGIDO: de columna 11 a 9
            lot_no = row[10] if len(row) > 10 else ''  # CORREGIDO: de columna 12 a 10
            barcode = row[11] if len(row) > 11 else ''  # CORREGIDO: de columna 13 a 11
            feeder_base = row[12] if len(row) > 12 else ''  # CORREGIDO: de columna 14 a 12
            
            return (scan_date, scan_time, slot_no, result, part_name, quantity,
                   vendor, lot_no, l_position, m_position, seq, barcode, feeder_base, 
                   previous_barcode, filename, line_number, mounter_number, file_hash)
                   
        except Exception as e:
            logger.error(f"Error parseando fila: {e}")
            return None
    
    def parse_date(self, date_str):
        """Parsea fecha con múltiples formatos incluyendo formato compacto"""
        date_formats = [
            '%Y%m%d',      # 20250725 (formato SMT compacto)
            '%Y-%m-%d', 
            '%Y/%m/%d', 
            '%d/%m/%Y', 
            '%m/%d/%Y', 
            '%d-%m-%Y'
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except:
                continue
        
        # Si no puede parsear, usar fecha actual
        logger.warning(f"No se pudo parsear fecha: {date_str}")
        return datetime.now().date()
    
    def parse_time(self, time_str):
        """Parsea hora con múltiples formatos incluyendo formato compacto"""
        time_formats = [
            '%H%M%S',      # 012344 (formato SMT compacto)
            '%H:%M:%S', 
            '%H:%M', 
            '%I:%M:%S %p', 
            '%I:%M %p'
        ]
        
        for fmt in time_formats:
            try:
                return datetime.strptime(time_str.strip(), fmt).time()
            except:
                continue
        
        # Si no puede parsear, usar hora actual
        logger.warning(f"No se pudo parsear hora: {time_str}")
        return datetime.now().time()
    
    def parse_int(self, int_str):
        """Parsea entero de forma segura"""
        try:
            return int(float(int_str.strip()))
        except:
            return 0

class SMTFileWatcher(FileSystemEventHandler):
    """Observador de archivos CSV"""
    
    def __init__(self, db_manager, watch_config):
        self.db_manager = db_manager
        self.watch_config = watch_config
        self.processing_files = set()  # Para evitar procesamiento múltiple
    
    def on_created(self, event):
        """Archivo creado"""
        if not event.is_directory and event.src_path.endswith('.csv'):
            logger.info(f"Nuevo archivo detectado: {event.src_path}")
            self.process_file_async(event.src_path)
    
    def on_modified(self, event):
        """Archivo modificado"""
        if not event.is_directory and event.src_path.endswith('.csv'):
            # Esperar para asegurar que el archivo esté completo
            threading.Timer(2.0, lambda: self.process_file_async(event.src_path)).start()
    
    def process_file_async(self, filepath):
        """Procesa archivo en hilo separado"""
        if filepath in self.processing_files:
            return
        
        self.processing_files.add(filepath)
        
        try:
            # Esperar a que el archivo esté disponible
            self.wait_for_file_ready(filepath)
            
            # Extraer línea y mounter
            line_number, mounter_number = self.extract_line_mounter(filepath)
            
            # Procesar archivo
            success, records = self.db_manager.process_csv_file(
                filepath, line_number, mounter_number
            )
            
            if success:
                logger.info(f"Archivo procesado: {os.path.basename(filepath)} ({records} registros)")
            else:
                logger.error(f"Error procesando: {os.path.basename(filepath)}")
                
        except Exception as e:
            logger.error(f"Error en procesamiento async: {e}")
        finally:
            self.processing_files.discard(filepath)
    
    def wait_for_file_ready(self, filepath, timeout=30):
        """Espera a que el archivo esté listo para leer"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # Intentar abrir el archivo en modo exclusivo
                with open(filepath, 'r+b') as f:
                    pass
                return True
            except (IOError, OSError):
                time.sleep(0.5)
        
        logger.warning(f"Timeout esperando archivo listo: {filepath}")
        return False
    
    def extract_line_mounter(self, filepath):
        """Extrae línea y mounter del path"""
        path_str = str(filepath).lower()
        
        # Buscar patrones en el path
        line_match = re.search(r'(\d+)line|line(\d+)|l(\d+)', path_str)
        mounter_match = re.search(r'm(\d+)|mounter(\d+)', path_str)
        
        line_number = 1
        mounter_number = 1
        
        if line_match:
            line_number = int(next(g for g in line_match.groups() if g))
        
        if mounter_match:
            mounter_number = int(next(g for g in mounter_match.groups() if g))
        
        logger.debug(f"Extraído del path {filepath}: Línea={line_number}, Mounter={mounter_number}")
        return line_number, mounter_number

def main():
    """Función principal"""
    logger.info("Iniciando SMT CSV Monitor...")
    
    # Importar configuración
    try:
        from config import DATABASE, WATCH_FOLDERS
        db_config = DATABASE
        watch_folders = WATCH_FOLDERS
    except ImportError:
        logger.error("No se pudo importar config.py. Usando configuración por defecto.")
        # Configuración por defecto
        db_config = {
            'host': 'localhost',
            'user': 'root',
            'password': '',
            'database': 'isemm_mes'
        }
        watch_folders = []
    
    try:
        # Inicializar manejador de base de datos
        db_manager = SMTDatabaseManager(db_config)
        
        # Crear observador de archivos
        watch_config = {'folders': watch_folders}
        event_handler = SMTFileWatcher(db_manager, watch_config)
        observer = Observer()
        
        # Agregar carpetas a observar
        for folder in watch_folders:
            if os.path.exists(folder):
                observer.schedule(event_handler, folder, recursive=True)
                logger.info(f"Monitoreando: {folder}")
            else:
                logger.warning(f"Carpeta no encontrada: {folder}")
        
        # Procesar archivos existentes (opcional)
        logger.info("Procesando archivos existentes...")
        for folder in watch_folders:
            if os.path.exists(folder):
                for root, dirs, files in os.walk(folder):
                    for file in files:
                        if file.endswith('.csv'):
                            filepath = os.path.join(root, file)
                            event_handler.process_file_async(filepath)
        
        # Iniciar observador
        observer.start()
        logger.info("Monitor iniciado. Presiona Ctrl+C para detener.")
        
        # Mantener el script corriendo
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Deteniendo monitor...")
            observer.stop()
        
        observer.join()
        logger.info("Monitor detenido correctamente.")
        
    except Exception as e:
        logger.error(f"Error fatal: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
