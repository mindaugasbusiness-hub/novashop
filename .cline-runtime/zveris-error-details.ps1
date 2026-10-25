$dir='C:\Users\M\Desktop\pakeitimai 111\_zveris_watch'
Write-Output '===== PASKUTINIAI TRACEBACK ====='
foreach($name in @('ui-out.log','ui-err.log')){
 $p=Join-Path $dir $name
 Write-Output ('--- '+$name+' ---')
 Select-String -LiteralPath $p -Pattern 'Traceback|ERROR:|Exception|FileNotFound|Template|jinja|Unicode' -Context 2,18 -ErrorAction SilentlyContinue | Select-Object -Last 4 | Format-List
}
Write-Output '===== UI_APP PRADZIA ====='
Get-Content -LiteralPath (Join-Path $dir 'ui_app.py') -Encoding UTF8 -TotalCount 210
Write-Output '===== API STATUS ====='
& curl.exe -sS -i --max-time 8 'http://127.0.0.1:8091/api/status'
Write-Output "`n===== BRIDGE PING ====="
& curl.exe -sS -i --max-time 8 'http://127.0.0.1:18765/api/ping'
