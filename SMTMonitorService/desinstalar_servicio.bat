@echo off
echo ========================================
echo  DESINSTALADOR DE SERVICIO SMT MONITOR
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

echo Deteniendo servicio SMT Monitor...
python smt_monitor_service.py stop

echo.
echo Desinstalando servicio...
python smt_monitor_service.py remove

if %errorLevel% neq 0 (
    echo ERROR: No se pudo desinstalar el servicio
    pause
    exit /b 1
) else (
    echo.
    echo ==========================================
    echo  SERVICIO SMT MONITOR DESINSTALADO
    echo ==========================================
    echo.
    echo El servicio ha sido removido del sistema
)

echo.
pause
