# atstatyti-tasku.ps1 -- atstato visą būseną į pasirinktą ATSTATYMO TAŠKĄ.
#
# Kai direktorius pasakys „atstatyti į Nr. 1" -- paleidžiama:
#   powershell -NoProfile -ExecutionPolicy Bypass -File atstatyti-tasku.ps1 -Numer 1
#
# SAUGUMAI:
#   1) Pirmiausia patikrinama taško SHA256 vientisumas -- sugadinto taško nestato.
#   2) Dabartinė būklė VISADA išsaugoma (PRADINE-BUKLE_<data>) -- nieko neprarandama.
#   3) -Sausai parodo, ką darytų, bet nieko nekeičia.
#
# Grąžina: 0 = atstatyta ir servisai veikia, 1 = klaida, 2 = taškas sugadintas, 3 = sausas režimas

[CmdletBinding()]
param(
    [int]$Numer = 1,
    [switch]$Sausai,
    # Duomenų bazė atstatoma NUTYLĖJUS (nes „atstatyti į Nr. 1" = visa būsena).
    # Jei nori atstatyti tik failus, o DB palikti dabartinę -- naudok -BeDuomenuBazes.
    [switch]$BeDuomenuBazes,
    [switch]$SuDuomenuBaze,      # senas vardas; paliktas suderinamumui (dabar ir taip įtraukta)
    [switch]$NepaleistiServisu,
    [switch]$Tyliai
)

$ErrorActionPreference = 'Continue'

if (-not $env:N8N_ROOT)      { $env:N8N_ROOT      = 'C:\Users\M\Desktop\Kumstis' }
if (-not $env:N8N_TOOLS_DIR) { $env:N8N_TOOLS_DIR = 'C:\Users\M\CLINE\tools\n8n' }
if (-not $env:CLINE_HOME)    { $env:CLINE_HOME    = 'C:\Users\M\CLINE' }

$CLINE_HOME = $env:CLINE_HOME
$TASKU_ROOT = Join-Path $CLINE_HOME 'VISKAS\ATSTATYMO_TASKAI'

function Sakyk([string]$t) { if (-not $Tyliai) { Write-Output $t } }
function Klaida([string]$t) { Write-Output "KLAIDA: $t" }

# --- 1) Rasti tašką -------------------------------------------------------
# Imamas NAUJAUSIAS taškas, kuris turi TASKAS.json (t. y. tikrai užbaigtas).
$visiKandidatai = @(Get-ChildItem -Path $TASKU_ROOT -Directory -Filter "TASKAS-$Numer`_*" -ErrorAction SilentlyContinue |
                    Sort-Object Name -Descending)
$kandidatai = @($visiKandidatai | Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName 'TASKAS.json') })

if ($kandidatai.Count -eq 0) {
    if ($visiKandidatai.Count -gt 0) {
        Klaida "taškas Nr. $Numer yra, bet NEPILNAS (nėra TASKAS.json): $($visiKandidatai[0].FullName)"
        Sakyk "Sukurk jį iš naujo: sukurkti-taskas.ps1 -Numer $Numer"
    } else {
        Klaida "nera atstatymo taško Nr. $Numer ($TASKU_ROOT\TASKAS-$Numer`_*)"
        Sakyk "Sukurk: sukurkti-taskas.ps1 -Numer $Numer"
    }
    exit 1
}
$taskas = $kandidatai[0].FullName
$manifestoFailas = Join-Path $taskas 'TASKAS.json'

Sakyk "Atstatymo taškas: $taskas"
if (-not (Test-Path -LiteralPath $manifestoFailas)) {
    Klaida "taške nėra TASKAS.json -- negaliu patikrinti vientisumo, nestatau"
    exit 2
}

$manifestas = Get-Content -LiteralPath $manifestoFailas -Raw | ConvertFrom-Json
Sakyk "  sukurtas:  $($manifestas.Sukurtas)"
Sakyk "  pastaba:   $($manifestas.Pastaba)"
Sakyk "  failų:     $($manifestas.FailuViso)"
Sakyk "  kompiuteris: $($manifestas.Kompiuteris)"

# --- 2) SHA256 vientisumo patikra ----------------------------------------
$blogi = @()
foreach ($f in $manifestas.Failai) {
    $kelias = Join-Path $taskas $f.Kelias
    if (-not (Test-Path -LiteralPath $kelias)) { $blogi += "$($f.Kelias): NĖRA"; continue }
    $hash = (Get-FileHash -LiteralPath $kelias -Algorithm SHA256).Hash
    if ($hash -ne $f.Sha256) { $blogi += "$($f.Kelias): SHA256 nesutampa" }
}

