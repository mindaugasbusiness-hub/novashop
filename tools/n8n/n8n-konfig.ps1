# n8n-konfig.ps1 -- bendra n8n paleidimo konfigūracija (vienintelė tiesos vieta)
# Naudojimas: . "$PSScriptRoot\n8n-konfig.ps1"   (dot-source, be parametro)
# Sukurta: 2026-10-28 · Šaka: cline/da6qq3k9
#
# SVARBU APIE PRIEVADUS (patikrinta realioje aplinkoje 2026-10-24..28):
#   5678 = n8n SERVERIS (naršyklės UI, webhook'ai, /healthz)
#   5679 = n8n TASK BROKERIS (vidinis task-runner brokeris, N8N_RUNNERS_TASK_BROKER_PORT).
#          Tai NĖRA antras n8n egzempliorius -- abu prievadus laiko TAS PATS PID.
#          Klaida "Task Broker's port 5679 is already in use" reiškia: veikiantis serveris
#          jau laiko 5679, o CLI komanda (n8n execute) bando jį užimti antrą kartą.
#          Sprendimas: CLI komandoms duoti LAISVĄ brokerio prievadą (žr. n8n-cli.ps1).

$ErrorActionPreference = 'Continue'

# --- Keliai (automatiškai; perrašomi per aplinkos kintamuosius) ---
if (-not $env:N8N_ROOT)      { $env:N8N_ROOT      = 'C:\Users\M\Desktop\Kumstis' }
if (-not $env:N8N_TOOLS_DIR) { $env:N8N_TOOLS_DIR = 'C:\Users\M\CLINE\tools\n8n' }

$N8nKonfig = [ordered]@{
    Root       = $env:N8N_ROOT
    ToolsDir   = $env:N8N_TOOLS_DIR
    Runtime    = (Join-Path $env:N8N_ROOT 'runtime')
    Node       = (Join-Path $env:N8N_ROOT 'runtime\node24\node.exe')
    N8nBin     = (Join-Path $env:N8N_ROOT 'runtime\n8n\node_modules\n8n\bin\n8n')
    DataDir    = (Join-Path $env:N8N_ROOT 'runtime\n8n-data')
    LogsDir    = (Join-Path $env:N8N_ROOT 'runtime\logs')
    PidFile    = (Join-Path $env:N8N_ROOT 'runtime\pids.json')
    EnvFile    = (Join-Path $env:N8N_ROOT '.env')

    # --- Prievadai ---
    ServerioPrievadas  = 5678   # N8N_PORT
    BrokerioPrievadas  = 5679   # N8N_RUNNERS_TASK_BROKER_PORT (serverio)
    CliBrokerisNuo     = 5690   # CLI ieško laisvo brokerio prievado intervale 5690..5699
    CliBrokerisIki     = 5699
    TikrinamiPrievadai = @(5678, 5679)

    SveikatosTikrinimas = 'http://127.0.0.1:5678/healthz'
    PaleidimoLaukimas   = 90    # sekundės, kiek laukiama /healthz po starto
    BudetojoIntervalas  = 30    # sekundės tarp budėtojo ciklų (-Loop režime)
}

# --- Žurnalai ---
$N8nKonfig.WatchdogLog = (Join-Path $N8nKonfig.LogsDir 'n8n-watchdog.log')
$N8nKonfig.BootMarker  = (Join-Path $N8nKonfig.LogsDir 'n8n-booting.marker')
$N8nKonfig.ServerLog   = (Join-Path $N8nKonfig.LogsDir 'n8n-server.out.log')
$N8nKonfig.ServerErr   = (Join-Path $N8nKonfig.LogsDir 'n8n-server.err.log')

function Write-N8nLog {
    param([string]$Text, [string]$File)
    if (-not $File) { $File = $N8nKonfig.WatchdogLog }
    $dir = Split-Path -Parent $File
    if ($dir -and -not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
    }
    $line = '[{0}] {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Text
    Add-Content -LiteralPath $File -Value $line -Encoding UTF8
}

# --- Sveikatos patikra: $true, jei /healthz atsako 200 ---
function Test-N8nSveikas {
    param([int]$TimeoutSec = 5)
    try {
        $r = Invoke-WebRequest -Uri $N8nKonfig.SveikatosTikrinimas -UseBasicParsing -TimeoutSec $TimeoutSec
        return ($r.StatusCode -eq 200)
    } catch {
        return $false
    }
}

# --- Prievado patikra: grąžina PID (0 = laisvas) ---
function Test-PrievadasUzimtas {
    param([int]$Port)
    $c = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
         Select-Object -First 1
    if ($c) { return [int]$c.OwningProcess }
    return 0
}

# --- Laisvo brokerio prievado radimas CLI komandoms ---
function Get-LaisvasBrokerioPrievadas {
    for ($p = $N8nKonfig.CliBrokerisNuo; $p -le $N8nKonfig.CliBrokerisIki; $p++) {
        if ((Test-PrievadasUzimtas -Port $p) -eq 0) { return $p }
    }
    return 0
}

