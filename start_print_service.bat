@echo off
title ILSAN Print Service - Zebra ZT230
echo ================================
echo  ILSAN Print Service - Zebra ZT230
echo ================================
echo.

REM Obtener la ruta del script y cambiar al directorio
set SCRIPT_DIR=%~dp0
echo Script ubicado en: %SCRIPT_DIR%

REM Cambiar al directorio del script
cd /d "%SCRIPT_DIR%"
echo Directorio de trabajo actual: %CD%

REM Verificar que estamos en el directorio correcto
if not "%CD%" == "%SCRIPT_DIR:~0,-1%" (
    echo ADVERTENCIA: No se pudo cambiar al directorio del script
    echo Intentando ruta alternativa...
    
    REM Intentar con la ruta de red completa
    cd /d "\\192.168.1.230\qa\ILSAN_MES\ISEMM_MES"
    echo Directorio corregido: %CD%
)
echo.

REM Verificar si Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python no está instalado o no está en PATH
    echo Instale Python 3.8+ desde https://python.org
    echo.
    echo INSTRUCCIONES:
    echo 1. Descargue Python desde https://python.org/downloads/
    echo 2. Durante la instalación, marque "Add Python to PATH"
    echo 3. Reinicie este script
    pause
    exit /b 1
)

echo Verificando dependencias...

REM Verificar si existe el archivo de requirements
if exist print_requirements.txt (
    echo Archivo print_requirements.txt encontrado. Instalando dependencias...
    pip install -r print_requirements.txt --quiet
    
    if errorlevel 1 (
        echo ADVERTENCIA: Error al instalar desde requirements.txt
        echo Intentando instalación manual...
        goto :install_manual
    ) else (
        echo Dependencias instaladas correctamente desde requirements.txt
        goto :start_service
    )
) else (
    echo ADVERTENCIA: print_requirements.txt no encontrado
    echo Instalando dependencias manualmente...
    goto :install_manual
)

:install_manual
echo.
echo Instalando Flask...
pip install flask --quiet
if errorlevel 1 (
    echo ERROR: No se pudo instalar Flask
    pause
    exit /b 1
)

echo Instalando Flask-CORS...
pip install flask-cors --quiet
if errorlevel 1 (
    echo ERROR: No se pudo instalar Flask-CORS
    pause
    exit /b 1
)

echo Instalando PyWin32...
pip install pywin32 --quiet
if errorlevel 1 (
    echo ERROR: No se pudo instalar PyWin32
    echo.
    echo SOLUCIÓN ALTERNATIVA:
    echo 1. Abra PowerShell como Administrador
    echo 2. Ejecute: pip install pywin32
    echo 3. Ejecute: python Scripts/pywin32_postinstall.py -install
    pause
    exit /b 1
)

echo Dependencias instaladas manualmente.

:start_service

:start_service
echo.
echo Verificando archivos del servicio...

REM Verificar que existe el archivo Python del servicio
if not exist print_service.py (
    echo ERROR: print_service.py no encontrado
    echo.
    echo El archivo print_service.py debe estar en la misma carpeta que este script.
    echo Directorio actual: %CD%
    echo.
    echo Archivos encontrados:
    dir *.py
    pause
    exit /b 1
)

echo Archivo print_service.py encontrado correctamente.
echo.
echo Iniciando servicio de impresión...
echo.
echo INFORMACIÓN IMPORTANTE:
echo - El servicio se ejecutará en http://localhost:5002
echo - Para detener el servicio presione Ctrl+C
echo - Deje esta ventana abierta mientras use la impresión automática
echo.
echo ================================
echo  SERVICIO INICIÁNDOSE...
echo ================================

REM Ejecutar el servicio
python print_service.py

echo.
echo ================================
echo  SERVICIO DETENIDO
echo ================================
echo.
pause
