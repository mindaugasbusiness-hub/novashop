$ErrorActionPreference='Stop'
$root='C:\Users\M\Desktop\Kumstis';$runtime=Join-Path $root 'runtime';$n8nData=Join-Path $runtime 'n8n-data'
$pidsFile=Join-Path $runtime 'pids.json';$node=Join-Path $runtime 'node24\node.exe';$n8nBin=Join-Path $runtime 'n8n\node_modules\n8n\bin\n8n';$logs=Join-Path $runtime 'logs'
$stamp=Get-Date -Format 'yyyyMMdd_HHmmss';Set-Location $root
$conn=Get-NetTCPConnection -LocalPort 5678 -State Listen -ErrorAction SilentlyContinue|Select-Object -First 1
if(-not $conn){throw 'Neradau 5678 savininko'}
$old=[int]$conn.OwningProcess
$proc=Get-CimInstance Win32_Process -Filter "ProcessId=$old"
if(-not $proc -or $proc.CommandLine -notmatch 'n8n'){throw "5678 savininkas nera n8n: PID=$old"}
$children=Get-CimInstance Win32_Process|Where-Object {$_.ParentProcessId -eq $old}
Copy-Item -LiteralPath $pidsFile -Destination (Join-Path $runtime "pids.json.bak2-$stamp") -Force
Write-Output ('STOP tikras n8n PID='+$old)
Stop-Process -Id $old -Force
for($i=0;$i -lt 20;$i++){Start-Sleep -Milliseconds 500;if(-not (Get-NetTCPConnection -LocalPort 5678 -State Listen -ErrorAction SilentlyContinue)){break}}
foreach($child in $children){Stop-Process -Id $child.ProcessId -Force -ErrorAction SilentlyContinue}
foreach($line in Get-Content -LiteralPath (Join-Path $root '.env') -Encoding UTF8){
 if($line -match '^\s*([A-Z0-9_]+)\s*=\s*(.*)$'){[Environment]::SetEnvironmentVariable($Matches[1],$Matches[2].Trim().Trim('"').Trim("'"),'Process')}
}
$env:N8N_USER_FOLDER=$n8nData;$env:N8N_BLOCK_ENV_ACCESS_IN_NODE='false';$env:N8N_RUNNERS_MODE='internal'
$env:N8N_LISTEN_ADDRESS='127.0.0.1';$env:N8N_HOST='localhost';$env:N8N_PORT='5678';$env:N8N_PROTOCOL='http';$env:WEBHOOK_URL='http://localhost:5678/'
$env:GENERIC_TIMEZONE='Europe/Vilnius';$env:EXECUTIONS_TIMEOUT='3600';$env:EXECUTIONS_TIMEOUT_MAX='7200';$env:N8N_DIAGNOSTICS_ENABLED='false'
$out=Join-Path $logs "n8n-cline-restart2-$stamp.out.log";$err=Join-Path $logs "n8n-cline-restart2-$stamp.err.log"
$new=Start-Process -FilePath $node -ArgumentList @("`"$n8nBin`"",'start') -WorkingDirectory $root -WindowStyle Hidden -RedirectStandardOutput $out -RedirectStandardError $err -PassThru
$ok=$false
for($i=0;$i -lt 60;$i++){
 Start-Sleep -Seconds 2
 if($new.HasExited){break}
 $owner=Get-NetTCPConnection -LocalPort 5678 -State Listen -ErrorAction SilentlyContinue|Select-Object -First 1
 if($owner -and [int]$owner.OwningProcess -eq $new.Id){try{$r=Invoke-WebRequest 'http://127.0.0.1:5678/healthz' -UseBasicParsing -TimeoutSec 3;if($r.StatusCode -eq 200){$ok=$true;break}}catch{}}
}
if(-not $ok){Write-Output ('N8N_START_FAILED newPID='+$new.Id+' exited='+$new.HasExited);if(Test-Path $out){Get-Content $out -Tail 20};if(Test-Path $err){Get-Content $err -Tail 20};exit 1}
$pids=Get-Content -LiteralPath $pidsFile -Raw|ConvertFrom-Json
$pids|Add-Member -NotePropertyName n8n -NotePropertyValue $new.Id -Force
$pids|ConvertTo-Json|Set-Content -LiteralPath $pidsFile -Encoding Ascii
Write-Output ('N8N_OK NEW_PID='+$new.Id+' LOG='+$out)
Get-Content -LiteralPath $pidsFile -Raw
