@echo off
echo ===================================
echo  INSTALACION DE SERVICIO WINDOWS
echo  Servicio de Impresion Local Zebra
echo ===================================
echo.

REM Verificar si se ejecuta como administrador
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: Este script debe ejecutarse como ADMINISTRADOR
    echo.
    echo SOLUCION:
    echo 1. Haz clic derecho en el archivo instalar_servicio.bat
    echo 2. Selecciona "Ejecutar como administrador"
    echo 3. Confirma en el dialogo de UAC
    echo.
    pause
    exit /b 1
)

REM Cambiar al directorio donde está el script
cd /d "%~dp0"
echo Directorio de trabajo: %CD%
echo.

echo 1. Verificando Python...
python --version
if %errorLevel% neq 0 (
    echo ERROR: Python no encontrado en PATH
    echo Instale Python y agregelo al PATH del sistema
    pause
    exit /b 1
)

echo.
echo 2. Instalando dependencias de Python...
pip install flask flask-cors pywin32
if %errorLevel% neq 0 (
    echo ERROR: No se pudieron instalar las dependencias
    pause
    exit /b 1
)

echo.
echo 3. Configurando pywin32...
python -c "import win32serviceutil; print('pywin32 OK')"
if %errorLevel% neq 0 (
    echo ERROR: pywin32 no funciona correctamente
    echo Ejecute: pip install --force-reinstall pywin32
    pause
    exit /b 1
)

echo.
echo 4. Deteniendo servicio si existe...
sc stop ZebraPrintService >nul 2>&1
sc delete ZebraPrintService >nul 2>&1
timeout /t 2 /nobreak >nul

echo.
echo 5. Instalando servicio de Windows...
python "%~dp0print_service_windows.py" install
if %errorLevel% neq 0 (
    echo ERROR: No se pudo instalar el servicio
    echo Verifique los logs y permisos
    pause
    exit /b 1
)

echo.
echo 6. Configurando servicio para inicio automatico...
sc config ZebraPrintService start= auto
sc config ZebraPrintService obj= LocalSystem

echo.
echo 7. Estableciendo descripcion del servicio...
sc description ZebraPrintService "Servicio de impresion local para impresoras Zebra ZT230. Puerto 5003."

echo.
echo 8. Iniciando servicio...
sc start ZebraPrintService
if %errorLevel% neq 0 (
    echo ADVERTENCIA: No se pudo iniciar el servicio automaticamente
    echo Revise el Visor de Eventos o inicie manualmente desde services.msc
    echo.
    echo Para revisar errores:
    echo - Presione Win+R, escriba "eventvwr.msc"
    echo - Vaya a "Registros de Windows" - "Sistema"
    echo - Busque errores relacionados con "ZebraPrintService"
) else (
    echo EXITO: Servicio instalado e iniciado correctamente
)

echo.
echo ===================================
echo  INSTALACION COMPLETADA
echo ===================================
echo.
echo Servicio: "Servicio de Impresion Local Zebra"
echo Nombre tecnico: ZebraPrintService
echo Puerto: 5003
echo Estado: Para verificar ejecute "gestionar_servicio.bat"
echo.
echo Para administrar:
echo - services.msc (Servicios de Windows)
echo - gestionar_servicio.bat (Este directorio)
echo.
pause
