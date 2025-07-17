@echo off
title ILSAN Print Service - Zebra ZT230 (Directo)
echo ================================
echo  ILSAN Print Service - Zebra ZT230
echo  Método de inicio directo con mapeo de unidad
echo ================================
echo.

REM Buscar una letra de unidad disponible
set DRIVE_LETTER=
for %%i in (Z Y X W V U T S R Q P O N M L K J I H G F E) do (
    if not exist %%i:\ (
        set DRIVE_LETTER=%%i
        goto :found_drive
    )
)

:found_drive
if "%DRIVE_LETTER%"=="" (
    echo ERROR: No se encontró una letra de unidad disponible
    echo Intentando método alternativo...
    goto :alternative_method
)

echo Mapeando unidad temporal %DRIVE_LETTER%: ...
net use %DRIVE_LETTER%: "\\192.168.1.230\qa\ILSAN_MES\ISEMM_MES" >nul 2>&1

if errorlevel 1 (
    echo ADVERTENCIA: No se pudo mapear la unidad de red
    echo Intentando método alternativo...
    goto :alternative_method
)

REM Cambiar al directorio mapeado
%DRIVE_LETTER%:
cd /d %DRIVE_LETTER%:\
echo Directorio de trabajo: %CD%
echo.
goto :continue_setup

:alternative_method
echo.
echo MÉTODO ALTERNATIVO: Ejecutando desde ruta de red...
echo NOTA: Algunos comandos pueden requerir ruta completa
echo.
set "PROJECT_PATH=\\192.168.1.230\qa\ILSAN_MES\ISEMM_MES"
echo Ruta del proyecto: %PROJECT_PATH%
echo.

:continue_setup

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
    goto :cleanup_and_exit
)

echo Verificando archivos del servicio...

REM Verificar que existe el archivo Python del servicio
if defined DRIVE_LETTER (
    REM Estamos en unidad mapeada
    if not exist print_service.py (
        echo ERROR: print_service.py no encontrado en:
        echo %CD%
        echo.
        echo Archivos Python encontrados:
        dir *.py /b 2>nul
        goto :cleanup_and_exit
    )
    set "PYTHON_SERVICE=print_service.py"
) else (
    REM Estamos usando método alternativo
    if not exist "%PROJECT_PATH%\print_service.py" (
        echo ERROR: print_service.py no encontrado en:
        echo %PROJECT_PATH%
        echo.
        echo Verificando archivos en la ruta de red...
        dir "%PROJECT_PATH%\*.py" /b 2>nul
        goto :cleanup_and_exit
    )
    set "PYTHON_SERVICE=%PROJECT_PATH%\print_service.py"
)

echo Archivo print_service.py encontrado correctamente.
echo.

echo Instalando dependencias esenciales...
pip install flask flask-cors pywin32 --quiet

echo.
echo Iniciando servicio de impresión...
echo.
echo INFORMACIÓN IMPORTANTE:
echo - El servicio se ejecutará en http://localhost:5000
echo - Para detener el servicio presione Ctrl+C
echo - Deje esta ventana abierta mientras use la impresión automática
echo.
echo ================================
echo  SERVICIO INICIÁNDOSE...
echo ================================

REM Ejecutar el servicio
python "%PYTHON_SERVICE%"

echo.
echo ================================
echo  SERVICIO DETENIDO
echo ================================

:cleanup_and_exit
REM Limpiar unidad mapeada si se creó
if defined DRIVE_LETTER (
    echo.
    echo Desmontando unidad temporal %DRIVE_LETTER%:...
    net use %DRIVE_LETTER%: /delete >nul 2>&1
)

echo.
pause
