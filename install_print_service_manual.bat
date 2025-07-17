@echo off
title ILSAN Print Service - INSTALACIÓN MANUAL
echo ================================================
echo  ILSAN Print Service - INSTALACIÓN MANUAL
echo ================================================
echo.

REM Cambiar al directorio donde está el script
cd /d "%~dp0"
echo Directorio de trabajo: %CD%
echo.

echo PASOS PARA INSTALACIÓN MANUAL:
echo.
echo 1. Instalar Flask:
echo    pip install flask
echo.
echo 2. Instalar PyWin32:
echo    pip install pywin32
echo.
echo 3. Ejecutar el servicio:
echo    python print_service.py
echo.
echo ================================================

echo.
echo ¿Desea intentar la instalación automática? (S/N)
set /p respuesta="Ingrese su opción: "

if /i "%respuesta%"=="S" goto :auto_install
if /i "%respuesta%"=="s" goto :auto_install
goto :manual_instructions

:auto_install
echo.
echo Intentando instalación automática...
echo.

echo Instalando Flask...
pip install flask
if errorlevel 1 (
    echo ❌ Error al instalar Flask
    goto :manual_instructions
) else (
    echo ✅ Flask instalado correctamente
)

echo.
echo Instalando PyWin32...
pip install pywin32
if errorlevel 1 (
    echo ❌ Error al instalar PyWin32
    goto :manual_instructions
) else (
    echo ✅ PyWin32 instalado correctamente
)

echo.
echo ✅ ¡Instalación completa!
echo.
echo Iniciando servicio...
python print_service.py
goto :end

:manual_instructions
echo.
echo ================================================
echo  INSTALACIÓN MANUAL REQUERIDA
echo ================================================
echo.
echo Abra una ventana de comandos como ADMINISTRADOR y ejecute:
echo.
echo   1. pip install flask
echo   2. pip install pywin32
echo   3. cd "%CD%"
echo   4. python print_service.py
echo.
echo Alternativamente, puede ejecutar estos comandos uno por uno:
echo.

echo Comando 1: pip install flask
pause
pip install flask

echo.
echo Comando 2: pip install pywin32
pause
pip install pywin32

echo.
echo Comando 3: Iniciar servicio
pause
python print_service.py

:end
pause
