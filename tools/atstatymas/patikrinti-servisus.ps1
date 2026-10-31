# patikrinti-servisus.ps1 -- tikrina VISUS 11 pulto servisų (taip pat, kaip pultas :8790).
# Naudojamas prieš ir po atstatymo, kad būtų aišku, ar būsena tikrai atstatyta.
#
# Naudojimas:
#   powershell -NoProfile -ExecutionPolicy Bypass -File patikrinti-servisus.ps1
#   powershell -NoProfile -ExecutionPolicy Bypass -File patikrinti-servisus.ps1 -Issaugoti
#   powershell -NoProfile -ExecutionPolicy Bypass -File patikrinti-servisus.ps1 -Tyliai
# Grąžina: 0 = visi veikia, 1 = bent vienas neveikia

[CmdletBinding()]
param(
    [switch]$Issaugoti,
    [switch]$Tyliai,
    [string]$AtaskaitosFailas = ''
)

$ErrorActionPreference = 'Continue'

if (-not $env:N8N_TOOLS_DIR) { $env:N8N_TOOLS_DIR = 'C:\Users\M\CLINE\tools\n8n' }
$n8nKonfig = Join-Path $env:N8N_TOOLS_DIR 'n8n-konfig.ps1'
$VISKAS = 'C:\Users\M\CLINE\VISKAS\ATSTATYMO_TASKAI'

# --- Servisų aprašas: tiksliai kaip pulto lentelėje ------------------------
$servisai = @(
    @{ Pavadinimas = 'n8n';                Tipas = 'http'; Adresas = 'http://127.0.0.1:5678/healthz';       Prievadas = 5678 },
    @{ Pavadinimas = 'Naršyklės daemonas'; Tipas = 'http'; Adresas = 'http://127.0.0.1:8099/health';        Prievadas = 8099 },
    @{ Pavadinimas = 'F6 panelis';         Tipas = 'http'; Adresas = 'http://127.0.0.1:8766/api/list';     Prievadas = 8766 },
    @{ Pavadinimas = 'Žvėris UI';          Tipas = 'http'; Adresas = 'http://127.0.0.1:8091/api/status';   Prievadas = 8091 },
    @{ Pavadinimas = 'Kumštis tools';      Tipas = 'http'; Adresas = 'http://127.0.0.1:8090/healthz';      Prievadas = 8090 },
    @{ Pavadinimas = 'Naršyklės CDP';      Tipas = 'http'; Adresas = 'http://127.0.0.1:9222/json/version'; Prievadas = 9222 },
    @{ Pavadinimas = 'n8n brokeris';       Tipas = 'port'; Adresas = '';                                  Prievadas = 5679 },
    @{ Pavadinimas = 'Qdrant';             Tipas = 'port'; Adresas = '';                                  Prievadas = 6333 },
    @{ Pavadinimas = 'Automatikos tiltas'; Tipas = 'http'; Adresas = 'http://127.0.0.1:8792/health';       Prievadas = 8792 },
    @{ Pavadinimas = 'AUSYS (balsas)';     Tipas = 'port'; Adresas = '';                                  Prievadas = 8795 },
    @{ Pavadinimas = 'PULTAS (šis)';       Tipas = 'port'; Adresas = '';                                  Prievadas = 8790 }
)

$eilutes = New-Object System.Collections.Generic.List[string]
function Add-Eil([string]$t) { $script:eilutes.Add($t); if (-not $Tyliai) { Write-Output $t } }

$veikia = 0
$neveikia = 0
$pradzia = Get-Date

Add-Eil "===== SERVISŲ PATIKRA $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ====="
Add-Eil ("{0,-22} {1,-26} {2,-10} {3}" -f 'Servisas', 'Adresas', 'Būsena', 'Detalės')

foreach ($s in $servisai) {
    $busena = 'NEVEIKIA'
    $detales = ''

    if ($s.Tipas -eq 'http') {
        try {
            $r = Invoke-WebRequest -Uri $s.Adresas -UseBasicParsing -TimeoutSec 5
            if ($r.StatusCode -eq 200) {
                $busena = 'VEIKIA'
                $detales = "HTTP 200 ($($r.RawContentLength) B)"
            } else {
                $detales = "HTTP $($r.StatusCode)"
            }
        } catch {
            $detales = ($_.Exception.Message -split "`n")[0]
            if ($detales.Length -gt 60) { $detales = $detales.Substring(0, 60) }
        }
    } else {
        $pidNr = 0
        $c = Get-NetTCPConnection -LocalPort $s.Prievadas -State Listen -ErrorAction SilentlyContinue |
             Select-Object -First 1
        if ($c) { $pidNr = [int]$c.OwningProcess }
        if ($pidNr -gt 0) {
            $busena = 'VEIKIA'
            $proc = Get-Process -Id $pidNr -ErrorAction SilentlyContinue
            $detales = "portas klauso (PID $pidNr, $($proc.ProcessName))"
        } else {
            $detales = 'portas neklauso'
        }
    }

    if ($busena -eq 'VEIKIA') { $veikia++ } else { $neveikia++ }
    Add-Eil ("{0,-22} {1,-26} {2,-10} {3}" -f $s.Pavadinimas, $s.Adresas, $busena, $detales)
}

$truko = [math]::Round(((Get-Date) - $pradzia).TotalSeconds, 1)
Add-Eil ""
Add-Eil "Servisai veikia: $veikia/$($servisai.Count)   (NEVEIKIA: $neveikia, truko $truko s)"

# --- Papildoma n8n informacija (brokerio PID turi sutapti su serverio) ---
$p5678 = 0; $p5679 = 0
$c1 = Get-NetTCPConnection -LocalPort 5678 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
$c2 = Get-NetTCPConnection -LocalPort 5679 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($c1) { $p5678 = [int]$c1.OwningProcess }
if ($c2) { $p5679 = [int]$c2.OwningProcess }
if ($p5678 -gt 0 -and $p5678 -eq $p5679) {
    Add-Eil "n8n: 5678 ir 5679 laiko TAS PATS PID ($p5678) -- normalu (5679 = Task Broker)"
} elseif ($p5678 -gt 0 -and $p5679 -gt 0) {
    Add-Eil "n8n ĮSPĖJIMAS: 5678 (PID $p5678) ir 5679 (PID $p5679) -- SKIRTINGI procesai!"
} else {
    Add-Eil "n8n: 5678=$p5678, 5679=$p5679"
}

# --- n8n diagnistikos nuoroda (jei yra) ---
if (Test-Path -LiteralPath $n8nKonfig) {
    Add-Eil "Išsami n8n būklė: tools\n8n\n8n-diagnostika.ps1"
}

$viska = $eilutes -join "`r`n"

if ($Issaugoti) {
    if (-not $AtaskaitosFailas) {
        New-Item -ItemType Directory -Force -Path $VISKAS | Out-Null
        $AtaskaitosFailas = Join-Path $VISKAS ("servisu-patrika-{0}.txt" -f (Get-Date -Format 'yyyyMMdd_HHmmss'))
    }
    Set-Content -LiteralPath $AtaskaitosFailas -Value $viska -Encoding UTF8
    if (-not $Tyliai) { Write-Output "Išsaugota: $AtaskaitosFailas" }
}

if ($neveikia -gt 0) { exit 1 }
exit 0
