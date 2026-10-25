Write-Output '===== DESKTOP KELIAS ====='
[Environment]::GetFolderPath('Desktop')
Write-Output '===== REGISTRO DESKTOP ====='
try { (Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders' -Name Desktop).Desktop } catch { 'NENUSKAITYTA' }
Write-Output '===== VISI DESKTOP FAILAI ====='
Get-ChildItem -LiteralPath 'C:\Users\M\Desktop' -Force | Select-Object Mode,Name,Length,LastWriteTime | Format-Table -AutoSize
Write-Output '===== PAIESKA PROFILYJE ====='
Get-ChildItem -LiteralPath 'C:\Users\M' -Recurse -File -Filter 'CLINE_ATASKAITA*' -ErrorAction SilentlyContinue -Force | Select-Object FullName,Length,LastWriteTime | Format-Table -AutoSize
Write-Output '===== ONEDRIVE ====='
foreach($p in @('C:\Users\M\OneDrive','C:\Users\M\OneDrive\Desktop','C:\Users\M\OneDrive - Personal')){Write-Output ($p+'|'+(Test-Path -LiteralPath $p))}
Write-Output '===== AR YRA ONEDRIVE PROCESAS ====='
Get-Process -Name OneDrive -ErrorAction SilentlyContinue | Select-Object Id,ProcessName | Format-Table -AutoSize
Write-Output '===== AR YRA ATASKAITA FAILU KUR NORS ====='
Get-ChildItem -LiteralPath 'C:\Users\M' -Recurse -File -ErrorAction SilentlyContinue -Force | Where-Object { $_.Name -match 'VISKAS_AUTOMATIKA|ATASKAITA_2026-10-25' } | Select-Object FullName,Length,LastWriteTime | Format-Table -AutoSize