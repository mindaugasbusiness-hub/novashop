$ErrorActionPreference = 'Continue'
'=== LOG PRIES ==='
Get-Content 'C:\Users\M\CLINE\PRANESIMU_LOG.txt' -Tail 2 -Encoding UTF8
'=== TESTAS 1: be SMS ==='
$b1 = @{ tema = 'TESTAS n8n tiltas'; tekstas = 'Testas be SMS - tik ntfy ir log'; svarbu = $false } | ConvertTo-Json -Compress
try {
    $r1 = Invoke-RestMethod -Uri 'http://127.0.0.1:8791/pranesti' -Method POST -ContentType 'application/json' -Body $b1 -TimeoutSec 90
    'ATSAKYMAS: ' + ($r1 | ConvertTo-Json -Compress)
} catch { 'KLAIDA: ' + $_.Exception.Message }
'=== TESTAS 2: su -Svarbu (SMS) ==='
$b2 = @{ tema = 'TESTAS: SVETAINE NUKRITO'; tekstas = 'Testas su SMS - statusas 0, laikas ' + (Get-Date -Format 'HH:mm'); svarbu = $true } | ConvertTo-Json -Compress
try {
    $r2 = Invoke-RestMethod -Uri 'http://127.0.0.1:8791/pranesti' -Method POST -ContentType 'application/json' -Body $b2 -TimeoutSec 120
    'ATSAKYMAS: ' + ($r2 | ConvertTo-Json -Compress)
} catch { 'KLAIDA: ' + $_.Exception.Message }
'=== LOG PO (paskutines 10) ==='
Get-Content 'C:\Users\M\CLINE\PRANESIMU_LOG.txt' -Tail 10 -Encoding UTF8
'=== SERVERIO LOG ==='
Get-Content 'C:\Users\M\CLINE\tools\pranesti-server.log' -Tail 6 -Encoding UTF8 -ErrorAction SilentlyContinue
