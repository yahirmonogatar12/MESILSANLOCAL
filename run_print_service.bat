@echo off
title ILSAN Print Service - SOLO EJECUTAR
cd /d "%~dp0"

echo ================================
echo  ILSAN Print Service - Zebra ZT230
echo ================================
echo Directorio: %CD%
echo Fecha: %DATE% %TIME%
echo.

REM Verificar que existe el archivo del servicio
if not exist print_service.py (
    echo ❌ ERROR: print_service.py no encontrado
    echo.
    echo Archivos en el directorio:
    dir *.py
    pause
    exit /b 1
)

echo ✅ Archivo del servicio encontrado
echo.
echo 🚀 Iniciando servicio en http://localhost:5000
echo.
echo ⚠️  IMPORTANTE: Deje esta ventana abierta
echo ⚠️  Para detener: Presione Ctrl+C
echo.
echo ================================

REM Ejecutar directamente
python print_service.py

echo.
echo ================================
echo Servicio detenido.
echo ================================
pause