# --- .env užkrovimas į procesą (verčių į žurnalą NERAŠOME -- 3 taisyklė) ---
function Import-N8nEnv {
    if (-not (Test-Path -LiteralPath $N8nKonfig.EnvFile)) { return }
    foreach ($line in Get-Content -LiteralPath $N8nKonfig.EnvFile -Encoding UTF8) {
        if ($line -match '^\s*#' -or $line -notmatch '=') { continue }
        if ($line -match '^\s*([A-Za-z0-9_]+)\s*=\s*(.*)$') {
            [Environment]::SetEnvironmentVariable($Matches[1], $Matches[2].Trim().Trim('"').Trim("'"), 'Process')
        }
    }
}

# --- Pastovi n8n aplinka (vienoda serveriui ir budėtojui) ---
function Set-N8nAplinka {
    param([int]$Brokeris = 5679)
    Import-N8nEnv
    $env:N8N_USER_FOLDER                   = $N8nKonfig.DataDir
    $env:N8N_BLOCK_ENV_ACCESS_IN_NODE      = 'false'
    $env:N8N_RUNNERS_MODE                  = 'internal'
    $env:N8N_LISTEN_ADDRESS                = '127.0.0.1'
    $env:N8N_HOST                          = 'localhost'
    $env:N8N_PORT                          = "$($N8nKonfig.ServerioPrievadas)"
    $env:N8N_PROTOCOL                      = 'http'
    $env:N8N_RUNNERS_TASK_BROKER_PORT      = "$Brokeris"
    $env:N8N_RUNNERS_BROKER_PORT           = "$Brokeris"    # senesnėms n8n versijoms
    $env:N8N_RUNNERS_BROKER_LISTEN_ADDRESS = '127.0.0.1'
    if (-not $env:WEBHOOK_URL)     { $env:WEBHOOK_URL     = "http://localhost:$($N8nKonfig.ServerioPrievadas)/" }
    if (-not $env:GENERIC_TIMEZONE) { $env:GENERIC_TIMEZONE = 'Europe/Vilnius' }
    $env:N8N_DIAGNOSTICS_ENABLED           = 'false'
}

# --- PID failo skaitymas / rašymas (su .bak kopija) ---
function Get-N8nPids {
    $obj = [pscustomobject]@{}
    if (Test-Path -LiteralPath $N8nKonfig.PidFile) {
        try { $obj = Get-Content -LiteralPath $N8nKonfig.PidFile -Raw | ConvertFrom-Json } catch { $obj = [pscustomobject]@{} }
    }
    return $obj
}

function Set-N8nPid {
    param([string]$Name, [int]$Value)
    $pidsObj = Get-N8nPids
    $stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    if (Test-Path -LiteralPath $N8nKonfig.PidFile) {
        Copy-Item -LiteralPath $N8nKonfig.PidFile -Destination "$($N8nKonfig.PidFile).bak-$stamp" -Force -ErrorAction SilentlyContinue
    }
    $pidsObj | Add-Member -NotePropertyName $Name -NotePropertyValue $Value -Force
    $pidsObj | ConvertTo-Json | Set-Content -LiteralPath $N8nKonfig.PidFile -Encoding UTF8
}

# --- Veikiančio n8n serverio proceso radimas (pagal komandinę eilutę) ---
function Get-N8nServerioProcesas {
    $p = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
         Where-Object { $_.Name -eq 'node.exe' -and $_.CommandLine -match 'n8n[\\/]bin[\\/]n8n"?\s+start' } |
         Select-Object -First 1
    if ($p) { return [int]$p.ProcessId }
    return 0
}

# --- Ar n8n šiuo metu kyla? (booting žyma jaunesnė nei $JaunesnisNeiSek) ---
function Test-KylaDabar {
    param([int]$JaunesnisNeiSek = 120)
    if (-not (Test-Path -LiteralPath $N8nKonfig.BootMarker)) { return $false }
    try {
        $kai = Get-Date (Get-Content -LiteralPath $N8nKonfig.BootMarker -Raw).Trim()
        return (((Get-Date) - $kai).TotalSeconds -lt $JaunesnisNeiSek)
    } catch {
        return $false
    }
}

# --- PAGRINDINIS SPRENDIMAS (tyras, be šalutinių poveikių -- todėl testuojamas) ---
# Grąžina vieną iš: GERAI | PERKRAUTI | SVETIMAS | KYLA | PALEISTI
#   GERAI     -- serveris atsako IR brokerio prievadas klausosi: nieko nedaryti
#   PERKRAUTI -- serveris atsako, bet brokeris neklauso: perkrauti
#   SVETIMAS  -- serveris neatsako, bet :5678 laiko svetimas procesas: NEKILLINTI
#   KYLA      -- serveris neatsako, bet ką tik buvo paleistas: palaukti
#   PALEISTI  -- serverio nėra ir prievadas laisvas: paleisti
function Get-N8nBusena {
    if (Test-N8nSveikas) {
        if ((Test-PrievadasUzimtas -Port $N8nKonfig.BrokerioPrievadas) -gt 0) { return 'GERAI' }
        return 'PERKRAUTI'
    }
    if ((Test-PrievadasUzimtas -Port $N8nKonfig.ServerioPrievadas) -gt 0) { return 'SVETIMAS' }
    if (Test-KylaDabar) { return 'KYLA' }
    return 'PALEISTI'
}


