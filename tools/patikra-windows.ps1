<#
  patikra-windows.ps1 - Windows pusės failų patikra (be Windows!).

  Ką tikrina:
    1. ar windows/*.ps1 failai išsiparsina (sintaksė),
    2. ar adreso atpažinimo logika (regex) teisingai veikia su realiais pavyzdžiais,
    3. ar visi url, kuriuos naudoja windows/irasyk.ps1, tikrai atsako 200 (kitaip būtų 404 tavo lange).

  Paleidimas (reikalauja PowerShell 7; Windows PowerShell 5.1 taip pat tinka):
      pwsh -NoProfile -File tools/patikra-windows.ps1
      pwsh -NoProfile -File tools/patikra-windows.ps1 -Baze https://raw.githubusercontent.com/mindaugasbusiness-hub/novashop/cline/lenta
#>
param(
    [string]$Baze = 'https://raw.githubusercontent.com/mindaugasbusiness-hub/novashop/cline/wfbfjc1p',
    [string]$Windows = 'windows'
)
$ErrorActionPreference = 'Continue'

$script:Ok = 0
$script:Fail = 0
function Patikrink([string]$vardas, [bool]$saliga, [string]$detale = '') {
    if ($saliga) { $script:Ok++; Write-Host ('  [OK]   ' + $vardas) }
    else { $script:Fail++; Write-Host ('  [FAIL] ' + $vardas + ' ' + $detale) -ForegroundColor Red }
}

$saknis = Split-Path -Parent $PSScriptRoot
$dir = Join-Path $saknis $Windows

Write-Host '1) sintaksė (parseriu, ne akimis)'
$failai = Get-ChildItem -Path $dir -Filter '*.ps1' | Sort-Object Name
Patikrink 'rasta .ps1 failų' ($failai.Count -gt 0) ('count=' + $failai.Count)
foreach ($f in $failai) {
    $klaidos = $null
    [void][System.Management.Automation.Language.Parser]::ParseFile($f.FullName, [ref]$null, [ref]$klaidos)
    if ($klaidos -and $klaidos.Count -gt 0) {
        foreach ($k in $klaidos) { Write-Host ('       ' + $f.Name + ':' + $k.Extent.StartLineNumber + ' ' + $k.Message) }
    }
    Patikrink ($f.Name + ' - sintaksė tvarkinga') (-not $klaidos -or $klaidos.Count -eq 0)
}

Write-Host ''
Write-Host '2) adreso atpažinimas (CLINE-RYSYS.ps1 logika)'
$rysysKelias = Join-Path $dir 'CLINE-RYSYS.ps1'
$rysys = Get-Content -Path $rysysKelias -Raw
$regexEilute = 'https://[A-Za-z0-9\.\-]+/agent\.ps1'
Patikrink 'paleidėjas naudoja tą patį regex, kurį tikrina testas' ($rysys.Contains([regex]::Escape($regexEilute)) -or $rysys.Contains($regexEilute))

function RaskAdresa([string]$tekstas) {
    if ([string]::IsNullOrWhiteSpace($tekstas)) { return $null }
    $m = [regex]::Match($tekstas, 'https://[A-Za-z0-9\.\-]+/agent\.ps1')
    if ($m.Success) { return $m.Value }
    return $null
}

$teisingi = @(
    'iex (irm https://amino-beneath-plugins-allergy.trycloudflare.com/agent.ps1)',
    'https://a-b-c.trycloudflare.com/agent.ps1',
    'labas https://x1.trycloudflare.com/agent.ps1 ir viso',
    "# CLINE adresu lenta`n# Gyva tik kol veikia sesija. Atnaujinta: 2026-10-26`nhttps://pastor-participant-lab-housewares.trycloudflare.com/agent.ps1`n"
)
foreach ($t in $teisingi) {
    $r = RaskAdresa $t
    Patikrink ('atpažįsta: ' + $t.Substring(0, [Math]::Min(45, $t.Length)).Replace("`n", ' ')) ($null -ne $r) ('gavau=' + $r)
}
$neteisingi = @('', '   ', 'labas', 'https://x.trycloudflare.com/health', 'iex (irm https://x.trycloudflare.com)')
foreach ($t in $neteisingi) {
    $r = RaskAdresa $t
    Patikrink ('neatpažįsta (teisingai): "' + $t + '"') ($null -eq $r) ('gavau=' + $r)
}

Write-Host ''
Write-Host ('3) ar įrašymo url tikrai gyvi (bazė: ' + $Baze + ')')
$irasyk = Get-Content -Path (Join-Path $dir 'irasyk.ps1') -Raw
$urls = [regex]::Matches($irasyk, "'(windows/[A-Za-z0-9\-\.]+|CLINE/[A-Za-z0-9\-\._]+)'") |
        ForEach-Object { $_.Groups[1].Value } | Sort-Object -Unique
Patikrink 'rado įrašymo sąrašą' ($urls.Count -gt 5) ('count=' + $urls.Count)
foreach ($u in $urls) {
    $pilnas = $Baze + '/' + $u
    try {
        $r = Invoke-WebRequest -Uri $pilnas -UseBasicParsing -TimeoutSec 20 -ErrorAction Stop
        Patikrink ($u + ' (' + $r.StatusCode + ')') ($r.StatusCode -eq 200)
    } catch {
        Patikrink ($u + ' pasiekiamas') $false $_.Exception.Message
    }
}

Write-Host ''
Write-Host ('Rezultatas: ' + $script:Ok + ' OK, ' + $script:Fail + ' FAIL')
if ($script:Fail -gt 0) { exit 1 }
exit 0