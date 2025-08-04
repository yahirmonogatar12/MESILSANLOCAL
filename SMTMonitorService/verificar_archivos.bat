@echo off
echo ========================================
echo  VERIFICADOR DE ARCHIVOS SMT MONITOR
echo ========================================
echo.

cd /d "%~dp0"
echo Directorio actual: %cd%
echo.

echo Verificando archivos necesarios...
echo.

set archivos_ok=1

if exist "smt_monitor_service.py" (
    echo ✅ smt_monitor_service.py
) else (
    echo ❌ smt_monitor_service.py - FALTANTE
    set archivos_ok=0
)

if exist "smt_monitor_local.py" (
    echo ✅ smt_monitor_local.py
) else (
    echo ❌ smt_monitor_local.py - FALTANTE
    set archivos_ok=0
)

if exist "instalar_servicio.bat" (
    echo ✅ instalar_servicio.bat
) else (
    echo ❌ instalar_servicio.bat - FALTANTE
    set archivos_ok=0
)

if exist "desinstalar_servicio.bat" (
    echo ✅ desinstalar_servicio.bat
) else (
    echo ❌ desinstalar_servicio.bat - FALTANTE
    set archivos_ok=0
)

if exist "administrar_servicio.bat" (
    echo ✅ administrar_servicio.bat
) else (
    echo ❌ administrar_servicio.bat - FALTANTE
    set archivos_ok=0
)

if exist "probar_conexion_bd.py" (
    echo ✅ probar_conexion_bd.py
) else (
    echo ❌ probar_conexion_bd.py - FALTANTE
    set archivos_ok=0
)

if exist "diagnostico_rapido.py" (
    echo ✅ diagnostico_rapido.py
) else (
    echo ❌ diagnostico_rapido.py - FALTANTE
    set archivos_ok=0
)

if exist "comparar_archivos.py" (
    echo ✅ comparar_archivos.py
) else (
    echo ❌ comparar_archivos.py - FALTANTE
    set archivos_ok=0
)

if exist "verificar_carpetas.py" (
    echo ✅ verificar_carpetas.py
) else (
    echo ❌ verificar_carpetas.py - FALTANTE
    set archivos_ok=0
)

if exist "README_SERVICIO.md" (
    echo ✅ README_SERVICIO.md
) else (
    echo ❌ README_SERVICIO.md - FALTANTE
    set archivos_ok=0
)

echo.
echo ========================================

if %archivos_ok%==1 (
    echo ✅ TODOS LOS ARCHIVOS ESTÁN PRESENTES
    echo.
    echo El servicio SMT Monitor está listo para instalar.
    echo Ejecuta: instalar_servicio.bat como Administrador
) else (
    echo ❌ FALTAN ARCHIVOS NECESARIOS
    echo.
    echo Por favor, copia todos los archivos antes de continuar.
)

echo ========================================
echo.
pause
