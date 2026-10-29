# TIKRAS end-to-end testas Windows: worker -> Cline (tavo prenumerata) -> failas diske.
# NIEKO NETRINA ir NEPERRAŠO: failo vardas visada unikalus (laikas).
#
#   powershell -ExecutionPolicy Bypass -File e2e-test.ps1
param(
  [string]$Root = 'C:\Users\M\CLINE\ai-stack',
  [int]$Port = 7070,
  [int]$TimeoutSec = 600
)
$ErrorActionPreference = 'Stop'

$tokenFile = Join-Path $Root 'worker-token.txt'
if (-not (Test-Path $tokenFile)) { throw "Nera $tokenFile - pirmiau paleisk start-worker.ps1" }
$token = (Get-Content $tokenFile -Raw).Trim()
$base = "http://127.0.0.1:$Port"
$work = Join-Path $Root 'work'
$dir = Join-Path $work 'projektas'

Write-Output '=== 1. /healthz ==='
try {
  $h = Invoke-RestMethod -Uri "$base/healthz" -TimeoutSec 10
  Write-Output ($h | ConvertTo-Json -Compress)
} catch {
  throw ("Worker neatsako: " + $_.Exception.Message + " - paleisk start-worker.ps1")
}

$name = 'labas-' + (Get-Date -Format 'HHmmss') + '.txt'
$prompt = "Sukurk faila $name su viena eilute: Labas is Cline grandines. Neko daugiau nekeisk."

Write-Output ''
Write-Output '=== 2. Uzduotis agentui ==='
Write-Output ("Failas: " + $name)
$body = @{ prompt = $prompt; cwd = 'projektas'; timeout = $TimeoutSec } | ConvertTo-Json -Compress
$sw = [Diagnostics.Stopwatch]::StartNew()
$r = $null
try {
  $r = Invoke-RestMethod -Uri "$base/run" -Method POST `
    -Headers @{ 'x-worker-token' = $token } `
    -ContentType 'application/json; charset=utf-8' `
    -Body ([Text.Encoding]::UTF8.GetBytes($body)) `
    -TimeoutSec ($TimeoutSec + 60)
} catch {
  $resp = $_.ErrorDetails.Message
  if ($resp) { $r = $resp | ConvertFrom-Json } else { throw $_.Exception.Message }
}
$sw.Stop()

Write-Output ("ok        : " + $r.ok)
Write-Output ("modelis   : " + $r.model)
Write-Output ("iteracijos: " + $r.iterations)
Write-Output ("trukme    : " + $r.durationMs + " ms (viso " + [int]$sw.Elapsed.TotalSeconds + " s)")
Write-Output ("tekstas   : " + $r.text)
if ($r.error) { Write-Output ("klaida    : " + $r.error) }

Write-Output ''
Write-Output '=== 3. Failas diske ==='
$file = Join-Path $dir $name
if (Test-Path $file) {
  $content = Get-Content $file -Raw -Encoding UTF8
  Write-Output ("rasta: " + $file)
  Write-Output ($content.Trim())
  if ($content -match 'Labas') {
    Write-Output ''
    Write-Output 'END-TO-END VEIKIA: n8n kvietimas -> Cline -> failas diske'
    exit 0
  }
  Write-Output 'Failas sukurtas, bet turinys netinka'
  exit 1
}

Write-Output 'FAILAS NESUKURTAS. Ka tikrinti:'
Write-Output '  - cline auth (ar prisijungta prie Cline / ClinePass)'
Write-Output ('  - log: ' + (Join-Path $Root 'worker.log') + ' ir ' + (Join-Path $Root 'worker.err.log'))
Write-Output '  - jei klaida 401/429: modelis netinkamai pasirinktas arba isemta kvota'
exit 1
