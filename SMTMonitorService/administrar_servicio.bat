@echo off
echo ========================================
echo  ADMINISTRADOR DE SERVICIO SMT MONITOR
echo ========================================
echo.

:: Cambiar al directorio del script
cd /d "%~dp0"

:menu
echo Selecciona una opcion:
echo.
echo 1. Ver estado del servicio
echo 2. Iniciar servicio
echo 3. Detener servicio
echo 4. Reiniciar servicio
echo 5. Ver logs del servicio
echo 6. Probar conexion BD
echo 7. Salir
echo.
set /p choice="Ingresa tu opcion (1-7): "

if "%choice%"=="1" goto status
if "%choice%"=="2" goto start
if "%choice%"=="3" goto stop
if "%choice%"=="4" goto restart
if "%choice%"=="5" goto logs
if "%choice%"=="6" goto testdb
if "%choice%"=="7" goto exit
echo Opcion invalida, intenta de nuevo
goto menu

:status
echo.
echo === ESTADO DEL SERVICIO ===
sc query SMTMonitorService
echo.
pause
goto menu

:start
echo.
echo Iniciando servicio SMT Monitor...
net start SMTMonitorService
echo.
pause
goto menu

:stop
echo.
echo Deteniendo servicio SMT Monitor...
net stop SMTMonitorService
echo.
pause
goto menu

:restart
echo.
echo Reiniciando servicio SMT Monitor...
net stop SMTMonitorService
timeout /t 3 /nobreak >nul
net start SMTMonitorService
echo.
pause
goto menu

:logs
echo.
echo === ULTIMAS 50 LINEAS DEL LOG ===
if exist smt_monitor_service.log (
    powershell "Get-Content smt_monitor_service.log | Select-Object -Last 50"
) else (
    echo No se encontro el archivo de log
)
echo.
pause
goto menu

:testdb
echo.
echo === PRUEBA DE CONEXION BD ===
if exist "probar_conexion_bd.py" (
    python probar_conexion_bd.py
) else (
    echo Archivo probar_conexion_bd.py no encontrado
)
echo.
pause
goto menu

:exit
echo.
echo Saliendo...
exit /b 0
