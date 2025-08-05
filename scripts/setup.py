"""
Instalador y configurador para SMT CSV Monitor
"""

import subprocess
import sys
import os

def install_requirements():
    """Instala los paquetes Python necesarios"""
    packages = [
        'mysql-connector-python==8.0.33',
        'watchdog==3.0.0',
        'python-dateutil==2.8.2'
    ]
    
    print("📦 Instalando dependencias...")
    for package in packages:
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
            print(f"✅ {package} instalado correctamente")
        except subprocess.CalledProcessError:
            print(f"❌ Error instalando {package}")
            return False
    return True

def create_windows_service():
    """Crea un servicio de Windows para el monitor"""
    service_script = """
import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import sys
import os

# Agregar el directorio del script al path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from smt_csv_monitor import main

class SMTMonitorService(win32serviceutil.ServiceFramework):
    _svc_name_ = "SMTCSVMonitor"
    _svc_display_name_ = "SMT CSV Monitor Service"
    _svc_description_ = "Monitorea archivos CSV de SMT y los sube a MySQL"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        socket.setdefaulttimeout(60)

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)

    def SvcDoRun(self):
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                            servicemanager.PYS_SERVICE_STARTED,
                            (self._svc_name_, ''))
        try:
            main()
        except Exception as e:
            servicemanager.LogErrorMsg(f"Error en servicio: {e}")

if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(SMTMonitorService)
"""
    
    with open('smt_monitor_service.py', 'w') as f:
        f.write(service_script)
    
    print("✅ Script de servicio creado: smt_monitor_service.py")
    print("Para instalar como servicio Windows:")
    print("  python smt_monitor_service.py install")
    print("  python smt_monitor_service.py start")

def create_batch_scripts():
    """Crea scripts .bat para facilitar la ejecución"""
    
    # Script para ejecutar manualmente
    run_script = f"""@echo off
cd /d "{os.getcwd()}"
python smt_csv_monitor.py
pause
"""
    
    with open('ejecutar_monitor.bat', 'w') as f:
        f.write(run_script)
    
    # Script para instalar servicio
    install_service = f"""@echo off
cd /d "{os.getcwd()}"
echo Instalando servicio SMT CSV Monitor...
python smt_monitor_service.py install
echo Iniciando servicio...
python smt_monitor_service.py start
echo Servicio instalado y iniciado
pause
"""
    
    with open('instalar_servicio.bat', 'w') as f:
        f.write(install_service)
    
    print("✅ Scripts batch creados:")
    print("  - ejecutar_monitor.bat (ejecución manual)")
    print("  - instalar_servicio.bat (instalar como servicio)")

def setup_database():
    """Configuración inicial de base de datos"""
    print("🗄️ Configuración de base de datos:")
    print("1. Asegúrate de que MySQL esté corriendo")
    print("2. Crea la base de datos 'isemm_mes' si no existe")
    print("3. Actualiza las credenciales en config.py")
    print("\nSQL para crear base de datos:")
    print("CREATE DATABASE IF NOT EXISTS isemm_mes CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")

def main():
    print("🚀 Configurador SMT CSV Monitor")
    print("=" * 40)
    
    # Verificar Python
    if sys.version_info < (3, 7):
        print("❌ Se requiere Python 3.7 o superior")
        return
    
    print(f"✅ Python {sys.version}")
    
    # Instalar dependencias
    if not install_requirements():
        print("❌ Error instalando dependencias")
        return
    
    # Crear scripts auxiliares
    create_windows_service()
    create_batch_scripts()
    
    # Información de configuración
    setup_database()
    
    print("\n✅ Configuración completada!")
    print("\nPasos siguientes:")
    print("1. Edita config.py con tus rutas y credenciales")
    print("2. Ejecuta: python smt_csv_monitor.py (modo manual)")
    print("3. O instala como servicio: instalar_servicio.bat")
    
    input("\nPresiona Enter para continuar...")

if __name__ == "__main__":
    main()
