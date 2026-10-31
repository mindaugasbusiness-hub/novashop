# registruok-uzduotis.ps1 -- užregistruoja Windows Task Scheduler užduotis,
# kad n8n pats prisikeltų po perkrovimo ir būtų nuolat prižiūrimas.
#
# Sukuriamos 2 užduotys:
#   N8N START LOGON  -- paleidžia start-n8n.cmd prisijungus (30 s delsa)
#   N8N WATCHDOG     -- kas 1 minutę patikrina :5678/:5679 ir prikelia, jei krenta
#
# Naudojimas (PowerShell, administratoriaus NEREIKIA -- užduotys kuriamos tavo naudotojui):
#   powershell -NoProfile -ExecutionPolicy Bypass -File registruok-uzduotis.ps1
#   powershell -NoProfile -ExecutionPolicy Bypass -File registruok-uzduotis.ps1 -Isregistruoti
#   powershell -NoProfile -ExecutionPolicy Bypass -File registruok-uzduotis.ps1 -Patikrinti
#
# Grąžina: 0 = gerai, 1 = klaida

[CmdletBinding()]
param(
    [switch]$Isregistruoti,
    [switch]$Patikrinti
)

$ErrorActionPreference = 'Continue'
. (Join-Path $PSScriptRoot 'n8n-konfig.ps1')

$uzduotiesVardas1 = 'N8N START LOGON'
$uzduotiesVardas2 = 'N8N WATCHDOG'
$toolsDir = $N8nKonfig.ToolsDir

function Test-Uzduotis {
    param([string]$Vardas)
    $r = schtasks /Query /TN $Vardas 2>&1
    return ($LASTEXITCODE -eq 0)
}

if ($Patikrinti) {
    foreach ($v in @($uzduotiesVardas1, $uzduotiesVardas2)) {
        if (Test-Uzduotis $v) {
            Write-Output "$v : UŽREGISTRUOTA"
            schtasks /Query /TN $v /FO LIST /V 2>&1 |
                Select-String -Pattern 'TaskName|Status|Next Run Time|Last Run Time|Last Result' |
                ForEach-Object { Write-Output "  $_" }
        } else {
            Write-Output "$v : NĖRA"
        }
    }
    exit 0
}

if ($Isregistruoti) {
    foreach ($v in @($uzduotiesVardas1, $uzduotiesVardas2)) {
        schtasks /Delete /TN $v /F 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) { Write-Output "$v : išregistruota" } else { Write-Output "$v : nebuvo užregistruota" }
    }
    exit 0
}

# --- Kelio patikra (kad užduotis nerodytų į neegzistuojantį failą) ---
if (-not (Test-Path -LiteralPath (Join-Path $toolsDir 'start-n8n.cmd'))) {
    Write-Output "KLAIDA: neradau $toolsDir\start-n8n.cmd"
    Write-Output "  Pirmiausia nukopijuok tools\n8n\* į $toolsDir"
    Write-Output "  arba nustatyk: `$env:N8N_TOOLS_DIR = 'C:\tikras\kelias\tools\n8n'"
    exit 1
}

$cmdKelias    = Join-Path $toolsDir 'start-n8n.cmd'
$watchdogKeli = Join-Path $toolsDir 'n8n-watchdog.ps1'

# --- 1) Startas prisijungus (30 s delsa, kad tinklas/diskai spėtų pakilti) ---
$tr1 = "cmd.exe /c `"$cmdKelias`""
schtasks /Create /TN $uzduotiesVardas1 /TR $tr1 /SC ONLOGON /DELAY 0000:30 /F | Out-Null
if ($LASTEXITCODE -eq 0) { Write-Output "$uzduotiesVardas1 : užregistruota (ONLOGON +30 s)" }
else { Write-Output "$uzduotiesVardas1 : KLAIDA ($LASTEXITCODE)"; exit 1 }

# --- 2) Budėtojas kas 1 minutę ---
$tr2 = "powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$watchdogKeli`""
schtasks /Create /TN $uzduotiesVardas2 /TR $tr2 /SC MINUTE /MO 1 /F | Out-Null
if ($LASTEXITCODE -eq 0) { Write-Output "$uzduotiesVardas2 : užregistruota (kas 1 min)" }
else { Write-Output "$uzduotiesVardas2 : KLAIDA ($LASTEXITCODE)"; exit 1 }

Write-Output ""
Write-Output "Patikrinti:  powershell -NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`" -Patikrinti"
Write-Output "Žurnalas:    $($N8nKonfig.WatchdogLog)"
Write-Output "Pastaba: ONLOGON užduotis veikia tavo naudotojo sesijoje -- tai ir reikia n8n,"
Write-Output "         nes jis naudoja tavo %USERPROFILE% duomenis ir paleidžia langą paslėptai."
exit 0
