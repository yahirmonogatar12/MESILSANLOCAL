#!/usr/bin/env python3
"""
Servicio de monitoreo SMT con estructura de tabla REAL
Basado en smt_monitor_local.py pero corregido para Windows Service
"""

import os
import sys
import time
import hashlib
import logging
import mysql.connector
from datetime import datetime, date
import win32serviceutil
import win32service
import win32event
import servicemanager
import socket

class SMTMonitorService(win32serviceutil.ServiceFramework):
    _svc_name_ = "SMTMonitorService"
    _svc_display_name_ = "SMT CSV Monitor Service"
    _svc_description_ = "Monitorea archivos CSV en carpetas SMT y los procesa"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        socket.setdefaulttimeout(60)
        
        # Configuración de logging
        self.setup_logging()
        
        # Configuración de la base de datos
        self.db_config = {
            'host': 'up-de-fra1-mysql-1.db.run-on-seenode.com',
            'port': 11550,
            'user': 'db_rrpq0erbdujn',
            'password': '5fUNbSRcPP3LN9K2I33Pr0ge',
            'database': 'db_rrpq0erbdujn'
        }
        
        # Carpeta base a monitorear
        self.base_folder = r"C:\LOT CHECK  ALL"
        
        # Archivos procesados (para evitar duplicados)
        self.processed_files = set()

    def setup_logging(self):
        """Configurar el sistema de logging"""
        log_path = os.path.join(os.path.dirname(__file__), 'smt_monitor_service.log')
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_path, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def SvcStop(self):
        """Detener el servicio"""
        self.logger.info("Deteniendo servicio SMT Monitor...")
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)

    def SvcDoRun(self):
        """Ejecutar el servicio"""
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                              servicemanager.PYS_SERVICE_STARTED,
                              (self._svc_name_, ''))
        self.main()

    def conectar_db(self):
        """Conectar a la base de datos"""
        try:
            conn = mysql.connector.connect(**self.db_config)
            self.logger.info("✅ Conexión exitosa a la base de datos")
            return conn
        except Exception as e:
            self.logger.error(f"❌ Error conectando a DB: {e}")
            return None

    def calcular_hash_archivo(self, filepath):
        """Calcular hash SHA-256 del archivo"""
        try:
            with open(filepath, 'rb') as f:
                file_hash = hashlib.sha256()
                for chunk in iter(lambda: f.read(4096), b""):
                    file_hash.update(chunk)
                return file_hash.hexdigest()
        except Exception as e:
            self.logger.error(f"Error calculando hash de {filepath}: {e}")
            return None

    def procesar_archivo_csv(self, filepath):
        """Procesar archivo CSV y guardarlo en la base de datos"""
        try:
            # Verificar si ya fue procesado
            file_hash = self.calcular_hash_archivo(filepath)
            if not file_hash:
                return False
            
            if file_hash in self.processed_files:
                return True  # Ya procesado
            
            # Obtener información del archivo
            dir_name = os.path.basename(os.path.dirname(filepath))
            filename = os.path.basename(filepath)
            
            # Extraer número de mounter del nombre del directorio
            mounter_number = 0
            try:
                # Buscar número en el nombre del directorio
                import re
                match = re.search(r'(\d+)', dir_name)
                if match:
                    mounter_number = int(match.group(1))
            except:
                pass
            
            self.logger.info(f"Procesando: {filepath}")
            
            # Leer archivo CSV
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as file:
                lines = file.readlines()
            
            if len(lines) < 2:  # No hay datos
                return False
            
            # Conectar a la base de datos
            conn = self.conectar_db()
            if not conn:
                return False
            
            cursor = conn.cursor()
            registros_insertados = 0
            
            try:
                # Procesar cada línea (saltando header)
                for line_num, line in enumerate(lines[1:], start=2):
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Dividir por comas pero respetando comillas
                    import csv
                    import io
                    reader = csv.reader(io.StringIO(line))
                    data = next(reader)
                    
                    if len(data) < 10:  # Mínimo de columnas requeridas
                        continue
                    
                    # Mapear datos a la estructura real de la tabla
                    try:
                        # Parsear fecha y hora
                        scan_date_str = data[0] if len(data) > 0 else ''
                        scan_time_str = data[1] if len(data) > 1 else ''
                        
                        # Convertir fecha
                        scan_date = None
                        if scan_date_str:
                            try:
                                scan_date = datetime.strptime(scan_date_str, '%Y/%m/%d').date()
                            except:
                                try:
                                    scan_date = datetime.strptime(scan_date_str, '%m/%d/%Y').date()
                                except:
                                    scan_date = date.today()
                        else:
                            scan_date = date.today()
                        
                        # Convertir hora
                        scan_time = None
                        if scan_time_str:
                            try:
                                scan_time = datetime.strptime(scan_time_str, '%H:%M:%S').time()
                            except:
                                scan_time = datetime.now().time()
                        else:
                            scan_time = datetime.now().time()
                        
                        # Preparar datos para inserción
                        registro = (
                            scan_date,                                    # scan_date
                            scan_time,                                    # scan_time
                            data[2] if len(data) > 2 else '',           # slot_no
                            data[3] if len(data) > 3 else '',           # result
                            data[4] if len(data) > 4 else '',           # part_name
                            int(data[5]) if len(data) > 5 and data[5].isdigit() else 0,  # quantity
                            data[6] if len(data) > 6 else '',           # vendor
                            data[7] if len(data) > 7 else '',           # lot_no
                            data[8] if len(data) > 8 else '',           # l_position
                            data[9] if len(data) > 9 else '',           # m_position
                            data[10] if len(data) > 10 else '',         # seq
                            data[11] if len(data) > 11 else '',         # barcode
                            data[12] if len(data) > 12 else '',         # feeder_base
                            data[13] if len(data) > 13 else '',         # previous_barcode
                            scan_date,                                   # product_date (usar scan_date como default)
                            filepath,                                    # source_file
                            line_num,                                    # line_number
                            mounter_number,                              # mounter_number
                            file_hash                                    # file_hash
                        )
                        
                        # Insertar en la base de datos
                        insert_query = """
                            INSERT INTO historial_cambio_material_smt 
                            (scan_date, scan_time, slot_no, result, part_name, quantity, 
                             vendor, lot_no, l_position, m_position, seq, barcode, 
                             feeder_base, previous_barcode, product_date, source_file, 
                             line_number, mounter_number, file_hash)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """
                        
                        cursor.execute(insert_query, registro)
                        registros_insertados += 1
                        
                    except Exception as e:
                        self.logger.error(f"Error procesando línea {line_num}: {e}")
                        continue
                
                # Confirmar transacción
                conn.commit()
                self.logger.info(f"✅ Archivo procesado: {filename} - {registros_insertados} registros")
                
                # Marcar como procesado
                self.processed_files.add(file_hash)
                
                return True
                
            except Exception as e:
                conn.rollback()
                self.logger.error(f"❌ Error procesando archivo {filepath}: {e}")
                return False
            finally:
                cursor.close()
                conn.close()
                
        except Exception as e:
            self.logger.error(f"❌ Error general procesando {filepath}: {e}")
            return False

    def monitorear_carpetas(self):
        """Monitorear las carpetas en busca de archivos CSV"""
        if not os.path.exists(self.base_folder):
            self.logger.error(f"❌ Carpeta base no existe: {self.base_folder}")
            return
        
        self.logger.info(f"🔍 Monitoreando: {self.base_folder}")
        
        try:
            # Listar subcarpetas
            subcarpetas = [d for d in os.listdir(self.base_folder) 
                          if os.path.isdir(os.path.join(self.base_folder, d))]
            
            self.logger.info(f"📁 Encontradas {len(subcarpetas)} subcarpetas")
            
            for subcarpeta in subcarpetas:
                ruta_subcarpeta = os.path.join(self.base_folder, subcarpeta)
                
                try:
                    # Buscar archivos CSV
                    archivos = [f for f in os.listdir(ruta_subcarpeta) 
                               if f.lower().endswith('.csv')]
                    
                    for archivo in archivos:
                        ruta_archivo = os.path.join(ruta_subcarpeta, archivo)
                        
                        # Verificar si el archivo ha sido modificado recientemente
                        try:
                            stat = os.stat(ruta_archivo)
                            tiempo_modificacion = stat.st_mtime
                            tiempo_actual = time.time()
                            
                            # Solo procesar si fue modificado en las últimas 24 horas
                            if (tiempo_actual - tiempo_modificacion) < (24 * 60 * 60):
                                self.procesar_archivo_csv(ruta_archivo)
                        
                        except Exception as e:
                            self.logger.error(f"Error verificando archivo {ruta_archivo}: {e}")
                
                except Exception as e:
                    self.logger.error(f"Error accediendo a subcarpeta {ruta_subcarpeta}: {e}")
        
        except Exception as e:
            self.logger.error(f"Error monitoreando carpetas: {e}")

    def main(self):
        """Función principal del servicio"""
        self.logger.info("🚀 Iniciando servicio SMT Monitor...")
        
        while True:
            # Verificar si se debe detener el servicio
            if win32event.WaitForSingleObject(self.hWaitStop, 0) == win32event.WAIT_OBJECT_0:
                break
            
            try:
                self.monitorear_carpetas()
                
                # Esperar 30 segundos antes del siguiente ciclo
                if win32event.WaitForSingleObject(self.hWaitStop, 30000) == win32event.WAIT_OBJECT_0:
                    break
                    
            except Exception as e:
                self.logger.error(f"❌ Error en ciclo principal: {e}")
                time.sleep(60)  # Esperar más tiempo en caso de error
        
        self.logger.info("🛑 Servicio SMT Monitor detenido")

if __name__ == '__main__':
    if len(sys.argv) == 1:
        # Ejecutar en modo consola para pruebas
        print("🔧 MODO CONSOLA - SMT Monitor Service")
        print("=" * 50)
        
        service = SMTMonitorService(sys.argv)
        try:
            service.main()
        except KeyboardInterrupt:
            print("\n🛑 Detenido por usuario")
    else:
        # Ejecutar como servicio de Windows
        win32serviceutil.HandleCommandLine(SMTMonitorService)
