@echo off
echo ========================================
echo INSTALADOR DE SERVICIO SMT MONITOR
echo ========================================
echo.

REM Cambiar al directorio del script
cd /d "%~dp0"

echo Detener servicio anterior si existe...
sc stop SMTMonitorService >nul 2>&1
sc delete SMTMonitorService >nul 2>&1

echo.
echo Instalando servicio SMT Monitor...
python smt_monitor_service.py install

if %ERRORLEVEL% EQU 0 (
    echo ✅ Servicio instalado correctamente
    echo.
    echo Iniciando servicio...
    sc start SMTMonitorService
    
    if %ERRORLEVEL% EQU 0 (
        echo ✅ Servicio iniciado correctamente
        echo.
        echo ESTADO DEL SERVICIO:
        sc query SMTMonitorService
        echo.
        echo 📋 VERIFICAR LOGS:
        echo    - Revisar archivo: smt_monitor_service.log
        echo    - Comando: type smt_monitor_service.log
        echo.
        echo 🔧 COMANDOS ÚTILES:
        echo    - Parar:     sc stop SMTMonitorService
        echo    - Iniciar:   sc start SMTMonitorService
        echo    - Estado:    sc query SMTMonitorService
        echo    - Logs:      type smt_monitor_service.log
    ) else (
        echo ❌ Error iniciando el servicio
        echo Revisar logs para más detalles
    )
) else (
    echo ❌ Error instalando el servicio
    echo Verificar que Python y pywin32 estén instalados
)

echo.
pause
