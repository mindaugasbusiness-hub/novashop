# ============================================================
#  Cline - prieigos prie kompiuterio nustatymas (Windows)
#  Paleidimas: PowerShell kaip ADMINISTRATORIUS, tada:
#     irm <URL> | iex
# ============================================================
$ErrorActionPreference = 'Stop'

function Info($m) { Write-Host $m -ForegroundColor Cyan }
function Ok($m)   { Write-Host $m -ForegroundColor Green }
function Bad($m)  { Write-Host $m -ForegroundColor Red }
function Warn($m) { Write-Host $m -ForegroundColor Yellow }

Info '=== 0/4 Tikrinu administratoriaus teises ==='
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Bad 'Si komanda turi buti paleista KAIP ADMINISTRATORIUS.'
    Warn 'Dešiniu peles klavišu ant Start -> "Terminal (Admin)" -> Taip, ir pakartok.'
    return
}
Ok 'Teises OK'

Info '=== 1/4 Ijungiu OpenSSH serveri ==='
$cap = Get-WindowsCapability -Online -Name 'OpenSSH.Server*' | Select-Object -First 1
if ($cap.State -ne 'Installed') {
    Add-WindowsCapability -Online -Name $cap.Name | Out-Null
    Ok 'OpenSSH serveris idiegiamas...'
} else {
    Ok 'OpenSSH serveris jau buvo idiegtas'
}
Set-Service -Name sshd -StartupType Automatic
if ((Get-Service sshd).Status -ne 'Running') { Start-Service sshd }
Ok 'sshd paleistas'

Info '=== 2/4 Idedu Cline rakta ==='
$key = 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIEPXP9UBfp179tBidPp7ttGNQIiESKvQWRb6ysoas3kl cline-sandbox-agent'

# a) vartotojo failas
$sshDir = Join-Path $env:USERPROFILE '.ssh'
New-Item -ItemType Directory -Force -Path $sshDir | Out-Null
$userKeys = Join-Path $sshDir 'authorized_keys'
$hasUserKey = (Test-Path $userKeys) -and (Select-String -Path $userKeys -SimpleMatch 'cline-sandbox-agent' -Quiet)
if (-not $hasUserKey) { Add-Content -Path $userKeys -Value $key -Encoding ascii }
icacls $userKeys /inheritance:r /grant "$($env:USERNAME):F" /grant '*S-1-5-18:F' | Out-Null

# b) administratoriu failas (Windows reikalauja, kai paskyra yra Administrators grupeje)
$adminKeys = Join-Path $env:ProgramData 'ssh\administrators_authorized_keys'
if (-not (Test-Path $adminKeys)) { New-Item -ItemType File -Path $adminKeys -Force | Out-Null }
if (-not (Select-String -Path $adminKeys -SimpleMatch 'cline-sandbox-agent' -Quiet)) {
    Add-Content -Path $adminKeys -Value $key -Encoding ascii
}
icacls $adminKeys /inheritance:r /grant '*S-1-5-32-544:F' /grant '*S-1-5-18:F' | Out-Null
Ok 'Raktas idetas'

Info '=== 3/4 Siunciu cloudflared (tunelis) ==='
$cf = Join-Path $env:TEMP 'cloudflared.exe'
if (-not (Test-Path $cf)) {
    Invoke-WebRequest -Uri 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe' -OutFile $cf -UseBasicParsing
}
Ok 'cloudflared parsiustas'

Info '=== 4/4 Tikrinu SSH ir atidarau tuneli ==='
$sshOk = $false
try {
    $tcp = New-Object System.Net.Sockets.TcpClient
    $tcp.Connect('127.0.0.1', 22)
    $tcp.Close()
    $sshOk = $true
    Ok 'SSH serveris atsako (portas 22)'
} catch {
    Warn 'SSH neatsake - bandau restartuoti sshd...'
    try { Restart-Service sshd; Start-Sleep -Seconds 3 } catch { Bad "Nepavyko paleisti sshd: $($_.Exception.Message)" }
}

Write-Host ''
Ok ("VARTOTOJAS (nukopijuok ir atsiusk man): {0}" -f $env:USERNAME)
Warn 'Zemiau atsiras eilute, prasidedanti "tcp://" - nukopijuok ja ir atsiusk i Cline pokalbi.'
Warn 'NEUZVERK sio lango, kol dirbame. Jei uzversi - prieiga dings (tada vel paleisk sia komanda).'
Write-Host ''
& $cf tunnel --url tcp://localhost:22
