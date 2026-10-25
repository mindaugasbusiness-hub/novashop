Write-Output '===== API LOG ====='
Get-Content -LiteralPath 'C:\Users\M\CLINE\AUTOMATION_API_LOG.txt' -Encoding UTF8 -Tail 10
Write-Output '===== API PROCESAS ====='
Get-CimInstance Win32_Process|Where-Object {$_.CommandLine -match 'automation_server.py|automation-server-loop'}|Select-Object ProcessId,ParentProcessId,Name|Format-Table -AutoSize
Write-Output '===== PORT 8792 ====='
Get-NetTCPConnection -LocalPort 8792 -State Listen -ErrorAction SilentlyContinue|Select-Object LocalPort,OwningProcess|Format-Table -AutoSize
