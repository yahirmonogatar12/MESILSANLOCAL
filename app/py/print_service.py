"""
Servicio de Impresión LOCAL para Zebra ZT230
IMPORTANTE: Este servicio debe ejecutarse en CADA máquina cliente
Implementa impresión directa via Win32 API sin diálogos ni confirmaciones
"""
from flask import Flask, request, abort, jsonify
from flask_cors import CORS
import win32print
import win32con
import os
import tempfile
import json
import logging
import socket
import os
from datetime import datetime

# Obtener el directorio donde está el script
script_dir = os.path.dirname(os.path.abspath(__file__))
log_file = os.path.join(script_dir, 'print_service.log')

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

app = Flask(__name__)

# Configurar CORS para permitir requests desde cualquier origen
CORS(app, origins=['*'], methods=['GET', 'POST', 'OPTIONS'], 
     allow_headers=['Content-Type', 'Authorization'])

# También agregar cabeceras CORS manualmente para mayor compatibilidad
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
    return response

# Configuración de impresoras (puedes ajustar estos nombres)
PRINTER_CONFIGS = {
    'zebra_usb_300dpi': r"ZDesigner ZT230-300dpi ZPL",
    'zebra_usb_200dpi': r"ZDesigner ZT230-200dpi ZPL",
    'zebra_usb_300dpi_usb002': r"ZDesigner ZT230-300dpi ZPL USB002",
    'zebra_usb_200dpi_usb002': r"ZDesigner ZT230-200dpi ZPL USB002",
    'zebra_usb_alt1': r"Zebra_USB", 
    'zebra_usb_alt2': r"ZT230",
    'zebra_usb_alt3': r"ZDesigner ZT230",
    'zebra_usb_alt4': r"ZT230-300dpi",
    'zebra_usb_alt5': r"ZT230-200dpi"
}

def get_local_machine_info():
    """Obtiene información de la máquina local"""
    try:
        hostname = socket.gethostname()
        
        # Obtener IP local
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        
        return {
            'hostname': hostname,
            'local_ip': local_ip
        }
    except Exception as e:
        logging.warning(f"Error obteniendo info de máquina: {e}")
        return {
            'hostname': 'unknown',
            'local_ip': 'localhost'
        }

def get_available_printers():
    """Obtiene lista de impresoras disponibles en el sistema"""
    try:
        printers = []
        for printer in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL):
            printers.append(printer[2])  # Nombre de la impresora
        return printers
    except Exception as e:
        logging.error(f"Error obteniendo impresoras: {e}")
        return []

def find_zebra_printer():
    """Busca automáticamente la impresora Zebra ZT230 (200dpi o 300dpi)"""
    available_printers = get_available_printers()
    logging.info(f"Impresoras disponibles: {available_printers}")
    
    # Buscar por orden de prioridad - configuraciones exactas
    for config_name, printer_name in PRINTER_CONFIGS.items():
        if printer_name in available_printers:
            logging.info(f"Impresora encontrada: {printer_name} ({config_name})")
            return printer_name
    
    # Buscar por patrones específicos de ZT230 con cualquier DPI
    zt230_patterns = [
        'ZDesigner ZT230-300dpi ZPL',
        'ZDesigner ZT230-200dpi ZPL', 
        'ZDesigner ZT230-300dpi',
        'ZDesigner ZT230-200dpi',
        'ZT230-300dpi ZPL',
        'ZT230-200dpi ZPL'
    ]
    
    for printer in available_printers:
        for pattern in zt230_patterns:
            if pattern in printer:
                logging.info(f"Impresora ZT230 encontrada por patrón: {printer}")
                return printer
    
    # Buscar por palabras clave si no se encuentra exacta
    zebra_keywords = ['zebra', 'zt230', 'zpl', 'zdesigner']
    for printer in available_printers:
        printer_lower = printer.lower()
        for keyword in zebra_keywords:
            if keyword in printer_lower:
                # Verificar que sea realmente una ZT230
                if 'zt230' in printer_lower or ('zdesigner' in printer_lower and 'zpl' in printer_lower):
                    logging.info(f"Impresora Zebra encontrada por keyword: {printer}")
                    return printer
    
    logging.warning("No se encontró impresora Zebra ZT230 (ni 200dpi ni 300dpi)")
    return None

