@echo off
cd /d "C:\Users\yahir\OneDrive\Escritorio\ISEMM_MES\scripts"
echo Instalando servicio SMT CSV Monitor...
python smt_monitor_service.py install
echo Iniciando servicio...
python smt_monitor_service.py start
echo Servicio instalado y iniciado
pause
