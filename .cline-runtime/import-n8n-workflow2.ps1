$ErrorActionPreference='Stop'
$wf='C:\Users\M\CLINE\tools\cline-auto-workflow.json'
Set-Location 'C:\Users\M\Desktop\Kumstis'
$env:N8N_USER_FOLDER='C:\Users\M\Desktop\Kumstis\runtime\n8n-data'
$node='C:\Users\M\Desktop\Kumstis\runtime\node24\node.exe'
$n8n='C:\Users\M\Desktop\Kumstis\runtime\n8n\node_modules\n8n\bin\n8n'
Write-Output '===== IMPORT ====='
& $node $n8n import:workflow --input=$wf 2>&1 | Out-String -Width 3000
Write-Output ('IMPORT_EXIT=' + $LASTEXITCODE)
Write-Output '===== PUBLISH ====='
& $node $n8n publish:workflow --id=clineAuto0000001 2>&1 | Out-String -Width 3000
Write-Output ('PUBLISH_EXIT=' + $LASTEXITCODE)
Set-Location 'C:\Users\M\CLINE'
