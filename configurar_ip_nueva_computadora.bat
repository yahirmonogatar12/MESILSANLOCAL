@echo off
title Configurador de IP para Nueva Computadora
echo ================================
echo  CONFIGURADOR DE IP AUTOMÁTICO
echo  Sistema de Impresión Zebra ZT230
echo ================================
echo.

REM Obtener la IP actual de la computadora
echo Detectando IP de esta computadora...

REM Usar PowerShell para obtener la IP
for /f "tokens=2 delims=:" %%a in ('powershell -Command "(Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias 'Ethernet*' | Where-Object {$_.IPAddress -like '192.168.*'})[0].IPAddress"') do (
    set CURRENT_IP=%%a
)

REM Limpiar espacios en blanco
set CURRENT_IP=%CURRENT_IP: =%

if "%CURRENT_IP%"=="" (
    echo.
    echo ⚠️  No se pudo detectar automáticamente la IP.
    echo.
    echo Ingrese manualmente la IP de esta computadora:
    echo Ejemplo: 192.168.0.220
    set /p CURRENT_IP="IP: "
)

echo.
echo 📍 IP detectada/configurada: %CURRENT_IP%
echo.

REM Validar formato de IP básico
echo %CURRENT_IP% | findstr /R "^192\.168\.[0-9]*\.[0-9]*$" >nul
if errorlevel 1 (
    echo ❌ Formato de IP inválido. Debe ser 192.168.x.x
    pause
    exit /b 1
)

echo ✅ Formato de IP válido
echo.

REM Preguntar si continuar
echo ¿Desea configurar el sistema para usar la IP %CURRENT_IP%? (S/N)
set /p CONTINUAR="Respuesta: "
if /i not "%CONTINUAR%"=="S" (
    echo Operación cancelada.
    pause
    exit /b 0
)

echo.
echo 🔄 Configurando sistema...

REM Verificar que existen los archivos necesarios
if not exist "app\templates\Control de material\Control de material de almacen.html" (
    echo ❌ ERROR: No se encuentra el archivo HTML principal
    echo Asegúrese de estar en la carpeta correcta del proyecto
    pause
    exit /b 1
)

if not exist "run.py" (
    echo ❌ ERROR: No se encuentra run.py
    echo Asegúrese de estar en la carpeta correcta del proyecto
    pause
    exit /b 1
)

echo.
echo 📝 Actualizando archivos...

REM Crear backup del HTML
copy "app\templates\Control de material\Control de material de almacen.html" "app\templates\Control de material\Control de material de almacen.html.backup" >nul
echo ✅ Backup creado del archivo HTML

REM Crear backup de run.py
copy "run.py" "run.py.backup" >nul
echo ✅ Backup creado de run.py

REM SOLO actualizar run.py (la aplicación web), NO el servicio de impresión
REM El servicio de impresión siempre usa localhost:5002 en cada PC
powershell -Command "(Get-Content 'run.py') -replace \"host='192\.168\.0\.211'\", \"host='%CURRENT_IP%'\" | Set-Content 'run.py'"
echo ✅ IP actualizada en run.py (aplicación web)
echo ℹ️  Servicio de impresión usa localhost:5002 (local en cada PC)

echo.
echo 🎉 ¡Configuración completada exitosamente!
echo.
echo 📋 Resumen de cambios:
echo    • IP de aplicación web: %CURRENT_IP%
echo    • Servicio de impresión: http://localhost:5002 (local)
echo    • Aplicación web: http://%CURRENT_IP%:5000
echo    • Backups creados con extensión .backup
echo.
echo 🚀 Próximos pasos:
echo    1. Ejecutar: start_print_service_local.bat
echo    2. Ejecutar: python run.py
echo    3. Acceder a: http://%CURRENT_IP%:5000
echo.
echo ⚠️  Nota: Si algo sale mal, puede restaurar los backups:
echo    - Control de material de almacen.html.backup
echo    - run.py.backup
echo.
pause
