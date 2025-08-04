@echo off
echo Otorgando permisos a SYSTEM para carpetas SMT...
echo.

set TARGET_PATH=C:\LOT CHECK  ALL

echo Verificando carpeta destino: %TARGET_PATH%
if not exist "%TARGET_PATH%" (
    echo ERROR: La carpeta %TARGET_PATH% no existe.
    pause
    exit /b 1
)

echo ✓ Carpeta encontrada: %TARGET_PATH%
echo.

echo Otorgando permisos completos a SYSTEM para %TARGET_PATH%...
icacls "%TARGET_PATH%" /grant "NT AUTHORITY\SYSTEM:(OI)(CI)F" /T

if %errorlevel% equ 0 (
    echo ✓ Permisos otorgados exitosamente
    echo.
    
    echo Verificando permisos otorgados...
    icacls "%TARGET_PATH%" | findstr "NT AUTHORITY\\SYSTEM"
    
    echo.
    echo Permisos configurados. El servicio SYSTEM ahora puede acceder a:
    echo - %TARGET_PATH%
    echo - Todas las subcarpetas (1line, 2line, 3line, 4line)
    echo - Todos los archivos CSV
    echo.
    
    echo Reiniciando servicio SMT Monitor...
    sc stop SMTMonitorService >nul 2>&1
    timeout /t 3 /nobreak >nul
    sc start SMTMonitorService
    
    if %errorlevel% equ 0 (
        echo ✓ Servicio reiniciado exitosamente
        echo.
        echo Verificando estado del servicio...
        sc query SMTMonitorService
    ) else (
        echo.
        echo ADVERTENCIA: Error al reiniciar el servicio.
        echo Verifica los logs en: C:\SMTMonitor\smt_monitor_service.log
    )
    
) else (
    echo.
    echo ERROR: No se pudieron otorgar los permisos.
    echo Asegúrate de ejecutar este script como Administrador.
    echo.
    echo Para ejecutar como Administrador:
    echo 1. Clic derecho en el archivo .bat
    echo 2. Seleccionar "Ejecutar como administrador"
)

echo.
echo Script completado.
pause
