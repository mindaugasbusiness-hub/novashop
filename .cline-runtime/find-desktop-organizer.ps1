Write-Output '===== APLANKO 2026010.24d TURINYS ====='
Get-ChildItem -LiteralPath 'C:\Users\M\Desktop\2026010.24d' -Force -Recurse -File | Select-Object FullName,Length,LastWriteTime | Format-Table -AutoSize
Write-Output '===== KAS SUKURE: GRAFIKAI SU TVARKYMU ====='
Get-ScheduledTask | Where-Object { $_.TaskName -match 'tvark|bordak|sutvark|desktop|clean' } | Select-Object TaskName,State | Format-Table -AutoSize
Write-Output '===== GRAFIKU VEIKSMAI ====='
Get-ScheduledTask | Where-Object { $_.TaskName -match 'tvark|bordak|sutvark|desktop|clean' } | ForEach-Object { $a=$_.Actions | ForEach-Object { $_.Execute + ' ' + $_.Arguments }; Write-Output ($_.TaskName+' => '+($a -join ' | ')) }
Write-Output '===== BORDAKO SUTVARKYMAS APLANKAS ====='
Get-ChildItem -LiteralPath 'C:\Users\M\Desktop\bordako sutvarkymas' -Force -Recurse -File -ErrorAction SilentlyContinue | Select-Object FullName,Length,LastWriteTime | Format-Table -AutoSize
Write-Output '===== PAIESKA SCRIPTU SU 2026010 ====='
Get-ChildItem -LiteralPath 'C:\Users\M\CLINE' -Recurse -File -Include *.ps1,*.py,*.cmd,*.vbs -ErrorAction SilentlyContinue | Select-String -Pattern '2026010|Desktop.*move|Move-Item.*Desktop' -List -ErrorAction SilentlyContinue | Select-Object -First 15 Path,LineNumber,Line | Format-List
Write-Output '===== STARTUOLIO IRASU SARASAS ====='
Get-ChildItem -LiteralPath ([Environment]::GetFolderPath('Startup')) -Force | Select-Object Name,LastWriteTime | Format-Table -AutoSize