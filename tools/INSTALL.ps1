# INSTALL.ps1 -- parsiunčia ir sudeda įrankius iš GitHub į tavo kompiuterį.
#
# Kodėl reikia: įrankiai sukurti repo šakoje `cline/da6qq3k9` ir užfiksuoti žyma `atstatymas-1`,
# o tavo mašinoje jų dar nėra. Šis failas nukopijuoja juos ten, kur jų tikisi pultas ir budėtojas.
#
# NAUDOJIMAS (Windows PowerShell 5.1 ir 7.x):
#   iwr -useb https://raw.githubusercontent.com/mindaugasbusiness-hub/novashop/cline/da6qq3k9/tools/GET.ps1 | iex
#
# Pastaba: `iwr ... | iex` ŠIO failo tiesiogiai vykdyti NEGALIMA senoje PowerShell 5.1 --
# ji nepriima `[CmdletBinding()]` per iex. Todėl yra GET.ps1, kuris parsiunčia ir paleidžia
# šį failą kaip failą (-File). Arba išsaugok ir paleisk tiesiogiai:
#   powershell -NoProfile -ExecutionPolicy Bypass -File INSTALL.ps1
#   powershell -NoProfile -ExecutionPolicy Bypass -File INSTALL.ps1 -Tikrinti
#
# NIEKO NETRINA: jei failas jau yra -- padaroma .bak-<data> kopija (1 taisyklė).

param(
    # Imama iš ŠAKOS, o ne iš žymos: taip pataisymai pasiekia tave iš karto.
    # Žyma `atstatymas-1` lieka kaip užfiksuota būsena dokumentuose.
    [string]$Ref = 'cline/da6qq3k9',
    [switch]$Tikrinti,              # tik patikrinti, ar viskas jau yra
    [string]$ClineHome = 'C:\Users\M\CLINE'
)


$ErrorActionPreference = 'Continue'
try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 } catch { }

$baze = "https://raw.githubusercontent.com/mindaugasbusiness-hub/novashop/$Ref"
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'

