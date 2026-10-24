$ErrorActionPreference = 'Continue'
$base = 'http://127.0.0.1:5678'
$txt = Get-Content 'C:\Users\M\Desktop\Kumstis\n8n-prisijungimas.txt' -Encoding UTF8
$email = ($txt | Where-Object { $_ -match 'pastas' } | Select-Object -First 1).Split(':')[1].Trim()
$pass  = ($txt | Where-Object { $_ -match 'Slaptazodis' } | Select-Object -First 1).Split(':')[1].Trim()
Invoke-WebRequest -Uri "$base/rest/login" -Method POST -ContentType 'application/json' `
  -Body (@{ emailOrLdapLoginId = $email; password = $pass } | ConvertTo-Json) -SessionVariable sess -UseBasicParsing -TimeoutSec 20 | Out-Null
'login ok, cookie: ' + ($sess.Cookies.Count)
$paths = @('/rest/settings','/rest/workflows','/rest/active-workflows','/rest/node-types','/types/nodes.json','/rest/me','/rest/projects')
foreach ($p in $paths) {
  try {
    $r = Invoke-WebRequest -Uri ($base + $p) -WebSession $sess -UseBasicParsing -TimeoutSec 25
    "$p -> " + $r.StatusCode + ' | ' + $r.Content.Length + ' B | ' + $r.Content.Substring(0, [Math]::Min(100, $r.Content.Length)).Replace("`n", ' ')
  } catch {
    "$p -> KLAIDA " + $(if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { $_.Exception.Message })
  }
}
'=== node-types paieska ==='
try {
  $nt = Invoke-RestMethod -Uri "$base/rest/node-types" -WebSession $sess -TimeoutSec 30
  'kiekis: ' + $nt.data.Count
} catch {
  'node-types KLAIDA: ' + $(if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { $_.Exception.Message })
  try {
    $j = Invoke-RestMethod -Uri "$base/types/nodes.json" -WebSession $sess -TimeoutSec 30
    $arr = if ($j -is [array]) { $j } else { $j.data }
    'nodes.json kiekis: ' + $arr.Count
    $arr | Where-Object { $_.name -match 'executeCommand|scheduleTrigger|httpRequest' } | ForEach-Object { 'RASTA: ' + $_.name }
  } catch { 'nodes.json KLAIDA: ' + $_.Exception.Message }
}
