<#
  irasyk.ps1 - vienintele eilute, kuria sutvarkoma visa M kompiuterio puse.

  Ka daro:
    1. atsisiuncia paleideja ir atminties failus is GitHub (stabili saka cline/lenta),
    2. NIEKO netrina - jei failas jau yra ir skiriasi, issaugo nauja su datos galune,
    3. sukuria/atnaujina darbalaukio nuorodas CLINE RYSYS ir CLINE - PRADZIA,
    4. parodo, ka daryti toliau.

  Paleidimas (viena eilute PowerShell lange):
      iex (irm https://raw.githubusercontent.com/mindaugasbusiness-hub/novashop/cline/lenta/windows/irasyk.ps1)
#>
param(
    [string]$Iranga = 'C:\Users\M\CLINE\iranga',
    [string]$Atmintis = 'C:\Users\M\CLINE',
    [switch]$BeNuorodu
)
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$Baze = 'https://raw.githubusercontent.com/mindaugasbusiness-hub/novashop/cline/lenta'
$Data = Get-Date -Format 'yyyyMMdd-HHmm'

function Rasyk([string]$t, [string]$c = 'White') { Write-Host $t -ForegroundColor $c }

function Imk([string]$saltinis, [string]$katalogas, [string]$failas) {
    if (-not (Test-Path $katalogas)) { New-Item -ItemType Directory -Force -Path $katalogas | Out-Null }
    $tikslas = Join-Path $katalogas $failas
    $url = $Baze + '/' + $saltinis
    try {
        $naujas = (Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 20 -ErrorAction Stop).Content
    } catch {
        Rasyk ('  [X] ' + $failas + ' - nepavyko atsisiusti: ' + $_.Exception.Message) 'Red'
        return $false
    }
    if (Test-Path $tikslas) {
        try { $senas = Get-Content -Path $tikslas -Raw -ErrorAction Stop } catch { $senas = $null }
        if ($senas -ne $null -and $senas.Trim() -eq $naujas.Trim()) {
            Rasyk ('  [=] ' + $failas + ' - jau toks pat, palieku') 'DarkGray'
            return $true
        }
        $atsarginis = Join-Path $katalogas ($failas + '.' + $Data + '.senas')
        try {
            Copy-Item -Path $tikslas -Destination $atsarginis -Force
            Rasyk ('  [!] ' + $failas + ' - buvo kitoks; sena versija issaugota: ' + (Split-Path $atsarginis -Leaf)) 'Yellow'
        } catch {
            Rasyk ('  [!] ' + $failas + ' - buvo kitoks, bet senos versijos issaugoti nepavyko') 'Yellow'
        }
    }
    try {
        Set-Content -Path $tikslas -Value $naujas -Encoding UTF8 -NoNewline
    } catch {
        Rasyk ('  [X] ' + $failas + ' - nepavyko irasyti: ' + $_.Exception.Message) 'Red'
        return $false
    }
    Rasyk ('  [OK] ' + $tikslas) 'Green'
    return $true
}

Rasyk ''
Rasyk '==============================================================' 'Cyan'
Rasyk '  CLINE - irasymas i si kompiuteri' 'Cyan'
Rasyk ('  data: ' + (Get-Date -Format 'yyyy-MM-dd HH:mm')) 'DarkGray'
Rasyk '  NIEKO netrinu: esami failai tik atsarginami su datos galune.' 'DarkGray'
Rasyk '==============================================================' 'Cyan'
Rasyk ''
Rasyk '1) iranga (paleidejas ir nuorodu kurejas):' 'White'
Imk 'windows/CLINE-RYSYS.ps1'   $Iranga 'CLINE-RYSYS.ps1'   | Out-Null
Imk 'windows/CLINE-RYSYS.cmd'   $Iranga 'CLINE-RYSYS.cmd'   | Out-Null
Imk 'windows/CLINE-PRADZIA.cmd' $Iranga 'CLINE-PRADZIA.cmd' | Out-Null
Imk 'windows/sukurk-nuorodas.ps1' $Iranga 'sukurk-nuorodas.ps1' | Out-Null

Rasyk ''
Rasyk '2) atmintis (ka skaityti pradedant darba):' 'White'
Imk 'CLINE/00_START_HERE.md'          $Atmintis '00_START_HERE.md'          | Out-Null
Imk 'CLINE/01_RYSYS.md'               $Atmintis '01_RYSYS.md'               | Out-Null
Imk 'CLINE/02_DIENORASTIS.md'         $Atmintis '02_DIENORASTIS.md'         | Out-Null
Imk 'CLINE/03_TAISYKLES.md'           $Atmintis '03_TAISYKLES.md'           | Out-Null
Imk 'CLINE/04_TODO.md'                $Atmintis '04_TODO.md'                | Out-Null
Imk 'CLINE/05_PRIJUNGIMAS_WINDOWS.md' $Atmintis '05_PRIJUNGIMAS_WINDOWS.md' | Out-Null
Imk 'CLINE/PRADZIOS_PROMPTAS.txt'     $Atmintis 'PRADZIOS_PROMPTAS.txt'     | Out-Null

if (-not $BeNuorodu) {
    Rasyk ''
    Rasyk '3) darbalaukio nuorodos:' 'White'
    & (Join-Path $Iranga 'sukurk-nuorodas.ps1') -Iranga $Iranga -Atmintis $Atmintis
}

Rasyk ''
Rasyk '4) kas toliau:' 'White'
Rasyk '   a) Sioje pokalbio sesijoje parasysiu viena eilute su adresu.'
Rasyk '   b) Nukopijuok ja (Ctrl+C) - darbalaukyje spaudi CLINE RYSYS.'
Rasyk '   c) Langas pats suras komanda (mainuose arba atmintyje) ir prisijungs.'
Rasyk '   Jei pamirsai nukopijuoti - langas paprasys iklijuoti ir Enter.'
Rasyk ''
Rasyk ('   Zurnalas, jei kazkas nepavyksta: ' + $Atmintis + '\logai') 'DarkGray'