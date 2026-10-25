$ErrorActionPreference='Continue'
$py='C:\Users\M\AppData\Local\Programs\Python\Python312\python.exe'
$server='C:\Users\M\CLINE\tools\automation_server.py'
& $py -m py_compile $server
Write-Output ('PY_COMPILE='+$LASTEXITCODE)
Write-Output '===== PORTAS ====='
$conn=Get-NetTCPConnection -LocalPort 8792 -State Listen -ErrorAction SilentlyContinue|Select-Object -First 1
if($conn){Write-Output ('PORT_OWNER='+$conn.OwningProcess)}else{Write-Output 'PORT_LAISVAS'}
Write-Output '===== PROCESAI ====='
Get-CimInstance Win32_Process|Where-Object {$_.CommandLine -match 'automation_server.py|automation-server-loop.ps1'}|Select-Object ProcessId,ParentProcessId,Name,CommandLine|Format-List
Write-Output '===== LOG ====='
if(Test-Path 'C:\Users\M\CLINE\AUTOMATION_API_STDOUT.log'){Get-Content 'C:\Users\M\CLINE\AUTOMATION_API_STDOUT.log' -Tail 30}
if(-not $conn){
  $out='C:\Users\M\CLINE\AUTOMATION_API_SERVER.out.log';$err='C:\Users\M\CLINE\AUTOMATION_API_SERVER.err.log'
  if((Test-Path $out) -or (Test-Path $err)){throw 'Log failai jau yra; neperrasau'}
  $p=Start-Process -FilePath $py -ArgumentList @('-X','utf8',$server) -WindowStyle Hidden -RedirectStandardOutput $out -RedirectStandardError $err -PassThru
  Start-Sleep -Seconds 3
  Write-Output ('SERVER_PID='+$p.Id+' EXITED='+$p.HasExited)
  if($p.HasExited){if(Test-Path $err){Get-Content $err -Tail 30};exit 1}
}
try{$h=Invoke-WebRequest 'http://127.0.0.1:8792/health' -UseBasicParsing -TimeoutSec 5;Write-Output ('HEALTH='+$h.StatusCode+' '+$h.Content)}catch{Write-Output ('HEALTH_KLAIDA='+$_.Exception.Message);exit 1}
$token=(Get-Content -LiteralPath 'C:\Users\M\CLINE\tools\automation-secret.txt' -Raw).Trim()
foreach($action in @('ensure','collect')){
 try{$r=Invoke-RestMethod -Uri ('http://127.0.0.1:8792/'+$action) -Method Post -Headers @{'X-Automation-Key'=$token} -TimeoutSec 130;Write-Output ($action+'_OK='+$r.ok+' EXIT='+$r.results[0].exit_code+' OUT='+$r.results[0].output.Substring(0,[Math]::Min(220,$r.results[0].output.Length)))}catch{Write-Output ($action+'_KLAIDA='+$_.Exception.Message)}
}
