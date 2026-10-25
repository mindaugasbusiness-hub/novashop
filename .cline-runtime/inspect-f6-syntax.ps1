$script = 'C:\Users\M\Desktop\pakeitimai 111\_vilkas_global_hotkeys.py'
$lines = Get-Content -LiteralPath $script -Encoding UTF8
for ($i = 295; $i -le [Math]::Min(330, $lines.Count); $i++) { Write-Output ('{0}: {1}' -f $i, $lines[$i-1]) }
Write-Output '===== PY_COMPILE ====='
& 'C:\Users\M\AppData\Local\Programs\Python\Python312\python.exe' -m py_compile $script 2>&1 | Out-String -Width 4096
Write-Output ('EXIT=' + $LASTEXITCODE)
Write-Output '===== NAUJAUSIOS KOPIJOS ====='
Get-ChildItem -LiteralPath 'C:\Users\M\CLINE\BACKUPS' -Directory | Sort-Object Name -Descending | Select-Object -First 3 FullName
