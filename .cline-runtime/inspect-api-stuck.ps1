Write-Output '===== SERVER ERR ====='
if(Test-Path 'C:\Users\M\CLINE\AUTOMATION_API_SERVER.err.log'){Get-Item 'C:\Users\M\CLINE\AUTOMATION_API_SERVER.err.log'|Select-Object Length,LastWriteTime|Format-List;Get-Content -LiteralPath 'C:\Users\M\CLINE\AUTOMATION_API_SERVER.err.log' -Encoding UTF8 -Tail 40}
Write-Output '===== SERVER OUT ====='
if(Test-Path 'C:\Users\M\CLINE\AUTOMATION_API_SERVER.out.log'){Get-Item 'C:\Users\M\CLINE\AUTOMATION_API_SERVER.out.log'|Select-Object Length,LastWriteTime|Format-List;Get-Content -LiteralPath 'C:\Users\M\CLINE\AUTOMATION_API_SERVER.out.log' -Encoding UTF8 -Tail 20}
Write-Output '===== BANDYMAS DABAR ====='
$token=(Get-Content -LiteralPath 'C:\Users\M\CLINE\tools\automation-secret.txt' -Raw).Trim()
& curl.exe -sS --max-time 25 -X POST -H "X-Automation-Key: $token" -w "`nHTTP=%{http_code} TIME=%{time_total}`n" 'http://127.0.0.1:8792/collect'
