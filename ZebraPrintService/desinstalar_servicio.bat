@echo off
echo ===================================
echo  DESINSTALACION DE SERVICIO WINDOWS
echo  Servicio de Impresion Local Zebra
echo ===================================
echo.

REM Verificar si se ejecuta como administrador
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: Este script debe ejecutarse como ADMINISTRADOR
    echo Haz clic derecho en el archivo y selecciona "Ejecutar como administrador"
    echo.
    pause
    exit /b 1
)

REM Cambiar al directorio donde está el script
cd /d "%~dp0"
echo Directorio de trabajo: %CD%
echo.

echo 1. Deteniendo servicio...
sc stop ZebraPrintService
timeout /t 5 /nobreak >nul

echo.
echo 2. Desinstalando servicio de Windows...
python "%~dp0print_service_windows.py" remove

if %errorLevel% neq 0 (
    echo ADVERTENCIA: Error al desinstalar con Python, intentando con sc...
    sc delete ZebraPrintService
)

echo.
echo ===================================
echo  DESINSTALACION COMPLETADA
echo ===================================
echo.
echo El servicio ha sido removido del sistema.
echo Los archivos del servicio siguen disponibles para reinstalacion.
echo.
pause
