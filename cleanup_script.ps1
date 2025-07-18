# Script para limpiar funciones de test y console.log excesivos
$filePath = "\\192.168.1.230\qa\ILSAN_MES\ISEMM_MES\app\templates\Control de material\Control de material de almacen.html"
$content = Get-Content $filePath -Raw

Write-Host "🧹 Iniciando limpieza masiva de funciones de test..."
Write-Host "📊 Líneas originales: $((Get-Content $filePath).Count)"

# Lista de funciones de test a eliminar completamente
$testFunctions = @(
    'window\.testEtiquetaPequena\s*=.*?};',
    'window\.mostrarLayoutPequeno\s*=.*?};',
    'window\.mostrarResumenQR\s*=.*?};',
    'window\.testFuentesGrandes\s*=.*?};',
    'window\.mostrarComparacionOptimizacion\s*=.*?};',
    'window\.testPlantillaProfesional\s*=.*?};',
    'window\.testGetCantidadActual\s*=.*?};',
    'window\.verificarCamposCantidad\s*=.*?};',
    'window\.verificarCantidadBD\s*=.*?};',
    'window\.testCantidadActual\s*=.*?};',
    'window\.diagnosticarCantidadCompleto\s*=.*?};',
    'window\.probarConCantidadEspecifica\s*=.*?};',
    'window\.testZPLConCantidad\s*=.*?};',
    'window\.testFuncionOriginalQueFunc\s*=.*?};',
    'window\.testImprimirConDatosEspecificos\s*=.*?};'
)

# Eliminar funciones de test
foreach ($func in $testFunctions) {
    $content = $content -replace $func, '', 'Singleline'
    Write-Host "✅ Eliminada función: $($func.Split('\.')[1].Split('\s')[0])"
}

# Limpiar console.log excesivos (mantener solo errores críticos)
$debugLogs = @(
    'console\.log\(''🧪.*?\);',
    'console\.log\(''🔤.*?\);',
    'console\.log\(''📊.*?\);',
    'console\.log\(''🏷️.*?\);',
    'console\.log\(''📐.*?\);',
    'console\.log\(''🎯.*?\);',
    'console\.log\(''✅.*TEST.*?\);',
    'console\.log\(''🔍.*===.*===.*?\);'
)

foreach ($log in $debugLogs) {
    $oldCount = ([regex]::Matches($content, $log)).Count
    $content = $content -replace $log, '', 'Singleline'
    if ($oldCount -gt 0) {
        Write-Host "🗑️ Eliminados $oldCount logs de debug: $($log.Substring(0,20))..."
    }
}

# Guardar archivo limpio
Set-Content -Path $filePath -Value $content -Encoding UTF8
Write-Host "📊 Líneas finales: $((Get-Content $filePath).Count)"
Write-Host "✅ Limpieza masiva completada!"
