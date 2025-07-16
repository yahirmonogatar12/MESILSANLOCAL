@echo off
title ILSAN Print Service - Método Local
echo ================================
echo  ILSAN Print Service - Zebra ZT230
echo  Método con copia local
echo ================================
echo.

REM Crear carpeta temporal en Documents del usuario
set "TEMP_DIR=%USERPROFILE%\Documents\ILSAN_PrintService"
echo Creando carpeta temporal: %TEMP_DIR%

if not exist "%TEMP_DIR%" (
    mkdir "%TEMP_DIR%"
)

echo Copiando archivos del servicio...
copy "\\192.168.1.230\qa\ILSAN_MES\ISEMM_MES\print_service.py" "%TEMP_DIR%\" >nul
copy "\\192.168.1.230\qa\ILSAN_MES\ISEMM_MES\print_requirements.txt" "%TEMP_DIR%\" >nul

if not exist "%TEMP_DIR%\print_service.py" (
    echo ERROR: No se pudo copiar print_service.py
    echo Verifique la conexión de red y permisos
    pause
    exit /b 1
)

REM Cambiar al directorio local
cd /d "%TEMP_DIR%"
echo Directorio de trabajo: %CD%
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

echo Verificando archivos del servicio...
echo Archivo print_service.py: ENCONTRADO
echo.

echo Instalando dependencias...
if exist print_requirements.txt (
    pip install -r print_requirements.txt --quiet
) else (
    pip install flask flask-cors pywin32 --quiet
)

echo.
echo Iniciando servicio de impresión...
echo.
echo INFORMACIÓN IMPORTANTE:
echo - El servicio se ejecutará en http://localhost:5002
echo - Para detener el servicio presione Ctrl+C
echo - Deje esta ventana abierta mientras use la impresión automática
echo - Los archivos temporales están en: %TEMP_DIR%
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

REM Preguntar si limpiar archivos temporales
echo ¿Desea eliminar los archivos temporales? (S/N)
set /p CLEANUP=
if /i "%CLEANUP%"=="S" (
    echo Limpiando archivos temporales...
    cd /d "%USERPROFILE%"
    rmdir /s /q "%TEMP_DIR%"
    echo Archivos temporales eliminados.
)

pause
