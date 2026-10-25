$ErrorActionPreference='Continue'
$root='C:\Users\M\Desktop\Kumstis';$runtime=Join-Path $root 'runtime';$n8nData=Join-Path $runtime 'n8n-data'
$pidsFile=Join-Path $runtime 'pids.json';$node=Join-Path $runtime 'node24\node.exe';$n8nBin=Join-Path $runtime 'n8n\node_modules\n8n\bin\n8n';$wf='C:\Users\M\CLINE\tools\cline-auto-workflow-v2.json';$logs=Join-Path $runtime 'logs'
$stamp=Get-Date -Format 'yyyyMMdd_HHmmss';Set-Location $root
$conn=Get-NetTCPConnection -LocalPort 5678 -State Listen -ErrorAction SilentlyContinue|Select-Object -First 1
if($conn){
 $old=[int]$conn.OwningProcess;$proc=Get-CimInstance Win32_Process -Filter "ProcessId=$old"
 if($proc -and $proc.CommandLine -match 'n8n'){
  $children=Get-CimInstance Win32_Process|Where-Object {$_.ParentProcessId -eq $old}
  Copy-Item -LiteralPath $pidsFile -Destination (Join-Path $runtime "pids.json.bak-final-$stamp") -Force -ErrorAction SilentlyContinue
  Write-Output ('STOP_N8N_PID='+$old)
  Stop-Process -Id $old -Force -ErrorAction SilentlyContinue
  for($i=0;$i -lt 20;$i++){Start-Sleep -Milliseconds 500;if(-not (Get-NetTCPConnection -LocalPort 5678 -State Listen -ErrorAction SilentlyContinue)){break}}
  foreach($child in $children){Stop-Process -Id $child.ProcessId -Force -ErrorAction SilentlyContinue}
 }else{throw "5678 savininkas nera n8n: $old"}
}else{Write-Output 'N8N_NEVEIKE'}
$ownerAfter=Get-NetTCPConnection -LocalPort 5678 -State Listen -ErrorAction SilentlyContinue|Select-Object -First 1
if($ownerAfter){throw ('Portas 5678 vis dar uzimtas PID='+$ownerAfter.OwningProcess)}
foreach($line in Get-Content -LiteralPath (Join-Path $root '.env') -Encoding UTF8){
 if($line -match '^\s*([A-Z0-9_]+)\s*=\s*(.*)$'){[Environment]::SetEnvironmentVariable($Matches[1],$Matches[2].Trim().Trim('"').Trim("'"),'Process')}
}
$env:N8N_USER_FOLDER=$n8nData;$env:N8N_BLOCK_ENV_ACCESS_IN_NODE='false';$env:N8N_RUNNERS_MODE='internal'
$env:N8N_LISTEN_ADDRESS='127.0.0.1';$env:N8N_HOST='localhost';$env:N8N_PORT='5678';$env:N8N_PROTOCOL='http';$env:WEBHOOK_URL='http://localhost:5678/'
$env:GENERIC_TIMEZONE='Europe/Vilnius';$env:EXECUTIONS_TIMEOUT='3600';$env:EXECUTIONS_TIMEOUT_MAX='7200';$env:N8N_DIAGNOSTICS_ENABLED='false'
Write-Output '===== IMPORT N8N NEVEIKIANT ====='
& $node $n8nBin import:workflow --input=$wf 2>&1 | Out-String -Width 3000
Write-Output ('IMPORT_EXIT='+$LASTEXITCODE)
Write-Output '===== PUBLISH N8N NEVEIKIANT ====='
& $node $n8nBin publish:workflow --id=clineAuto0000001 2>&1 | Out-String -Width 3000
Write-Output ('PUBLISH_EXIT='+$LASTEXITCODE)
$out=Join-Path $logs "n8n-v2-$stamp.out.log";$err=Join-Path $logs "n8n-v2-$stamp.err.log"
$new=Start-Process -FilePath $node -ArgumentList @("`"$n8nBin`"",'start') -WorkingDirectory $root -WindowStyle Hidden -RedirectStandardOutput $out -RedirectStandardError $err -PassThru
$ok=$false
for($i=0;$i -lt 60;$i++){
 Start-Sleep -Seconds 2
 if($new.HasExited){break}
 $owner=Get-NetTCPConnection -LocalPort 5678 -State Listen -ErrorAction SilentlyContinue|Select-Object -First 1
 if($owner -and [int]$owner.OwningProcess -eq $new.Id){$ok=$true;break}
}
if(-not $ok){Write-Output ('START_FAILED PID='+$new.Id+' EXITED='+$new.HasExited);if(Test-Path $out){Get-Content $out -Tail 30};exit 1}
$pids=Get-Content -LiteralPath $pidsFile -Raw|ConvertFrom-Json
$pids|Add-Member -NotePropertyName n8n -NotePropertyValue $new.Id -Force
$pids|ConvertTo-Json|Set-Content -LiteralPath $pidsFile -Encoding Ascii
Write-Output ('N8N_STARTED_PID='+$new.Id+' PORT_OWNER_OK=True')
