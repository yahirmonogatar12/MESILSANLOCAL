@echo off
title Instalación Completa - Nueva Computadora
echo ========================================
echo  INSTALACIÓN COMPLETA PARA NUEVA PC
echo  Sistema de Impresión Zebra ZT230
echo ========================================
echo.

echo 📋 Este script realizará:
echo    1. Verificación de prerequisitos
echo    2. Configuración automática de IP
echo    3. Instalación del servicio de impresión
echo    4. Verificación de la impresora Zebra
echo    5. Pruebas del sistema completo
echo.

echo ⚠️  PREREQUISITOS ANTES DE CONTINUAR:
echo    • Python 3.8+ instalado con PATH configurado
echo    • Impresora Zebra ZT230 conectada por USB
echo    • Drivers de Zebra instalados
echo    • Permisos de administrador
echo.

echo ¿Desea continuar con la instalación completa? (S/N)
set /p CONTINUAR="Respuesta: "
if /i not "%CONTINUAR%"=="S" (
    echo Instalación cancelada.
    pause
    exit /b 0
)

echo.
echo 🔍 === PASO 1: VERIFICACIÓN DE PREREQUISITOS ===
echo.

REM Verificar Python
echo Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ ERROR: Python no está instalado o no está en PATH
    echo.
    echo 📥 INSTALE PYTHON PRIMERO:
    echo    1. Vaya a: https://python.org/downloads/
    echo    2. Descargue la versión más reciente
    echo    3. Durante instalación marque "Add Python to PATH"
    echo    4. Reinicie esta instalación después
    pause
    exit /b 1
)

for /f "tokens=2" %%a in ('python --version 2^>^&1') do set PYTHON_VERSION=%%a
echo ✅ Python %PYTHON_VERSION% detectado correctamente

REM Verificar archivos del proyecto
echo.
echo Verificando archivos del proyecto...
if not exist "print_service.py" (
    echo ❌ ERROR: print_service.py no encontrado
    echo Asegúrese de estar en la carpeta correcta del proyecto
    pause
    exit /b 1
)
echo ✅ print_service.py encontrado

if not exist "app\templates\Control de material\Control de material de almacen.html" (
    echo ❌ ERROR: Archivo HTML principal no encontrado
    echo Verifique que todos los archivos estén copiados
    pause
    exit /b 1
)
echo ✅ Archivo HTML principal encontrado

if not exist "run.py" (
    echo ❌ ERROR: run.py no encontrado
    echo Verifique que todos los archivos estén copiados
    pause
    exit /b 1
)
echo ✅ run.py encontrado

echo.
echo 🔧 === PASO 2: CONFIGURACIÓN AUTOMÁTICA DE IP ===
echo.

REM Detectar IP automáticamente
echo Detectando IP de esta computadora...
for /f "tokens=2 delims=:" %%a in ('powershell -Command "(Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias 'Ethernet*' ^| Where-Object {$_.IPAddress -like '192.168.*'})[0].IPAddress"') do (
    set CURRENT_IP=%%a
)
set CURRENT_IP=%CURRENT_IP: =%

if "%CURRENT_IP%"=="" (
    echo ⚠️  No se pudo detectar automáticamente.
    set /p CURRENT_IP="Ingrese la IP manualmente (ej: 192.168.0.220): "
)

echo ✅ IP configurada: %CURRENT_IP%

REM Crear backups y actualizar archivos
echo.
echo Actualizando configuración...
copy "app\templates\Control de material\Control de material de almacen.html" "app\templates\Control de material\Control de material de almacen.html.backup" >nul
copy "run.py" "run.py.backup" >nul

REM SOLO actualizar run.py - el servicio de impresión siempre es localhost
powershell -Command "(Get-Content 'run.py') -replace \"host='192\.168\.0\.211'\", \"host='%CURRENT_IP%'\" | Set-Content 'run.py'"

echo ✅ Configuración actualizada:
echo    • Aplicación web: %CURRENT_IP%:5000
echo    • Servicio de impresión: localhost:5002 (local en cada PC)

echo.
echo 🖨️  === PASO 3: INSTALACIÓN DEL SERVICIO DE IMPRESIÓN ===
echo.

echo Instalando dependencias de Python...
pip install flask flask-cors pywin32 --quiet

if errorlevel 1 (
    echo ⚠️  Error en instalación automática. Intentando individual...
    pip install flask --quiet
    pip install flask-cors --quiet
    pip install pywin32 --quiet
)

echo ✅ Dependencias instaladas

