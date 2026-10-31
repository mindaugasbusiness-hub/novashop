# GET.ps1 -- saugus paleidiklis, kuris veikia ir Windows PowerShell 5.1 su `| iex`.
#
# Kodėl atskiras failas: `| iex` (Invoke-Expression) Windows PowerShell 5.1 NEPRIIMA
# `[CmdletBinding()]` bloko (klaida: "Unexpected attribute 'CmdletBinding'").
# Todėl šiame faile NĖRA nei param(), nei [CmdletBinding()] -- tik paprastos komandos.
# Jis parsiunčia INSTALL.ps1 į %TEMP% ir paleidžia jį kaip failą (per -File), kur param() veikia.
#
# Naudojimas (viena eilutė PowerShell lange, veikia 5.1 ir 7.x):
#   iwr -useb https://raw.githubusercontent.com/mindaugasbusiness-hub/novashop/cline/da6qq3k9/tools/GET.ps1 | iex

$ErrorActionPreference = 'Stop'
try {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 -bor [Net.SecurityProtocolType]::Tls11
} catch { }

$saltinis = 'https://raw.githubusercontent.com/mindaugasbusiness-hub/novashop/cline/da6qq3k9/tools/INSTALL.ps1'
$laikinas = Join-Path $env:TEMP 'novashop-INSTALL.ps1'
# Laiko žymeklis apeina GitHub CDN podėlį (kitaip galima gauti seną failą)
$cacheBuster = '?t=' + [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()

Write-Output "Atsiunčiu diegimo failą..."
Write-Output "  $saltinis"
Invoke-WebRequest -Uri "$saltinis$cacheBuster" -OutFile $laikinas -UseBasicParsing -TimeoutSec 60

if (-not (Test-Path -LiteralPath $laikinas)) {
    throw "KLAIDA: nepavyko atsisiųsti diegimo failo. Patikrink internetą arba atidaryk adresą naršyklėje."
}

$baitai = (Get-Item -LiteralPath $laikinas).Length
Write-Output "  gauta: $baitai B -> $laikinas"
Write-Output ""

# Paleidžiame kaip FAILĄ (ne per iex) -- taip param() ir [CmdletBinding()] veikia ir 5.1
$psExe = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
if (-not (Test-Path -LiteralPath $psExe)) { $psExe = 'powershell.exe' }

& $psExe -NoProfile -ExecutionPolicy Bypass -File $laikinas
$kodas = $LASTEXITCODE

Write-Output ""
if ($kodas -eq 0) {
    Write-Output "=== DIEGIMAS BAIGTAS (kodas 0) ==="
    Write-Output ""
    Write-Output "Kitas žingsnis -- patikrinti servisus:"
    Write-Output "  powershell -NoProfile -ExecutionPolicy Bypass -File `"$env:USERPROFILE\CLINE\tools\atstatymas\patikrinti-servisus.ps1`""
} else {
    Write-Output "=== DIEGIMAS NEPAVYKO (kodas $kodas) ==="
    Write-Output "Failas paliktas patikrinimui: $laikinas"
}

# SVARBU: jokio 'exit' -- šis failas vykdomas per `| iex`, o 'exit' uždarytų tavo PowerShell langą.