if ($blogi.Count -gt 0) {
    Klaida "taškas Nr. $Numer sugadintas ($($blogi.Count) failų). Nestatau."
    $blogi | Select-Object -First 10 | ForEach-Object { Sakyk "  - $_" }
    exit 2
}
Sakyk "SHA256 patikra: OK (visi $($manifestas.FailuViso) failai sveiki)"

if ($Sausai) {
    Sakyk ""
    Sakyk "SAUSAS REŽIMAS: būčiau atkūręs:"
    Sakyk "  pultas   -> $(Join-Path $CLINE_HOME 'pultas')"
    Sakyk "  tools    -> $(Join-Path $CLINE_HOME 'tools')"
    Sakyk "  atmintis -> $CLINE_HOME"
    Sakyk "  užduotys -> Task Scheduler (N8N/CLINE/KUMSTIS)"
    Sakyk "  n8n DB   -> $(if ($BeDuomenuBazes) { 'NE (-BeDuomenuBazes): DB liks dabartinė' } else { 'TAIP (bus atstatyta)' })"
    Sakyk "Nieko nepakeičiau."
    exit 3
}

# --- 3) Dabartinės būklės kopija (1 taisyklė: nieko netrinti) -------------
$stamp = Get-Date -Format 'yyyy-MM-dd_HHmm'
$priesTikslas = Join-Path $TASKU_ROOT ("PRADINE-BUKLE_$stamp")
Sakyk ""
Sakyk "Saugau dabartinę būklę: $priesTikslas"
foreach ($pora in @(
    @{ S = (Join-Path $CLINE_HOME 'pultas'); T = 'pultas' },
    @{ S = (Join-Path $CLINE_HOME 'tools');  T = 'tools' })) {
    if (Test-Path -LiteralPath $pora.S) {
        $tikslas = Join-Path $priesTikslas $pora.T
        New-Item -ItemType Directory -Force -Path $tikslas | Out-Null
        Copy-Item -Path (Join-Path $pora.S '*') -Destination $tikslas -Recurse -Force -ErrorAction SilentlyContinue
    }
}
Sakyk "  (jei atstatymas bus neteisingas -- viską galima grąžinti iš šio aplanko)"

# --- 3b) Sustabdyti n8n, kad DB failas nebūtų užrakintas ar pusiau įrašytas ---
if (-not $NepaleistiServisu) {
    $restartSkriptas = Join-Path $env:N8N_TOOLS_DIR 'restart-n8n.ps1'
    if (Test-Path -LiteralPath $restartSkriptas) {
        Sakyk "Stabdau n8n (kad DB būtų galima saugiai nukopijuoti)..."
        & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $restartSkriptas -TikStop | Out-Null
        Start-Sleep -Seconds 4
        $liko = (@(5678, 5679 | ForEach-Object {
            (Get-NetTCPConnection -LocalPort $_ -State Listen -ErrorAction SilentlyContinue | Measure-Object).Count
        }) | Measure-Object -Sum).Sum
        Sakyk "  n8n sustabdytas (likę klausantys prievadai: $liko)"
    } else {
        Sakyk "  restart-n8n.ps1 nerastas -- n8n nestabdau"
    }
}

# Dabar, kai n8n neveikia, išsaugome DABARTINĘ duomenų bazę (kitaip prarastume naujus duomenis)
if (-not $BeDuomenuBazes) {
    $dbDabartine = Join-Path (Join-Path $env:N8N_ROOT 'runtime') 'n8n-data\.n8n\database.sqlite'
    if (Test-Path -LiteralPath $dbDabartine) {
        try {
            New-Item -ItemType Directory -Force -Path (Join-Path $priesTikslas 'n8n') | Out-Null
            Copy-Item -LiteralPath $dbDabartine -Destination (Join-Path $priesTikslas 'n8n\database.sqlite') -Force -ErrorAction Stop
            Sakyk "  dabartinė n8n DB išsaugota PRADINE-BUKLE aplanke"
        } catch {
            Sakyk "  ĮSPĖJIMAS: nepavyko išsaugoti dabartinės DB ($($_.Exception.Message))"
            Sakyk "  -> atstatymą darau, bet DB nebus liesta"
            $BeDuomenuBazes = [switch]$true
        }
    }
}



