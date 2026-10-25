$ErrorActionPreference='Stop'
$file='C:\Users\M\Desktop\Kumstis\n8n-prisijungimas.txt'
$email=$null;$password=$null
foreach($line in Get-Content -LiteralPath $file -Encoding UTF8){
 if($line -match '^\s*El\. pastas\s*[=:]\s*(.+)$'){$email=$Matches[1].Trim()}
 elseif($line -match '^\s*Slaptazodis\s*[=:]\s*(.+)$'){$password=$Matches[1].Trim()}
}
if(-not $email -or -not $password){throw 'Nepavyko nuskaityti n8n prisijungimo'}
$session=New-Object Microsoft.PowerShell.Commands.WebRequestSession
$body=@{emailOrLdapLoginId=$email;password=$password}|ConvertTo-Json -Compress
try{
 $login=Invoke-WebRequest -Uri 'http://127.0.0.1:5678/rest/login' -Method Post -Body $body -ContentType 'application/json' -WebSession $session -UseBasicParsing -TimeoutSec 15
 Write-Output ('LOGIN_HTTP='+$login.StatusCode)
}catch{
 $status=if($_.Exception.Response){[int]$_.Exception.Response.StatusCode}else{0}
 Write-Output ('LOGIN_HTTP='+$status+' KLAIDA='+$_.Exception.Message)
 exit 1
}
try{
 $wf=Invoke-WebRequest -Uri 'http://127.0.0.1:5678/rest/workflows' -WebSession $session -UseBasicParsing -TimeoutSec 15
 Write-Output ('WORKFLOWS_HTTP='+$wf.StatusCode+' BYTES='+$wf.Content.Length)
 $json=$wf.Content|ConvertFrom-Json
 $list=if($json.data){$json.data}else{$json}
 $list|ForEach-Object{Write-Output ('WF '+$_.id+' | '+$_.name+' | active='+$_.active)}
}catch{Write-Output ('WORKFLOWS_KLAIDA='+$_.Exception.Message);exit 1}
# issaugome tik sesijos slapuka, kad sekantis zingsnis galetu aktyvuoti
$session.Cookies.GetCookies('http://127.0.0.1:5678')|ForEach-Object{Write-Output ('COOKIE_OK '+$_.Name+' len='+$_.Value.Length)}
