Write-Output '===== CLINE GRAFIKU VARDAI ====='
Get-ScheduledTask | Where-Object { $_.TaskName -like 'CLINE*' } | ForEach-Object { $i=$_|Get-ScheduledTaskInfo; Write-Output ($_.TaskName+'|'+$_.State+'|Result='+$i.LastTaskResult+'|Last='+$i.LastRunTime) }
Write-Output '===== TIKSLUS SVEIKATOS ADRESAI ====='
foreach($item in @(@('Kumstis','http://127.0.0.1:8090/health'),@('Zveris','http://127.0.0.1:8091/health'),@('Bridge','http://127.0.0.1:18765/health'),@('BridgeState','http://127.0.0.1:18765/state'))){
 try{$r=Invoke-WebRequest -Uri $item[1] -UseBasicParsing -TimeoutSec 6;$body=$r.Content;if($body.Length -gt 500){$body=$body.Substring(0,500)};Write-Output ($item[0]+'|'+$r.StatusCode+'|'+$body)}catch{$resp=$_.Exception.Response;if($resp){$reader=New-Object IO.StreamReader($resp.GetResponseStream());$body=$reader.ReadToEnd();if($body.Length -gt 700){$body=$body.Substring(0,700)};Write-Output ($item[0]+'|KLAIDA|'+$body)}else{Write-Output ($item[0]+'|KLAIDA|'+$_.Exception.Message)}}
}
Write-Output '===== ZVERIS PROCESAS IR LOGAI ====='
Get-CimInstance Win32_Process | Where-Object {$_.CommandLine -match 'ui_app:app'} | Select-Object ProcessId,Name,CommandLine | Format-List
Get-ChildItem -LiteralPath 'C:\Users\M\Desktop\pakeitimai 111\_zveris_watch' -File -ErrorAction SilentlyContinue | Where-Object {$_.Name -match 'log|out|err'} | Sort-Object LastWriteTime -Descending | Select-Object -First 5 FullName,Length,LastWriteTime | Format-Table -AutoSize
Write-Output '===== DARBALAUKIO CLINE/AUSYS/AKYS ====='
Get-ChildItem -LiteralPath 'C:\Users\M\Desktop' -File | Where-Object {$_.Name -match '^(CLINE|AUSYS|AKYS)'} | Select-Object Name,Length,LastWriteTime | Format-Table -AutoSize
