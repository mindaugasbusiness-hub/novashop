Write-Output '===== APLANKO 2026010.24d TURINYS ====='
Get-ChildItem -LiteralPath 'C:\Users\M\Desktop\2026010.24d' -Force | Select-Object Mode,Name,Length,LastWriteTime | Format-Table -AutoSize
Write-Output '===== GRAFIKAI (visi CLINE ir tvarkymo) ====='
Get-ScheduledTask | Where-Object { $_.TaskName -match 'CLINE|tvark|bordak|desktop' } | ForEach-Object { $i=$_|Get-ScheduledTaskInfo; $a=(($_.Actions)|ForEach-Object{$_.Execute}) -join ';'; Write-Output ($_.TaskName+'|'+$_.State+'|last='+$i.LastRunTime+'|exe='+$a) }
Write-Output '===== BORDAKO APLANKAS ====='
Get-ChildItem -LiteralPath 'C:\Users\M\Desktop\bordako sutvarkymas' -Force -ErrorAction SilentlyContinue | Select-Object Mode,Name,Length,LastWriteTime | Format-Table -AutoSize
Write-Output '===== STARTUOLIS ====='
Get-ChildItem -LiteralPath ([Environment]::GetFolderPath('Startup')) -Force | Select-Object Name,LastWriteTime | Format-Table -AutoSize
Write-Output '===== AR VEIKIA KOKS TVARKYTOJAS ====='
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'tvark|bordak' } | Select-Object ProcessId,Name,CommandLine | Format-List
Write-Output '===== VISKAS APLANKO ATASKAITOS ====='
Get-ChildItem -LiteralPath 'C:\Users\M\CLINE\VISKAS' -File -Filter '*ATASKAITA*' | Select-Object Name,Length,LastWriteTime | Format-Table -AutoSize