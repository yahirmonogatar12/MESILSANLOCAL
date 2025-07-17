@echo off
echo ===================================
echo  SERVICIO DE IMPRESION LOCAL
echo ===================================
echo.
echo Este servicio permite imprimir en la impresora
echo LOCAL de ESTA maquina, no en el servidor.
echo.

REM Cambiar al directorio donde está el script
cd /d "%~dp0"
echo Directorio de trabajo: %CD%
echo.

echo Instalando dependencias...
pip install flask flask-cors pywin32

echo.
echo Iniciando servicio de impresion local...
python "%~dp0print_service.py"

pause
