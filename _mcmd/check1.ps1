$ErrorActionPreference = 'Continue'
'=== LAIKAS ==='
Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz'
'=== HEALTHZ ==='
try { $r = Invoke-WebRequest -Uri 'http://127.0.0.1:5678/healthz' -TimeoutSec 10 -UseBasicParsing; 'healthz: ' + $r.StatusCode } catch { 'healthz KLAIDA: ' + $_.Exception.Message }
'=== PORTU KLAUSYMAS ==='
'5678 -> ' + ((Get-NetTCPConnection -LocalPort 5678 -State Listen -ErrorAction SilentlyContinue | Measure-Object).Count)
'5679 -> ' + ((Get-NetTCPConnection -LocalPort 5679 -State Listen -ErrorAction SilentlyContinue | Measure-Object).Count)
'=== PROCESAI ==='
Get-Process node,n8n -ErrorAction SilentlyContinue | Select-Object Id,ProcessName,@{n='MB';e={[math]::Round($_.WorkingSet64/1MB)}},StartTime | Format-Table -AutoSize | Out-String
'=== N8N KATALOGAS ==='
Get-ChildItem 'C:\Users\M\Desktop\Kumstis' -Force -ErrorAction SilentlyContinue | Select-Object Mode,@{n='KB';e={[math]::Round($_.Length/1KB,1)}},LastWriteTime,Name | Format-Table -AutoSize | Out-String
'=== N8N DB ==='
$db = 'C:\Users\M\Desktop\Kumstis\runtime\n8n-data\.n8n\database.sqlite'
if (Test-Path $db) { 'DB YRA: ' + [math]::Round((Get-Item $db).Length/1KB) + ' KB, ' + (Get-Item $db).LastWriteTime } else { 'DB NERA: ' + $db }
