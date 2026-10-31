# sukurkti-taskas.ps1 -- sukuria ATSTATYMO TAŠKĄ (viso veikiančio darbo kopiją).
#
# Ką fiksuoja:
#   * pultą        (C:\Users\M\CLINE\pultas\*)
#   * įrankius     (C:\Users\M\CLINE\tools\*)
#   * atmintį      (C:\Users\M\CLINE\*.md, VISKAS\*.md)
#   * n8n          (workflow eksportas + duomenų bazė + pids.json)
#   * užduotis     (Task Scheduler XML: N8N/CLINE/KUMSTIS)
#   * būklę        (11 servisų ataskaita + versijos)
#   * MANIFEST     (TASKAS.json su kiekvieno failo SHA256)
#
# Naudojimas:
#   powershell -NoProfile -ExecutionPolicy Bypass -File sukurkti-taskas.ps1
#   powershell -NoProfile -ExecutionPolicy Bypass -File sukurkti-taskas.ps1 -Numer 1 -Pastaba "11/11 veikia"
#   powershell -NoProfile -ExecutionPolicy Bypass -File sukurkti-taskas.ps1 -BeDuomenuBazes
# Grąžina: 0 = taškas sukurtas, 1 = klaida

[CmdletBinding()]
param(
    [int]$Numer = 0,
    [string]$Pastaba = '',
    [switch]$BeDuomenuBazes,
    [switch]$SuEksportu,
    [switch]$Tyliai
)

$ErrorActionPreference = 'Continue'

# Jei kas nors vis tiek sustabdytų skriptą -- pasakome AIŠKIAI, o ne tyliai.
trap {
    Write-Output ""
    Write-Output "=============================================="
    Write-Output "NEPAVYKO: $($_.Exception.Message)"
    Write-Output "  eilutė: $($_.InvocationInfo.ScriptLineNumber)"
    Write-Output "  Taškas gali būti nepilnas: $tikslas"
    Write-Output "  Ką daryti: paleisk dar kartą; jei kartoja -- atsiųsk šias eilutes"
    Write-Output "=============================================="
    exit 1
}

if (-not $env:N8N_ROOT)      { $env:N8N_ROOT      = 'C:\Users\M\Desktop\Kumstis' }
if (-not $env:N8N_TOOLS_DIR) { $env:N8N_TOOLS_DIR = 'C:\Users\M\CLINE\tools\n8n' }
if (-not $env:CLINE_HOME)    { $env:CLINE_HOME    = 'C:\Users\M\CLINE' }

$CLINE_HOME = $env:CLINE_HOME
$TASKU_ROOT = Join-Path $CLINE_HOME 'VISKAS\ATSTATYMO_TASKAI'

function Sakyk([string]$t) { if (-not $Tyliai) { Write-Output $t } }

# --- 1) Numeris ----------------------------------------------------------
if ($Numer -le 0) {
    $esami = @(Get-ChildItem -Path $TASKU_ROOT -Directory -Filter 'TASKAS-*' -ErrorAction SilentlyContinue)
    $Numer = $esami.Count + 1
}
$stamp = Get-Date -Format 'yyyy-MM-dd_HHmm'
$tikslas = Join-Path $TASKU_ROOT ("TASKAS-{0}_{1}" -f $Numer, $stamp)

Sakyk "Kuriu atstatymo tašką Nr. $Numer"
Sakyk "  -> $tikslas"
New-Item -ItemType Directory -Force -Path $tikslas | Out-Null

$surinkta = @()   # sąrašas failų, įtrauktų į tašką

