$ErrorActionPreference = 'Continue'
$date = Get-Date -Format 'yyyy-MM-dd'
'=== 1) DB BACKUP ==='
$db = 'C:\Users\M\Desktop\Kumstis\runtime\n8n-data\.n8n\database.sqlite'
$bak = $db + '.bak-' + $date
if (-not (Test-Path $bak)) { Copy-Item $db $bak -Force; 'Backup sukurtas: ' + $bak + ' (' + [math]::Round((Get-Item $bak).Length/1MB,1) + ' MB)' } else { 'Backup jau yra: ' + $bak }
'=== 2) SERVERIO PALEIDIMAS ==='
$already = $false
try { $h = Invoke-WebRequest -Uri 'http://127.0.0.1:8791/healthz' -UseBasicParsing -TimeoutSec 5; if ($h.StatusCode -eq 200) { $already = $true } } catch { }
if ($already) {
    'Serveris jau veikia (8791)'
} else {
    $log = 'C:\Users\M\CLINE\tools\pranesti-server.out.log'
    $err = 'C:\Users\M\CLINE\tools\pranesti-server.err.log'
    $p = Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File','C:\Users\M\CLINE\tools\pranesti-server.ps1') -WindowStyle Hidden -PassThru -RedirectStandardOutput $log -RedirectStandardError $err
    $p.Id | Set-Content 'C:\Users\M\CLINE\tools\pranesti-server.pid' -Encoding Ascii
    'Paleistas PID=' + $p.Id
    for ($i = 0; $i -lt 15; $i++) {
        Start-Sleep -Seconds 1
        try { $h = Invoke-WebRequest -Uri 'http://127.0.0.1:8791/healthz' -UseBasicParsing -TimeoutSec 3; if ($h.StatusCode -eq 200) { 'healthz OK po ' + ($i+1) + ' s'; break } } catch { }
    }
}
'=== 3) BUSENA ==='
try { $h = Invoke-WebRequest -Uri 'http://127.0.0.1:8791/healthz' -UseBasicParsing -TimeoutSec 5; 'healthz: ' + $h.StatusCode + ' | ' + $h.Content } catch { 'healthz KLAIDA: ' + $_.Exception.Message }
'8791 klauso: ' + ((Get-NetTCPConnection -LocalPort 8791 -State Listen -ErrorAction SilentlyContinue | Measure-Object).Count)
Get-Process powershell -ErrorAction SilentlyContinue | Select-Object Id,StartTime | Format-Table -AutoSize | Out-String
