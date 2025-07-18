@echo off
echo ===================================
echo  SOLUCION INTEGRADA ZEBRA FLASK
echo ===================================
echo.

REM Verificar administrador
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ❌ DEBE EJECUTARSE COMO ADMINISTRADOR
    pause
    exit /b 1
)

cd /d "%~dp0"

echo 1. Deteniendo servicios anteriores...
sc stop ZebraPrintService >nul 2>&1
sc stop ZebraFlaskIntegrado >nul 2>&1
sc delete ZebraPrintService >nul 2>&1
sc delete ZebraFlaskIntegrado >nul 2>&1
timeout /t 3 /nobreak >nul

echo.
echo 2. Verificando dependencias...
python -c "import flask, flask_cors, win32print; print('✅ Todas las dependencias OK')" 2>nul
if %errorLevel% neq 0 (
    echo ⚠️  Instalando dependencias...
    pip install flask flask-cors pywin32
)

echo.
echo 3. Copiando servicio a disco local...
if not exist "C:\ZebraService" mkdir "C:\ZebraService"
copy "%~dp0zebra_flask_integrado.py" "C:\ZebraService\" >nul

echo.
echo 4. Instalando servicio integrado...
python "C:\ZebraService\zebra_flask_integrado.py" install
if %errorLevel% neq 0 (
    echo ❌ Error instalando servicio
    pause
    exit /b 1
)

echo.
echo 5. Configurando servicio...
sc config ZebraFlaskIntegrado start= auto
sc config ZebraFlaskIntegrado obj= LocalSystem

echo.
echo 6. Iniciando servicio...
sc start ZebraFlaskIntegrado
if %errorLevel% neq 0 (
    echo ⚠️  Servicio instalado pero no pudo iniciar automáticamente
    echo Intente iniciar manualmente desde services.msc
) else (
    echo ✅ Servicio iniciado correctamente
)

echo.
echo 7. Esperando inicio completo...
timeout /t 10 /nobreak >nul

echo.
echo 8. Probando conectividad...
powershell -Command "try { $r = Invoke-WebRequest -Uri 'http://localhost:5003' -UseBasicParsing -TimeoutSec 10; Write-Host '✅ SERVICIO FUNCIONANDO - Estado:' $r.StatusCode } catch { Write-Host '⚠️  Servicio iniciando o con problemas...' }"

echo.
echo ===================================
echo  INSTALACION COMPLETADA
echo ===================================
echo.
echo ✅ Servicio: ZebraFlaskIntegrado
echo ✅ Puerto: 5003  
echo ✅ Ubicación: C:\ZebraService\
echo ✅ Logs: C:\ZebraService\zebra_flask_service.log
echo.
echo Para gestionar:
echo - services.msc (buscar "Servicio Zebra Flask Integrado")
echo - Logs en: C:\ZebraService\zebra_flask_service.log
echo.
pause
