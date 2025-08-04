@echo off
echo Revirtiendo servicio a SYSTEM y otorgando permisos...
echo.

:: Detener el servicio
echo Deteniendo servicio SMT Monitor...
sc stop SMTMonitorService >nul 2>&1
timeout /t 3 /nobreak >nul

:: Revertir a SYSTEM
echo Configurando servicio para ejecutarse como SYSTEM...
sc config SMTMonitorService obj= "LocalSystem" password= ""

if %errorlevel% equ 0 (
    echo ✓ Servicio reconfigurado como SYSTEM
    echo.
    
    :: Otorgar permisos a SYSTEM
    echo Otorgando permisos completos a SYSTEM para C:\LOT CHECK  ALL...
    icacls "C:\LOT CHECK  ALL" /grant "NT AUTHORITY\SYSTEM:(OI)(CI)F" /T
    
    if %errorlevel% equ 0 (
        echo ✓ Permisos otorgados exitosamente
        echo.
        
        :: Iniciar el servicio
        echo Iniciando servicio SMT Monitor...
        sc start SMTMonitorService
        
        if %errorlevel% equ 0 (
            echo ✓ Servicio iniciado exitosamente
            echo.
            echo El servicio ahora:
            echo - Se ejecuta como SYSTEM
            echo - Tiene acceso completo a C:\LOT CHECK  ALL
            echo - Debería poder monitorear todas las carpetas
            echo.
            echo Verificando estado del servicio...
            sc query SMTMonitorService
            echo.
            echo Monitorea el log para verificar funcionamiento:
            echo C:\SMTMonitor\smt_monitor_service.log
        ) else (
            echo ERROR: No se pudo iniciar el servicio
            echo Revisa el log: C:\SMTMonitor\smt_monitor_service.log
        )
    ) else (
        echo ERROR: No se pudieron otorgar permisos
        echo Asegúrate de ejecutar como Administrador
    )
) else (
    echo ERROR: No se pudo reconfigurar el servicio
    echo Ejecuta como Administrador
)

echo.
pause