function Kopijuoti-Kataloga {
    param([string]$Saltinis, [string]$Tikslas, [string[]]$Be = @())
    if (-not (Test-Path -LiteralPath $Saltinis)) { return 0 }
    New-Item -ItemType Directory -Force -Path $Tikslas | Out-Null
    $kiek = 0
    foreach ($f in Get-ChildItem -LiteralPath $Saltinis -Recurse -File -ErrorAction SilentlyContinue) {
        $praleisti = $false
        foreach ($sablonas in $Be) { if ($f.FullName -like $sablonas) { $praleisti = $true } }
        if ($praleisti) { continue }
        $santykis = $f.FullName.Substring($Saltinis.Length).TrimStart('\')
        $vieta = Join-Path $Tikslas $santykis
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $vieta) | Out-Null
        Copy-Item -LiteralPath $f.FullName -Destination $vieta -Force -ErrorAction SilentlyContinue
        $kiek++
    }
    return $kiek
}

# --- 2) Pultas ------------------------------------------------------------
$pultoKiekis = Kopijuoti-Kataloga -Saltinis (Join-Path $CLINE_HOME 'pultas') `
                                  -Tikslas (Join-Path $tikslas 'pultas') `
                                  -Be @('*__pycache__*', '*.pyc')
Sakyk "  pultas:        $pultoKiekis failų"

# --- 3) Įrankiai ----------------------------------------------------------
$irankiuKiekis = Kopijuoti-Kataloga -Saltinis (Join-Path $CLINE_HOME 'tools') `
                                    -Tikslas (Join-Path $tikslas 'tools') `
                                    -Be @('*__pycache__*', '*.pyc', '*.log')
Sakyk "  tools:         $irankiuKiekis failų"

# --- 4) Atmintis (CLINE *.md + VISKAS *.md) -------------------------------
$atmintiesKiekis = 0
$atmintisTikslas = Join-Path $tikslas 'atmintis'
New-Item -ItemType Directory -Force -Path $atmintisTikslas | Out-Null
foreach ($sablonas in @('*.md', '*.txt')) {
    foreach ($f in Get-ChildItem -LiteralPath $CLINE_HOME -File -Filter $sablonas -ErrorAction SilentlyContinue) {
        Copy-Item -LiteralPath $f.FullName -Destination (Join-Path $atmintisTikslas $f.Name) -Force
        $atmintiesKiekis++
    }
}
$viskasDir = Join-Path $CLINE_HOME 'VISKAS'
if (Test-Path -LiteralPath $viskasDir) {
    foreach ($f in Get-ChildItem -LiteralPath $viskasDir -File -ErrorAction SilentlyContinue) {
        Copy-Item -LiteralPath $f.FullName -Destination (Join-Path $atmintisTikslas $f.Name) -Force -ErrorAction SilentlyContinue
        $atmintiesKiekis++
    }
}
Sakyk "  atmintis:      $atmintiesKiekis failų"


# --- 5) n8n: workflow eksportas + duomenų bazė + pids.json ----------------
$n8nTikslas = Join-Path $tikslas 'n8n'
New-Item -ItemType Directory -Force -Path $n8nTikslas | Out-Null
$n8nInfo = @()

$runtime = Join-Path $env:N8N_ROOT 'runtime'
$pidsFile = Join-Path $runtime 'pids.json'
if (Test-Path -LiteralPath $pidsFile) {
    Copy-Item -LiteralPath $pidsFile -Destination (Join-Path $n8nTikslas 'pids.json') -Force
    $n8nInfo += 'pids.json: TAIP'
} else { $n8nInfo += 'pids.json: NĖRA' }

Sakyk "  n8n:           kopijuoju..."
$db = Join-Path $runtime 'n8n-data\.n8n\database.sqlite'
if ((Test-Path -LiteralPath $db) -and (-not $BeDuomenuBazes)) {
    try {
        $mb = [math]::Round((Get-Item -LiteralPath $db).Length / 1MB, 1)
        if ($mb -lt 500) {
            Copy-Item -LiteralPath $db -Destination (Join-Path $n8nTikslas 'database.sqlite') -Force -ErrorAction Stop
            $n8nInfo += "database.sqlite: TAIP ($mb MB)"
        } else {
            $n8nInfo += "database.sqlite: PRALEISTA (per didelė: $mb MB)"
        }
    } catch {
        $n8nInfo += "database.sqlite: NEPAVYKO kopijuoti ($($_.Exception.Message))"
        $n8nInfo += '  -> naudok -BeDuomenuBazes arba sustabdyk n8n'
    }
} elseif ($BeDuomenuBazes) { $n8nInfo += 'database.sqlite: praleista (-BeDuomenuBazes)' }
else { $n8nInfo += 'database.sqlite: NĖRA' }

