Write-Output '===== F6 NUORODOS STARTUOLYJE IR IRANKIUOSE ====='
Get-ChildItem -LiteralPath 'C:\Users\M\CLINE\tools' -File -Include *.ps1,*.cmd,*.py | Select-String -Pattern '8766|F6 panelis|hotkeys' | Select-Object Path, LineNumber, Line | Format-List
Write-Output '===== 8766 PORTAS ====='
Get-NetTCPConnection -LocalPort 8766 -ErrorAction SilentlyContinue | Format-Table -AutoSize
Write-Output '===== SUSIJE PROCESAI ====='
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match '8766|f6|hotkey' } | Select-Object ProcessId, Name, CommandLine | Format-List
Write-Output '===== STARTUOLIO F6 DALIS ====='
Select-String -LiteralPath 'C:\Users\M\CLINE\tools\sesijos-pradzia.ps1' -Pattern 'F6|8766|hotkeys' -Context 5,8 | Format-List
