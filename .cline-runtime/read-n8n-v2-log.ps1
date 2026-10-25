$f=(Get-ChildItem -LiteralPath 'C:\Users\M\Desktop\Kumstis\runtime\logs' -File -Filter 'n8n-v2-*.out.log'|Sort-Object LastWriteTime -Descending|Select-Object -First 1).FullName
Select-String -LiteralPath $f -Pattern 'Published version|cannot run|Unrecognized|error|Error|Editor is now accessible|Building workflow' -Context 0,2 | Format-List
