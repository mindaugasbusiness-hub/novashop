# n8n-diagnostika.ps1 -- vieno ekrano n8n būklės ataskaita (nieko NEKEIČIA, tik rodo).
# Naudojimas:
#   powershell -NoProfile -ExecutionPolicy Bypass -File n8n-diagnostika.ps1
#   powershell -NoProfile -ExecutionPolicy Bypass -File n8n-diagnostika.ps1 -Issaugoti
# Grąžina: 0 = viskas veikia, 1 = yra problemų

[CmdletBinding()]
param([switch]$Issaugoti)

$ErrorActionPreference = 'Continue'
. (Join-Path $PSScriptRoot 'n8n-konfig.ps1')

$eilutes = New-Object System.Collections.Generic.List[string]
function Add-Eil([string]$t) { $script:eilutes.Add($t) }

$problemu = 0

Add-Eil "===== n8n DIAGNOSTIKA $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ====="
Add-Eil "Root:      $($N8nKonfig.Root)"
Add-Eil "Node:      $($N8nKonfig.Node)  (yra: $(Test-Path -LiteralPath $N8nKonfig.Node))"
Add-Eil "n8n bin:   $($N8nKonfig.N8nBin)  (yra: $(Test-Path -LiteralPath $N8nKonfig.N8nBin))"
Add-Eil "Duomenys:  $($N8nKonfig.DataDir)"
Add-Eil ""

# --- 1) Sveikata ---
$sveikas = Test-N8nSveikas
Add-Eil "1) /healthz :5678 -> $(if ($sveikas) { 'VEIKIA (200)' } else { 'NEVEIKIA' })"
if (-not $sveikas) { $problemu++ }

# --- 2) Prievadai ir jų PID ---
Add-Eil ""
Add-Eil "2) PRIEVADAI (Get-NetTCPConnection, LISTEN)"
foreach ($p in $N8nKonfig.TikrinamiPrievadai) {
    $uz = Test-PrievadasUzimtas -Port $p
    if ($uz -gt 0) {
        $pr = Get-Process -Id $uz -ErrorAction SilentlyContinue
        $wmi = Get-CimInstance Win32_Process -Filter "ProcessId=$uz" -ErrorAction SilentlyContinue
        $start = ''
        try { $start = (Get-Process -Id $uz).StartTime.ToString('yyyy-MM-dd HH:mm:ss') } catch { }
        Add-Eil ("   {0} -> PID {1} ({2}, pradžia {3})" -f $p, $uz, $pr.ProcessName, $start)
        if ($wmi -and $wmi.CommandLine) {
            $cl = $wmi.CommandLine
            if ($cl.Length -gt 150) { $cl = $cl.Substring(0, 150) + '...' }
            Add-Eil "        cmd: $cl"
        }
    } else {
        Add-Eil "   $p -> LAISVAS (niekas neklauso)"
        if ($p -eq 5679 -and $sveikas) {
            Add-Eil "        ĮSPĖJIMAS: serveris veikia, bet brokeris neklauso"
            $problemu++
        }
    }
}

# --- 3) Ar 5678 ir 5679 laiko TAS PATS PID (normalu) ---
Add-Eil ""
$pid5678 = Test-PrievadasUzimtas -Port 5678
$pid5679 = Test-PrievadasUzimtas -Port 5679
if ($pid5678 -gt 0 -and $pid5678 -eq $pid5679) {
    Add-Eil "3) 5678 ir 5679 laiko tas pats PID ($pid5678) -> NORMALU."
    Add-Eil "   5679 yra n8n Task Broker (N8N_RUNNERS_TASK_BROKER_PORT), ne antras n8n."
} elseif ($pid5678 -gt 0 -and $pid5679 -gt 0) {
    Add-Eil "3) 5678 (PID $pid5678) ir 5679 (PID $pid5679) -- SKIRTINGI procesai!"
    Add-Eil "   Tai reiškia du n8n egzempliorius. Vieną reikia uždaryti."
    $problemu++
} else {
    Add-Eil "3) Prievadų būsena: 5678=$pid5678, 5679=$pid5679"
}

