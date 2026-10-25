$ErrorActionPreference='Continue'
function Test-Port([int]$Port) {
    try { $client = New-Object Net.Sockets.TcpClient; $client.Connect('127.0.0.1', $Port); $client.Close(); return $true } catch { return $false }
}
Write-Output '===== POWERSHELL PROCESAI ====='
$all = Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" | Select-Object ProcessId,ParentProcessId,CommandLine
foreach($p in $all){
  $cmd = if($p.CommandLine){$p.CommandLine.Substring(0,[Math]::Min(150,$p.CommandLine.Length))}else{'<nera>'}
  Write-Output ('PID='+$p.ProcessId+' PPID='+$p.ParentProcessId+' CMD='+$cmd)
}
$targets = $all | Where-Object { $_.CommandLine -like '*automation-server-loop*' }
Write-Output ('LOOP_PROCESS_COUNT='+($targets|Measure-Object).Count)
foreach($t in $targets){ Write-Output ('STOP_LOOP pid='+$t.ProcessId); Stop-Process -Id $t.ProcessId -Force -ErrorAction SilentlyContinue }
$servers = Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -like '*automation_server.py*' }
foreach($s in $servers){ Write-Output ('STOP_SERVER pid='+$s.ProcessId); Stop-Process -Id $s.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep -Seconds 3
Write-Output ('PORT_LAISVAS='+(-not (Test-Port 8792)))
$loop='C:\Users\M\CLINE\tools\automation-server-loop.ps1'
$stamp=Get-Date -Format 'yyyy-MM-dd_HHmmss'
$bak="C:\Users\M\CLINE\BACKUPS\$stamp\CLINE\tools"
New-Item -ItemType Directory -Path $bak -Force|Out-Null
Copy-Item -LiteralPath $loop -Destination (Join-Path $bak 'automation-server-loop.ps1')
[IO.File]::WriteAllBytes($loop,[Convert]::FromBase64String('__PAYLOAD__'))
$errs=$null
[void][System.Management.Automation.Language.Parser]::ParseFile($loop,[ref]$null,[ref]$errs)
Write-Output ('PARSE_ERRORS='+(($errs|Measure-Object).Count))
Start-Process -FilePath 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe' -ArgumentList @('-NoProfile','-WindowStyle','Hidden','-ExecutionPolicy','Bypass','-File',$loop) -WindowStyle Hidden
$ok=$false
for($i=0;$i -lt 40;$i++){
  Start-Sleep -Milliseconds 500
  try{$h=Invoke-WebRequest 'http://127.0.0.1:8792/health' -UseBasicParsing -TimeoutSec 2;if($h.StatusCode -eq 200){$ok=$true;break}}catch{}
}
Write-Output ('HEALTH_OK='+$ok)
if(-not $ok){Get-Content -LiteralPath 'C:\Users\M\CLINE\AUTOMATION_API_STDOUT.log' -Encoding UTF8 -Tail 15;exit 1}
$token=(Get-Content -LiteralPath 'C:\Users\M\CLINE\tools\automation-secret.txt' -Raw).Trim()
foreach($action in @('ensure','collect','collect','ensure')){
 $r=& curl.exe -sS --max-time 45 -X POST -H "X-Automation-Key: $token" -w "|HTTP=%{http_code}|T=%{time_total}" ('http://127.0.0.1:8792/'+$action) 2>&1 | Out-String
 Write-Output ($action+' => '+($r.Trim()))
}
Write-Output '===== API LOG ====='
Get-Content -LiteralPath 'C:\Users\M\CLINE\AUTOMATION_API_LOG.txt' -Encoding UTF8 -Tail 8