$ErrorActionPreference = 'Continue'
'=== C:\Users\M\CLINE\n8n ==='
Get-ChildItem 'C:\Users\M\CLINE\n8n' -Force -ErrorAction SilentlyContinue | Select-Object Name,Length,LastWriteTime | Format-Table -AutoSize | Out-String
'=== C:\Users\M\CLINE\tools (nauji failai) ==='
Get-ChildItem 'C:\Users\M\CLINE\tools' -Filter '*pranesti*' | Select-Object Name,Length,LastWriteTime | Format-Table -AutoSize | Out-String
'=== serverio PID failas ==='
Get-Content 'C:\Users\M\CLINE\tools\pranesti-server.pid' -ErrorAction SilentlyContinue
'8791 klauso: ' + ((Get-NetTCPConnection -LocalPort 8791 -State Listen -ErrorAction SilentlyContinue | Measure-Object).Count)
try { $h = Invoke-WebRequest 'http://127.0.0.1:8791/healthz' -UseBasicParsing -TimeoutSec 5; 'healthz: ' + $h.StatusCode } catch { 'healthz KLAIDA: ' + $_.Exception.Message }
'=== backup failai ==='
Get-ChildItem 'C:\Users\M\Desktop\Kumstis\runtime\n8n-data\.n8n' -Filter '*.bak-*' | Select-Object Name,@{n='MB';e={[math]::Round($_.Length/1MB,1)}} | Format-Table -AutoSize | Out-String
'=== startup nuoroda (pakartotinai) ==='
$p1 = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\CLINE-N8N.lnk"
'CLINE-N8N.lnk: ' + (Test-Path $p1)
