# Paleidzia Cline worker'į Windows fone (be lango) ir patikrina /healthz.
# NIEKO NETRINA. Jei worker jau veikia - tik parodo būseną.
#
#   powershell -ExecutionPolicy Bypass -File start-worker.ps1
param(
  [string]$Root = 'C:\Users\M\CLINE\ai-stack',
  [int]$Port = 7070
)
$ErrorActionPreference = 'Stop'

try {
  $h = Invoke-RestMethod -Uri ("http://127.0.0.1:$Port/healthz") -TimeoutSec 5
  Write-Output 'Worker jau veikia - neperleidžiu.'
  Write-Output ($h | ConvertTo-Json -Compress)
  exit 0
} catch { }

$tokenFile = Join-Path $Root 'worker-token.txt'
if (Test-Path $tokenFile) {
  $token = (Get-Content $tokenFile -Raw).Trim()
} else {
  $chars = 'abcdefghijklmnopqrstuvwxyz0123456789'.ToCharArray()
  $token = -join (1..40 | ForEach-Object { $chars | Get-Random })
  Set-Content -Path $tokenFile -Value $token -Encoding ASCII
  Write-Output "Sukurtas tokenas: $tokenFile"
}

$work = Join-Path $Root 'work'
if (-not (Test-Path $work)) { New-Item -ItemType Directory -Path $work -Force | Out-Null }

$env:PORT = "$Port"
$env:WORKER_TOKEN = $token
$env:WORKSPACE_ROOT = $work

$log = Join-Path $Root 'worker.log'
$errLog = Join-Path $Root 'worker.err.log'
$p = Start-Process -FilePath 'node' -ArgumentList 'server.js' `
  -WorkingDirectory $Root -PassThru -WindowStyle Hidden `
  -RedirectStandardOutput $log -RedirectStandardError $errLog

Start-Sleep -Seconds 4
Write-Output ("Worker PID: " + $p.Id + "  (log: " + $log + ")")

try {
  $h = Invoke-RestMethod -Uri ("http://127.0.0.1:$Port/healthz") -TimeoutSec 10
  Write-Output ($h | ConvertTo-Json -Compress)
} catch {
  Write-Output ("healthz klaida: " + $_.Exception.Message)
  if (Test-Path $errLog) { Write-Output '--- stderr ---'; Get-Content $errLog -Raw }
}