echo.
echo 🔍 === PASO 4: VERIFICACIÓN DE IMPRESORA ZEBRA ===
echo.

echo Iniciando verificación de impresora...
echo Esto tomará unos segundos...

REM Crear script temporal para verificar impresora
echo import win32print > temp_check_printer.py
echo printers = [printer[2] for printer in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL)] >> temp_check_printer.py
echo zebra_found = any('zebra' in p.lower() or 'zt230' in p.lower() or 'zpl' in p.lower() for p in printers) >> temp_check_printer.py
echo print('ZEBRA_FOUND' if zebra_found else 'ZEBRA_NOT_FOUND') >> temp_check_printer.py
echo print('PRINTERS:' + ';'.join(printers)) >> temp_check_printer.py

python temp_check_printer.py > printer_check_result.txt 2>&1

if exist printer_check_result.txt (
    findstr "ZEBRA_FOUND" printer_check_result.txt >nul
    if not errorlevel 1 (
        echo ✅ Impresora Zebra detectada correctamente
    ) else (
        echo ⚠️  Impresora Zebra no detectada
        echo.
        echo 📋 Impresoras encontradas:
        findstr "PRINTERS:" printer_check_result.txt
        echo.
        echo 🔧 VERIFIQUE:
        echo    • Impresora conectada por USB
        echo    • Impresora encendida
        echo    • Drivers de Zebra instalados
        echo.
        echo ¿Desea continuar de todos modos? (S/N)
        set /p CONTINUAR_SIN_ZEBRA="Respuesta: "
        if /i not "%CONTINUAR_SIN_ZEBRA%"=="S" (
            echo Instalación cancelada.
            del temp_check_printer.py printer_check_result.txt 2>nul
            pause
            exit /b 1
        )
    )
)

del temp_check_printer.py printer_check_result.txt 2>nul

echo.
echo 🎉 === INSTALACIÓN COMPLETADA ===
echo.

echo ✅ Configuración finalizada:
echo    • IP de aplicación web: %CURRENT_IP%
echo    • Servicio de impresión: http://localhost:5002 (local)
echo    • Aplicación web: http://%CURRENT_IP%:5000
echo    • Dependencias: Flask, Flask-CORS, PyWin32
echo    • Backups creados: *.backup
echo.

echo 🚀 PARA USAR EL SISTEMA:
echo.
echo    1. INICIAR SERVICIO DE IMPRESIÓN:
echo       → Doble clic en: start_print_service_local.bat
echo       → O ejecutar: python print_service.py
echo.
echo    2. INICIAR APLICACIÓN WEB:
echo       → Abrir nueva ventana CMD
echo       → Ejecutar: python run.py
echo.
echo    3. ACCEDER AL SISTEMA:
echo       → Navegador: http://%CURRENT_IP%:5000
echo.

echo 🧪 PARA PROBAR EL SISTEMA:
echo    • En el navegador, presione F12 (consola)
echo    • Ejecute: testServicioWin32()
echo    • Debe mostrar impresora Zebra detectada
echo.

echo ¿Desea iniciar automáticamente los servicios ahora? (S/N)
set /p INICIAR_SERVICIOS="Respuesta: "
if /i "%INICIAR_SERVICIOS%"=="S" (
    echo.
    echo 🚀 Iniciando servicios...
    echo.
    echo ⚠️  Se abrirán 2 ventanas de CMD:
    echo    1. Servicio de impresión (puerto 5002)
    echo    2. Aplicación web (puerto 5000)
    echo.
    echo 💡 IMPORTANTE: Mantenga ambas ventanas abiertas
    echo.
    pause
    
    REM Iniciar servicio de impresión en nueva ventana
    start "Servicio de Impresión Zebra" cmd /k "echo Iniciando servicio de impresión... && python print_service.py"
    
    REM Esperar un poco
    timeout /t 3 /nobreak >nul
    
    REM Iniciar aplicación web en nueva ventana
    start "Aplicación Web ILSAN" cmd /k "echo Iniciando aplicación web... && python run.py"
    
    echo.
    echo ✅ Servicios iniciados en ventanas separadas
    echo.
    echo 🌐 Acceda al sistema en:
    echo    http://%CURRENT_IP%:5000
    echo.
)

echo.
echo 📞 Si tiene problemas, consulte:
echo    • GUIA_INSTALACION_NUEVA_COMPUTADORA.md
echo    • Los archivos de log generados
echo    • Sección de troubleshooting en README
echo.

pause
