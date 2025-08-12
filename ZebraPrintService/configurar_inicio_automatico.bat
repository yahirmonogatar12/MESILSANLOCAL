@echo off
echo ===================================
echo  SOLUCION AUTOMATICA ALTERNATIVA
echo  Inicio automatico sin servicio Windows
echo ===================================
echo.

REM Verificar permisos
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ❌ EJECUTAR COMO ADMINISTRADOR
    pause
    exit /b 1
)

cd /d "%~dp0"

echo 1. Creando tarea programada...
echo.

REM Crear script de inicio automatico
echo @echo off > start_service_auto.bat
echo cd /d "%~dp0" >> start_service_auto.bat  
echo python print_service.py >> start_service_auto.bat

REM Crear tarea que se ejecute al inicio
schtasks /create /tn "ZebraPrintServiceAuto" /tr "%~dp0start_service_auto.bat" /sc onstart /ru SYSTEM /f

if %errorLevel% equ 0 (
    echo  Tarea programada creada exitosamente
    echo.
    echo 2. Configurando para ejecutar ahora...
    schtasks /run /tn "ZebraPrintServiceAuto"
    
    echo.
    echo  CONFIGURACION COMPLETADA
    echo.
    echo El servicio ahora se iniciara automaticamente:
    echo - Al encender la computadora
    echo - Como tarea del sistema  
    echo - En puerto 5003
    echo.
    echo Para gestionar:
    echo - taskschd.msc (Programador de tareas)
    echo - O usar gestionar_servicio.bat
    echo.
) else (
    echo ❌ Error creando tarea programada
)

pause
