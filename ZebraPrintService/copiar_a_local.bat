@echo off
echo ===================================
echo  SOLUCION: COPIAR A DISCO LOCAL
echo ===================================
echo.

echo El problema es que estas trabajando desde una ruta de red:
echo %CD%
echo.
echo Los servicios de Windows NO pueden ejecutarse desde rutas de red.
echo.

set /p drive=En que unidad quieres instalar el servicio? (C, D, E, etc): 
if "%drive%"=="" set drive=C

set LOCAL_DIR=%drive%:\ZebraPrintService

echo.
echo Creando directorio local: %LOCAL_DIR%
if not exist "%LOCAL_DIR%" mkdir "%LOCAL_DIR%"

echo.
echo Copiando archivos necesarios...
copy "%~dp0print_service.py" "%LOCAL_DIR%\" >nul
copy "%~dp0print_service_windows.py" "%LOCAL_DIR%\" >nul
copy "%~dp0*.bat" "%LOCAL_DIR%\" >nul
copy "%~dp0*.txt" "%LOCAL_DIR%\" >nul 2>nul

if exist "%LOCAL_DIR%\print_service.py" (
    echo ✅ Archivos copiados correctamente
    echo.
    echo SIGUIENTE PASO:
    echo 1. Abrir: %LOCAL_DIR%
    echo 2. Ejecutar como ADMINISTRADOR: instalar_servicio.bat
    echo.
    echo ¿Quieres abrir la carpeta ahora? (S/N)
    set /p open=
    if /i "%open%"=="S" explorer "%LOCAL_DIR%"
) else (
    echo ❌ Error copiando archivos
)

pause
