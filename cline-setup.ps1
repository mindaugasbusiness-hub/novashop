# ============================================================
#  Cline - prieigos prie kompiuterio nustatymas (Windows 10/11)
#
#  Paleidimas (PowerShell KAIP ADMINISTRATORIUS):
#      irm <URL> | iex
#
#  Ka daro:
#   1) ijungia Windows OpenSSH serveri (portas 22)
#   2) ideda Cline sesijos VIESA rakta (privatus raktas lieka pas Cline)
#   3) parsiuncia cloudflared
#   4) atidaro tuneli ir parodo prisijungimo eilute "tcp://..."
#
#  Atsaukti prieiga: istrinti eilute su "cline-sandbox-agent" is
#     %USERPROFILE%\.ssh\authorized_keys
#     C:\ProgramData\ssh\administrators_authorized_keys
#  ir paleisti:  Restart-Service sshd
# ============================================================
$ErrorActionPreference = 'Stop'

function Info($m) { Write-Host $m -ForegroundColor Cyan }
function Ok($m)   { Write-Host $m -ForegroundColor Green }
function Bad($m)  { Write-Host $m -ForegroundColor Red }
function Warn($m) { Write-Host $m -ForegroundColor Yellow }

Info '=== 0/4 Tikrinu administratoriaus teises ==='
$isAdmin = $false
try {
    $isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
} catch {
    $isAdmin = $false
}
if (-not $isAdmin) {
    Bad 'Si komanda turi buti paleista KAIP ADMINISTRATORIUS.'
    Warn 'Desiniu peles klavisu ant Start -> "Terminal (Admin)" -> Taip, ir pakartok.'
    return
}
Ok 'Teises OK'

Info '=== 1/4 Ijungiu OpenSSH serveri ==='
try {
    $cap = Get-WindowsCapability -Online -Name 'OpenSSH.Server*' | Select-Object -First 1
    if ($cap.State -ne 'Installed') { Add-WindowsCapability -Online -Name $cap.Name | Out-Null }
    Ok 'OpenSSH serveris paruostas'
} catch {
    Warn "Standartinis diegimas nepavyko: $($_.Exception.Message)"
    Warn 'Bandau atsargini varianta (portable OpenSSH)...'
    try {
        $zip = Join-Path $env:TEMP 'openssh-portable.zip'
        $dst = Join-Path $env:ProgramFiles 'OpenSSH-Portable'
        $rel = Invoke-RestMethod -Uri 'https://api.github.com/repos/PowerShell/Win32-OpenSSH/releases/latest'
        $asset = $rel.assets | Where-Object { $_.name -eq 'OpenSSH-Win64.zip' } | Select-Object -First 1
        if (-not $asset) { throw 'Neradau OpenSSH-Win64.zip' }
        Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $zip -UseBasicParsing
        if (Test-Path $dst) { Remove-Item $dst -Recurse -Force }
        Expand-Archive -Path $zip -DestinationPath $dst -Force
        $inner = Get-ChildItem $dst -Directory | Where-Object { $_.Name -like 'OpenSSH-Win64*' } | Select-Object -First 1
        $root = if ($inner) { $inner.FullName } else { $dst }
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root 'Install-sshd.ps1')
        Ok 'Portable OpenSSH idiegtas'
    } catch {
        Bad "Nepavyko idiegti OpenSSH: $($_.Exception.Message)"
        Warn 'Nukopijuok si teksta ir atsiusk man i Cline pokalbi - duosiu kita kelia.'
        return
    }
}
try {
    Set-Service -Name sshd -StartupType Automatic
    if ((Get-Service sshd).Status -ne 'Running') { Start-Service sshd }
    Ok 'sshd paleistas'
} catch {
    Warn "sshd paleisti nepavyko: $($_.Exception.Message)"
}

Info '=== 2/4 Idedu Cline rakta ==='
$key = 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIEPXP9UBfp179tBidPp7ttGNQIiESKvQWRb6ysoas3kl cline-sandbox-agent'

# a) vartotojo failas
$sshDir = Join-Path $env:USERPROFILE '.ssh'
New-Item -ItemType Directory -Force -Path $sshDir | Out-Null
$userKeys = Join-Path $sshDir 'authorized_keys'
$hasUserKey = (Test-Path $userKeys) -and (Select-String -Path $userKeys -SimpleMatch 'cline-sandbox-agent' -Quiet)
if (-not $hasUserKey) { Add-Content -Path $userKeys -Value $key -Encoding ascii }
icacls $userKeys /inheritance:r /grant "$($env:USERNAME):F" /grant '*S-1-5-18:F' | Out-Null

# b) administratoriu failas (kai paskyra yra Administrators grupeje, sshd naudoja butent ji)
$adminDir = Join-Path $env:ProgramData 'ssh'
New-Item -ItemType Directory -Force -Path $adminDir | Out-Null
$adminKeys = Join-Path $adminDir 'administrators_authorized_keys'
if (-not (Test-Path $adminKeys)) { New-Item -ItemType File -Path $adminKeys -Force | Out-Null }
if (-not (Select-String -Path $adminKeys -SimpleMatch 'cline-sandbox-agent' -Quiet)) {
    Add-Content -Path $adminKeys -Value $key -Encoding ascii
}
icacls $adminKeys /inheritance:r /grant '*S-1-5-32-544:F' /grant '*S-1-5-18:F' | Out-Null
Ok 'Raktas idetas'

Info '=== 3/4 Siunciu cloudflared (tunelis) ==='
$cf = Join-Path $env:TEMP 'cloudflared.exe'
try {
    if (-not (Test-Path $cf)) {
        Invoke-WebRequest -Uri 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe' -OutFile $cf -UseBasicParsing
    }
    Ok 'cloudflared parsiustas'
} catch {
    Bad "Nepavyko parsiusti cloudflared: $($_.Exception.Message)"
    Warn 'Patikrink interneto rysi arba antivirusa ir paleisk komanda dar karta.'
    return
}

Info '=== 4/4 Tikrinu SSH ir atidarau tuneli ==='
try {
    $tcp = New-Object System.Net.Sockets.TcpClient
    $tcp.Connect('127.0.0.1', 22)
    $tcp.Close()
    Ok 'SSH serveris atsako (portas 22)'
} catch {
    Warn 'SSH neatsake - bandau restartuoti sshd...'
    try { Restart-Service sshd; Start-Sleep -Seconds 3 } catch { Bad "Nepavyko: $($_.Exception.Message)" }
}

Write-Host ''
Ok ("VARTOTOJAS (nukopijuok ir atsiusk man): {0}" -f $env:USERNAME)
Warn 'Zemiau atsiras eilute su "tcp://" - nukopijuok ja ir atsiusk i Cline pokalbi.'
Warn 'NEUZVERK sio lango, kol dirbame. Jei uzversi - prieiga dings (tada vel paleisk sia komanda).'
Write-Host ''
& $cf tunnel --url tcp://localhost:22
