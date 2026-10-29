# START-AI-STACK.ps1 - vienu paspaudimu: n8n + Cline worker + patikra.
# NIEKO NETRINA ir neperraso. Jei kas jau veikia - praleidzia.
#
# n8n paleidziamas TIESIOGIAI (ne per start-native.ps1), nes tas krenta ties
# embedding'u patikra (truksta sentence-transformers modelio) ir n8n nepaleidzia.
# Trukstamiems kintamiesiems (N8N_ENCRYPTION_KEY ir kt.) nuskaitomas Kumstis .env.
param(
  [string]$Root = 'C:\Users\M\CLINE\ai-stack',
  [int]$Port = 7070,
  [int]$N8nPort = 5678,
  [int]$WaitSec = 120,
  [string]$N8nRoot = 'C:\Users\M\Desktop\Kumstis',
  [string]$N8nNode = 'C:\Users\M\Desktop\Kumstis\runtime\node24\node.exe',
  [string]$N8nCli = 'C:\Users\M\Desktop\Kumstis\runtime\n8n\node_modules\n8n\bin\n8n'
)
$ErrorActionPreference = 'Continue'

function Test-Tcp([int]$p) {
  $c = New-Object Net.Sockets.TcpClient
  try { $c.Connect('127.0.0.1', $p); $c.Close(); return $true } catch { return $false }
}
function Get-WorkerHealth {
  try { return (Invoke-RestMethod "http://127.0.0.1:$Port/healthz" -TimeoutSec 5) } catch { return $null }
}

$logDir = Join-Path $Root 'logs'
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }

Write-Output '=== AI STACK START ==='
Write-Output ('Laikas: ' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'))

# --- 1. n8n ---
if (Test-Tcp $N8nPort) {
  Write-Output ("n8n :$N8nPort - jau veikia, neperleidziu")
} elseif ((Test-Path $N8nNode) -and (Test-Path $N8nCli)) {
  $envFile = Join-Path $N8nRoot '.env'
  $loaded = 0
  if (Test-Path $envFile) {
    foreach ($line in (Get-Content $envFile -Encoding UTF8)) {
      $t = $line.Trim()
      if ($t -eq '' -or $t.StartsWith('#')) { continue }
      $i = $t.IndexOf('=')
      if ($i -lt 1) { continue }
      $k = $t.Substring(0, $i).Trim()
      $v = $t.Substring($i + 1).Trim().Trim('"')
      Set-Item -Path ('Env:' + $k) -Value $v
      $loaded++
    }
  }
  if (-not $env:N8N_PORT) { $env:N8N_PORT = "$N8nPort" }
  if (-not $env:N8N_LISTEN_ADDRESS) { $env:N8N_LISTEN_ADDRESS = '127.0.0.1' }
  if (-not $env:N8N_RUNNERS_MODE) { $env:N8N_RUNNERS_MODE = 'internal' }
  if (-not $env:GENERIC_TIMEZONE) { $env:GENERIC_TIMEZONE = 'Europe/Vilnius' }
  # ta pati failu prieigos riba, kaip start-native.ps1 (170-173 eil.)
  if (-not $env:REPORTS_DIR) { $env:REPORTS_DIR = (Join-Path $N8nRoot 'DeFi ataskaitos') }
  if (-not $env:N8N_RESTRICT_FILE_ACCESS_TO) { $env:N8N_RESTRICT_FILE_ACCESS_TO = $env:REPORTS_DIR }
  $env:PATH = (Split-Path $N8nNode) + ';' + $env:PATH
  Write-Output ('n8n - krauta kintamuju is .env: ' + $loaded)

  Start-Process -FilePath $N8nNode -ArgumentList ("`"$N8nCli`"", 'start') `
    -WorkingDirectory $N8nRoot -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $logDir 'n8n.log') `
    -RedirectStandardError (Join-Path $logDir 'n8n.err.log') | Out-Null
  Write-Output ("n8n :$N8nPort - paleistas")
} else {
  Write-Output 'n8n - NERASTAS (patikrink N8nNode / N8nCli)'
}

# --- 2. Cline worker ---
if (Get-WorkerHealth) {
  Write-Output ("worker :$Port - jau veikia")
} else {
  $starter = Join-Path $Root 'start-worker.ps1'
  if (Test-Path $starter) {
    & $starter -Root $Root -Port $Port | Out-Null
    Write-Output ("worker :$Port - paleistas")
  } else {
    Write-Output ('worker - NERASTAS: ' + $starter)
  }
}

# --- 3. laukiam ---
$deadline = (Get-Date).AddSeconds($WaitSec)
while ((Get-Date) -lt $deadline) {
  if ((Test-Tcp $N8nPort) -and (Get-WorkerHealth)) { break }
  Start-Sleep -Seconds 2
}

# --- 4. ataskaita ---
$h = Get-WorkerHealth
$n8nOk = Test-Tcp $N8nPort
Write-Output ''
Write-Output '=== BUSENA ==='
Write-Output ("n8n :$N8nPort      " + $(if ($n8nOk) { 'VEIKIA' } else { 'NEVEIKIA' }))
Write-Output ("worker :$Port   " + $(if ($h) { 'VEIKIA' } else { 'NEVEIKIA' }))
if ($h) {
  Write-Output ('  provider : ' + $h.provider)
  Write-Output ('  modelis  : ' + $h.model)
  Write-Output ('  cline    : ' + $h.clineVersion)
  Write-Output ('  aplankas : ' + $h.workspaceRoot)
} else {
  Write-Output ('  log: ' + (Join-Path $logDir 'worker.err.log'))
}
if (-not $n8nOk) { Write-Output ('  n8n log: ' + (Join-Path $logDir 'n8n.err.log')) }
if ($n8nOk -and $h) { exit 0 } else { exit 1 }