if ($SuEksportu) {
    $cli = Join-Path $env:N8N_TOOLS_DIR 'n8n-cli.ps1'
    $wf = Join-Path $n8nTikslas 'workflows.json'
    if (Test-Path -LiteralPath $cli) {
        Sakyk "  n8n:           eksportuoju workflow (max 45 s)..."
        try {
            $p = Start-Process -FilePath 'powershell.exe' `
                -ArgumentList @('-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                                '-File', "`"$cli`"", 'export:workflow', '--all', "--output=`"$wf`"") `
                -WindowStyle Hidden -PassThru
            if (-not $p.WaitForExit(45000)) {
                Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
                $n8nInfo += 'workflows.json: NUTRAUKTA po 45 s (DB kopija yra atsarginis kelias)'
            } elseif (Test-Path -LiteralPath $wf) {
                $n8nInfo += 'workflows.json: TAIP'
            } else {
                $n8nInfo += 'workflows.json: nepavyko (DB kopija yra atsarginis kelias)'
            }
        } catch { $n8nInfo += "workflows.json: klaida ($($_.Exception.Message))" }
    } else { $n8nInfo += 'workflows.json: praleista (nėra n8n-cli.ps1)' }
} else {
    $n8nInfo += 'workflows.json: praleista (nereikia -- DB nukopijuota; norint: -SuEksportu)'
}


foreach ($i in $n8nInfo) { Sakyk "  n8n:           $i" }

# --- 6) Task Scheduler užduotys (XML) ------------------------------------
Sakyk "  užduotys:      skaitau..."
$uzduociuTikslas = Join-Path $tikslas 'uzduotys'
New-Item -ItemType Directory -Force -Path $uzduociuTikslas | Out-Null
$uzduociuKiekis = 0
try {
    $uzduotys = Get-ScheduledTask -ErrorAction SilentlyContinue |
                Where-Object { $_.TaskName -match 'N8N|CLINE|KUMSTIS|PULTAS|HOTKEY' }
} catch {
    Sakyk "  užduotys:      Get-ScheduledTask neprieinamas -- bandau per schtasks"
    $uzduotys = @(schtasks /Query /FO CSV /NH 2>$null |
                  ForEach-Object { $n = ($_ -split '","')[0].Trim('"'); if ($n -match 'N8N|CLINE|KUMSTIS|PULTAS|HOTKEY') { [pscustomobject]@{ TaskName = $n } } })
}
foreach ($u in $uzduotys) {
    $failas = Join-Path $uzduociuTikslas (($u.TaskName -replace '[\\/:*?"<>|]', '_') + '.xml')
    $xml = schtasks /Query /TN $u.TaskName /XML 2>&1
    if ($LASTEXITCODE -eq 0) {
        Set-Content -LiteralPath $failas -Value ($xml -join "`r`n") -Encoding Unicode
        $uzduociuKiekis++
    }
}
Sakyk "  užduotys:      $uzduociuKiekis XML failų"

# --- 7) Būklė: 11 servisų ataskaita + versijos ----------------------------
$bukleTikslas = Join-Path $tikslas 'bukle'
New-Item -ItemType Directory -Force -Path $bukleTikslas | Out-Null

$patikra = Join-Path $PSScriptRoot 'patikrinti-servisus.ps1'
$servisuFailas = Join-Path $bukleTikslas 'servisai.txt'
if (Test-Path -LiteralPath $patikra) {
    & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $patikra `
        -Issaugoti -Tyliai -AtaskaitosFailas $servisuFailas | Out-Null
    $santrauka = (@(Get-Content -LiteralPath $servisuFailas -ErrorAction SilentlyContinue) |
                  Where-Object { $_ -match 'Servisai veikia:' } | Select-Object -First 1)
    Sakyk "  būklė:         $santrauka"
} else {
    Set-Content -LiteralPath $servisuFailas -Value 'patikrinti-servisus.ps1 nerastas' -Encoding UTF8
    Sakyk "  būklė:         patikrinti-servisus.ps1 nerastas"
}

$versijos = New-Object System.Collections.Generic.List[string]
$versijos.Add("data=$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')")
$versijos.Add("kompiuteris=$env:COMPUTERNAME")
$versijos.Add("naudotojas=$env:USERNAME")
$versijos.Add("powershell=$($PSVersionTable.PSVersion)")
$versijos.Add("windows=$((Get-CimInstance Win32_OperatingSystem -ErrorAction SilentlyContinue).Caption)")
$nodeExe = Join-Path $env:N8N_ROOT 'runtime\node24\node.exe'
if (Test-Path -LiteralPath $nodeExe) { $versijos.Add("node=$(& $nodeExe -v 2>&1)") }
$pkg = Join-Path $env:N8N_ROOT 'runtime\n8n\node_modules\n8n\package.json'
if (Test-Path -LiteralPath $pkg) {
    $versijos.Add("n8n=$((Get-Content -LiteralPath $pkg -Raw | ConvertFrom-Json).version)")
}
try { $versijos.Add("python=$(& python --version 2>&1)") } catch { }
$versijos | Set-Content -LiteralPath (Join-Path $bukleTikslas 'versijos.txt') -Encoding UTF8

# --- 8) MANIFESTAS: TASKAS.json su SHA256 kiekvienam failui ---------------
$failai = @()
foreach ($f in Get-ChildItem -LiteralPath $tikslas -Recurse -File -ErrorAction SilentlyContinue) {
    if ($f.Name -eq 'TASKAS.json') { continue }
    $santykis = $f.FullName.Substring($tikslas.Length).TrimStart('\')
    $hash = (Get-FileHash -LiteralPath $f.FullName -Algorithm SHA256).Hash
    $failai += [pscustomobject]@{
        Kelias = $santykis
        Baitai = $f.Length
        Sha256 = $hash
    }
}

$manifestas = [pscustomobject]@{
    Numeris      = $Numer
    Sukurtas     = (Get-Date -Format 'o')
    Pastaba      = $Pastaba
    Kompiuteris  = $env:COMPUTERNAME
    Naudotojas   = $env:USERNAME
    N8nRoot      = $env:N8N_ROOT
    ClineHome    = $CLINE_HOME
    FailuViso    = $failai.Count
    BaitaiViso   = ($failai | Measure-Object -Property Baitai -Sum).Sum
    Failai       = $failai
    Ispejimas    = 'Šiame aplanke gali būti slaptažodžių ir raktų. NIEKADA nekelk jo į git/GitHub.'
}

$manifestas | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $tikslas 'TASKAS.json') -Encoding UTF8

$mb = [math]::Round(($manifestas.BaitaiViso / 1MB), 1)
Sakyk ""
Sakyk "TAŠKAS Nr. $Numer SUKURTAS"
Sakyk "  aplankas:      $tikslas"
Sakyk "  failų:         $($manifestas.FailuViso) ($mb MB)"
Sakyk "  manifestas:    TASKAS.json (SHA256)"
Sakyk ""
Sakyk "SVARBU: šiame aplanke gali būti slaptažodžių -- NIEKADA nekelk į git."
Sakyk "Atstatymas:    atstatyti-tasku.ps1 -Numer $Numer"
exit 0