def print_raw(data: bytes, printer_name: str = None):
    """Envía datos RAW a la impresora Windows mediante Win32 API."""
    if not printer_name:
        printer_name = find_zebra_printer()
        
    if not printer_name:
        raise Exception("No se encontró impresora Zebra ZT230 disponible")
    
    try:
        logging.info(f"Iniciando impresión en: {printer_name}")
        logging.info(f"Datos a imprimir: {len(data)} bytes")
        
        hPrinter = win32print.OpenPrinter(printer_name)
        try:
            # DOC_INFO_1: (pDocName, pOutputFile, pDatatype)
            doc_info = (f"ILSAN-Etiqueta-{datetime.now().strftime('%H%M%S')}", None, "RAW")
            job_id = win32print.StartDocPrinter(hPrinter, 1, doc_info)
            
            logging.info(f"Job ID creado: {job_id}")
            
            win32print.StartPagePrinter(hPrinter)
            bytes_written = win32print.WritePrinter(hPrinter, data)
            win32print.EndPagePrinter(hPrinter)
            win32print.EndDocPrinter(hPrinter)
            
            logging.info(f"Impresión completada exitosamente. Bytes escritos: {bytes_written}")
            return True, bytes_written
            
        finally:
            win32print.ClosePrinter(hPrinter)
            
    except Exception as e:
        error_msg = f"Error en impresión: {str(e)}"
        logging.error(error_msg)
        raise Exception(error_msg)

@app.route("/", methods=["GET"])
def status():
    """Endpoint de estado del servicio"""
    available_printers = get_available_printers()
    zebra_printer = find_zebra_printer()
    machine_info = get_local_machine_info()
    
    return jsonify({
        "service": "ILSAN Print Service LOCAL",
        "status": "active",
        "timestamp": datetime.now().isoformat(),
        "machine": machine_info['hostname'],
        "local_ip": machine_info['local_ip'],
        "zebra_printer": zebra_printer,
        "available_printers": available_printers,
        "printer_configs": PRINTER_CONFIGS,
        "note": "Este servicio imprime LOCALMENTE en esta máquina"
    })

