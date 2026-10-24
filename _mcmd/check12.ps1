$ErrorActionPreference = 'Continue'
$n8n = 'C:\Users\M\Desktop\Kumstis\runtime\n8n\node_modules\n8n'
'=== n8n paketo struktura ==='
Get-ChildItem $n8n -Force -ErrorAction SilentlyContinue | Select-Object Name | Format-Table -AutoSize | Out-String
'=== ExecuteCommand mazgo kodas ==='
'ExecuteCommand dir: ' + (Test-Path 'C:\Users\M\Desktop\Kumstis\runtime\n8n\node_modules\n8n-nodes-base\dist\nodes\ExecuteCommand')
Get-ChildItem 'C:\Users\M\Desktop\Kumstis\runtime\n8n\node_modules\n8n-nodes-base\dist\nodes' -ErrorAction SilentlyContinue -Filter '*Command*' | Select-Object Name | Out-String
'=== NODES_EXCLUDE paieska (dist) ==='
$hits = Get-ChildItem "$n8n\dist" -Recurse -Filter '*.js' -ErrorAction SilentlyContinue |
  Select-String -Pattern 'NODES_EXCLUDE' -List -ErrorAction SilentlyContinue | Select-Object -First 4
foreach ($h in $hits) { 'FAILAS: ' + $h.Path; 'EILUTE: ' + $h.Line.Trim().Substring(0, [Math]::Min(300, $h.Line.Trim().Length)) }
'=== default exclude reiksme ==='
Get-ChildItem "$n8n\dist" -Recurse -Filter '*.js' -ErrorAction SilentlyContinue |
  Select-String -Pattern 'n8n-nodes-base.executeCommand' -List -ErrorAction SilentlyContinue | Select-Object -First 4 | ForEach-Object { 'FAILAS: ' + $_.Path + ' || ' + $_.Line.Trim().Substring(0,[Math]::Min(200,$_.Line.Trim().Length)) }
