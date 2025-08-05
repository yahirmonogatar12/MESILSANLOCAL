@echo off
echo Mapeando unidad de red para SMT Monitor...
net use Z:: \\100.79.250.73\LOT CHECK  ALL /user:a1234* /persistent:yes
if %errorlevel% == 0 (
    echo ✅ Unidad mapeada exitosamente
) else (
    echo ❌ Error mapeando unidad
)
pause
