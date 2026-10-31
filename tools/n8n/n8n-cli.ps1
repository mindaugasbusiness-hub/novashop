# n8n-cli.ps1 -- n8n CLI komandų apvalkalas, kuris NEUŽIMA brokerio prievado 5679.
#
# PROBLEMA (patikrinta 2026-10-25, _out/runWf.txt):
#   „n8n Task Broker's port 5679 is already in use. Do you have another instance of n8n running already?"
#   execute exit: 1
# KAS IŠ TIKRŲJŲ VYKSTA:
#   5679 yra to paties veikiančio serverio vidinis Task Broker (N8N_RUNNERS_TASK_BROKER_PORT).
#   Bet kuri CLI komanda (execute, import:workflow, publish:workflow) irgi bando pakelti
#   brokerį -- todėl susiduria su jau veikiančiu serveriu. Tai nėra „antras n8n egzempliorius".
# SPRENDIMAS:
#   CLI komandoms duodamas LAISVAS brokerio prievadas (5690..5699). Patikrinta: su 5699
#   „n8n Task Broker ready on 127.0.0.1, port 5699" ir execute grąžina 0.
#
# Naudojimas:
#   .\n8n-cli.ps1 execute --id=aukcionas0000001 --rawOutput
#   .\n8n-cli.ps1 import:workflow --input="C:\Users\M\CLINE\n8n\aukciono-stebejimas.json"
#   .\n8n-cli.ps1 publish:workflow --id=aukcionas0000001
#   .\n8n-cli.ps1 -Komanda execute -Argumentai @('--id=aukcionas0000001')
# Grąžina: n8n exit kodą.

[CmdletBinding()]
param(
    [Parameter(Position = 0, Mandatory = $true)]
    [string]$Komanda,

    [Parameter(Position = 1, ValueFromRemainingArguments = $true)]
    [string[]]$Argumentai = @(),

    # Jei nori fiksuoto brokerio prievado vietoj automatinio paieškos
    [int]$Brokeris = 0
)

$ErrorActionPreference = 'Continue'
. (Join-Path $PSScriptRoot 'n8n-konfig.ps1')

if (-not (Test-Path -LiteralPath $N8nKonfig.Node))   { Write-Output "KLAIDA: nėra node.exe"; exit 2 }
if (-not (Test-Path -LiteralPath $N8nKonfig.N8nBin)) { Write-Output "KLAIDA: nėra n8n bin";   exit 2 }

# --- Svarbu: serverio prievadas lieka 5678, bet brokeris turi būti LAISVAS ---
if ($Brokeris -le 0) {
    $Brokeris = Get-LaisvasBrokerioPrievadas
    if ($Brokeris -eq 0) {
        Write-Output "KLAIDA: nėra laisvo brokerio prievado intervale $($N8nKonfig.CliBrokerisNuo)-$($N8nKonfig.CliBrokerisIki)"
        Write-Output "  Uždaryk bereikalingus procesus arba nurodyk -Brokeris <prievadas>"
        exit 3
    }
}

Set-N8nAplinka -Brokeris $Brokeris
Set-Location -LiteralPath $N8nKonfig.Root

Write-N8nLog "CLI: n8n $Komanda $($Argumentai -join ' ') (brokeris=$Brokeris)"

$out = & $N8nKonfig.Node $N8nKonfig.N8nBin $Komanda @Argumentai 2>&1
$rc = $LASTEXITCODE

# Brokerio klaidos atpažinimas -- jei vis tiek susidūrė, pasakyti aiškiai
$tekstas = ($out | Out-String)
if ($tekstas -match "Task Broker's port (\d+) is already in use") {
    Write-Output "KLAIDA: brokerio prievadas $($Matches[1]) vis tiek užimtas."
    Write-Output "  Bandžiau brokerį $Brokeris. Patikrink, kas užima prievadus:"
    Write-Output "    powershell -NoProfile -File `"$PSScriptRoot\n8n-diagnostika.ps1`""
    Write-N8nLog "CLI KLAIDA: brokeris užimtas ($($Matches[1])), bandytas $Brokeris"
    Write-Output $tekstas
    exit 1
}

if ($out) { $out | ForEach-Object { Write-Output $_ } }
Write-N8nLog "CLI: exit=$rc"
exit $rc
