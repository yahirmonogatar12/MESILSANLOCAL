$content = Get-Content 'c:\Users\yahir\OneDrive\Escritorio\ISEMM_MES\app\smt_routes_fixed.py'
$content[169] = '                PartName, Quantity, SEQ, Vendor,'
$newContent = $content[0..169] + '                PreviousBarcode, Productdate, FeederBase' + $content[170..($content.Length-1)]
$newContent | Set-Content 'c:\Users\yahir\OneDrive\Escritorio\ISEMM_MES\app\smt_routes_fixed.py'
