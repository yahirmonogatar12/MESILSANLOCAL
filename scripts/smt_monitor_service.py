
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
