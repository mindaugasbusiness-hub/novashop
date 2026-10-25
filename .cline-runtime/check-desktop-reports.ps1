Write-Output '===== DESKTOP FAILAI CLINE ====='
Get-ChildItem -LiteralPath 'C:\Users\M\Desktop' -File | Where-Object {$_.Name -match 'CLINE|ATASKAITA'} | Select-Object Name,Length,LastWriteTime | Format-Table -AutoSize
Write-Output '===== VISKAS 06 BUSENA ====='
Get-Content -LiteralPath 'C:\Users\M\CLINE\VISKAS\06_DABARTINE_BUSENA.md' -Encoding UTF8 -TotalCount 20
