$ErrorActionPreference = 'Continue'
'=== PASKUTINIS PERKROVIMAS ==='
$os = Get-CimInstance Win32_OperatingSystem
'LastBootUpTime: ' + $os.LastBootUpTime
'Dabar         : ' + (Get-Date)
'=== n8n PROCESU PRADZIA ==='
Get-Process node -ErrorAction SilentlyContinue | Select-Object Id,@{n='MB';e={[math]::Round($_.WorkingSet64/1MB)}},StartTime | Sort-Object StartTime | Format-Table -AutoSize | Out-String
'=== pids.json ==='
Get-Content 'C:\Users\M\Desktop\Kumstis\runtime\pids.json' -ErrorAction SilentlyContinue
'=== n8n-autostart.log (paskutines 25 eil.) ==='
$al = 'C:\Users\M\Desktop\Kumstis\runtime\logs\n8n-autostart.log'
if (Test-Path $al) { 'Failas yra, ' + [math]::Round((Get-Item $al).Length/1KB,1) + ' KB, keistas ' + (Get-Item $al).LastWriteTime; Get-Content $al -Tail 25 -Encoding UTF8 } else { 'n8n-autostart.log NERA - start-n8n.cmd dar nebuvo paleistas per autostart' }
'=== runtime\logs ==='
Get-ChildItem 'C:\Users\M\Desktop\Kumstis\runtime\logs' -ErrorAction SilentlyContinue | Select-Object Name,@{n='KB';e={[math]::Round($_.Length/1KB,1)}},LastWriteTime | Sort-Object LastWriteTime | Format-Table -AutoSize | Out-String
'=== STARTUP NUORODOS BUSENA ==='
Get-ChildItem "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup" -Force | Select-Object Name,LastWriteTime | Format-Table -AutoSize | Out-String
'=== AR YRA UZDUOCIUS PLANUOTOJAS n8n ==='
Get-ScheduledTask -ErrorAction SilentlyContinue | Where-Object { $_.TaskName -match 'n8n|cline|kumstis' } | Select-Object TaskName,State | Format-Table -AutoSize | Out-String
