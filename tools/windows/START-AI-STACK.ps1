# START-AI-STACK.ps1 - vienu paspaudimu: n8n + Cline worker + patikra.
# NIEKO NETRINA ir neperraso. Jei kas jau veikia - praleidzia.
#
#   powershell -ExecutionPolicy Bypass -File START-AI-STACK.ps1
param(
  [string]$Root = 'C:\Users\M\CLINE\ai-stack',
  [int]$Port = 7070,
  [int]$N8nPort = 5678,
  [int]$WaitSec = 60,
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
  $n8nDir = Split-Path (Split-Path $N8nCli)
  Start-Process -FilePath $N8nNode -ArgumentList ("`"$N8nCli`"", 'start') `
    -WorkingDirectory $n8nDir -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $logDir 'n8n.log') `
    -RedirectStandardError (Join-Path $logDir 'n8n.err.log') | Out-Null
  Write-Output ("n8n :$N8nPort - paleistas")
} else {
  Write-Output 'n8n - NERASTAS (patikrink kelią N8nNode / N8nCli)'
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

# --- 3. laukiam, kol abu atsakys ---
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
if ($n8nOk -and $h) { exit 0 } else { exit 1 }
