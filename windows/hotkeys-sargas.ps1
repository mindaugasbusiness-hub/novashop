# F6-F11 KLAVISU SARGAS
# Tikrina kas minute, ar gyvas F-klavisu daemonas ir F6 dainu panelis; jei mire - prikelia.
# Kodel reikia: daemonas laiko ir klavisus (F6-F11), ir F6 paneli (:8766).
# Jam mirus, nustoja veikti IR F6, IR F9/F10 - butent taip ir buvo.
# Rankinis paleidimas: powershell -ExecutionPolicy Bypass -File hotkeys-sargas.ps1
param([switch]$Tyliu)

$ErrorActionPreference = 'SilentlyContinue'
$CLINE = 'C:\Users\M\CLINE'
$dir   = 'C:\Users\M\Desktop\pakeitimai 111'
$log   = Join-Path $CLINE 'HOTKEYS_SARGAS_LOG.txt'
$pyw   = 'C:\Users\M\AppData\Local\Programs\Python\Python312\pythonw.exe'
$sk    = Join-Path $dir '_vilkas_global_hotkeys.py'
$panel = Join-Path $dir '_desk_dainu_panelis.py'

function Log($m) {
    Add-Content -Path $log -Value ((Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + '  ' + $m) -Encoding UTF8
    if (-not $Tyliu) { Write-Host $m }
}
function Daemonas {
    Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -match '_vilkas_global_hotkeys' }
}
function PortUp($p) {
    (Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue | Measure-Object).Count -gt 0
}

$keiciau = $false

# 1) F-klavisu daemonas (F6-F11)
$d = Daemonas
if (-not $d) {
    $keiciau = $true
    Log 'daemonas NUKRITES - prikeliu'
    if ((Test-Path $pyw) -and (Test-Path $sk)) {
        Start-Process -FilePath $pyw -ArgumentList @('-X','utf8',('"' + $sk + '"')) -WorkingDirectory $dir -WindowStyle Hidden
        Start-Sleep -Seconds 5
        $d2 = Daemonas
        if ($d2) { Log ('daemonas VEIKIA (PID ' + $d2.ProcessId + ')') } else { Log 'daemonas VIS DAR NEVEIKIA' }
    } else {
        Log 'NERA pythonw.exe arba _vilkas_global_hotkeys.py'
    }
}

# 2) F6 dainu panelis (:8766)
if (-not (PortUp 8766)) {
    $keiciau = $true
    Log 'F6 panelis (:8766) NUKRITES - prikeliu'
    if (Test-Path $panel) {
        Start-Process -FilePath $pyw -ArgumentList @('-X','utf8',('"' + $panel + '"')) -WorkingDirectory $dir -WindowStyle Hidden
        Start-Sleep -Seconds 4
        if (PortUp 8766) { Log ':8766 KLAUSO' } else { Log ':8766 VIS DAR NE' }
    } else {
        Log 'NERA _desk_dainu_panelis.py'
    }
}

# 3) logas neturi augti be ribos
if ((Test-Path $log) -and ((Get-Item $log).Length -gt 1MB)) {
    Set-Content -Path $log -Value (Get-Content $log -Tail 500 -Encoding UTF8) -Encoding UTF8
}

if (-not $Tyliu) {
    if ($keiciau) { Write-Host 'buvo pataisyta' } else { Write-Host 'viskas gerai' }
}