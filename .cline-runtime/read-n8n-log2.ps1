$log=(Get-ChildItem -LiteralPath 'C:\Users\M\Desktop\Kumstis\runtime\logs' -File -Filter 'n8n-cline-restart2-*.out.log'|Sort-Object LastWriteTime -Descending|Select-Object -First 1).FullName
Write-Output ('LOG='+$log+' SIZE='+(Get-Item -LiteralPath $log).Length)
Select-String -LiteralPath $log -Pattern 'Active workflow|Activated|Deactivated|clineAuto|Editor is now accessible|ready|error|Error' -Context 1,2 | Select-Object -Last 25 | Format-List
