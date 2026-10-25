$token=(Get-Content -LiteralPath 'C:\Users\M\CLINE\tools\automation-secret.txt' -Raw).Trim()
Write-Output '===== HEALTH ====='
& curl.exe -sS --max-time 6 -w "`nHTTP=%{http_code}`n" 'http://127.0.0.1:8792/health'
Write-Output '===== PORT/PROCESS ====='
$conn=Get-NetTCPConnection -LocalPort 8792 -State Listen -ErrorAction SilentlyContinue|Select-Object -First 1
if($conn){Write-Output ('PORT_OWNER='+$conn.OwningProcess)}else{Write-Output 'PORT_LAISVAS'}
Get-CimInstance Win32_Process|Where-Object {$_.CommandLine -match 'automation_server.py'}|Select-Object ProcessId,ParentProcessId,Name,CommandLine|Format-List
Write-Output '===== ENSURE ====='
& curl.exe -sS --max-time 30 -X POST -H "X-Automation-Key: $token" -w "`nHTTP=%{http_code}`n" 'http://127.0.0.1:8792/ensure'
Write-Output '===== COLLECT ====='
& curl.exe -sS --max-time 30 -X POST -H "X-Automation-Key: $token" -w "`nHTTP=%{http_code}`n" 'http://127.0.0.1:8792/collect'
Write-Output '===== SERVER LOG ====='
if(Test-Path 'C:\Users\M\CLINE\AUTOMATION_API_LOG.txt'){Get-Content -LiteralPath 'C:\Users\M\CLINE\AUTOMATION_API_LOG.txt' -Encoding UTF8 -Tail 12}
