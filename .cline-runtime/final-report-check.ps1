Write-Output '===== ATASKAITA DARBALAUKE ====='
Get-ChildItem -LiteralPath 'C:\Users\M\Desktop' -File | Where-Object {$_.Name -match 'ATASKAITA'} | Select-Object Name,Length,LastWriteTime | Format-Table -AutoSize
Write-Output '===== ATASKAITOS PRADZIA ====='
Get-Content -LiteralPath 'C:\Users\M\Desktop\CLINE_ATASKAITA_2026-10-25_VISKAS_AUTOMATIKA.md' -Encoding UTF8 -TotalCount 14
Write-Output '===== AUTOMATIKOS TILTAS ====='
& curl.exe -sS --max-time 8 'http://127.0.0.1:8792/health'
Write-Output ''
Write-Output '===== ZVERIS ====='
& curl.exe -sS -o NUL --max-time 8 -w 'zveris=%{http_code}' 'http://127.0.0.1:8091/'
Write-Output ''
Write-Output '===== F6 ====='
& curl.exe -sS -o NUL --max-time 8 -w 'f6=%{http_code}' 'http://127.0.0.1:8766/'
Write-Output ''
Write-Output '===== API LOG ====='
Get-Content -LiteralPath 'C:\Users\M\CLINE\AUTOMATION_API_LOG.txt' -Encoding UTF8 -Tail 4
