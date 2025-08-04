@echo off
cd /d "%~dp0"
echo Reinstalando servicio SMT Monitor con ruta corregida...
echo Directorio actual: %CD%
echo.

:: Verificar que el archivo existe
if not exist "smt_monitor_service.py" (
    echo ERROR: Archivo smt_monitor_service.py no encontrado en %CD%
    echo Verifica que el script se ejecute desde la carpeta correcta
    pause
    exit /b 1
)

echo ✓ Archivo smt_monitor_service.py encontrado
echo.

:: Detener y desinstalar el servicio actual
echo Deteniendo servicio actual...
sc stop SMTMonitorService >nul 2>&1
timeout /t 3 /nobreak >nul

echo Desinstalando servicio actual...
sc delete SMTMonitorService >nul 2>&1
timeout /t 2 /nobreak >nul

:: Verificar que Python existe
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python no encontrado en PATH
    echo Instala Python o agregalo al PATH del sistema
    pause
    exit /b 1
)

echo Python encontrado: 
python --version

:: Instalar el servicio corregido
echo.
echo Instalando servicio SMT Monitor con ruta corregida...
python smt_monitor_service.py install

if %errorlevel% equ 0 (
    echo ✓ Servicio instalado exitosamente
    echo.
    
    :: Configurar para inicio automático
    echo Configurando inicio automático...
    sc config SMTMonitorService start= auto
    
    :: Otorgar permisos a SYSTEM
    echo Otorgando permisos a SYSTEM para carpetas...
    icacls "C:\LOT CHECK  ALL" /grant "NT AUTHORITY\SYSTEM:(OI)(CI)F" /T >nul 2>&1
    
    :: Iniciar el servicio
    echo Iniciando servicio SMT Monitor...
    sc start SMTMonitorService
    
    if %errorlevel% equ 0 (
        echo ✓ Servicio iniciado exitosamente
        echo.
        echo ✅ INSTALACIÓN COMPLETADA ✅
        echo.
        echo El servicio SMT Monitor está ahora:
        echo - Instalado con la ruta corregida: C:\LOT CHECK  ALL
        echo - Configurado para inicio automático
        echo - Con permisos para acceder a las carpetas
        echo.
        echo Verificando estado...
        sc query SMTMonitorService
        echo.
        echo Para verificar funcionamiento, revisa:
        echo C:\SMTMonitorService\smt_monitor_service.log
    ) else (
        echo ✗ Error iniciando el servicio
        echo Revisa el log para detalles: C:\SMTMonitorService\smt_monitor_service.log
    )
) else (
    echo ✗ Error instalando el servicio
    echo Verifica que:
    echo 1. Tienes permisos de administrador
    echo 2. El archivo smt_monitor_service.py existe
    echo 3. Python está correctamente instalado
)

echo.
echo Script completado.
pause
