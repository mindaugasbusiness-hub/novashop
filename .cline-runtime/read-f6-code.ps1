Write-Output '===== F6 KODAS ====='
Get-Content -LiteralPath 'C:\Users\M\Desktop\pakeitimai 111\_vilkas_global_hotkeys.py' -Raw -Encoding UTF8
Write-Output "`n===== PYTHON PROCESAI ====="
Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^pythonw?\.exe$' } | Select-Object ProcessId, Name, CommandLine | Format-List
Write-Output "`n===== AUTOHOTKEY PROCESAI ====="
Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'AutoHotkey|ahk' } | Select-Object ProcessId, Name, CommandLine | Format-List
