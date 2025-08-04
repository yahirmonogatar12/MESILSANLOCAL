@echo off
echo ========================================
echo  COPIADOR A PC DESTINO
echo ========================================
echo.

set /p destino="Ingresa la ruta de destino (ej: C:\SMTMonitor): "

if "%destino%"=="" (
    echo Error: Debes especificar una ruta de destino
    pause
    exit /b 1
)

echo.
echo Creando carpeta de destino...
mkdir "%destino%" 2>nul

echo Copiando archivos del servicio...
copy "smt_monitor_service.py" "%destino%\"
copy "smt_monitor_local.py" "%destino%\"
copy "instalar_servicio.bat" "%destino%\"
copy "desinstalar_servicio.bat" "%destino%\"
copy "administrar_servicio.bat" "%destino%\"
copy "probar_conexion_bd.py" "%destino%\"
copy "diagnostico_rapido.py" "%destino%\"
copy "comparar_archivos.py" "%destino%\"
copy "verificar_carpetas.py" "%destino%\"
copy "verificar_archivos.bat" "%destino%\"
copy "README_SERVICIO.md" "%destino%\" 2>nul

echo.
echo Creando carpeta scripts en destino...
mkdir "%destino%\scripts" 2>nul

echo Copiando monitor actualizado...
copy "..\scripts\smt_csv_monitor.py" "%destino%\scripts\" 2>nul

echo.
echo ============================================
echo  ARCHIVOS COPIADOS A: %destino%
echo ============================================
echo.
echo SIGUIENTE PASO EN LA PC DESTINO:
echo 1. Crear las carpetas de monitoreo:
echo    - C:\LOT CHECK  ALL\1line\L1 m1
echo    - C:\LOT CHECK  ALL\1line\L1 m2
echo    - C:\LOT CHECK  ALL\1line\L1 m3
echo    - C:\LOT CHECK  ALL\2line\L2 m1
echo    - C:\LOT CHECK  ALL\2line\L2 m2
echo    - C:\LOT CHECK  ALL\2line\L2 m3
echo    - C:\LOT CHECK  ALL\3line\L3 m1
echo    - C:\LOT CHECK  ALL\3line\L3 m2
echo    - C:\LOT CHECK  ALL\3line\L3 m3
echo    - C:\LOT CHECK  ALL\4line\L4 m1
echo    - C:\LOT CHECK  ALL\4line\L4 m2
echo    - C:\LOT CHECK  ALL\4line\L4 m3
echo.
echo 1. Ejecutar: verificar_archivos.bat (para comprobar que todos los archivos están presentes)
echo.
echo 2. Ejecutar como Administrador: instalar_servicio.bat
echo.
echo 3. Verificar conexion a base de datos: up-de-fra1-mysql-1.db.run-on-seenode.com:11550
echo.

pause
