$dir='C:\Users\M\Desktop\pakeitimai 111\_zveris_watch'
Write-Output '===== HTTP 8091 ====='
& curl.exe -sS -i --max-time 10 'http://127.0.0.1:8091/'
Write-Output "`n===== UI-OUT ====="
Get-Content -LiteralPath (Join-Path $dir 'ui-out.log') -Encoding UTF8 -Tail 100 -ErrorAction SilentlyContinue
Write-Output "`n===== UI-ERR ====="
Get-Content -LiteralPath (Join-Path $dir 'ui-err.log') -Encoding UTF8 -Tail 100 -ErrorAction SilentlyContinue
Write-Output "`n===== KEEPALIVE LOG ====="
Get-Content -LiteralPath (Join-Path $dir 'zveris_keepalive.log') -Encoding UTF8 -Tail 60 -ErrorAction SilentlyContinue
Write-Output "`n===== UI_APP FAILAS ====="
Get-Item -LiteralPath (Join-Path $dir 'ui_app.py') | Select-Object FullName,Length,LastWriteTime | Format-List
Write-Output "`n===== ROUTES IR ENDPOINTAI ====="
Select-String -LiteralPath (Join-Path $dir 'ui_app.py') -Pattern '^@app|^async def|^def |8091|smegen|busena|json' | Select-Object -First 140 LineNumber,Line | Format-Table -AutoSize
Write-Output "`n===== KEEPALIVE KODAS ====="
Get-Content -LiteralPath 'C:\Users\M\AppData\Local\Zveris\keepalive.ps1' -Raw -Encoding UTF8
