@echo off
cd /d "%~dp0"
echo.
echo ===============================================
echo INSTALADOR DE SERVICIO SMT MONITOR (CORREGIDO)
echo ===============================================
echo.

:: Verificar permisos de administrador
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Este script debe ejecutarse como Administrador
    echo.
    echo Para ejecutar como administrador:
    echo 1. Clic derecho en el archivo .bat
    echo 2. Seleccionar "Ejecutar como administrador"
    echo.
    pause
    exit /b 1
)

echo ✓ Ejecutandose como Administrador
echo.

:: Verificar que los archivos necesarios existen
echo Verificando archivos necesarios...
if not exist "smt_monitor_service.py" (
    echo ERROR: smt_monitor_service.py no encontrado
    pause
    exit /b 1
)

echo ✓ Archivo smt_monitor_service.py encontrado
echo.

:: Verificar Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python no encontrado en PATH
    echo Instala Python 3.7+ y agregalo al PATH del sistema
    pause
    exit /b 1
)

echo ✓ Python encontrado:
python --version
echo.

:: Verificar/instalar dependencias de Python
echo Verificando dependencias de Python...
python -c "import mysql.connector" >nul 2>&1
if %errorlevel% neq 0 (
    echo Instalando mysql-connector-python...
    pip install mysql-connector-python
)

python -c "import pywin32" >nul 2>&1
if %errorlevel% neq 0 (
    echo Instalando pywin32...
    pip install pywin32
)

echo ✓ Dependencias verificadas
echo.

:: Detener y desinstalar servicio existente si existe
echo Limpiando instalacion previa...
sc query SMTMonitorService >nul 2>&1
if %errorlevel% equ 0 (
    echo Deteniendo servicio existente...
    sc stop SMTMonitorService >nul 2>&1
    timeout /t 3 /nobreak >nul
    
    echo Desinstalando servicio existente...
    sc delete SMTMonitorService >nul 2>&1
    timeout /t 2 /nobreak >nul
)

:: Crear directorio de destino
set INSTALL_DIR=C:\SMTMonitor
echo Creando directorio de instalacion: %INSTALL_DIR%
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

:: Copiar archivos
echo Copiando archivos al directorio de instalacion...
copy "smt_monitor_service.py" "%INSTALL_DIR%\" >nul
if exist "smt_monitor_local.py" copy "smt_monitor_local.py" "%INSTALL_DIR%\" >nul

echo ✓ Archivos copiados
echo.

:: Crear carpetas de monitoreo si no existen
echo Verificando/creando carpetas de monitoreo...
set BASE_PATH=C:\LOT CHECK  ALL

if not exist "%BASE_PATH%" (
    echo ADVERTENCIA: Carpeta base no encontrada: %BASE_PATH%
    echo Creando estructura de carpetas...
    mkdir "%BASE_PATH%" 2>nul
)

:: Crear subcarpetas
mkdir "%BASE_PATH%\1line" 2>nul
mkdir "%BASE_PATH%\1line\L1 m1" 2>nul
mkdir "%BASE_PATH%\1line\L1 m2" 2>nul
mkdir "%BASE_PATH%\1line\L1 m3" 2>nul

mkdir "%BASE_PATH%\2line" 2>nul
mkdir "%BASE_PATH%\2line\L2 m1" 2>nul
mkdir "%BASE_PATH%\2line\L2 m2" 2>nul
mkdir "%BASE_PATH%\2line\L2 m3" 2>nul

mkdir "%BASE_PATH%\3line" 2>nul
mkdir "%BASE_PATH%\3line\L3 m1" 2>nul
mkdir "%BASE_PATH%\3line\L3 m2" 2>nul
mkdir "%BASE_PATH%\3line\L3 m3" 2>nul

mkdir "%BASE_PATH%\4line" 2>nul
mkdir "%BASE_PATH%\4line\L4 m1" 2>nul
mkdir "%BASE_PATH%\4line\L4 m2" 2>nul
mkdir "%BASE_PATH%\4line\L4 m3" 2>nul

echo ✓ Estructura de carpetas verificada
echo.

:: Instalar el servicio
echo Instalando servicio SMT Monitor...
cd /d "%INSTALL_DIR%"
python smt_monitor_service.py install

if %errorlevel% neq 0 (
    echo ERROR: Fallo la instalacion del servicio
    echo Verifica que Python y las dependencias esten correctamente instaladas
    pause
    exit /b 1
)

echo ✓ Servicio instalado exitosamente
echo.

:: Configurar el servicio
echo Configurando servicio...
sc config SMTMonitorService start= auto
sc config SMTMonitorService DisplayName= "SMT CSV Monitor Service"

:: Otorgar permisos a SYSTEM para acceder a las carpetas
echo Otorgando permisos a SYSTEM para carpetas de monitoreo...
icacls "%BASE_PATH%" /grant "NT AUTHORITY\SYSTEM:(OI)(CI)F" /T >nul 2>&1

if %errorlevel% equ 0 (
    echo ✓ Permisos otorgados exitosamente
) else (
    echo ADVERTENCIA: No se pudieron otorgar algunos permisos
)

:: Iniciar el servicio
echo.
echo Iniciando servicio SMT Monitor...
sc start SMTMonitorService

if %errorlevel% equ 0 (
    echo ✓ Servicio iniciado exitosamente
    echo.
    echo ================================================
    echo ✅ INSTALACION COMPLETADA EXITOSAMENTE ✅
    echo ================================================
    echo.
    echo Configuracion del servicio:
    echo - Nombre: SMTMonitorService
    echo - Inicio: Automatico
    echo - Carpetas monitoreadas: %BASE_PATH%
    echo - Log del servicio: %INSTALL_DIR%\smt_monitor_service.log
    echo.
    echo Verificando estado del servicio...
    sc query SMTMonitorService
    echo.
    echo El servicio esta monitoreando las siguientes carpetas:
    echo    - %BASE_PATH%\1line\L1 m1
    echo    - %BASE_PATH%\1line\L1 m2  
    echo    - %BASE_PATH%\1line\L1 m3
    echo    - %BASE_PATH%\2line\L2 m1
    echo    - %BASE_PATH%\2line\L2 m2
    echo    - %BASE_PATH%\2line\L2 m3
    echo    - %BASE_PATH%\3line\L3 m1
    echo    - %BASE_PATH%\3line\L3 m2
    echo    - %BASE_PATH%\3line\L3 m3
    echo    - %BASE_PATH%\4line\L4 m1
    echo    - %BASE_PATH%\4line\L4 m2
    echo    - %BASE_PATH%\4line\L4 m3
    echo.
    echo Para verificar funcionamiento:
    echo 1. Revisa el log: %INSTALL_DIR%\smt_monitor_service.log
    echo 2. Coloca archivos CSV en las carpetas monitoreadas
    echo 3. Verifica que se procesen en la base de datos
    
) else (
    echo ERROR: No se pudo iniciar el servicio
    echo.
    echo Pasos para diagnosticar:
    echo 1. Revisa el log: %INSTALL_DIR%\smt_monitor_service.log
    echo 2. Verifica la configuracion de la base de datos
    echo 3. Ejecuta: sc query SMTMonitorService
    echo 4. Ejecuta: python "%INSTALL_DIR%\smt_monitor_local.py" para test manual
)

echo.
echo Instalacion completada.
pause
