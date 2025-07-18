"""
Servicio de Windows para el Servicio de Impresión LOCAL Zebra ZT230
Este archivo convierte el servicio Flask en un servicio de Windows que se ejecuta automáticamente
"""
import win32serviceutil
import win32service
import win32event
import win32api
import servicemanager
import socket
import sys
import os
import time
import threading
import subprocess
import logging
from pathlib import Path

class PrintService(win32serviceutil.ServiceFramework):
    _svc_name_ = "ZebraPrintService"
    _svc_display_name_ = "Servicio de Impresión Local Zebra"
    _svc_description_ = "Servicio de impresión local para impresoras Zebra ZT230. Permite imprimir códigos QR y etiquetas desde aplicaciones web."
    
    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.is_alive = True
        self.process = None
        
        # Configurar directorio del servicio
        self.service_dir = os.path.dirname(os.path.abspath(__file__))
        self.log_file = os.path.join(self.service_dir, 'service_windows.log')
        
        # Configurar logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file),
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def SvcStop(self):
        self.logger.info("Deteniendo servicio de impresión...")
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self.is_alive = False
        
        # Terminar el proceso Flask si está ejecutándose
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                self.process.wait(timeout=10)
                self.logger.info("Proceso Flask terminado correctamente")
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.logger.warning("Proceso Flask forzado a terminar")
            except Exception as e:
                self.logger.error(f"Error al terminar proceso Flask: {e}")
        
        win32event.SetEvent(self.hWaitStop)
        self.logger.info("Servicio de impresión detenido")
        
    def SvcDoRun(self):
        self.logger.info("Iniciando servicio de impresión...")
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        
        try:
            self.main()
        except Exception as e:
            self.logger.error(f"Error en el servicio: {e}")
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_ERROR_TYPE,
                servicemanager.PYS_SERVICE_STOPPED,
                (self._svc_name_, str(e))
            )
    
    def main(self):
        """Función principal del servicio"""
        self.logger.info("Servicio de impresión iniciado correctamente")
        
        while self.is_alive:
            try:
                # Verificar si el proceso Flask sigue ejecutándose
                if self.process is None or self.process.poll() is not None:
                    self.start_flask_service()
                
                # Esperar 30 segundos antes de la siguiente verificación
                if win32event.WaitForSingleObject(self.hWaitStop, 30000) == win32event.WAIT_OBJECT_0:
                    break
                    
            except Exception as e:
                self.logger.error(f"Error en el bucle principal: {e}")
                time.sleep(30)  # Esperar antes de reintentar
    
    def start_flask_service(self):
        """Iniciar el servicio Flask"""
        try:
            python_exe = sys.executable
            script_path = os.path.join(self.service_dir, 'print_service.py')
            
            self.logger.info(f"Iniciando servicio Flask: {python_exe} {script_path}")
            
            # Asegurar que el directorio de trabajo sea correcto
            os.chdir(self.service_dir)
            
            # Crear proceso Flask sin ventana visible
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = 0  # SW_HIDE
            
            self.process = subprocess.Popen(
                [python_exe, script_path],
                cwd=self.service_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                startupinfo=si
            )
            
            self.logger.info(f"Servicio Flask iniciado con PID: {self.process.pid}")
            
        except Exception as e:
            self.logger.error(f"Error al iniciar servicio Flask: {e}")
            self.process = None

if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(PrintService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(PrintService)