$ErrorActionPreference='Stop'
$root='C:\Users\M\Desktop\Kumstis'
Set-Location $root
foreach($line in Get-Content -LiteralPath (Join-Path $root '.env') -Encoding UTF8){
 if($line -match '^\s*([A-Z0-9_]+)\s*=\s*(.*)$'){[Environment]::SetEnvironmentVariable($Matches[1],$Matches[2].Trim().Trim('"').Trim("'"),'Process')}
}
$env:N8N_USER_FOLDER='C:\Users\M\Desktop\Kumstis\runtime\n8n-data'
$env:N8N_RUNNERS_MODE='internal'
$env:N8N_BLOCK_ENV_ACCESS_IN_NODE='false'
$node='C:\Users\M\Desktop\Kumstis\runtime\node24\node.exe'
$n8n='C:\Users\M\Desktop\Kumstis\runtime\n8n\node_modules\n8n\bin\n8n'
& $node $n8n execute --id=clineAuto0000001 2>&1 | Out-String -Width 3000
Write-Output ('EXECUTE_EXIT='+$LASTEXITCODE)
Set-Location 'C:\Users\M\CLINE'
