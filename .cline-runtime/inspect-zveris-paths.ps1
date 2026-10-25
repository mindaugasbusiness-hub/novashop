$dir='C:\Users\M\Desktop\pakeitimai 111\_zveris_watch'
Write-Output '===== PROJEKTO STRUKTURA ====='
Get-ChildItem -LiteralPath $dir -Force | Select-Object Mode,Name,Length,LastWriteTime | Format-Table -AutoSize
Write-Output '===== INDEX FAILAI ====='
Get-ChildItem -LiteralPath $dir -Recurse -File -Filter 'index.html' -ErrorAction SilentlyContinue | Select-Object FullName,Length,LastWriteTime | Format-Table -AutoSize
Write-Output '===== KELIU PATIKRA ====='
foreach($p in @('C:\workspace\zveris\ui\static\index.html',(Join-Path $dir 'ui\static\index.html'),(Join-Path $dir 'static\index.html'),(Join-Path $dir 'agent'),(Join-Path $dir 'memory'),(Join-Path $dir 'uploads'))){Write-Output ($p+'|'+(Test-Path -LiteralPath $p))}
Write-Output '===== ROUTES API STATUS IR ROOT ====='
Select-String -LiteralPath (Join-Path $dir 'ui_app.py') -Pattern 'api/status|FileResponse|StaticFiles|@app.get\("/"' -Context 4,8 | Format-List
Write-Output '===== NETEISINGAI SUKURTA STRUKTURA (TIK PATIKRA) ====='
Get-ChildItem -LiteralPath 'C:\workspace\zveris' -Force -ErrorAction SilentlyContinue | Select-Object Mode,Name,LastWriteTime | Format-Table -AutoSize
