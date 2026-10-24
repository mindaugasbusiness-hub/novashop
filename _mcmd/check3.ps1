$ErrorActionPreference = 'Continue'
'=== STARTUP APLANKAS ==='
Get-ChildItem "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup" -Force -ErrorAction SilentlyContinue | Select-Object Name,Length,LastWriteTime | Format-Table -AutoSize | Out-String
$p1 = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\CLINE-N8N.lnk"
'CLINE-N8N.lnk yra: ' + (Test-Path $p1)
if (Test-Path $p1) {
  $sh = New-Object -ComObject WScript.Shell
  $lnk = $sh.CreateShortcut($p1)
  'Target : ' + $lnk.TargetPath
  'Args   : ' + $lnk.Arguments
  'WorkDir: ' + $lnk.WorkingDirectory
}
'=== RUN / RUNONCE ==='
Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run' -ErrorAction SilentlyContinue | Format-List | Out-String
'=== start-n8n.cmd ==='
Get-Content 'C:\Users\M\CLINE\tools\start-n8n.cmd' -ErrorAction SilentlyContinue
'=== start-n8n-direct.ps1 ==='
Get-Content 'C:\Users\M\CLINE\tools\start-n8n-direct.ps1' -ErrorAction SilentlyContinue
'=== PRANESIMU_LOG.txt (paskutines 15 eil.) ==='
Get-Content 'C:\Users\M\CLINE\PRANESIMU_LOG.txt' -Tail 15 -ErrorAction SilentlyContinue
