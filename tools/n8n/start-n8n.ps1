# start-n8n.ps1 -- paleidžia VIENĄ n8n serverį (:5678, brokeris :5679)
# Naudojimas:
#   powershell -NoProfile -ExecutionPolicy Bypass -File start-n8n.ps1            # įprastai
#   powershell -NoProfile -ExecutionPolicy Bypass -File start-n8n.ps1 -Force     # per prievadą
#   powershell -NoProfile -ExecutionPolicy Bypass -File start-n8n.ps1 -Tyliai    # be išvesties (budėtojui)
# Grąžina: 0 = veikia, 1 = nepavyko, 2 = trūksta failų, 3 = prievadą laiko svetimas procesas

[CmdletBinding()]
param(
    [switch]$Force,
    [switch]$Tyliai
)

$ErrorActionPreference = 'Continue'
. (Join-Path $PSScriptRoot 'n8n-konfig.ps1')

function Out-Log([string]$msg) {
    if (-not $Tyliai) { Write-Output $msg }
    Write-N8nLog $msg
}

# --- 0) Failų patikra ---
if (-not (Test-Path -LiteralPath $N8nKonfig.Node)) {
    Out-Log "KLAIDA: nėra node.exe ($($N8nKonfig.Node))"
    exit 2
}
if (-not (Test-Path -LiteralPath $N8nKonfig.N8nBin)) {
    Out-Log "KLAIDA: nėra n8n bin ($($N8nKonfig.N8nBin))"
    exit 2
}
New-Item -ItemType Directory -Force -Path $N8nKonfig.LogsDir | Out-Null

# --- 1) Ar jau veikia? (dvigubo starto apsauga) ---
if (-not $Force -and (Test-N8nSveikas)) {
    Out-Log "n8n jau veikia (:5678) -- startas praleistas. Naudok -Force, jei reikia per prievadą."
    exit 0
}

# --- 2) Sustabdyti seną n8n (serveris + jo vaikai = task runner + brokeris) ---
$senasPid = Get-N8nServerioProcesas
$saved = Get-N8nPids
if ($saved.n8n) { $senasPid = [int]$saved.n8n }

if ($senasPid -gt 0) {
    $vaikai = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
                Where-Object { $_.ParentProcessId -eq $senasPid } | ForEach-Object { [int]$_.ProcessId })
    Out-Log "Stabdau seną n8n PID=$senasPid (vaikai: $($vaikai -join ', '))"
    Stop-Process -Id $senasPid -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 3
    foreach ($v in $vaikai) { Stop-Process -Id $v -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 2
}

# --- 3) Prievadų patikra: ar 5678/5679 neužėmė SVETIMAS procesas ---
foreach ($p in $N8nKonfig.TikrinamiPrievadai) {
    $uzemejas = Test-PrievadasUzimtas -Port $p
    if ($uzemejas -gt 0) {
        $proc = Get-Process -Id $uzemejas -ErrorAction SilentlyContinue
        Out-Log "KLAIDA: prievadą $p laiko PID=$uzemejas ($($proc.ProcessName)). Serveris nepaleistas, kad neprarastum duomenų."
        Out-Log "  Patikrink: netstat -ano | findstr `":$p`"  ·  žr. tools\n8n\n8n-diagnostika.ps1"
        exit 3
    }
}

# --- 4) Windows rezervuotų prievadų patikra (Hyper-V po perkrovimo) ---
try {
    $israiskos = (netsh int ipv4 show excludedportrange protocol=tcp) -join "`n"
    $rezervuota = $false
    foreach ($eil in ($israiskos -split "`n")) {
        if ($eil -match '^\s*(\d+)\s+(\d+)\s*$') {
            $nuo = [int]$Matches[1]; $iki = [int]$Matches[2]
            foreach ($p in $N8nKonfig.TikrinamiPrievadai) {
                if ($p -ge $nuo -and $p -le $iki) { $rezervuota = $true; Out-Log "ĮSPĖJIMAS: prievadas $p yra Windows rezervuotame diapazone $nuo-$iki" }
            }
        }
    }
    if ($rezervuota) { Out-Log "  Jei n8n pakimba be klaidos -- keisk prievadą n8n-konfig.ps1 (ServerioPrievadas)." }
} catch { }

# --- 5) Aplinka + startas (paslėptas langas, žurnalai į failus) ---
Set-N8nAplinka -Brokeris $N8nKonfig.BrokerioPrievadas
Set-Location -LiteralPath $N8nKonfig.Root

$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$out = Join-Path $N8nKonfig.LogsDir "n8n-start-$stamp.out.log"
$err = Join-Path $N8nKonfig.LogsDir "n8n-start-$stamp.err.log"

Write-N8nLog ("Pradedu n8n: port={0} broker={1} data={2}" -f $env:N8N_PORT, $env:N8N_RUNNERS_TASK_BROKER_PORT, $env:N8N_USER_FOLDER)
Set-Content -LiteralPath $N8nKonfig.BootMarker -Value (Get-Date -Format 'o') -Encoding UTF8

$proc = Start-Process -FilePath $N8nKonfig.Node `
    -ArgumentList @("`"$($N8nKonfig.N8nBin)`"", 'start') `
    -WorkingDirectory $N8nKonfig.Root -WindowStyle Hidden `
    -RedirectStandardOutput $out -RedirectStandardError $err -PassThru

Set-N8nPid -Name 'n8n' -Value $proc.Id

# --- 6) Laukti /healthz ---
$ok = $false
for ($i = 0; $i -lt [math]::Ceiling($N8nKonfig.PaleidimoLaukimas / 2); $i++) {
    Start-Sleep -Seconds 2
    if (Test-N8nSveikas) { $ok = $true; break }
    if ($proc.HasExited) { break }
}

if ($ok) {
    Remove-Item -LiteralPath $N8nKonfig.BootMarker -Force -ErrorAction SilentlyContinue
    Out-Log "n8n VEIKIA: http://127.0.0.1:5678 (PID=$($proc.Id)) · brokeris :$($N8nKonfig.BrokerioPrievadas)"
    exit 0
}

Remove-Item -LiteralPath $N8nKonfig.BootMarker -Force -ErrorAction SilentlyContinue
Out-Log "KLAIDA: n8n neatsakė per $($N8nKonfig.PaleidimoLaukimas) s. Žurnalas: $err"
if (Test-Path -LiteralPath $err) {
    $uodegos = Get-Content -LiteralPath $err -Tail 12 -ErrorAction SilentlyContinue
    foreach ($u in $uodegos) { Out-Log "  | $u" }
}
exit 1
