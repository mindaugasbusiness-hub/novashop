# install-autostart.ps1 - įrašo START-AI-STACK.ps1 į Windows Startup (prisijungus).
# NIEKO NETRINA. Jei nuoroda jau yra - praleidžia ir parodo, kur ji.
#
#   powershell -ExecutionPolicy Bypass -File install-autostart.ps1
#   powershell -ExecutionPolicy Bypass -File install-autostart.ps1 -Remove   # pasalinti
param(
  [string]$Root = 'C:\Users\M\CLINE\ai-stack',
  [switch]$Remove
)
$ErrorActionPreference = 'Stop'

$script = Join-Path $Root 'START-AI-STACK.ps1'
$startup = [Environment]::GetFolderPath('Startup')
$lnk = Join-Path $startup 'CLINE-AI-STACK.lnk'

if ($Remove) {
  if (Test-Path $lnk) { Remove-Item $lnk -Force; Write-Output ('Pasalinta: ' + $lnk) }
  else { Write-Output 'Nuorodos nebuvo' }
  exit 0
}

if (-not (Test-Path $script)) { throw ('Nera ' + $script) }

if (Test-Path $lnk) {
  Write-Output ('JAU YRA - neperrasau: ' + $lnk)
} else {
  $ws = New-Object -ComObject WScript.Shell
  $s = $ws.CreateShortcut($lnk)
  $s.TargetPath = 'powershell.exe'
  $s.Arguments = ('-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "' + $script + '"')
  $s.WorkingDirectory = $Root
  $s.WindowStyle = 7
  $s.Description = 'CLINE AI STACK: n8n + Cline worker'
  $s.Save()
  Write-Output ('Sukurta: ' + $lnk)
}

Write-Output ''
Write-Output 'Startup aplanko turinys:'
Get-ChildItem $startup -Filter *.lnk | ForEach-Object { Write-Output ('  - ' + $_.Name) }
Write-Output ''
Write-Output 'Patikrinimas dabar (paleidžia kaip po perkrovimo):'
& $script
