$ErrorActionPreference = 'Continue'
$base = 'http://127.0.0.1:5678'
$txt = Get-Content 'C:\Users\M\Desktop\Kumstis\n8n-prisijungimas.txt' -Encoding UTF8
$email = ($txt | Where-Object { $_ -match 'pastas' } | Select-Object -First 1).Split(':')[1].Trim()
$pass  = ($txt | Where-Object { $_ -match 'Slaptazodis' } | Select-Object -First 1).Split(':')[1].Trim()
$r = Invoke-WebRequest -Uri "$base/rest/login" -Method POST -ContentType 'application/json' `
  -Body (@{ emailOrLdapLoginId = $email; password = $pass } | ConvertTo-Json) -SessionVariable sess -UseBasicParsing -TimeoutSec 20
'login kodas: ' + $r.StatusCode
'Set-Cookie headers:'
$r.Headers['Set-Cookie'] | ForEach-Object { ($_ -split ';')[0] }
'cookies objekte: ' + $sess.Cookies.Count
$sess.Cookies.GetCookies($base) | ForEach-Object { 'COOKIE: ' + $_.Name + ' path=' + $_.Path + ' domain=' + $_.Domain }
$ck = ($sess.Cookies.GetCookies($base) | ForEach-Object { $_.Name + '=' + $_.Value }) -join '; '
'bandymas su Cookie header:'
try { $x = Invoke-WebRequest -Uri "$base/rest/workflows" -Headers @{ Cookie = $ck; 'browser-id' = 'clineagent0000000000000000000000' } -UseBasicParsing -TimeoutSec 20; 'kodas: ' + $x.StatusCode + ' len=' + $x.Content.Length } catch { 'klaida: ' + $(if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { $_.Exception.Message }) }
