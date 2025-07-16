@echo off
title ILSAN Print Service - PowerShell Method
echo ================================
echo  ILSAN Print Service - Zebra ZT230
echo  Método PowerShell (Compatible con UNC)
echo ================================
echo.

REM Verificar si PowerShell está disponible
powershell -Command "Get-Host" >nul 2>&1
if errorlevel 1 (
    echo ERROR: PowerShell no está disponible
    echo Use start_print_service_direct.bat en su lugar
    pause
    exit /b 1
)

echo Ejecutando con PowerShell para compatibilidad con rutas UNC...
echo.

REM Ejecutar con PowerShell que soporta rutas UNC
powershell -ExecutionPolicy Bypass -Command ^
"Set-Location '\\192.168.1.230\qa\ILSAN_MES\ISEMM_MES'; ^
Write-Host 'Directorio de trabajo:' (Get-Location); ^
Write-Host ''; ^
if (-not (Get-Command python -ErrorAction SilentlyContinue)) { ^
    Write-Host 'ERROR: Python no está instalado o no está en PATH'; ^
    Write-Host 'Instale Python 3.8+ desde https://python.org'; ^
    Write-Host 'Durante la instalación, marque Add Python to PATH'; ^
    Read-Host 'Presione Enter para continuar...'; ^
    exit 1; ^
}; ^
Write-Host 'Verificando archivos del servicio...'; ^
if (-not (Test-Path 'print_service.py')) { ^
    Write-Host 'ERROR: print_service.py no encontrado'; ^
    Write-Host 'Archivos Python encontrados:'; ^
    Get-ChildItem *.py | Select-Object Name; ^
    Read-Host 'Presione Enter para continuar...'; ^
    exit 1; ^
}; ^
Write-Host 'Archivo print_service.py encontrado correctamente.'; ^
Write-Host ''; ^
Write-Host 'Instalando dependencias...'; ^
pip install flask flask-cors pywin32 --quiet; ^
Write-Host ''; ^
Write-Host 'Iniciando servicio de impresión...'; ^
Write-Host ''; ^
Write-Host 'INFORMACIÓN IMPORTANTE:'; ^
Write-Host '- El servicio se ejecutará en http://localhost:5000'; ^
Write-Host '- Para detener el servicio presione Ctrl+C'; ^
Write-Host '- Deje esta ventana abierta mientras use la impresión automática'; ^
Write-Host ''; ^
Write-Host '================================'; ^
Write-Host '  SERVICIO INICIÁNDOSE...'; ^
Write-Host '================================'; ^
python print_service.py"

echo.
echo ================================
echo  SERVICIO DETENIDO
echo ================================
echo.
pause
