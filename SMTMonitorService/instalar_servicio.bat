@echo off
echo ========================================
echo  INSTALADOR DE SERVICIO SMT MONITOR
echo ========================================
echo.

:: Verificar permisos de administrador
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: Este script debe ejecutarse como Administrador
    echo Haz clic derecho y selecciona "Ejecutar como administrador"
    pause
    exit /b 1
)

:: Cambiar al directorio del script
cd /d "%~dp0"
echo Directorio de trabajo: %cd%

echo.
echo Verificando/creando carpetas de monitoreo...
mkdir "C:\LOT CHECK  ALL\1line\L1 m1" 2>nul
mkdir "C:\LOT CHECK  ALL\1line\L1 m2" 2>nul
mkdir "C:\LOT CHECK  ALL\1line\L1 m3" 2>nul
mkdir "C:\LOT CHECK  ALL\2line\L2 m1" 2>nul
mkdir "C:\LOT CHECK  ALL\2line\L2 m2" 2>nul
mkdir "C:\LOT CHECK  ALL\2line\L2 m3" 2>nul
mkdir "C:\LOT CHECK  ALL\3line\L3 m1" 2>nul
mkdir "C:\LOT CHECK  ALL\3line\L3 m2" 2>nul
mkdir "C:\LOT CHECK  ALL\3line\L3 m3" 2>nul
mkdir "C:\LOT CHECK  ALL\4line\L4 m1" 2>nul
mkdir "C:\LOT CHECK  ALL\4line\L4 m2" 2>nul
mkdir "C:\LOT CHECK  ALL\4line\L4 m3" 2>nul

echo Ejecutando diagnostico...
if exist "diagnostico_rapido.py" (
    python diagnostico_rapido.py
) else (
    echo Archivo diagnostico_rapido.py no encontrado, saltando...
)

echo.
echo Probando conexion a base de datos...
if exist "probar_conexion_bd.py" (
    python probar_conexion_bd.py
) else (
    echo Archivo probar_conexion_bd.py no encontrado, saltando...
)

echo.
echo Instalando dependencias...
pip install pywin32 mysql-connector-python

echo.
echo Instalando servicio SMT Monitor...
if exist "smt_monitor_service.py" (
    python smt_monitor_service.py install
) else (
    echo ERROR: Archivo smt_monitor_service.py no encontrado
    pause
    exit /b 1
)

if %errorLevel% neq 0 (
    echo ERROR: No se pudo instalar el servicio
    pause
    exit /b 1
)

echo.
echo Configurando inicio automatico...
sc config SMTMonitorService start= auto

echo.
echo Iniciando servicio...
python smt_monitor_service.py start

if %errorLevel% neq 0 (
    echo ADVERTENCIA: No se pudo iniciar el servicio automaticamente
    echo Puedes iniciarlo manualmente con: net start SMTMonitorService
) else (
    echo.
    echo ============================================
    echo  SERVICIO SMT MONITOR INSTALADO EXITOSAMENTE
    echo ============================================
    echo.
    echo El servicio esta corriendo y monitoreando:
    echo - C:\LOT CHECK  ALL\1line\L1 m1
    echo - C:\LOT CHECK  ALL\1line\L1 m2
    echo - C:\LOT CHECK  ALL\1line\L1 m3
    echo - C:\LOT CHECK  ALL\2line
    echo - C:\LOT CHECK  ALL\3line
    echo - C:\LOT CHECK  ALL\4line
    echo.
    echo Logs del servicio: smt_monitor_service.log
)

echo.
pause
