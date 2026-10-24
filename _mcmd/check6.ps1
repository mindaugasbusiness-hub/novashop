$ErrorActionPreference = 'Continue'
$root = 'C:\Users\M\Desktop\Kumstis'
$env:N8N_USER_FOLDER = 'C:\Users\M\Desktop\Kumstis\runtime\n8n-data'
$node = 'C:\Users\M\Desktop\Kumstis\runtime\node24\node.exe'
$bin  = 'C:\Users\M\Desktop\Kumstis\runtime\n8n\node_modules\n8n\bin\n8n'
'=== n8n list:workflow ==='
& $node $bin list:workflow 2>&1 | Out-String
'=== REST API be rakto ==='
try { $r = Invoke-WebRequest -Uri 'http://127.0.0.1:5678/api/v1/workflows' -TimeoutSec 10 -UseBasicParsing; 'Kodas: ' + $r.StatusCode + ' body: ' + $r.Content.Substring(0,[Math]::Min(200,$r.Content.Length)) } catch { 'Klaida: ' + $_.Exception.Message }
'=== api_keys DB ==='
$db = 'C:\Users\M\Desktop\Kumstis\runtime\n8n-data\.n8n\database.sqlite'
'DB: ' + (Test-Path $db)
'=== n8n log failai ==='
Get-ChildItem 'C:\Users\M\Desktop\Kumstis\runtime\logs' -ErrorAction SilentlyContinue | Select-Object Name,@{n='KB';e={[math]::Round($_.Length/1KB,1)}},LastWriteTime | Format-Table -AutoSize | Out-String
