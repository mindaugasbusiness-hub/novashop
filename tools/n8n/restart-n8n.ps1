# restart-n8n.ps1 -- sustabdo ir iš naujo paleidžia n8n (:5678 + brokeris :5679)
# Tai yra skriptas, kurį kviečia pulto (:8790) mygtukas „Restartuoti n8n" per act('/restart-n8n').
# Naudojimas:
#   powershell -NoProfile -ExecutionPolicy Bypass -File restart-n8n.ps1
#   powershell -NoProfile -ExecutionPolicy Bypass -File restart-n8n.ps1 -TikStop
# Grąžina: 0 = gerai, 1 = nepavyko

[CmdletBinding()]
param(
    [switch]$TikStop
)

$ErrorActionPreference = 'Continue'
. (Join-Path $PSScriptRoot 'n8n-konfig.ps1')

$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'

# --- 1) Surasti n8n procesą (PID failas, tada -- pagal komandinę eilutę) ---
$pidNr = 0
$saved = Get-N8nPids
if ($saved.n8n) { $pidNr = [int]$saved.n8n }
if ($pidNr -le 0) { $pidNr = Get-N8nServerioProcesas }

# --- 2) Sustabdyti jį ir visus vaikus (task runner, brokeris) ---
if ($pidNr -gt 0) {
    $vaikai = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
                Where-Object { $_.ParentProcessId -eq $pidNr } | ForEach-Object { [int]$_.ProcessId })
    Write-N8nLog "RESTART: stabdau PID=$pidNr (vaikai: $($vaikai -join ', '))"
    Stop-Process -Id $pidNr -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 3
    foreach ($v in $vaikai) { Stop-Process -Id $v -Force -ErrorAction SilentlyContinue }
} else {
    Write-N8nLog "RESTART: n8n procesas nerastas -- bus paleistas nuo nulio"
}

# --- 3) Palaukti, kol prievadai 5678/5679 atsilaisvins (max 30 s) ---
for ($i = 0; $i -lt 15; $i++) {
    $uzimta = $false
    foreach ($p in $N8nKonfig.TikrinamiPrievadai) {
        if ((Test-PrievadasUzimtas -Port $p) -gt 0) { $uzimta = $true }
    }
    if (-not $uzimta) { break }
    Start-Sleep -Seconds 2
}

foreach ($p in $N8nKonfig.TikrinamiPrievadai) {
    $liko = Test-PrievadasUzimtas -Port $p
    if ($liko -gt 0) {
        Write-N8nLog "RESTART ĮSPĖJIMAS: prievadas $p vis dar užimtas (PID=$liko)"
    }
}

if ($TikStop) {
    Write-N8nLog "RESTART: -TikStop -- n8n sustabdytas, nepaleistas iš naujo"
    Write-Output "n8n sustabdytas (TikStop)."
    exit 0
}

# --- 4) Paleisti iš naujo per tą patį starto skriptą ---
$startScript = Join-Path $PSScriptRoot 'start-n8n.ps1'
& powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $startScript -Force
$rc = $LASTEXITCODE

if ($rc -eq 0) {
    Write-N8nLog "RESTART: baigtas sėkmingai ($stamp)"
    Write-Output "n8n perkrautas: http://127.0.0.1:5678 · brokeris :$($N8nKonfig.BrokerioPrievadas)"
} else {
    Write-N8nLog "RESTART: KLAIDA, start-n8n.ps1 grąžino $rc"
    Write-Output "n8n perkrovimas NEPAVYKO (kodas $rc). Žiūrėk $($N8nKonfig.WatchdogLog)"
}
exit $rc
