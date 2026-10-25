$ErrorActionPreference='Stop'
$root='C:\Users\M\Desktop\Kumstis'
$runtime=Join-Path $root 'runtime'
$n8nData=Join-Path $runtime 'n8n-data'
$pidsFile=Join-Path $runtime 'pids.json'
$node=Join-Path $runtime 'node24\node.exe'
$n8nBin=Join-Path $runtime 'n8n\node_modules\n8n\bin\n8n'
$logs=Join-Path $runtime 'logs'
$stamp=Get-Date -Format 'yyyyMMdd_HHmmss'
Set-Location $root
$pids=[pscustomobject]@{}
if(Test-Path -LiteralPath $pidsFile){$pids=Get-Content -LiteralPath $pidsFile -Raw | ConvertFrom-Json}
$old=[int]($pids.n8n)
if(-not $old){$found=Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'node.exe' -and $_.CommandLine -match 'n8n\\bin\\n8n"?\s+start'} | Select-Object -First 1;if($found){$old=[int]$found.ProcessId}}
if($old -gt 0){
 $children=Get-CimInstance Win32_Process | Where-Object {$_.ParentProcessId -eq $old}
 Copy-Item -LiteralPath $pidsFile -Destination (Join-Path $runtime "pids.json.bak-$stamp") -Force
 Write-Output ('STOP n8n PID='+$old)
 Stop-Process -Id $old -Force -ErrorAction SilentlyContinue
 Start-Sleep -Seconds 4
 foreach($child in $children){Stop-Process -Id $child.ProcessId -Force -ErrorAction SilentlyContinue}
}
foreach($line in Get-Content -LiteralPath (Join-Path $root '.env') -Encoding UTF8){
 if($line -match '^\s*([A-Z0-9_]+)\s*=\s*(.*)$'){[Environment]::SetEnvironmentVariable($Matches[1],$Matches[2].Trim().Trim('"').Trim("'"),'Process')}
}
$env:N8N_USER_FOLDER=$n8nData
$env:N8N_BLOCK_ENV_ACCESS_IN_NODE='false'
$env:N8N_RUNNERS_MODE='internal'
$env:N8N_LISTEN_ADDRESS='127.0.0.1'
$env:N8N_HOST='localhost'
$env:N8N_PORT='5678'
$env:N8N_PROTOCOL='http'
$env:WEBHOOK_URL='http://localhost:5678/'
$env:GENERIC_TIMEZONE='Europe/Vilnius'
$env:EXECUTIONS_TIMEOUT='3600'
$env:EXECUTIONS_TIMEOUT_MAX='7200'
$env:N8N_DIAGNOSTICS_ENABLED='false'
$out=Join-Path $logs "n8n-cline-restart-$stamp.out.log"
$err=Join-Path $logs "n8n-cline-restart-$stamp.err.log"
$proc=Start-Process -FilePath $node -ArgumentList @("`"$n8nBin`"",'start') -WorkingDirectory $root -WindowStyle Hidden -RedirectStandardOutput $out -RedirectStandardError $err -PassThru
$pids | Add-Member -NotePropertyName n8n -NotePropertyValue $proc.Id -Force
$pids | ConvertTo-Json | Set-Content -LiteralPath $pidsFile -Encoding Ascii
for($i=0;$i -lt 60;$i++){
 Start-Sleep -Seconds 2
 try{$r=Invoke-WebRequest -Uri 'http://127.0.0.1:5678/healthz' -UseBasicParsing -TimeoutSec 3;if($r.StatusCode -eq 200){Write-Output ('N8N_OK PID='+$proc.Id);break}}catch{}
}
Write-Output '===== DB BUSENA ====='
Write-Output ('DB='+$n8nData+'\database.sqlite')
