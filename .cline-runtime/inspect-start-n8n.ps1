$node='C:\Users\M\Desktop\Kumstis\runtime\node24\node.exe'
$n8n='C:\Users\M\Desktop\Kumstis\runtime\n8n\node_modules\n8n\bin\n8n'
Write-Output '===== START-NATIVE PRADZIA ====='
Get-Content -LiteralPath 'C:\Users\M\Desktop\Kumstis\start-native.ps1' -Encoding UTF8 -TotalCount 120
Write-Output '===== IMPORT HELP ====='
$env:N8N_USER_FOLDER='C:\Users\M\Desktop\Kumstis\runtime\n8n-data\.n8n'
& $node $n8n import:workflow --help 2>&1 | Out-String -Width 2000
Write-Output '===== PUBLISH HELP ====='
& $node $n8n publish:workflow --help 2>&1 | Out-String -Width 2000
Write-Output '===== N8N ENV FAILAI ====='
Get-ChildItem -LiteralPath 'C:\Users\M\Desktop\Kumstis' -Force -File | Where-Object {$_.Name -match '^\.env|n8n'} | Select-Object Name,Length,LastWriteTime | Format-Table -AutoSize
