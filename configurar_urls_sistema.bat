@echo off
title Configurador de URLs del Sistema
echo =============================================
echo  CONFIGURADOR DE URLs - SERVIDOR PRINCIPAL
echo =============================================
echo.

echo 🌐 Configurar donde está hospedado el servidor principal
echo.
echo Opciones disponibles:
echo.
echo 1. Desarrollo Local    → http://localhost:5000
echo 2. IP Específica       → http://192.168.x.x:5000  
echo 3. Dominio Web         → https://mi-dominio.com
echo 4. Servidor Externo    → http://servidor:puerto
echo 5. Configuración Manual
echo.

set /p OPCION="Seleccione una opción (1-5): "

if "%OPCION%"=="1" (
    set NEW_URL=http://localhost:5000
    echo ✅ Configurando para desarrollo local...
    goto APLICAR
)

if "%OPCION%"=="2" (
    echo.
    echo Ingrese la IP del servidor (ejemplo: 192.168.0.211):
    set /p SERVER_IP="IP: "
    set /p SERVER_PORT="Puerto (presione Enter para 5000): "
    if "%SERVER_PORT%"=="" set SERVER_PORT=5000
    set NEW_URL=http://%SERVER_IP%:%SERVER_PORT%
    goto APLICAR
)

if "%OPCION%"=="3" (
    echo.
    echo Ingrese el dominio web (ejemplo: mi-sistema.com):
    set /p DOMAIN="Dominio: "
    echo.
    echo ¿Usar HTTPS? (S/N - recomendado S para producción):
    set /p USE_HTTPS="HTTPS: "
    if /i "%USE_HTTPS%"=="S" (
        set NEW_URL=https://%DOMAIN%
    ) else (
        set NEW_URL=http://%DOMAIN%
    )
    goto APLICAR
)

if "%OPCION%"=="4" (
    echo.
    echo Ingrese la URL del servidor externo:
    echo Ejemplo: http://mi-servidor.empresa.com:8080
    set /p NEW_URL="URL completa: "
    goto APLICAR
)

if "%OPCION%"=="5" (
    echo.
    echo Ingrese la URL completa del servidor principal:
    echo Ejemplos:
    echo   http://192.168.1.100:5000
    echo   https://sistema-mes.miempresa.com
    echo   http://servidor-central:8080
    set /p NEW_URL="URL: "
    goto APLICAR
)

echo ❌ Opción inválida
pause
exit /b 1

:APLICAR
echo.
echo 🔄 Aplicando configuración...
echo.
echo 📋 Nueva configuración:
echo    Servidor Principal: %NEW_URL%
echo    Servicio Impresión: http://localhost:5002 (no cambia)
echo.

REM Verificar que existe el archivo HTML
if not exist "app\templates\Control de material\Control de material de almacen.html" (
    echo ❌ ERROR: No se encuentra el archivo HTML principal
    echo Asegúrese de estar en la carpeta correcta del proyecto
    pause
    exit /b 1
)

REM Crear backup
echo 💾 Creando backup...
copy "app\templates\Control de material\Control de material de almacen.html" "app\templates\Control de material\Control de material de almacen.html.backup-%date:~-4,4%%date:~-10,2%%date:~-7,2%" >nul

REM Aplicar cambio usando PowerShell
echo 🔧 Actualizando configuración...
powershell -Command "& { $content = Get-Content 'app\templates\Control de material\Control de material de almacen.html' -Raw; $pattern = \"server_url: 'http://[^']*'\"; $replacement = \"server_url: '%NEW_URL%'\"; $newContent = $content -replace $pattern, $replacement; Set-Content 'app\templates\Control de material\Control de material de almacen.html' -Value $newContent }"

if %errorLevel% == 0 (
    echo ✅ Configuración aplicada exitosamente!
) else (
    echo ❌ Error aplicando configuración
    pause
    exit /b 1
)

echo.
echo 🎉 ¡CONFIGURACIÓN COMPLETADA!
echo.
echo 📊 Resumen de URLs:
echo    🌐 Servidor Principal: %NEW_URL%
echo    🖨️  Servicio Impresión: http://localhost:5002
echo.
echo 🚀 Próximos pasos:
echo    1. Reiniciar servidor Flask si está ejecutándose
echo    2. Probar acceso desde navegador: %NEW_URL%
echo    3. Verificar que la aplicación funciona correctamente
echo.
echo 💡 Nota: Si necesita cambiar nuevamente, ejecute este script otra vez
echo.
echo 📁 Backup creado en: Control de material de almacen.html.backup-YYYYMMDD
echo.
pause
