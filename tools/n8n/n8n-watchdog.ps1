# n8n-watchdog.ps1 -- kas ciklą patikrina :5678 ir :5679 ir prikelia n8n, jei krenta.
#
# Du režimai:
#   1) VIENKARTINIS (numatytas) -- tinka Task Scheduler užduočiai „kas 1 minutę":
#        powershell -NoProfile -ExecutionPolicy Bypass -File n8n-watchdog.ps1
#   2) CIKLAS -- jei nori vieno nuolatinio proceso (be Task Scheduler):
#        powershell -NoProfile -ExecutionPolicy Bypass -File n8n-watchdog.ps1 -Loop
#
# Apsaugos (kad budėtojas pats neprikurtų dviejų n8n):
#   * startas praleidžiamas, jei /healthz jau atsako 200;
#   * startas praleidžiamas, jei yra „booting" žyma jaunesnė nei 120 s (n8n dar kyla);
#   * vienu metu leidžiamas tik VIENAS budėtojas (mutex failas su PID);
#   * jei prievadą laiko svetimas procesas -- NIEKO NEŽUDOME, tik rašome į žurnalą.
#
# Grąžina: 0 = viskas veikia arba paleista, 1 = nepavyko prikelti, 2 = kitas budėtojas veikia

[CmdletBinding()]
param(
    [switch]$Loop,
    [int]$Intervalas = 0
)

$ErrorActionPreference = 'Continue'
. (Join-Path $PSScriptRoot 'n8n-konfig.ps1')

if ($Intervalas -le 0) { $Intervalas = $N8nKonfig.BudetojoIntervalas }

$muzoFailas = Join-Path $N8nKonfig.LogsDir 'n8n-watchdog.pid'

function Test-BudetojasVienintelis {
    if (Test-Path -LiteralPath $muzoFailas) {
        $senasPid = 0
        try { $senasPid = [int](Get-Content -LiteralPath $muzoFailas -Raw).Trim() } catch { $senasPid = 0 }
        if ($senasPid -gt 0 -and $senasPid -ne $PID) {
            $gyvas = Get-Process -Id $senasPid -ErrorAction SilentlyContinue
            if ($gyvas) { return $false }
        }
        # negyvas arba tuščias -- perimam
        Remove-Item -LiteralPath $muzoFailas -Force -ErrorAction SilentlyContinue
    }
    Set-Content -LiteralPath $muzoFailas -Value "$PID" -Encoding UTF8
    return $true
}

# Sprendimas ateina iš Get-N8nBusena (n8n-konfig.ps1) -- ten jis ir testuojamas.
function Invoke-VienasCiklas {
    $busena = Get-N8nBusena
    switch ($busena) {
        'GERAI'     { return 'GERAI' }
        'PERKRAUTI' { Write-N8nLog "WATCHDOG: serveris atsako, bet brokeris :$($N8nKonfig.BrokerioPrievadas) neklauso -- perkraunu"; return 'PERKRAUTI' }
        'SVETIMAS'  {
            $uzemejas = Test-PrievadasUzimtas -Port $N8nKonfig.ServerioPrievadas
            Write-N8nLog "WATCHDOG: /healthz neatsako, bet :$($N8nKonfig.ServerioPrievadas) laiko PID=$uzemejas -- nekillinu, reikia žmogaus"
            return 'SVETIMAS'
        }
        'KYLA'      { Write-N8nLog "WATCHDOG: n8n dar kyla (booting žyma) -- startas praleistas"; return 'KYLA' }
        default     { Write-N8nLog "WATCHDOG: n8n NEVEIKIA -- paleidžiu start-n8n.ps1"; return 'PALEISTI' }
    }
}

function Invoke-Paleidimas {
    $startScript = Join-Path $PSScriptRoot 'start-n8n.ps1'
    & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $startScript -Tyliai | Out-Null
    return $LASTEXITCODE
}

if (-not (Test-Path -LiteralPath $N8nKonfig.LogsDir)) {
    New-Item -ItemType Directory -Force -Path $N8nKonfig.LogsDir | Out-Null
}

if (-not (Test-BudetojasVienintelis)) {
    Write-Output "Kitas budėtojas jau veikia -- šis baigia darbą."
    exit 2
}

try {
    if (-not $Loop) {
        $busena = Invoke-VienasCiklas
        $rc = 0
        if ($busena -eq 'PALEISTI' -or $busena -eq 'PERKRAUTI') {
            $rc = Invoke-Paleidimas
            if ($rc -eq 0) { Write-N8nLog "WATCHDOG: prikelta sėkmingai" }
            else { Write-N8nLog "WATCHDOG: prikėlimas NEPAVYKO (kodas $rc)" }
        }
        Write-Output "Budėtojas: $busena (kodas $rc)"
        exit $rc
    }

    Write-N8nLog "WATCHDOG: ciklinis režimas, intervalas $Intervalas s"
    while ($true) {
        $busena = Invoke-VienasCiklas
        if ($busena -eq 'PALEISTI' -or $busena -eq 'PERKRAUTI') {
            $rc = Invoke-Paleidimas
            Write-N8nLog "WATCHDOG: startas grąžino $rc"
        }
        Start-Sleep -Seconds $Intervalas
    }
} finally {
    Remove-Item -LiteralPath $muzoFailas -Force -ErrorAction SilentlyContinue
}
