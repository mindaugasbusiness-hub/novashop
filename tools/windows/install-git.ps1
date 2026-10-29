# install-git.ps1 - parsiuncia nesiojama MinGit i ai-stack\tools\git.
# NEREIKIA adminu, nieko neperraso sistemoje, neregistruoja PATH globaliai.
# PATH pridedamas tik worker'io procesui (start-worker.ps1).
param(
  [string]$Root = 'C:\Users\M\CLINE\ai-stack'
)
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$tools = Join-Path $Root 'tools'
if (-not (Test-Path $tools)) { New-Item -ItemType Directory -Path $tools -Force | Out-Null }
$gitDir = Join-Path $tools 'git'
$gitExe = Join-Path $gitDir 'cmd\git.exe'

if (Test-Path $gitExe) {
  Write-Output 'git jau yra - neperrasau'
  & $gitExe --version
  exit 0
}

Write-Output 'Ieskom naujausio MinGit...'
$rel = Invoke-RestMethod 'https://api.github.com/repos/git-for-windows/git/releases/latest' -TimeoutSec 60
$a = $rel.assets | Where-Object { $_.name -like 'MinGit-*-64-bit.zip' } | Select-Object -First 1
if (-not $a) { throw 'MinGit asset nerastas releases sarase' }
Write-Output ('Atsiunciu: ' + $a.name + ' (' + [math]::Round($a.size / 1MB, 1) + ' MB)')

$zip = Join-Path $tools 'mingit.zip'
Invoke-WebRequest -UseBasicParsing -Uri $a.browser_download_url -OutFile $zip -TimeoutSec 900
Write-Output ('Atsiusta: ' + [math]::Round((Get-Item $zip).Length / 1MB, 1) + ' MB')

Expand-Archive -Path $zip -DestinationPath $gitDir -Force
Write-Output 'Iskelti failai'
Remove-Item $zip -Force

$ver = & $gitExe --version
Write-Output ('git: ' + $ver)
Write-Output ('Kelias: ' + $gitExe)
Write-Output 'BAIGTA'
