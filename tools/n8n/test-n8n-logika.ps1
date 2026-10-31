# test-n8n-logika.ps1 -- n8n sprendimų logikos savitikra.
#
# Ką tikrina: Get-N8nBusena (5 būsenos), Get-LaisvasBrokerioPrievadas, Test-KylaDabar,
# Set-N8nAplinka, Write-N8nLog. NIEKO realiai nepaleidžia ir nieko nežudo --
# priklausomybės (sveikata, prievadai) pakeičiamos imitacijomis.
#
# Veikia ir Windows PowerShell, ir Linux pwsh:
#   powershell -NoProfile -ExecutionPolicy Bypass -File test-n8n-logika.ps1
#   pwsh -NoProfile -File test-n8n-logika.ps1
# Grąžina: 0 = viskas praėjo, 1 = yra klaidų

[CmdletBinding()]
param()

$ErrorActionPreference = 'Continue'

# --- Laikinas "Windows" katalogas: kad testai veiktų ir Linux pwsh ---
$script:tmpDir = Join-Path ([System.IO.Path]::GetTempPath()) ("n8n-test-{0}" -f [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force -Path $script:tmpDir | Out-Null
$env:N8N_ROOT = $script:tmpDir
$env:N8N_TOOLS_DIR = $PSScriptRoot

. (Join-Path $PSScriptRoot 'n8n-konfig.ps1')

# --- Imitacijos (mock) -----------------------------------------------------
$script:mockSveikas = $false
$script:mockPorts = @{}

function Test-N8nSveikas { param([int]$TimeoutSec = 5) return $script:mockSveikas }
function Test-PrievadasUzimtas {
    param([int]$Port)
    if ($script:mockPorts.ContainsKey($Port)) { return [int]$script:mockPorts[$Port] }
    return 0
}

$N8nKonfig.BootMarker = Join-Path $script:tmpDir 'n8n-booting.marker'
$N8nKonfig.WatchdogLog = Join-Path $script:tmpDir 'test-watchdog.log'


$script:atvejai = 0
$script:klaidos = 0

function Tikrinti {
    param([string]$Pavadinimas, $Gauta, $Tiketa)
    $script:atvejai++
    $ok = ("$Gauta" -eq "$Tiketa")
    if (-not $ok) { $script:klaidos++ }
    Write-Output ("{0}  {1,-52} gauta={2}" -f $(if ($ok) { 'PASS' } else { 'FAIL' }), $Pavadinimas, $Gauta)
    if (-not $ok) { Write-Output ("      tikėtasi={0}" -f $Tiketa) }
}

function NustatytiBusena {
    param([bool]$Sveikas, [hashtable]$Prievadai)
    $script:mockSveikas = $Sveikas
    $script:mockPorts = $Prievadai
}

# --- 1) PRIEVADŲ KONFIGŪRACIJA --------------------------------------------
Write-Output "--- 1) Prievadų konfigūracija ---"
Tikrinti "serverio prievadas = 5678" $N8nKonfig.ServerioPrievadas 5678
Tikrinti "brokerio prievadas = 5679" $N8nKonfig.BrokerioPrievadas 5679
Tikrinti "CLI brokerio intervalas 5690-5699" "$($N8nKonfig.CliBrokerisNuo)-$($N8nKonfig.CliBrokerisIki)" "5690-5699"
Tikrinti "tikrinami prievadai = 5678,5679" ($N8nKonfig.TikrinamiPrievadai -join ',') "5678,5679"

# --- 2) GET-N8NBUSENA: penkios būsenos ------------------------------------
Write-Output ""
Write-Output "--- 2) Get-N8nBusena sprendimai ---"

NustatytiBusena -Sveikas $true -Prievadai @{ 5679 = 4242 }
Tikrinti "veikia serveris + brokeris -> GERAI" (Get-N8nBusena) 'GERAI'

NustatytiBusena -Sveikas $true -Prievadai @{}
Tikrinti "veikia serveris, brokeris neklauso -> PERKRAUTI" (Get-N8nBusena) 'PERKRAUTI'

NustatytiBusena -Sveikas $false -Prievadai @{ 5678 = 4242; 5679 = 4242 }
Tikrinti "neveikia, 5678 laiko svetimas PID -> SVETIMAS" (Get-N8nBusena) 'SVETIMAS'

NustatytiBusena -Sveikas $false -Prievadai @{}
Set-Content -LiteralPath $N8nKonfig.BootMarker -Value (Get-Date -Format 'o') -Encoding UTF8
Tikrinti "neveikia, bet ką tik paleistas (žyma) -> KYLA" (Get-N8nBusena) 'KYLA'

NustatytiBusena -Sveikas $false -Prievadai @{}
Set-Content -LiteralPath $N8nKonfig.BootMarker -Value ((Get-Date).AddMinutes(-5).ToString('o')) -Encoding UTF8
Tikrinti "neveikia, sena žyma (>120 s) -> PALEISTI" (Get-N8nBusena) 'PALEISTI'

NustatytiBusena -Sveikas $false -Prievadai @{}
Remove-Item -LiteralPath $N8nKonfig.BootMarker -Force -ErrorAction SilentlyContinue
Tikrinti "neveikia, prievadas laisvas, be žymos -> PALEISTI" (Get-N8nBusena) 'PALEISTI'

NustatytiBusena -Sveikas $false -Prievadai @{ 5679 = 4242 }
Tikrinti "neveikia, brokerio prievadas liko (zombis) -> PALEISTI" (Get-N8nBusena) 'PALEISTI'

NustatytiBusena -Sveikas $true -Prievadai @{ 5679 = 4242; 5678 = 4242 }
Tikrinti "tas pats PID abiejuose (normalu) -> GERAI" (Get-N8nBusena) 'GERAI'

# --- 3) LAISVO BROKERIO PRIEVADO PAIEŠKA (CLI apsauga nuo :5679 konflikto) ---
Write-Output ""
Write-Output "--- 3) Get-LaisvasBrokerioPrievadas ---"

NustatytiBusena -Sveikas $true -Prievadai @{ 5678 = 100; 5679 = 100 }
Tikrinti "5679 užimtas, 5690-5699 laisvi -> 5690" (Get-LaisvasBrokerioPrievadas) 5690

NustatytiBusena -Sveikas $true -Prievadai @{ 5690 = 100; 5691 = 100; 5692 = 100 }
Tikrinti "5690-5692 užimti -> 5693" (Get-LaisvasBrokerioPrievadas) 5693

$visi = @{}
for ($p = 5690; $p -le 5699; $p++) { $visi[$p] = 100 }
NustatytiBusena -Sveikas $true -Prievadai $visi
Tikrinti "visi 5690-5699 užimti -> 0 (klaida, ne spėjimas)" (Get-LaisvasBrokerioPrievadas) 0

NustatytiBusena -Sveikas $true -Prievadai @{ 5679 = 100 }
Tikrinti "5679 neužimtas CLI rinkinyje (nenaudojamas)" (Get-LaisvasBrokerioPrievadas) 5690

# --- 4) BŪSENA SU SUGADINTA ŽYMA (turi nekristi) ---------------------------
Write-Output ""
Write-Output "--- 4) Atsparumas sugadintiems duomenims ---"

Set-Content -LiteralPath $N8nKonfig.BootMarker -Value 'tai ne data' -Encoding UTF8
Tikrinti "sugadinta žyma -> Test-KylaDabar False (be klaidos)" (Test-KylaDabar) $false

Set-Content -LiteralPath $N8nKonfig.BootMarker -Value '' -Encoding UTF8
Tikrinti "tuščia žyma -> Test-KylaDabar False" (Test-KylaDabar) $false

Set-Content -LiteralPath $N8nKonfig.BootMarker -Value (Get-Date -Format 'o') -Encoding UTF8
Tikrinti "šviežia žyma -> Test-KylaDabar True" (Test-KylaDabar) $true

Set-Content -LiteralPath $N8nKonfig.BootMarker -Value ((Get-Date).AddSeconds(-5).ToString('o')) -Encoding UTF8
Tikrinti "5 s sena žyma su 1 s riba -> False" (Test-KylaDabar -JaunesnisNeiSek 1) $false
Tikrinti "5 s sena žyma su 120 s riba -> True" (Test-KylaDabar -JaunesnisNeiSek 120) $true

# --- 5) APLINKA (Set-N8nAplinka) ------------------------------------------
Write-Output ""
Write-Output "--- 5) Aplinkos kintamieji ---"

Set-N8nAplinka -Brokeris 5679
Tikrinti "N8N_PORT=5678" $env:N8N_PORT '5678'
Tikrinti "brokeris=5679" $env:N8N_RUNNERS_TASK_BROKER_PORT '5679'
Tikrinti "senas kintamasis irgi 5679" $env:N8N_RUNNERS_BROKER_PORT '5679'
Tikrinti "listen=127.0.0.1" $env:N8N_LISTEN_ADDRESS '127.0.0.1'
Tikrinti "runners režimas=internal" $env:N8N_RUNNERS_MODE 'internal'
Tikrinti "webhook į 5678" $env:WEBHOOK_URL 'http://localhost:5678/'

Set-N8nAplinka -Brokeris 5699
Tikrinti "CLI režimas: brokeris=5699" $env:N8N_RUNNERS_TASK_BROKER_PORT '5699'
Tikrinti "CLI režimas: serverio prievadas nepakitęs" $env:N8N_PORT '5678'

# --- 6) ŽURNALAS (Write-N8nLog) -------------------------------------------
Write-Output ""
Write-Output "--- 6) Žurnalo eilutė ---"

Remove-Item -LiteralPath $N8nKonfig.WatchdogLog -Force -ErrorAction SilentlyContinue
Write-N8nLog "testinė eilutė" | Out-Null
Write-N8nLog "antra eilutė" | Out-Null
$turinys = Get-Content -LiteralPath $N8nKonfig.WatchdogLog
Tikrinti "žurnale 2 eilutės" $turinys.Count 2
Tikrinti "eilutė turi datą laiką [yyyy-MM-dd" ($turinys[0] -match '^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\]') $true
Tikrinti "tekstas išsaugotas" ($turinys[1] -match 'antra eilutė') $true
Tikrinti "žurnalas sukuriamas naujame aplanke (be klaidos)" (Test-Path -LiteralPath $N8nKonfig.WatchdogLog) $true

# --- 7) AR NĖRA DESTRUKTYVIŲ KOMANDŲ --------------------------------------
Write-Output ""
Write-Output "--- 7) Saugumas: ar nėra masinio žudymo ---"

$watchdogTekstas = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'n8n-watchdog.ps1') -Raw
Tikrinti "budėtojas nežudo pagal vardą (Stop-Process -Name)" ($watchdogTekstas -match 'Stop-Process\s+-Name') $false
Tikrinti "budėtojas turi svetimo proceso apsaugą (SVETIMAS)" ($watchdogTekstas -match 'SVETIMAS') $true
Tikrinti "budėtojas turi vieno egzemplioriaus apsaugą" ($watchdogTekstas -match 'Test-BudetojasVienintelis') $true

$startTekstas = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'start-n8n.ps1') -Raw
Tikrinti "startas nekillina svetimo proceso (exit 3)" ($startTekstas -match 'exit 3') $true
Tikrinti "startas turi dvigubo paleidimo apsaugą" ($startTekstas -match 'jau veikia') $true

$cliTekstas = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'n8n-cli.ps1') -Raw
Tikrinti "CLI naudoja laisvą brokerio prievadą" ($cliTekstas -match 'Get-LaisvasBrokerioPrievadas') $true
Tikrinti "CLI atpažįsta brokerio klaidą" ($cliTekstas -match "Task Broker's port") $true

# --- 8) IŠVADA -------------------------------------------------------------
Remove-Item -LiteralPath $script:tmpDir -Recurse -Force -ErrorAction SilentlyContinue

Write-Output ""
Write-Output ("{0}/{1} patikrų praėjo" -f ($script:atvejai - $script:klaidos), $script:atvejai)
if ($script:klaidos -gt 0) { exit 1 }
exit 0