@app.route("/print", methods=["POST"])
def api_print():
    """
    Endpoint para impresión directa
    Espera un JSON:
    {
      "zpl": "<^XA^FO50,50^BCN,100,Y,N,N^FD12345678^FS^XZ>",
      "codigo": "M2606809020,202507160001",
      "printer": "opcional - nombre específico de impresora"
    }
    """
    try:
        body = request.get_json(force=True, silent=True)
        if not body or "zpl" not in body:
            abort(400, "JSON inválido, se requiere clave 'zpl'")
        
        zpl_str = body["zpl"]
        codigo = body.get("codigo", "sin-codigo")
        printer_name = body.get("printer", None)
        
        if not isinstance(zpl_str, str):
            abort(400, "El campo 'zpl' debe ser un string")
        
        if not zpl_str.strip():
            abort(400, "El comando ZPL no puede estar vacío")
        
        logging.info(f"Solicitud de impresión recibida para código: {codigo}")
        logging.info(f"ZPL command: {zpl_str[:100]}...")  # Log primeros 100 chars
        
        # Convertir string a bytes
        data = zpl_str.encode("utf-8", errors="ignore")
        
        # Imprimir
        success, bytes_written = print_raw(data, printer_name)
        
        if success:
            response = {
                "status": "printed",
                "codigo": codigo,
                "bytes": bytes_written,
                "printer": find_zebra_printer() if not printer_name else printer_name,
                "machine": get_local_machine_info()['hostname'],
                "local_ip": get_local_machine_info()['local_ip'],
                "timestamp": datetime.now().isoformat()
            }
            logging.info(f"Impresión exitosa LOCAL: {response}")
            return jsonify(response)
        else:
            raise Exception("La impresión no se completó correctamente")
            
    except Exception as e:
        error_msg = str(e)
        logging.error(f"Error en api_print: {error_msg}")
        
        return jsonify({
            "status": "error",
            "error": error_msg,
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route("/test", methods=["GET", "POST"])
def test_print():
    """Endpoint de prueba para verificar que la impresión funciona"""
    try:
        # ZPL de prueba simple
        test_zpl = """^XA
^FO50,50^ADN,36,20^FDTEST PRINT^FS
^FO50,100^ADN,18,10^FD{timestamp}^FS
^FO50,130^ADN,14,8^FDILSAN ELECTRONICS^FS
^FO50,160^BQN,2,4^FDMA,TEST-{time}^FS
^XZ""".format(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            time=datetime.now().strftime("%H%M%S")
        )
        
        data = test_zpl.encode("utf-8")
        success, bytes_written = print_raw(data)
        
        if success:
            return jsonify({
                "status": "test_printed",
                "message": "Etiqueta de prueba enviada exitosamente",
                "bytes": bytes_written,
                "printer": find_zebra_printer(),
                "zpl_used": test_zpl,
                "timestamp": datetime.now().isoformat()
            })
        else:
            raise Exception("Test de impresión falló")
            
    except Exception as e:
        logging.error(f"Error en test_print: {e}")
        return jsonify({
            "status": "test_error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route("/printers", methods=["GET"])
def list_printers():
    """Lista todas las impresoras disponibles"""
    try:
        available_printers = get_available_printers()
        zebra_printer = find_zebra_printer()
        
        return jsonify({
            "available_printers": available_printers,
            "zebra_printer_detected": zebra_printer,
            "printer_configs": PRINTER_CONFIGS,
            "total_printers": len(available_printers)
        })
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

if __name__ == "__main__":
    machine_info = get_local_machine_info()
    
    print("\n" + "="*60)
    print("🖨️  ILSAN Print Service LOCAL - Zebra ZT230")
    print("="*60)
    print(f"🕒 Iniciado: {datetime.now()}")
    print(f"💻 Máquina: {machine_info['hostname']}")
    print(f"🌐 IP Local: {machine_info['local_ip']}")
    print("📋 IMPORTANTE: Este servicio imprime LOCALMENTE en esta máquina")
    
    # Verificar impresoras al inicio
    available_printers = get_available_printers()
    zebra_printer = find_zebra_printer()
    
    print(f"🖨️  Impresoras disponibles: {len(available_printers)}")
    for i, printer in enumerate(available_printers, 1):
        marker = "✅" if printer == zebra_printer else "  "
        print(f"   {marker} {i}. {printer}")
    
    if zebra_printer:
        print(f"🎯 Impresora Zebra detectada: {zebra_printer}")
    else:
        print("⚠️  No se detectó impresora Zebra ZT230")
        print("💡 Verifique que la impresora esté conectada y configurada")
    
    print("="*60)
    print("🌐 Endpoints disponibles:")
    print("   GET  /         - Estado del servicio")
    print("   GET  /printers - Lista de impresoras")
    print("   GET  /test     - Prueba de impresión")
    print("   POST /print    - Impresión de ZPL")
    print("="*60)
    print("🚀 Ejecutándose en:")
    print("   http://localhost:5003")
    print("   http://127.0.0.1:5003") 
    print(f"   http://{machine_info['local_ip']}:5003")
    print("="*60)
    print("⚠️  CADA MÁQUINA DEBE EJECUTAR SU PROPIO SERVICIO")
    print("✅ Este servicio imprime en la impresora LOCAL de esta máquina")
    print("="*60)
    
    # Ejecutar el servicio Flask
    app.run(
        host="0.0.0.0",  # Permite conexiones externas
        port=5003,       # Puerto diferente para servicio local
        debug=False,     # Cambiar a True para desarrollo
        threaded=True    # Permite múltiples requests simultáneos
    )
