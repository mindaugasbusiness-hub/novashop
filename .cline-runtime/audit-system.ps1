$ErrorActionPreference = 'Continue'
Write-Output '===== KONTEKSTO SARGAS ====='
& 'C:\Users\M\AppData\Local\Programs\Python\Python312\python.exe' 'C:\Users\M\CLINE\tools\konteksto-sargas.py' check 2>&1 | Out-String -Width 1000
Write-Output '===== HTTP SERVISAI ====='
$urls = @(
 @('n8n','http://127.0.0.1:5678/healthz'), @('Qdrant','http://127.0.0.1:6333/'),
 @('Kumstis8090','http://127.0.0.1:8090/'), @('Zveris8091','http://127.0.0.1:8091/'),
 @('Browser8099','http://127.0.0.1:8099/health'), @('F6_8766','http://127.0.0.1:8766/'),
 @('Pultas8790','http://127.0.0.1:8790/'), @('Ausys8795','http://127.0.0.1:8795/health'),
 @('CDP9222','http://127.0.0.1:9222/json/version'), @('Bridge18765','http://127.0.0.1:18765/'),
 @('Svetaine','https://penktadienioaukcionas.lt/')
)
foreach ($item in $urls) {
 try { $r=Invoke-WebRequest -Uri $item[1] -UseBasicParsing -TimeoutSec 6; Write-Output ($item[0]+'|HTTP '+$r.StatusCode+'|bytes='+$r.RawContentLength) }
 catch { Write-Output ($item[0]+'|KLAIDA|'+$_.Exception.Message) }
}
Write-Output '===== TCP 5679 ====='
$t=Test-NetConnection -ComputerName 127.0.0.1 -Port 5679 -WarningAction SilentlyContinue
Write-Output ('broker5679|'+$t.TcpTestSucceeded)
Write-Output '===== CDP PROCESAS ====='
Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'chrome.exe' -and $_.CommandLine -match 'chrome_agent' -and $_.CommandLine -match 'remote-debugging-port=9222' } | Select-Object -First 1 ProcessId,CommandLine | Format-List
Write-Output '===== GRAFIKAI ====='
$names=@('CLINE Būdėjimas','CLINE VISKAS kas 5 min','CLINE VISKAS pries isjungima','CLINE AutoBackup','CLINE VPS kopijos','CLINE HealthCheck','CLINE Perkelimas','CLINE PreFlight')
foreach($name in $names){
 $task=Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
 if($task){$info=$task|Get-ScheduledTaskInfo; $tr=($task.Triggers|ForEach-Object{$_.CimClass.CimClassName}) -join ','; Write-Output ($name+'|State='+$task.State+'|Result='+$info.LastTaskResult+'|Last='+$info.LastRunTime+'|Next='+$info.NextRunTime+'|Trigger='+$tr)}else{Write-Output ($name+'|NERA')}
}
Write-Output '===== STARTUOLIO NUORODOS ====='
$startup=[Environment]::GetFolderPath('Startup')
$shell=New-Object -ComObject WScript.Shell
foreach($name in @('CLINE-AUTOCONNECT2.lnk','CLINE-VISKAS.lnk','CLINE-AUSYS.lnk','CLINE-N8N.lnk','CLINE-BROWSER.lnk','CLINE-PULTAS.lnk')){
 $path=Join-Path $startup $name
 if(Test-Path -LiteralPath $path){$s=$shell.CreateShortcut($path);Write-Output ($name+'|YRA|'+$s.TargetPath+'|'+$s.Arguments)}else{Write-Output ($name+'|NERA')}
}
