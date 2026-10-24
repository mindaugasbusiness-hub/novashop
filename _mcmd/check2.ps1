$ErrorActionPreference = 'Continue'
'=== n8n-prisijungimas.txt ==='
Get-Content 'C:\Users\M\Desktop\Kumstis\n8n-prisijungimas.txt' -ErrorAction SilentlyContinue
'=== .env (maska) ==='
Get-Content 'C:\Users\M\Desktop\Kumstis\.env' -ErrorAction SilentlyContinue | ForEach-Object { if ($_ -match '=') { $p=$_.Split('=',2); $p[0] + ' = [len ' + $p[1].Length + ']' } else { $_ } }
'=== .clinerules ==='
Get-Content 'C:\Users\M\Desktop\Kumstis\.clinerules' -ErrorAction SilentlyContinue
'=== RUNTIME ==='
Get-ChildItem 'C:\Users\M\Desktop\Kumstis\runtime' -Force -ErrorAction SilentlyContinue | Select-Object Name,LastWriteTime | Format-Table -AutoSize | Out-String
'=== N8N CLI ==='
$cli = 'C:\Users\M\Desktop\Kumstis\runtime\n8n\node_modules\n8n\bin\n8n'
'N8N bin yra: ' + (Test-Path $cli)
$node = 'C:\Users\M\Desktop\Kumstis\runtime\node24\node.exe'
'node24 yra: ' + (Test-Path $node)
'=== PRANESTI TOOL ==='
'pranesti.ps1: ' + (Test-Path 'C:\Users\M\CLINE\tools\pranesti.ps1')
Get-ChildItem 'C:\Users\M\CLINE\tools' -ErrorAction SilentlyContinue | Select-Object @{n='KB';e={[math]::Round($_.Length/1KB,1)}},LastWriteTime,Name | Format-Table -AutoSize | Out-String
'=== LOG ==='
Get-ChildItem 'C:\Users\M\CLINE' -Filter '*PRANESIM*' -Recurse -Depth 2 -ErrorAction SilentlyContinue | Select-Object FullName,@{n='KB';e={[math]::Round($_.Length/1KB,1)}},LastWriteTime | Format-Table -AutoSize | Out-String
