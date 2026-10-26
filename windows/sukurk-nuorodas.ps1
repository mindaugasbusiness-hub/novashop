<#
  sukurk-nuorodas.ps1 - sutvarko darbalaukio nuorodas "CLINE RYSYS" ir "CLINE - PRADZIA".
  Naudinga, kai: nuorodos dingo, atsirado naujas kompiuteris, ar nustatymai sugadinti.

  Paleidimas:
      powershell -ExecutionPolicy Bypass -File sukurk-nuorodas.ps1
      powershell -ExecutionPolicy Bypass -File sukurk-nuorodas.ps1 -Iranga "D:\kita\vieta"
#>
param(
    [string]$Iranga = 'C:\Users\M\CLINE\iranga',
    [string]$Atmintis = 'C:\Users\M\CLINE'
)
$ErrorActionPreference = 'Stop'

function Rasyk([string]$t) { Write-Host $t }

$rysysCmd = Join-Path $Iranga 'CLINE-RYSYS.cmd'
$pradziaCmd = Join-Path $Iranga 'CLINE-PRADZIA.cmd'

if (-not (Test-Path $rysysCmd)) { throw ('Nera ' + $rysysCmd + ' - pirma paleisk irasyk.ps1') }
if (-not (Test-Path $pradziaCmd)) { throw ('Nera ' + $pradziaCmd + ' - pirma paleisk irasyk.ps1') }

$darbalaukis = [Environment]::GetFolderPath('Desktop')
if (-not $darbalaukis -or -not (Test-Path $darbalaukis)) {
    $darbalaukis = Join-Path $env:USERPROFILE 'Desktop'
}
if (-not (Test-Path $darbalaukis)) { New-Item -ItemType Directory -Force -Path $darbalaukis | Out-Null }

$apvalkalas = New-Object -ComObject WScript.Shell

function SukurkNuoroda([string]$pavadinimas, [string]$taikinys, [string]$aprasymas, [int]$Ikona) {
    $kelias = Join-Path $darbalaukis ($pavadinimas + '.lnk')
    $nuoroda = $apvalkalas.CreateShortcut($kelias)
    $nuoroda.TargetPath = $taikinys
    $nuoroda.WorkingDirectory = (Split-Path $taikinys -Parent)
    $nuoroda.Description = $aprasymas
    $nuoroda.IconLocation = "$env:SystemRoot\System32\shell32.dll,$Ikona"
    $nuoroda.Save()
    Rasyk ('  [OK] ' + $kelias)
}

SukurkNuoroda 'CLINE RYSYS' $rysysCmd 'Paima siandienos prisijungimo komanda ir prijungia Cline (2-3 sek.)' 25
SukurkNuoroda 'CLINE - PRADZIA' $pradziaCmd 'Atidaro atsiminima: C:\Users\M\CLINE\00_START_HERE.md' 71

# prisijungimo failas turi buti, kad paleidejas rastu vieta (jei tuscias - paklaus Taves)
$prisijungimas = Join-Path $Atmintis 'prisijungimas.txt'
if (-not (Test-Path $prisijungimas)) {
    Set-Content -Path $prisijungimas -Value '# Cia irasoma siandienos eilute: iex (irm https://.../agent.ps1)' -Encoding UTF8
    Rasyk ('  [OK] sukurta tuscia atmintine: ' + $prisijungimas)
}
$logai = Join-Path $Atmintis 'logai'
if (-not (Test-Path $logai)) { New-Item -ItemType Directory -Force -Path $logai | Out-Null }

Rasyk ''
Rasyk 'Padaryta. Darbalaukyje yra dvi nuorodos: CLINE RYSYS ir CLINE - PRADZIA.'