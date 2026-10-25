$log=Get-ChildItem -LiteralPath 'C:\Users\M\Desktop\Kumstis\runtime\logs' -File -Filter 'n8n-cline-restart-*.out.log' | Sort-Object LastWriteTime -Descending | Select-Object -First 1
Write-Output ('LOG='+$log.FullName)
Select-String -LiteralPath $log.FullName -Pattern 'Active workflow|Activated|Deactivated|clineAuto|error|Error|ERROR|Editor is now accessible|n8n ready' -Context 1,2 | Select-Object -Last 20 | Format-List
Write-Output '===== KEEPALIVE / ERROR LOG ====='
$err=[IO.Path]::ChangeExtension($log.FullName,'.err.log')
if(Test-Path -LiteralPath $err){Get-Content -LiteralPath $err -Encoding UTF8 -Tail 60}
Write-Output '===== DABARTINIS LAIKAS ====='
Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
