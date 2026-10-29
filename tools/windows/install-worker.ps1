# Cline worker installer for M's PC (Windows).
# TAISYKLE: nieko netrina, nepervardina ir neperraso. Jei failas yra - praleidzia.
#
# Naudojimas (per relay):
#   powershell -ExecutionPolicy Bypass -File install-worker.ps1 -WorkerJsBase64 <b64>
param(
  [Parameter(Mandatory = $true)][string]$WorkerJsBase64,
  [string]$Root = 'C:\Users\M\CLINE\ai-stack',
  [int]$Port = 7070
)

$ErrorActionPreference = 'Stop'
function Have($cmd) { return [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }

Write-Host '=== 1. Kas jau idiegta ==='
$tools = [ordered]@{
  node   = (Have node)
  npm    = (Have npm)
  git    = (Have git)
  docker = (Have docker)
  cline  = (Have cline)
}
$tools.GetEnumerator() | ForEach-Object { Write-Host ("  {0,-7} {1}" -f $_.Key, $_.Value) }
if ($tools.node) { Write-Host ("  node versija: " + (node -v)) }
if ($tools.cline) { Write-Host ("  cline versija: " + ((cline --version) -join ' ')) }

Write-Host '=== 2. Cline CLI ==='
if (-not $tools.cline) {
  if (-not $tools.npm) { throw 'Nera npm - reikia Node.js LTS is nodejs.org (as neinstaliuoju sisteminiu programu be leidimo).' }
  Write-Host '  Diegiu cline per npm (globaliai, tai naujas idiegimas, ne perrasymas)'
  npm install -g cline
} else {
  Write-Host '  jau yra - praleidziu'
}

Write-Host '=== 3. Katalogas ==='
if (-not (Test-Path $Root)) {
  New-Item -ItemType Directory -Path $Root -Force | Out-Null
  Write-Host "  sukurtas naujas: $Root"
} else {
  Write-Host "  jau yra, naudoju: $Root (nieko netrinu)"
}

Write-Host '=== 4. server.js (tik jei nera) ==='
$serverPath = Join-Path $Root 'server.js'
if (Test-Path $serverPath) {
  Write-Host '  server.js jau yra - NEperrasau (taisykle nr.1)'
} else {
  [IO.File]::WriteAllBytes($serverPath, [Convert]::FromBase64String($WorkerJsBase64))
  Write-Host "  irasytas: $serverPath"
}

Write-Host '=== 5. Aplinka ==='
$work = Join-Path $Root 'work'
if (-not (Test-Path $work)) { New-Item -ItemType Directory -Path $work -Force | Out-Null }
if (-not $env:WORKER_TOKEN) {
  $token = -join ((48..57) + (97..122) | Get-Random -Count 40 | ForEach-Object { [char]$_ })
  Write-Host "  WORKER_TOKEN (issisaugok): $token"
} else {
  $token = $env:WORKER_TOKEN
}

Write-Host '=== 6. Prisijungimas prie Cline (ClinePass / nemokamas modelis) ==='
$auth = Join-Path $env:USERPROFILE '.cline\data\settings\providers.json'
if (Test-Path $auth) {
  Write-Host "  jau prisijungta: $auth"
} else {
  Write-Host '  NERA prisijungimo. Reikia viena karta paleisti interaktyviai:'
  Write-Host '     cline auth'
  Write-Host '  (Cline account -> ClinePass / FREE modelis). Tada pokalbis gali testi.'
}

Write-Host '=== 7. Paleidimas ==='
Write-Host "  cd `"$Root`""
Write-Host "  `$env:WORKER_TOKEN='$token'; `$env:WORKSPACE_ROOT='$work'; `$env:PORT='$Port'; node server.js"
Write-Host ''
Write-Host "  Patikra:  curl http://127.0.0.1:$Port/healthz"
Write-Host '  n8n (Docker) -> http://host.docker.internal:' + $Port + '/run'
Write-Host '  n8n (tas pats PC) -> http://127.0.0.1:' + $Port + '/run'