# --- 4) Failų atstatymas --------------------------------------------------
$atkurta = 0
foreach ($f in $manifestas.Failai) {
    $saltinis = Join-Path $taskas $f.Kelias
    if (-not (Test-Path -LiteralPath $saltinis)) { continue }

    if ($f.Kelias -like 'n8n\database.sqlite' -and $BeDuomenuBazes) { continue }

    if ($f.Kelias -like 'pultas\*')      { $tikslas = Join-Path $CLINE_HOME $f.Kelias }
    elseif ($f.Kelias -like 'tools\*')   { $tikslas = Join-Path $CLINE_HOME $f.Kelias }
    elseif ($f.Kelias -like 'atmintis\*') { $tikslas = Join-Path $CLINE_HOME (Split-Path $f.Kelias -Leaf) }
    elseif ($f.Kelias -like 'n8n\database.sqlite') { $tikslas = Join-Path $env:N8N_ROOT 'runtime\n8n-data\.n8n\database.sqlite' }
    elseif ($f.Kelias -like 'n8n\pids.json')       { $tikslas = Join-Path $env:N8N_ROOT 'runtime\pids.json' }
    else { continue }   # uzduotys, bukle -- atkuriamos atskirai

    # jei failas jau yra -- kopija su data (nieko netriname)
    if (Test-Path -LiteralPath $tikslas) {
        Copy-Item -LiteralPath $tikslas -Destination "$tikslas.bak-pries-atstatyma-$stamp" -Force -ErrorAction SilentlyContinue
    }
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $tikslas) | Out-Null
    Copy-Item -LiteralPath $saltinis -Destination $tikslas -Force
    $atkurta++
}
Sakyk "Atkurta failų: $atkurta"

# --- 5) Task Scheduler užduotys ------------------------------------------
$uzduociuTikslas = Join-Path $taskas 'uzduotys'
$uzduociuKiekis = 0
if (Test-Path -LiteralPath $uzduociuTikslas) {
    foreach ($x in Get-ChildItem -LiteralPath $uzduociuTikslas -Filter '*.xml' -ErrorAction SilentlyContinue) {
        $rez = schtasks /Create /TN ($x.BaseName) /XML $x.FullName /F 2>&1
        if ($LASTEXITCODE -eq 0) { $uzduociuKiekis++ }
        else { Sakyk "  užduotis $($x.BaseName): nepavyko" }
    }
}
Sakyk "Atkurta užduočių: $uzduociuKiekis"

# --- 6) Servisų paleidimas ------------------------------------------------
if (-not $NepaleistiServisu) {
    Sakyk ""
    Sakyk "Paleidžiu servisus..."
    $restart = Join-Path $env:N8N_TOOLS_DIR 'restart-n8n.ps1'
    if (Test-Path -LiteralPath $restart) {
        & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $restart | Out-Null
        Sakyk "  n8n: perkrautas (kodas $LASTEXITCODE)"
    } else { Sakyk "  n8n: restart-n8n.ps1 nerastas" }

    $pultasPy = Join-Path $CLINE_HOME 'pultas\pultas.py'
    if (Test-Path -LiteralPath $pultasPy) {
        $jauVeikia = (Get-NetTCPConnection -LocalPort 8790 -State Listen -ErrorAction SilentlyContinue | Measure-Object).Count -gt 0
        if ($jauVeikia) { Sakyk "  pultas: jau veikia (:8790)" }
        else {
            Start-Process -FilePath 'python' -ArgumentList @("`"$pultasPy`"") -WorkingDirectory (Split-Path $pultasPy -Parent) -WindowStyle Hidden
            Sakyk "  pultas: paleistas"
        }
    }
    Start-Sleep -Seconds 10
}

# --- 7) Patikra: 11 servisų ----------------------------------------------
Sakyk ""
$patikra = Join-Path $PSScriptRoot 'patikrinti-servisus.ps1'
if (Test-Path -LiteralPath $patikra) {
    & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $patikra
    $rc = $LASTEXITCODE
} else {
    Klaida "patikrinti-servisus.ps1 nerastas -- negaliu patvirtinti būklės"
    $rc = 1
}

Sakyk ""
if ($rc -eq 0) {
    Sakyk "ATSTATYMAS Į TAŠKĄ Nr. $Numer BAIGTAS: servisai veikia (11/11)."
    exit 0
}
Sakyk "ATSTATYMAS Į TAŠKĄ Nr. $Numer atliktas, BET ne visi servisai atsako."
Sakyk "Žiūrėk ataskaitą aukščiau; jei reikia -- grąžinimas iš $priesTikslas"
exit 1