# --- 4) Windows rezervuoti prievadai (Hyper-V po perkrovimo) ---
Add-Eil ""
Add-Eil "4) WINDOWS REZERVUOTI TCP PRIEVADAI (netsh excludedportrange)"
try {
    $raw = (netsh int ipv4 show excludedportrange protocol=tcp) 2>&1
    $rezervuota = @()
    foreach ($eil in $raw) {
        if ("$eil" -match '^\s*(\d+)\s+(\d+)\s*$') {
            $nuo = [int]$Matches[1]; $iki = [int]$Matches[2]
            Add-Eil ("   diapazonas {0}-{1}" -f $nuo, $iki)
            foreach ($p in @(5678, 5679)) {
                if ($p -ge $nuo -and $p -le $iki) { $rezervuota += $p }
            }
        }
    }
    if ($rezervuota.Count -gt 0) {
        $unikalus = $rezervuota | Select-Object -Unique
        Add-Eil "   ĮSPĖJIMAS: Windows rezervavo prievadus: $($unikalus -join ', ')"
        Add-Eil "   Sprendimas: pakeisk ServerioPrievadas n8n-konfig.ps1 į laisvą (pvz. 13625)"
        Add-Eil "   arba po perkrovimo: net stop winnat / net start winnat (reikia administratoriaus)"
        $problemu++
    } else {
        Add-Eil "   5678/5679 NĖRA rezervuotų diapazonų -- gerai."
    }
} catch {
    Add-Eil "   netsh nepavyko: $($_.Exception.Message)"
}

# --- 5) Versija ir žurnalai ---
Add-Eil ""
Add-Eil "5) VERSIJA IR ŽURNALAI"
try {
    $pkg = Join-Path $N8nKonfig.Runtime 'n8n\node_modules\n8n\package.json'
    if (Test-Path -LiteralPath $pkg) {
        $v = (Get-Content -LiteralPath $pkg -Raw | ConvertFrom-Json).version
        Add-Eil "   n8n versija: $v"
        Add-Eil "   (žinoma klaida su pakibusiu startu taisyta n8n 1.105.0+)"
    } else {
        Add-Eil "   n8n package.json nerastas: $pkg"
    }
} catch { Add-Eil "   versijos nustatyti nepavyko: $($_.Exception.Message)" }

foreach ($lg in @($N8nKonfig.WatchdogLog, $N8nKonfig.ServerErr)) {
    if (Test-Path -LiteralPath $lg) {
        $dydis = [math]::Round((Get-Item -LiteralPath $lg).Length / 1KB, 1)
        Add-Eil "   $lg ($dydis KB) -- paskutinės 5 eilutės:"
        Get-Content -LiteralPath $lg -Tail 5 -ErrorAction SilentlyContinue | ForEach-Object { Add-Eil "     | $_" }
    }
}

# --- 6) Užduotys planuotojuje ---
Add-Eil ""
Add-Eil "6) TASK SCHEDULER UŽDUOTYS"
try {
    $uz = Get-ScheduledTask -ErrorAction SilentlyContinue | Where-Object { $_.TaskName -match 'N8N|CLINE|KUMSTIS' }
    if ($uz) {
        foreach ($u in $uz) { Add-Eil ("   {0} -> {1}" -f $u.TaskName, $u.State) }
    } else {
        Add-Eil "   užduočių nėra. Registruok: registruok-uzduotis.ps1"
        $problemu++
    }
} catch { Add-Eil "   Get-ScheduledTask nepavyko: $($_.Exception.Message)" }

Add-Eil ""
Add-Eil "===== IŠVADA: problemų rasta $problemu ====="

$viska = $eilutes -join "`r`n"
Write-Output $viska

if ($Issaugoti) {
    New-Item -ItemType Directory -Force -Path $N8nKonfig.LogsDir | Out-Null
    $is = Join-Path $N8nKonfig.LogsDir ("n8n-diagnostika-{0}.txt" -f (Get-Date -Format 'yyyyMMdd_HHmmss'))
    Set-Content -LiteralPath $is -Value $viska -Encoding UTF8
    Write-Output "Išsaugota: $is"
}

if ($problemu -gt 0) { exit 1 } else { exit 0 }
