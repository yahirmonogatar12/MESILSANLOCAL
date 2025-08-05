$filePath = 'c:\Users\yahir\OneDrive\Escritorio\ISEMM_MES\app\smt_routes_fixed.py'
$content = Get-Content $filePath

# Líneas que necesitan actualizar (según el resultado anterior)
# Línea 258: archivo, linea, maquina, PartName, Quantity, SEQ, Vendor
# Línea 268: archivo, linea, maquina, PartName, Quantity, SEQ, Vendor  
# Línea 340: archivo, linea, maquina, PartName, Quantity, SEQ, Vendor
# Línea 403: PartName, Quantity, SEQ, Vendor
# Línea 415: PartName, Quantity, SEQ, Vendor
# Línea 572: PartName, Quantity, SEQ, Vendor

# Actualizar línea 258 (debug endpoint con folder)
$content[257] = '                       archivo, linea, maquina, PartName, Quantity, SEQ, Vendor,'
$content = $content[0..257] + '                       PreviousBarcode, Productdate, FeederBase' + $content[258..($content.Length-1)]

# Actualizar línea 268+1 (debug endpoint sin folder) 
$content[268] = '                       archivo, linea, maquina, PartName, Quantity, SEQ, Vendor,'
$content = $content[0..268] + '                       PreviousBarcode, Productdate, FeederBase' + $content[269..($content.Length-1)]

# Actualizar línea 340+2 (tabla endpoint)
$content[341] = '                   archivo, linea, maquina, PartName, Quantity, SEQ, Vendor,'
$content = $content[0..341] + '                   PreviousBarcode, Productdate, FeederBase' + $content[342..($content.Length-1)]

# Actualizar línea 403+3 (historial/data con folder)
$content[406] = '                    PartName, Quantity, SEQ, Vendor,'
$content = $content[0..406] + '                    PreviousBarcode, Productdate, FeederBase' + $content[407..($content.Length-1)]

# Actualizar línea 415+4 (historial/data sin folder)
$content[419] = '                    PartName, Quantity, SEQ, Vendor,'
$content = $content[0..419] + '                    PreviousBarcode, Productdate, FeederBase' + $content[420..($content.Length-1)]

# Actualizar línea 572+5 (filter endpoint)
$content[577] = '                PartName, Quantity, SEQ, Vendor,'
$content = $content[0..577] + '                PreviousBarcode, Productdate, FeederBase' + $content[578..($content.Length-1)]

$content | Set-Content $filePath
Write-Host "Archivo actualizado con todas las columnas faltantes"
