<#
  CLINE RYSYS - paleidejas (M kompiuteriui)
  ---------------------------------------------------------------
  Ka daro: suranda siandienos prisijungimo adresa ir paleidzia rysi.
  Saltiniai is eiles:
      1) atmintis  - C:\Users\M\CLINE\prisijungimas.txt   <- patikimiausia
      2) mainai    - Ctrl+C nukopijuota eilute (Get-Clipboard)
      3) lenta     - adresu lenta GitHub (TIK su -Auto, zr. README)
      4) paklausia Taves, jei nieko nerado
  Paleidimas: dukart spaudi darbalaukyje "CLINE RYSYS" (arba si faila).
#>
param(
    [switch]$Auto,
    [string]$Atmintis = 'C:\Users\M\CLINE'
)
$ErrorActionPreference = 'Continue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$Lenta = 'https://raw.githubusercontent.com/mindaugasbusiness-hub/novashop/cline/lenta/relay-adresas.txt'
$Host.UI.RawUI.WindowTitle = 'CLINE RYSYS'
$logDir = Join-Path $Atmintis 'logai'
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Force -Path $logDir | Out-Null }
$log = Join-Path $logDir ('rysys-' + (Get-Date -Format 'yyyyMMdd') + '.log')

function Rasyk([string]$t, [string]$c = 'White') {
    Write-Host $t -ForegroundColor $c
    try { Add-Content -Path $log -Value ((Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + '  ' + $t) -Encoding UTF8 } catch { }
}

function RaskAdresa([string]$tekstas) {
    if ([string]::IsNullOrWhiteSpace($tekstas)) { return $null }
    $m = [regex]::Match($tekstas, 'https://[A-Za-z0-9\.\-]+/agent\.ps1')
    if ($m.Success) { return $m.Value }
    return $null
}

function ImkIsFailo([string]$kelias) {
    if (-not (Test-Path $kelias)) { return $null }
    try { return (Get-Content -Path $kelias -Raw -ErrorAction Stop) } catch { return $null }
}

function ImkIsMainu() {
    try {
        $t = (Get-Clipboard -Raw -Format Text -ErrorAction Stop)
    } catch { return $null }
    return $t
}

function ImkIsLentos() {
    try {
        $t = (Invoke-WebRequest -Uri $Lenta -UseBasicParsing -TimeoutSec 12 -ErrorAction Stop).Content
    } catch {
        Rasyk ('  lenta nepasiekiama: ' + $_.Exception.Message) 'DarkYellow'
        return $null
    }
    return $t
}

function Gyvas([string]$adresas) {
    $sveikata = $adresas -replace '/agent\.ps1$', '/health'
    try {
        $r = Invoke-WebRequest -Uri $sveikata -UseBasicParsing -TimeoutSec 10 -ErrorAction Stop
        return ($r.StatusCode -eq 200)
    } catch { return $false }
}

Write-Host ''
Write-Host '==============================================================' -ForegroundColor Green
Write-Host '  CLINE RYSYS  -  jungiuosi prie siandienos sesijos' -ForegroundColor Green
Write-Host ('  laikas: ' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')) -ForegroundColor DarkGray
Write-Host '==============================================================' -ForegroundColor Green

$adresas = $null
$saltinis = ''
$prisijungimoFailas = Join-Path $Atmintis 'prisijungimas.txt'

# 1. atmintis
$adresas = RaskAdresa (ImkIsFailo $prisijungimoFailas)
if ($adresas) { $saltinis = 'atmintis (prisijungimas.txt)' }

# 2. mainai (Ctrl+C)
if (-not $adresas) {
    $adresas = RaskAdresa (ImkIsMainu)
    if ($adresas) { $saltinis = 'mainai (Ctrl+C)' }
}

# 3. adresu lenta - tik jei paprasyta -Auto
if (-not $adresas -and $Auto) {
    $adresas = RaskAdresa (ImkIsLentos)
    if ($adresas) { $saltinis = 'adresu lenta (GitHub)' }
}

# 4. paklausti Taves
while (-not $adresas) {
    Rasyk '  Komandos neradau.' 'Yellow'
    $ivesta = Read-Host '  Ikijuok komanda (iex (irm https://.../agent.ps1)) ir spausk Enter'
    $adresas = RaskAdresa $ivesta
    if ($adresas) { $saltinis = 'ivesta ranka' }
    elseif ([string]::IsNullOrWhiteSpace($ivesta)) { Rasyk '  Tustas ivedimas - bandome dar karta. Parasysiu eilute, ja nukopijuok (Ctrl+C).' 'Yellow' }
}

Rasyk ('  saltinis: ' + $saltinis) 'DarkGray'
Rasyk ('  adresas: ' + $adresas) 'DarkGray'
Rasyk '  tikrinu, ar adresas gyvas...' 'DarkGray'

if (-not (Gyvas $adresas)) {
    Rasyk '' 
    Rasyk '  Adresas neatsako (negyvas arba sesija jau baigta).' 'Red'
    Rasyk '  Ka daryti: parasysiu nauja eilute sioje pokalbio sesijoje - nukopijuok ja ir paleisk dar karta.' 'Yellow'
    Rasyk '  (Senas adresas nebeatgyja: kiekviena sesija turi savo adresa.)' 'DarkGray'
    Write-Host ''
    Read-Host '  Enter - uzdaryti langa'
    exit 1
}

Rasyk '  adresas gyvas - jungiuosi.' 'Green'
Write-Host ''
try {
    Invoke-Expression ('iex (irm ' + $adresas + ')')
} catch {
    Rasyk ('  Rysys nutruko: ' + $_.Exception.Message) 'Red'
    Read-Host '  Enter - uzdaryti langa'
    exit 1
}