# GitHub CDN (Fastly) laiko senas kopijas iki ~5 min. Todėl prie kiekvieno URL
# pridedame unikalų laiko žymeklį -- taip visada gaunama NAUJAUSIA versija.
# (2026-10-31: be šito buvo atsiųsta sena 10326 B versija vietoj pataisytos 10313 B.)
$cacheBuster = '?t=' + [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()

# --- Failų sąrašas: kur imti -> kur dėti ---------------------------------
$failai = @(
    @{ Url = 'tools/n8n/n8n-konfig.ps1';             Dir = "$ClineHome\tools\n8n" },
    @{ Url = 'tools/n8n/start-n8n.ps1';              Dir = "$ClineHome\tools\n8n" },
    @{ Url = 'tools/n8n/start-n8n.cmd';              Dir = "$ClineHome\tools\n8n" },
    @{ Url = 'tools/n8n/restart-n8n.ps1';            Dir = "$ClineHome\tools\n8n" },
    @{ Url = 'tools/n8n/n8n-watchdog.ps1';           Dir = "$ClineHome\tools\n8n" },
    @{ Url = 'tools/n8n/n8n-cli.ps1';                Dir = "$ClineHome\tools\n8n" },
    @{ Url = 'tools/n8n/n8n-diagnostika.ps1';        Dir = "$ClineHome\tools\n8n" },
    @{ Url = 'tools/n8n/registruok-uzduotis.ps1';    Dir = "$ClineHome\tools\n8n" },
    @{ Url = 'tools/n8n/test-n8n-logika.ps1';        Dir = "$ClineHome\tools\n8n" },
    @{ Url = 'tools/n8n/savitikra.py';               Dir = "$ClineHome\tools\n8n" },
    @{ Url = 'tools/n8n/README.md';                  Dir = "$ClineHome\tools\n8n" },
    @{ Url = 'tools/atstatymas/patikrinti-servisus.ps1'; Dir = "$ClineHome\tools\atstatymas" },
    @{ Url = 'tools/atstatymas/sukurkti-taskas.ps1';     Dir = "$ClineHome\tools\atstatymas" },
    @{ Url = 'tools/atstatymas/atstatyti-tasku.ps1';     Dir = "$ClineHome\tools\atstatymas" },
    @{ Url = 'tools/atstatymas/savitikra.py';            Dir = "$ClineHome\tools\atstatymas" },
    @{ Url = 'tools/atstatymas/vps-taskas.sh';           Dir = "$ClineHome\tools\atstatymas" },
    @{ Url = 'tools/atstatymas/test-vps-taskas.sh';      Dir = "$ClineHome\tools\atstatymas" },
    @{ Url = 'tools/pulto-mygtukas-restart-n8n.py';  Dir = "$ClineHome\tools" },
    # Atminties dokumentas -- į VISKAS aplanką (ten, kur M laiko savo žinias)
    @{ Url = 'CLINE/VISKAS/12_ATLIKTA_2026-10-31.md'; Dir = "$ClineHome\VISKAS" }
)

Write-Output "=== n8n ir atstatymo įrankių diegimas ==="
Write-Output "Šaltinis: $baze"
Write-Output "Tikslas:  $ClineHome\tools"
Write-Output ""

$ok = 0
$jau = 0
$klaidos = @()

foreach ($f in $failai) {
    $vardas = Split-Path $f.Url -Leaf
    $tikslas = Join-Path $f.Dir $vardas

    if (Test-Path -LiteralPath $tikslas) {
        $jau++
        if ($Tikrinti) { Write-Output "YRA   $tikslas" }
        else { Write-Output "YRA   $vardas (atnaujinu, sena -> .bak-$stamp)" }
    }

    if ($Tikrinti) { continue }

    if (-not (Test-Path -LiteralPath $f.Dir)) {
        New-Item -ItemType Directory -Force -Path $f.Dir | Out-Null
    }

    try {
        # 1 taisyklė: sena kopija, o ne trynimas
        if (Test-Path -LiteralPath $tikslas) {
            Copy-Item -LiteralPath $tikslas -Destination "$tikslas.bak-$stamp" -Force
        }
        Invoke-WebRequest -Uri "$baze/$($f.Url)$cacheBuster" -OutFile $tikslas -UseBasicParsing -TimeoutSec 60
        $dydis = (Get-Item -LiteralPath $tikslas).Length
        if ($dydis -lt 50) { throw "failas per mažas ($dydis B)" }
        Write-Output "OK    $vardas ($dydis B)"
        $ok++
    } catch {
        $klaidos += "$vardas : $($_.Exception.Message)"
        Write-Output "KLAIDA $vardas : $($_.Exception.Message)"
    }
}

Write-Output ""
if ($Tikrinti) {
    Write-Output "Rasta jau esamų failų: $jau iš $($failai.Count)"
    if ($jau -eq $failai.Count) { Write-Output "Viskas jau įdiegta."; exit 0 }
    Write-Output "Trūksta $($failai.Count - $jau). Paleisk be -Tikrinti, kad įdiegčiau."
    exit 1
}

Write-Output "Įdiegta: $ok · jau buvo: $jau · klaidų: $($klaidos.Count)"
if ($klaidos.Count -gt 0) {
    Write-Output ""
    Write-Output "Klaidos:"
    $klaidos | ForEach-Object { Write-Output "  - $_" }
    Write-Output ""
    Write-Output "Patikrink internetą arba bandyk dar kartą su -Ref cline/da6qq3k9"
    exit 1
}

# --- Greita patikra, ar failai sveiki ------------------------------------
Write-Output ""
Write-Output "=== Patikra ==="
$konfig = Join-Path "$ClineHome\tools\n8n" 'n8n-konfig.ps1'
if (Test-Path -LiteralPath $konfig) {
    $baitai = [System.IO.File]::ReadAllBytes($konfig)
    $turiBom = ($baitai.Length -ge 3 -and $baitai[0] -eq 0xEF -and $baitai[1] -eq 0xBB -and $baitai[2] -eq 0xBF)
    Write-Output "n8n-konfig.ps1 UTF-8 BOM: $(if ($turiBom) { 'TAIP (gerai)' } else { 'NE (blogai!)' })"
}

Write-Output ""
Write-Output "=== KAS TOLIAU (2 žingsniai) ==="
Write-Output ""
Write-Output "1) Patikrinti, ar visi 11 servisų veikia:"
Write-Output "   powershell -NoProfile -ExecutionPolicy Bypass -File `"$ClineHome\tools\atstatymas\patikrinti-servisus.ps1`""
Write-Output ""
Write-Output "2) Sukurti atstatymo tašką Nr. 1 (mašinos dalis):"
Write-Output "   powershell -NoProfile -ExecutionPolicy Bypass -File `"$ClineHome\tools\atstatymas\sukurkti-taskas.ps1`" -Numer 1 -Pastaba `"11/11 veikia`""
Write-Output ""
exit 0
