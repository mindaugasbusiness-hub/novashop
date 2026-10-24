$ErrorActionPreference = 'Continue'
$root = 'C:\Users\M\Desktop\Kumstis'
'=== n8n.out.log ==='
Get-Content (Join-Path $root 'runtime\logs\n8n.out.log') -Encoding UTF8 -ErrorAction SilentlyContinue | Select-Object -Last 10
'=== n8n.err.log ==='
Get-Content (Join-Path $root 'runtime\logs\n8n.err.log') -Encoding UTF8 -ErrorAction SilentlyContinue | Select-Object -Last 10
'=== start-out.log (paskutines 12) ==='
Get-Content (Join-Path $root 'runtime\logs\start-out.log') -Encoding UTF8 -ErrorAction SilentlyContinue | Select-Object -Last 12
'=== n8n --help komandos ==='
$env:N8N_USER_FOLDER = Join-Path $root 'runtime\n8n-data'
& (Join-Path $root 'runtime\node24\node.exe') (Join-Path $root 'runtime\n8n\node_modules\n8n\bin\n8n') '--help' 2>&1 | Out-String
