$ErrorActionPreference='Continue'
$file='C:\Users\M\Desktop\Kumstis\n8n-prisijungimas.txt'
$email=$null;$password=$null
foreach($line in Get-Content -LiteralPath $file -Encoding UTF8){
 if($line -match '^\s*El\. pastas\s*[=:]\s*(.+)$'){$email=$Matches[1].Trim()}
 elseif($line -match '^\s*Slaptazodis\s*[=:]\s*(.+)$'){$password=$Matches[1].Trim()}
}
if(-not $email -or -not $password){Write-Output 'LOGIN_CREDENTIALS=NERASTA';exit 1}
$body=@{emailOrLdapLoginId=$email;password=$password}|ConvertTo-Json -Compress
$headers=$body | & curl.exe -sS --max-time 12 -D - -o NUL -H 'Content-Type: application/json' --data-binary '@-' 'http://127.0.0.1:5678/rest/login' 2>&1 | Out-String
$statusLine=($headers -split "`r?`n" | Select-Object -First 1)
Write-Output ('LOGIN_STATUS='+$statusLine)
if($statusLine -notmatch '\s200\s'){exit 1}
$cookies=@()
foreach($line in ($headers -split "`r?`n")){if($line -match '^set-cookie:\s*([^;]+)'){$cookies+=$Matches[1].Trim()}}
if(-not $cookies.Count){Write-Output 'COOKIE=NERA';exit 1}
$cookieHeader=$cookies -join '; '
Write-Output ('COOKIE_COUNT='+$cookies.Count)
$wfText=& curl.exe -sS --max-time 12 -H "Cookie: $cookieHeader" 'http://127.0.0.1:5678/rest/workflows' 2>&1 | Out-String
try{$json=$wfText|ConvertFrom-Json}catch{Write-Output ('WF_JSON_KLAIDA='+$_.Exception.Message);exit 1}
$list=if($json.data){$json.data}else{$json}
foreach($w in $list){Write-Output ('WF '+$w.id+' | '+$w.name+' | active='+$w.active+' | versionId='+$w.versionId)}
$target=$list|Where-Object {$_.id -eq 'clineAuto0000001'}|Select-Object -First 1
if($target){
 $detail=& curl.exe -sS --max-time 12 -H "Cookie: $cookieHeader" 'http://127.0.0.1:5678/rest/workflows/clineAuto0000001' 2>&1 | Out-String
 try{$d=$detail|ConvertFrom-Json;if($d.data){$d=$d.data};Write-Output ('TARGET_DETAIL active='+$d.active+' versionId='+$d.versionId+' checksum='+$d.checksum+' updatedAt='+$d.updatedAt)}catch{Write-Output 'TARGET_DETAIL_PARSE=KLAIDA'}
}else{Write-Output 'TARGET=NERA'}
