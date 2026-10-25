& 'C:\Users\M\AppData\Local\Programs\Python\Python312\python.exe' -X utf8 'C:\Users\M\CLINE\tools\surinkti-viska.py' 2>&1 | Out-String -Width 2000
Write-Output ('COLLECT2_EXIT=' + $LASTEXITCODE)
& 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe' -NoProfile -NonInteractive -ExecutionPolicy Bypass -File 'C:\Users\M\CLINE\tools\zveris-ensure.ps1' 2>&1 | Out-String -Width 2000
Write-Output ('ENSURE_HEALTHY_EXIT=' + $LASTEXITCODE)
& 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe' -NoProfile -NonInteractive -ExecutionPolicy Bypass -File 'C:\Users\M\CLINE\tools\zveris-ensure.ps1' -TestRefresh 2>&1 | Out-String -Width 2000
Write-Output ('ENSURE_F5_EXIT=' + $LASTEXITCODE)
Get-Content -LiteralPath 'C:\Users\M\CLINE\ZVERIS_AUTO_LOG.txt' -Encoding UTF8 -Tail 10 -ErrorAction SilentlyContinue
