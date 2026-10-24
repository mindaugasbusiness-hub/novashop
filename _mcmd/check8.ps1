$ErrorActionPreference = 'Continue'
$base = 'http://127.0.0.1:5678'
$txt = Get-Content 'C:\Users\M\Desktop\Kumstis\n8n-prisijungimas.txt' -Encoding UTF8
$email = ($txt | Where-Object { $_ -match 'pastas' } | Select-Object -First 1).Split(':')[1].Trim()
$pass  = ($txt | Where-Object { $_ -match 'Slaptazodis' } | Select-Object -First 1).Split(':')[1].Trim()
'email nuskaitytas: ' + ($email.Length -gt 0) + ' | pass ilgis: ' + $pass.Length
try {
  $login = Invoke-WebRequest -Uri "$base/rest/login" -Method POST -ContentType 'application/json' `
    -Body (@{ emailOrLdapLoginId = $email; password = $pass } | ConvertTo-Json) -SessionVariable sess -UseBasicParsing -TimeoutSec 20
  'LOGIN kodas: ' + $login.StatusCode
  $sess | Export-Clixml 'C:\Users\M\CLINE\tools\_n8n_sess.xml'
  $nt = Invoke-RestMethod -Uri "$base/rest/node-types" -WebSession $sess -TimeoutSec 30
  'node-types kiekis: ' + $nt.data.Count
  $exec = $nt.data | Where-Object { $_.name -eq 'n8n-nodes-base.executeCommand' }
  'executeCommand YRA: ' + [bool]$exec
  if ($exec) { 'executeCommand hidden: ' + $exec.hidden }
  foreach ($n in @('n8n-nodes-base.scheduleTrigger','n8n-nodes-base.httpRequest','n8n-nodes-base.if','n8n-nodes-base.set','n8n-nodes-base.code','n8n-nodes-base.manualTrigger')) {
    $f = $nt.data | Where-Object { $_.name -eq $n }
    $n + ' -> ' + [bool]$f
  }
  $wf = Invoke-RestMethod -Uri "$base/rest/workflows" -WebSession $sess -TimeoutSec 30
  '=== WORKFLOWS per REST ==='
  foreach ($w in $wf.data) { $w.id + ' | ' + $w.name + ' | active=' + $w.active + ' | nodes=' + $w.nodes.Count }
} catch {
  'KLAIDA: ' + $_.Exception.Message
  if ($_.Exception.Response) { 'HTTP: ' + [int]$_.Exception.Response.StatusCode }
}
