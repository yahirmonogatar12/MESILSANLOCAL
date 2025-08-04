@echo off
echo Reconfigurando servicio SMT Monitor para usuario actual...
echo.

:: Obtener información del usuario actual
set CURRENT_USER=%USERNAME%
set CURRENT_DOMAIN=%USERDOMAIN%

echo Usuario actual: %CURRENT_DOMAIN%\%CURRENT_USER%
echo.

:: Detener el servicio si está corriendo
echo Deteniendo servicio SMT Monitor...
sc stop SMTMonitorService >nul 2>&1

:: Esperar a que se detenga
timeout /t 3 /nobreak >nul

:: Reconfigurar el servicio para ejecutarse como usuario actual
echo Reconfigurando servicio para usuario %CURRENT_DOMAIN%\%CURRENT_USER%...
sc config SMTMonitorService obj= "%CURRENT_DOMAIN%\%CURRENT_USER%" password= ""

if %errorlevel% neq 0 (
    echo.
    echo ERROR: No se pudo reconfigurar el servicio.
    echo Esto puede ser porque:
    echo 1. Se requiere contraseña para el usuario
    echo 2. El usuario no tiene permisos de "Logon as a service"
    echo.
    echo Intentando configurar permisos de servicio...
    
    :: Intentar otorgar permiiso "Log on as a service"
    echo Configurando permisos "Log on as a service" para %CURRENT_USER%...
    secedit /export /cfg temp_policy.inf >nul 2>&1
    
    :: Verificar si el usuario ya tiene el permiso
    findstr /C:"SeServiceLogonRight" temp_policy.inf | findstr /C:"%CURRENT_USER%" >nul
    if %errorlevel% neq 0 (
        echo Agregando permiso "Log on as a service"...
        powershell -Command "& {$policy = Get-Content 'temp_policy.inf'; $policy = $policy -replace '(SeServiceLogonRight = .*)', '$1,%CURRENT_DOMAIN%\%CURRENT_USER%'; $policy | Set-Content 'temp_policy_new.inf'}" >nul 2>&1
        secedit /configure /db temp_policy.sdb /cfg temp_policy_new.inf >nul 2>&1
        del temp_policy.inf temp_policy_new.inf temp_policy.sdb >nul 2>&1
    ) else (
        echo Usuario ya tiene permisos de servicio.
        del temp_policy.inf >nul 2>&1
    )
    
    :: Intentar reconfigurar nuevamente
    echo Intentando reconfigurar servicio nuevamente...
    sc config SMTMonitorService obj= "%CURRENT_DOMAIN%\%CURRENT_USER%" password= ""
)

if %errorlevel% equ 0 (
    echo ✓ Servicio reconfigurado exitosamente
    echo.
    
    :: Iniciar el servicio
    echo Iniciando servicio SMT Monitor...
    sc start SMTMonitorService
    
    if %errorlevel% equ 0 (
        echo ✓ Servicio iniciado exitosamente
        echo.
        echo El servicio ahora se ejecuta como: %CURRENT_DOMAIN%\%CURRENT_USER%
        echo Esto debería resolver el problema de acceso a las carpetas.
        echo.
        echo Verificando estado del servicio...
        sc query SMTMonitorService
    ) else (
        echo.
        echo ERROR: No se pudo iniciar el servicio.
        echo Verifica los logs en: C:\SMTMonitor\smt_monitor_service.log
    )
) else (
    echo.
    echo ERROR: No se pudo reconfigurar el servicio.
    echo.
    echo OPCIONES ALTERNATIVAS:
    echo 1. Ejecutar este script como Administrador
    echo 2. Configurar manualmente en services.msc:
    echo    - Abrir services.msc
    echo    - Buscar "SMT CSV Monitor Service" 
    echo    - Clic derecho → Properties → Log On
    echo    - Seleccionar "This account": %CURRENT_DOMAIN%\%CURRENT_USER%
    echo    - Dejar password en blanco si no tienes contraseña
    echo 3. Dar permisos explícitos a SYSTEM para C:\LOT CHECK  ALL
)

echo.
echo Script completado.
pause
