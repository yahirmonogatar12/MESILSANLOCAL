"""
Servicio Flask integrado para Windows - Solución al problema de rutas de red
Este archivo combina el servicio Windows y Flask en uno solo
"""
import win32serviceutil
import win32service
import win32event
import servicemanager
import sys
import os
import time
import logging
import tempfile

# Importar Flask y dependencias directamente
try:
    from flask import Flask, request, jsonify
    from flask_cors import CORS
    import win32print
    import win32con
    import socket
    from datetime import datetime
except ImportError as e:
    # Si falta alguna dependencia, crear log de error
    with open('C:\\temp\\zebra_service_error.log', 'w') as f:
        f.write(f"Error importando dependencias: {e}\n")
        f.write("Ejecute: pip install flask flask-cors pywin32\n")

class ZebraFlaskService(win32serviceutil.ServiceFramework):
    _svc_name_ = "ZebraFlaskIntegrado"
    _svc_display_name_ = "Servicio Zebra Flask Integrado"
    _svc_description_ = "Servicio integrado de impresión Zebra con Flask"
    
    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.is_alive = True
        
        # Configurar directorio de logs en ubicación local
        self.log_dir = 'C:\\ZebraService'
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
            
        self.log_file = os.path.join(self.log_dir, 'zebra_flask_service.log')
        
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
        self.logger.info("Deteniendo servicio...")
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self.is_alive = False
        win32event.SetEvent(self.hWaitStop)
        
    def SvcDoRun(self):
        self.logger.info("Iniciando servicio Flask integrado...")
        
        try:
            self.run_flask_service()
        except Exception as e:
            self.logger.error(f"Error en servicio: {e}")
            
    def run_flask_service(self):
        """Ejecutar Flask directamente en el servicio"""
        try:
            # Crear aplicación Flask
            app = Flask(__name__)
            CORS(app)
            
            self.logger.info("Flask app creada")
            
            # Configuración de impresoras
            PRINTER_CONFIGS = {
                'zebra_usb': "ZDesigner ZT230-300dpi ZPL",
                'zebra_usb_alt1': "Zebra_USB", 
                'zebra_usb_alt2': "ZT230",
            }
            
            def get_machine_info():
                try:
                    hostname = socket.gethostname()
                    local_ip = socket.gethostbyname(hostname)
                    return hostname, local_ip
                except:
                    return "Unknown", "0.0.0.0"
            
            def find_zebra_printer():
                """Buscar impresora Zebra disponible"""
                try:
                    printers = [printer[2] for printer in win32print.EnumPrinters(2)]
                    self.logger.info(f"Impresoras disponibles: {printers}")
                    
                    for config_name, printer_name in PRINTER_CONFIGS.items():
                        if any(printer_name.lower() in p.lower() for p in printers):
                            found_printer = next(p for p in printers if printer_name.lower() in p.lower())
                            self.logger.info(f"Impresora encontrada: {found_printer} ({config_name})")
                            return found_printer
                    
                    return None
                except Exception as e:
                    self.logger.error(f"Error buscando impresora: {e}")
                    return None
            
            @app.route('/', methods=['GET'])
            def status():
                machine, ip = get_machine_info()
                return jsonify({
                    'status': 'running',
                    'service': 'Zebra Print Service Flask Integrado',
                    'machine': machine,
                    'ip': ip,
                    'timestamp': datetime.now().isoformat()
                })
            
            @app.route('/print', methods=['POST'])
            def print_label():
                try:
                    data = request.get_json()
                    zpl_content = data.get('zpl_content', '')
                    
                    if not zpl_content:
                        return jsonify({'error': 'No ZPL content provided'}), 400
                    
                    printer = find_zebra_printer()
                    if not printer:
                        return jsonify({'error': 'No Zebra printer found'}), 404
                    
                    # Imprimir
                    hPrinter = win32print.OpenPrinter(printer)
                    try:
                        hJob = win32print.StartDocPrinter(hPrinter, 1, ("ZPL Label", None, "RAW"))
                        win32print.StartPagePrinter(hPrinter)
                        win32print.WritePrinter(hPrinter, zpl_content.encode('utf-8'))
                        win32print.EndPagePrinter(hPrinter)
                        win32print.EndDocPrinter(hPrinter)
                        
                        machine, ip = get_machine_info()
                        result = {
                            'status': 'printed',
                            'bytes': len(zpl_content.encode('utf-8')),
                            'printer': printer,
                            'machine': machine,
                            'local_ip': ip,
                            'timestamp': datetime.now().isoformat()
                        }
                        
                        self.logger.info(f"Impresión exitosa: {result}")
                        return jsonify(result)
                        
                    finally:
                        win32print.ClosePrinter(hPrinter)
                        
                except Exception as e:
                    self.logger.error(f"Error imprimiendo: {e}")
                    return jsonify({'error': str(e)}), 500
            
            @app.route('/printers', methods=['GET'])
            def list_printers():
                try:
                    printers = [printer[2] for printer in win32print.EnumPrinters(2)]
                    return jsonify({'printers': printers})
                except Exception as e:
                    return jsonify({'error': str(e)}), 500
            
            # Configurar Flask para ejecutar en el servicio
            self.logger.info("Iniciando servidor Flask en puerto 5003...")
            
            # Ejecutar Flask en modo servicio
            app.run(
                host="0.0.0.0",
                port=5003,
                debug=False,
                threaded=True,
                use_reloader=False  # Importante: No usar reloader en servicio
            )
            
        except Exception as e:
            self.logger.error(f"Error iniciando Flask: {e}")
            
        # Mantener servicio vivo
        while self.is_alive:
            if win32event.WaitForSingleObject(self.hWaitStop, 5000) == win32event.WAIT_OBJECT_0:
                break

if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(ZebraFlaskService)
